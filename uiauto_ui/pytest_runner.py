# uiauto_ui/pytest_runner.py
"""
pytest-based test runner for cita-uiauto-engine scenarios.

Provides:
- ``run_scenario_with_allure``: helper called by generated test files to execute
  a single YAML scenario with per-step allure reporting.
- ``generate_pytest_files``: creates temporary pytest test files from YAML
  scenario(s) ready for pytest discovery.
- ``PytestExecutor``: QThread-based executor that runs scenarios via pytest +
  allure-pytest, streams live output, and produces an Allure HTML report.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject

from .cli_executor import BaseExecutor
from .utils.logging import get_logger
from .utils.platform import get_python_executable, get_startupinfo, get_subprocess_env

logger = get_logger(__name__)

# Prefix emitted on the output line that carries the Allure report URL.
# OutputViewer detects this prefix to render a clickable link.
ALLURE_REPORT_PREFIX = "[ALLURE REPORT]"


# ---------------------------------------------------------------------------
# Core helper – called from generated test files
# ---------------------------------------------------------------------------


def run_scenario_with_allure(
    elements_path: str,
    scenario_path: str,
    schema_path: str,
    timing_preset: str = "default",
    variables: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Run a single YAML scenario as a pytest test with per-step allure reporting.

    This function is imported and called by the auto-generated test files.
    It replicates the internals of ``Runner.run()`` while wrapping every step
    in an ``allure.step()`` context and printing live PASSED/FAILED lines.

    Args:
        elements_path: Absolute path to elements.yaml.
        scenario_path: Absolute path to the scenario YAML file.
        schema_path: Absolute path to the JSON schema file.
        timing_preset: Timing preset name (``"default"``, ``"ci"``, etc.).
        variables: Optional CLI/runtime variable overrides.
    """
    import time as _time

    import allure

    from uiauto.actions import Actions
    from uiauto.config import TimeConfig
    from uiauto.context import ActionContextManager
    from uiauto.repository import Repository
    from uiauto.resolver import Resolver
    from uiauto.runner import Runner, _substitute
    from uiauto.session import Session

    variables = variables or {}

    repo = Repository(elements_path)
    runner = Runner(repo, schema_path)

    scenario_data = runner._load_yaml(scenario_path)
    runner.validate(scenario_data)

    # Merge variables: scenario-embedded vars take lower priority than CLI vars
    scenario_vars = scenario_data.get("vars", {}) or {}
    if isinstance(scenario_vars, dict):
        variables = {**scenario_vars, **variables}

    steps = scenario_data.get("steps", [])
    steps = _substitute(steps, variables)

    run_time_config = runner._build_time_config(preset=timing_preset, overrides={})
    TimeConfig.install_run_config(run_time_config)

    sess = Session(
        backend=repo.app.backend,
        default_timeout=repo.app.default_timeout,
        polling_interval=repo.app.polling_interval,
    )

    try:
        resolver = Resolver(sess, repo)
        actions = Actions(resolver)

        for idx, step in enumerate(steps, start=1):
            if not isinstance(step, dict) or len(step) != 1:
                raise ValueError(f"Invalid step format at index {idx}: {step}")

            keyword, args = next(iter(step.items()))
            args = args or {}
            if not isinstance(args, dict):
                raise ValueError(f"Step args must be a mapping at index {idx}")

            step_label = f"Step {idx}: {keyword}"
            if args:
                step_label += f" {args}"

            step_start = _time.time()
            with allure.step(step_label):
                try:
                    ActionContextManager.clear()
                    runner._execute(keyword, args, sess, actions)
                    duration = _time.time() - step_start
                    print(f"  \u2713 {step_label} \u2014 PASSED ({duration:.2f}s)")
                except Exception as e:
                    duration = _time.time() - step_start
                    print(f"  \u2717 {step_label} \u2014 FAILED ({duration:.2f}s)")
                    print(f"    {type(e).__name__}: {e}")
                    allure.attach(
                        str(e),
                        name="Error Details",
                        attachment_type=allure.attachment_type.TEXT,
                    )
                    raise
    finally:
        try:
            sess.close_main_windows(timeout=TimeConfig.current().window_close.timeout)
        except Exception:
            pass
        TimeConfig.clear_run_config()
        ActionContextManager.clear()


# ---------------------------------------------------------------------------
# Test file generation
# ---------------------------------------------------------------------------


def _sanitize_func_name(name: str) -> str:
    """Convert an arbitrary string to a valid pytest function name."""
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_") or "scenario"
    if sanitized[0].isdigit():
        sanitized = "s_" + sanitized
    if not sanitized.startswith("test_"):
        sanitized = "test_" + sanitized
    return sanitized


def _build_conftest(project_root: str) -> str:
    """Return conftest.py content that puts the project root on sys.path."""
    return (
        "# Auto-generated conftest.py\n"
        "import sys\n"
        "\n"
        f"_PROJECT_ROOT = {repr(project_root)}\n"
        "if _PROJECT_ROOT not in sys.path:\n"
        "    sys.path.insert(0, _PROJECT_ROOT)\n"
    )


def _build_test_file(
    elements_path: str,
    scenario_paths: List[str],
    schema_path: str,
    timing_preset: str,
    variables: Dict[str, Any],
) -> str:
    """Return complete test file source code for the given scenario(s)."""
    lines = [
        "# Auto-generated by cita-uiauto-engine pytest runner",
        "# Do not edit manually",
        "",
        "import json",
        "import allure",
        "import pytest",
        "from uiauto_ui.pytest_runner import run_scenario_with_allure",
        "",
    ]

    used_names: set = set()

    for scenario_path in scenario_paths:
        scenario_name = os.path.splitext(os.path.basename(scenario_path))[0]
        func_name = _sanitize_func_name(scenario_name)

        # Ensure uniqueness across scenarios in the same file
        base_name = func_name
        counter = 1
        while func_name in used_names:
            func_name = f"{base_name}_{counter}"
            counter += 1
        used_names.add(func_name)

        # Use json.dumps/json.loads for safe, portable serialisation of variables
        variables_json = json.dumps(variables)

        lines += [
            "",
            f'@allure.feature("UI Automation")',
            f"@allure.story({repr(scenario_name)})",
            f"@allure.title({repr(os.path.basename(scenario_path))})",
            f"def {func_name}():",
            f'    """Auto-generated test for scenario: {scenario_name}"""',
            f"    run_scenario_with_allure(",
            f"        elements_path={repr(elements_path)},",
            f"        scenario_path={repr(scenario_path)},",
            f"        schema_path={repr(schema_path)},",
            f"        timing_preset={repr(timing_preset)},",
            f"        variables=json.loads({repr(variables_json)}),",
            f"    )",
        ]

    return "\n".join(lines) + "\n"


def generate_pytest_files(
    elements_path: str,
    scenario_paths: List[str],
    schema_path: str,
    timing_preset: str = "default",
    variables: Optional[Dict[str, Any]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """
    Generate a pytest test file (and supporting conftest.py) from YAML scenarios.

    Args:
        elements_path: Absolute path to elements.yaml.
        scenario_paths: List of absolute paths to scenario YAML files.
        schema_path: Absolute path to the JSON schema file.
        timing_preset: Timing preset name.
        variables: Optional variable dict.
        output_dir: Directory for generated files; a temp dir is used if None.

    Returns:
        Path to the generated test file.
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="cita_pytest_")
    else:
        os.makedirs(output_dir, exist_ok=True)

    variables = variables or {}

    # Project root is two levels up from this file (uiauto_ui/pytest_runner.py)
    project_root = str(Path(__file__).parent.parent.resolve())

    conftest_path = os.path.join(output_dir, "conftest.py")
    with open(conftest_path, "w", encoding="utf-8") as f:
        f.write(_build_conftest(project_root))

    test_content = _build_test_file(
        elements_path=elements_path,
        scenario_paths=scenario_paths,
        schema_path=schema_path,
        timing_preset=timing_preset,
        variables=variables,
    )
    test_file_path = os.path.join(output_dir, "test_scenarios.py")
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(test_content)

    logger.debug(f"Generated pytest files in: {output_dir}")
    return test_file_path


# ---------------------------------------------------------------------------
# PytestExecutor – QThread-based executor
# ---------------------------------------------------------------------------


class PytestExecutor(BaseExecutor):
    """
    QThread executor that runs scenarios through pytest + allure-pytest.

    Lifecycle:
    1. Generates temporary pytest test files from YAML scenario(s).
    2. Runs ``python -m pytest <test_file> --alluredir=<results_dir> -v --tb=short -s``
       as a subprocess, streaming every line of output in real time.
    3. After pytest exits, attempts to run ``allure generate`` to produce an
       HTML report.
    4. Emits ``[ALLURE REPORT] file:///path/index.html`` so the GUI's
       OutputViewer can render it as a clickable link.
    """

    def __init__(
        self,
        elements_path: str,
        scenario_paths: List[str],
        schema_path: str,
        timing_preset: str = "default",
        variables: Optional[Dict[str, Any]] = None,
        allure_report_dir: Optional[str] = None,
        argv: Optional[List[str]] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(argv or ["run"], parent)
        self.elements_path = os.path.abspath(elements_path)
        self.scenario_paths = [os.path.abspath(p) for p in scenario_paths]
        self.schema_path = os.path.abspath(schema_path)
        self.timing_preset = timing_preset
        self.variables = variables or {}
        self.allure_report_dir = os.path.abspath(allure_report_dir or "allure-report")
        self._process: Optional[subprocess.Popen] = None
        self._temp_dir: Optional[str] = None

    @property
    def is_cancellable(self) -> bool:
        return True

    def request_stop(self) -> None:
        """Terminate the running pytest subprocess."""
        super().request_stop()
        if self._process is not None:
            try:
                logger.info("Terminating pytest subprocess…")
                self._process.terminate()
            except (OSError, ProcessLookupError) as exc:
                logger.warning(f"Could not terminate pytest process: {exc}")

    def _execute(self) -> int:
        """Run pytest with allure and return the pytest exit code."""
        try:
            return self._run_pytest_with_allure()
        finally:
            self._cleanup_temp_dir()

    def _run_pytest_with_allure(self) -> int:
        self._temp_dir = tempfile.mkdtemp(prefix="cita_pytest_")
        allure_results_dir = os.path.join(self._temp_dir, "allure-results")
        os.makedirs(allure_results_dir, exist_ok=True)

        scenario_names = ", ".join(
            os.path.basename(p) for p in self.scenario_paths
        )
        separator = "\u2550" * 55
        self._emit_output(separator)
        self._emit_output(f"\U0001f9ea pytest + allure: {scenario_names}")
        self._emit_output(separator)

        try:
            test_file = generate_pytest_files(
                elements_path=self.elements_path,
                scenario_paths=self.scenario_paths,
                schema_path=self.schema_path,
                timing_preset=self.timing_preset,
                variables=self.variables,
                output_dir=self._temp_dir,
            )
        except Exception as exc:
            self._emit_error(f"[ERROR] Failed to generate test files: {exc}")
            logger.exception(f"Failed to generate test files: {exc}")
            return 1

        cmd = [
            get_python_executable(),
            "-m", "pytest",
            test_file,
            f"--alluredir={allure_results_dir}",
            "-v",
            "--tb=short",
            "-s",
        ]
        logger.debug(f"pytest command: {' '.join(cmd)}")

        env = get_subprocess_env()
        startupinfo = get_startupinfo()

        pytest_rc = self._stream_subprocess(cmd, env, startupinfo)

        if not self._should_stop:
            self._generate_allure_report(allure_results_dir)

        return pytest_rc

    def _stream_subprocess(self, cmd: List[str], env: Dict, startupinfo) -> int:
        """Start *cmd* and stream its stdout line-by-line. Returns exit code."""
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
                env=env,
                startupinfo=startupinfo,
                cwd=os.getcwd(),
            )
            logger.info(f"Subprocess started: pid={self._process.pid}")

            for line in iter(self._process.stdout.readline, ""):
                if self._should_stop:
                    self._process.terminate()
                    self._emit_output("[Stopped by user]")
                    break
                line = line.rstrip("\n\r")
                if line:
                    self._emit_output(line)

            self._process.wait()
            return_code = self._process.returncode
            return return_code if return_code is not None else -1

        except FileNotFoundError as exc:
            self._emit_error(f"[ERROR] Python executable not found: {exc}")
            return 1
        except OSError as exc:
            self._emit_error(f"[ERROR] Failed to start subprocess: {exc}")
            return 1
        except Exception as exc:
            self._emit_error(f"[EXCEPTION] {type(exc).__name__}: {exc}")
            logger.exception(f"Exception in PytestExecutor subprocess: {exc}")
            return 1
        finally:
            self._process = None

    def _generate_allure_report(self, allure_results_dir: str) -> None:
        """Generate Allure HTML report if the allure CLI is available."""
        allure_cmd = shutil.which("allure")
        if allure_cmd is None:
            self._emit_output(
                f"[INFO] Install allure CLI to generate HTML reports. "
                f"Raw results at: {allure_results_dir}"
            )
            return

        try:
            os.makedirs(self.allure_report_dir, exist_ok=True)
            cmd = [
                allure_cmd,
                "generate",
                allure_results_dir,
                "-o", self.allure_report_dir,
                "--clean",
            ]
            logger.debug(f"allure command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode == 0:
                report_index = os.path.join(self.allure_report_dir, "index.html")
                report_url = Path(report_index).as_uri()
                self._emit_output(f"{ALLURE_REPORT_PREFIX} {report_url}")
            else:
                self._emit_error(
                    f"[WARNING] allure report generation failed: {result.stderr.strip()}"
                )
                self._emit_output(
                    f"[INFO] Raw allure results at: {allure_results_dir}"
                )
        except Exception as exc:
            self._emit_error(f"[WARNING] Could not generate allure report: {exc}")
            self._emit_output(f"[INFO] Raw allure results at: {allure_results_dir}")

    def _cleanup_temp_dir(self) -> None:
        """Remove the temporary directory created for this run."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
                logger.debug(f"Cleaned up temp dir: {self._temp_dir}")
            except Exception as exc:
                logger.warning(f"Could not clean up temp dir {self._temp_dir}: {exc}")
            finally:
                self._temp_dir = None
