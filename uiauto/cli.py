# uiauto/cli.py
"""
@file cli.py
@brief Command-line interface for cita-uiauto-engine.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .actionlogger import ACTION_LOGGER
from .context import ActionContextManager
from .inspector import (emit_elements_yaml_stateful, inspect_window,
                        write_inspect_outputs)
from .repository import Repository
from .runner import Runner
from .waits import TIMING_LOGGER

# Import recorder conditionally to avoid hard dependency on optional packages
try:
    from .recorder import record_session
    RECORDER_AVAILABLE = True
except ImportError:
    RECORDER_AVAILABLE = False
    record_session = None


def _resolve_timing_options(args: argparse.Namespace) -> tuple[str, Dict[str, Any]]:
    """Resolve deterministic timing preset and CLI overrides without mutating global state."""
    preset = "default"
    if getattr(args, "ci", False):
        preset = "ci"
    elif getattr(args, "fast", False):
        preset = "fast"
    elif getattr(args, "slow", False):
        preset = "slow"

    overrides: Dict[str, Any] = {}
    timeout = getattr(args, "timeout", None)
    if timeout is not None:
        overrides = {
            "element_wait": {"timeout": timeout},
            "window_wait": {"timeout": timeout * 2},
            "visibility_wait": {"timeout": timeout},
            "enabled_wait": {"timeout": timeout / 2},
            "resolve_window": {"timeout": timeout},
            "resolve_element": {"timeout": timeout},
            "wait_for_any": {"timeout": timeout},
            "exists_wait": {"timeout": max(timeout / 5, 0.1)},
        }
    return preset, overrides


def _resolve_scenario_paths(
    single_scenario: Optional[str],
    scenarios_dir: Optional[str],
    elements_path: Optional[str],
) -> List[str]:
    """Resolve scenarios for single or bulk execution."""
    if single_scenario:
        return [os.path.abspath(single_scenario)]
    if not scenarios_dir:
        return []

    base = Path(scenarios_dir).resolve()
    if not base.exists() or not base.is_dir():
        return []

    scenario_files = list(base.rglob("*.yaml")) + list(base.rglob("*.yml"))
    elements_abs = os.path.abspath(elements_path) if elements_path else None
    unique = sorted({str(path.resolve()) for path in scenario_files})
    if elements_abs:
        unique = [path for path in unique if os.path.abspath(path) != elements_abs]
    return unique


def _build_report_path(base_report_path: str, scenario_path: str, index: int, bulk_mode: bool) -> str:
    """Build report path while preserving existing single-scenario behavior."""
    if not bulk_mode:
        return base_report_path

    base = Path(base_report_path)
    stem = base.stem
    suffix = base.suffix or ".json"
    scenario_stem = Path(scenario_path).stem
    filename = f"{stem}__{index:03d}_{scenario_stem}{suffix}"
    return str((base.parent / filename).resolve())


def _print_bulk_summary(results: List[Dict[str, Any]]) -> None:
    """Print compact summary of all scenarios in bulk mode."""
    print("\nBulk Summary")
    print("-" * 80)
    print(f"{'#':<4} {'Status':<8} {'Duration':<10} Scenario (Report)")
    for idx, result in enumerate(results, start=1):
        status = str(result.get("status", "unknown")).upper()
        duration = float(result.get("duration_sec", 0))
        scenario_path = str(result.get("scenario_path", ""))
        report_path = str(result.get("report_path", ""))
        print(f"{idx:<4} {status:<8} {duration:<10.2f} {scenario_path} ({report_path})")
    summary = _build_combined_summary(results)
    print("-" * 80)
    print(
        f"Total: {summary['total']}  Passed: {summary['passed']}  "
        f"Failed: {summary['failed']}  Exit code: {0 if summary['failed'] == 0 else 2}"
    )


def _build_combined_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build machine-readable combined summary."""
    passed = sum(1 for item in results if item.get("status") == "passed")
    failed = sum(1 for item in results if item.get("status") != "passed")
    return {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "status": "passed" if failed == 0 else "failed",
        "results": results,
    }


def _print_validation_summary(results: List[Dict[str, Any]]) -> None:
    """Print summary for bulk validation."""
    print("\nValidation Summary")
    print("-" * 80)
    print(f"{'#':<4} {'Status':<8} Scenario")
    for idx, result in enumerate(results, start=1):
        status = str(result.get("status", "unknown")).upper()
        scenario_path = str(result.get("scenario_path", ""))
        print(f"{idx:<4} {status:<8} {scenario_path}")
    total = len(results)
    invalid = sum(1 for item in results if item.get("status") != "valid")
    valid = total - invalid
    print("-" * 80)
    print(f"Total: {total}  Valid: {valid}  Invalid: {invalid}")


def _configure_action_logger_from_env() -> None:
    """Configure action logging from environment variables."""
    enabled = os.getenv("UIAUTO_ACTION_LOGGING", "").lower() in {"1", "true", "yes", "on"}
    if not enabled:
        ACTION_LOGGER.disable()
        return

    log_file = os.getenv("UIAUTO_ACTION_LOG_FILE")
    level = os.getenv("UIAUTO_ACTION_LOG_LEVEL", "INFO")
    fmt = os.getenv("UIAUTO_ACTION_LOG_FORMAT", "line")
    max_tb_chars = int(os.getenv("UIAUTO_ACTION_LOG_MAX_TRACEBACK", "4000"))
    sample_retry = int(os.getenv("UIAUTO_ACTION_LOG_SAMPLE_RETRY", "1"))
    ACTION_LOGGER.configure(
        console=True,
        file_path=log_file,
        level=level,
        format=fmt,
        max_traceback_chars=max_tb_chars,
        sample_retry_events=sample_retry,
    )
    ACTION_LOGGER.enable()


def _configure_timing_logger_from_env() -> None:
    """Configure timing logging from environment variables."""
    enabled = os.getenv("UIAUTO_TIMING_LOGGING", "").lower() in {"1", "true", "yes", "on"}
    if not enabled:
        TIMING_LOGGER.disable()
        return

    log_file = os.getenv("UIAUTO_TIMING_LOG_FILE")
    level = os.getenv("UIAUTO_TIMING_LOG_LEVEL", "INFO")
    TIMING_LOGGER.configure(console=True, file_path=log_file, level=level)
    TIMING_LOGGER.enable()


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI."""
    argv = argv or sys.argv[1:]
    _configure_action_logger_from_env()
    _configure_timing_logger_from_env()

    p = argparse.ArgumentParser(
        prog="uiauto",
        description="cita-uiauto-engine - Windows UI automation framework",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # -------------------------
    # run
    # -------------------------
    runp = sub.add_parser("run", help="Run a YAML scenario using an elements.yaml object map")
    runp.add_argument("--elements", "-e", required=True, help="Path to elements.yaml (object map)")
    runp.add_argument("--scenario", "-s", required=False, help="Path to scenario.yaml")
    runp.add_argument("--scenarios-dir", default=None, help="Run all scenarios under directory (recursively searches for *.yaml/*.yml)")
    runp.add_argument("--schema", default=os.path.join(os.path.dirname(__file__), "schemas", "scenario.schema.json"), help="Path to scenario schema JSON")
    runp.add_argument("--app", "-a", default=None, help="Optional app path to start (can also use open_app step)")
    runp.add_argument("--vars", default=None, help="Optional vars JSON file")
    runp.add_argument("--var", "-v", action="append", help="Variable in KEY=VALUE format (can be used multiple times)")
    runp.add_argument("--report", "-r", default="report.json", help="Report output path (JSON)")
    runp.add_argument("--timeout", "-t", type=float, default=None, help="Override base timeouts in seconds (intervals stay from preset)")
    runp.add_argument("--ci", action="store_true", help="Use CI-optimized timeout settings")
    runp.add_argument("--fast", action="store_true", help="Use fast timeout settings for local development")
    runp.add_argument("--slow", action="store_true", help="Use slow timeout settings for unstable environments")
    runp.add_argument("--verbose", action="store_true", help="Show detailed step output")
    runp.add_argument("--summary-json", default=None, help="Optional output path for combined bulk summary (JSON)")

    # -------------------------
    # inspect
    # -------------------------
    insp = sub.add_parser("inspect", help="Inspect Desktop UIA and dump control candidates (JSON/TXT)")
    insp.add_argument("--window-title-re", default=None, help="Optional: filter visible windows by title regex (best-effort)")
    insp.add_argument("--out", "-o", default="reports", help="Output directory for inspect reports")
    insp.add_argument("--query", "-q", default=None, help="Filter controls by contains; use 'regex:<pattern>' for regex search")
    insp.add_argument("--max-controls", type=int, default=3000, help="Max number of descendants to scan")
    insp.add_argument("--include-invisible", action="store_true", help="Include invisible controls")
    insp.add_argument("--exclude-disabled", action="store_true", help="Exclude disabled controls")
    insp.add_argument("--emit-elements-yaml", default=None, help="Optional: write generated elements.yaml to this path")
    insp.add_argument("--emit-window-name", default="main", help="Window name used in generated elements.yaml (default: main)")
    insp.add_argument("--state", default="default", help="UI state name (default: 'default')")
    insp.add_argument("--merge", action="store_true", help="Merge with existing elements.yaml")

    # -------------------------
    # record
    # -------------------------
    recp = sub.add_parser("record", help="Record user interactions into semantic YAML steps")
    recp.add_argument("--elements", "-e", required=True, help="Path to elements.yaml (will be updated with new elements)")
    recp.add_argument("--scenario-out", "-s", required=True, help="Output path for recorded scenario YAML")
    recp.add_argument("--window-title-re", default=None, help="Filter recording to window matching title regex")
    recp.add_argument("--window-name", default="main", help="Window name for element specs (default: main)")
    recp.add_argument("--state", default="default", help="UI state name for recorded elements (default: 'default')")
    recp.add_argument("--debug-json-out", default=None, help="Optional: save debug snapshots to this JSON file")

    # -------------------------
    # validate
    # -------------------------
    valp = sub.add_parser("validate", help="Validate configuration files")
    valp.add_argument("--elements", "-e", required=True, help="Path to elements.yaml file")
    valp.add_argument("--scenario", "-s", default=None, help="Path to scenario YAML file (optional)")
    valp.add_argument("--scenarios-dir", default=None, help="Validate all scenarios under directory (recursively searches for *.yaml/*.yml)")
    valp.add_argument("--schema", default=None, help="Path to scenario JSON schema")

    # -------------------------
    # list-elements
    # -------------------------
    listp = sub.add_parser("list-elements", help="List all defined windows and elements")
    listp.add_argument("--elements", "-e", required=True, help="Path to elements.yaml file")

    args = p.parse_args(argv)

    # -------------------------
    # Execute commands
    # -------------------------

    if args.cmd == "run":
        if args.scenario and args.scenarios_dir:
            print("Error: --scenario and --scenarios-dir are mutually exclusive", file=sys.stderr)
            return 1
        if not args.scenario and not args.scenarios_dir:
            print("Error: one of --scenario or --scenarios-dir is required", file=sys.stderr)
            return 1

        # Clear any stale action context
        ActionContextManager.clear()

        try:
            repo = Repository(args.elements)
        except Exception as e:
            print(f"Error loading elements file: {e}", file=sys.stderr)
            return 1

        timing_preset, timing_overrides = _resolve_timing_options(args)

        runner = Runner(repo, schema_path=args.schema)

        variables: Dict[str, Any] = {}
        if args.vars:
            with open(args.vars, "r", encoding="utf-8") as f:
                variables = json.load(f)
            if not isinstance(variables, dict):
                raise ValueError("--vars must be a JSON object mapping")

        # Parse inline variables
        if args.var:
            for var_spec in args.var:
                if "=" in var_spec:
                    key, value = var_spec.split("=", 1)
                    variables[key.strip()] = value.strip()

        scenario_paths = _resolve_scenario_paths(args.scenario, args.scenarios_dir, args.elements)
        if not scenario_paths:
            print("Error: no scenario files found", file=sys.stderr)
            return 1

        bulk_mode = len(scenario_paths) > 1 or bool(args.scenarios_dir)
        scenario_results: List[Dict[str, Any]] = []

        for idx, scenario_path in enumerate(scenario_paths, start=1):
            per_report_path = _build_report_path(args.report, scenario_path, idx, bulk_mode)
            report = runner.run(
                scenario_path=scenario_path,
                app_path=args.app,
                variables=variables,
                report_path=per_report_path,
                timing_preset=timing_preset,
                timing_overrides=timing_overrides,
            )

            scenario_results.append({
                "scenario_path": scenario_path,
                "status": report.get("status", "unknown"),
                "duration_sec": report.get("duration_sec", 0),
                "report_path": per_report_path,
                "errors": report.get("errors", []),
            })

            # Print per-scenario summary
            print("\n" + "=" * 60)
            print(f"Scenario: {report.get('scenario', os.path.basename(scenario_path))}")
            print(f"Status:   {report.get('status', 'unknown').upper()}")
            print(f"Duration: {report.get('duration_sec', 0):.2f}s")

            # Print step details if verbose or failed
            if args.verbose or report.get("status") == "failed":
                print("\nStep Details:")
                for step in report.get("steps", []):
                    status_icon = "+" if step["status"] == "passed" else "X"
                    print(f"  {status_icon} [{step['index']}] {step['keyword']}: {step['status']} ({step.get('duration_sec', 0):.2f}s)")
                    if step["status"] == "failed" and "error" in step:
                        print(f"      Error: {step['error']}")

            # Print errors
            if report.get("errors"):
                print("\nErrors:")
                for error in report["errors"]:
                    print(f"  - {error}")

            print("=" * 60)

            # Also print JSON for machine parsing if verbose
            if args.verbose:
                print("\nFull Report (JSON):")
                print(json.dumps(report, indent=2, ensure_ascii=False))

        if bulk_mode:
            _print_bulk_summary(scenario_results)

        combined_summary = _build_combined_summary(scenario_results)
        if args.summary_json:
            os.makedirs(os.path.dirname(os.path.abspath(args.summary_json)) or ".", exist_ok=True)
            with open(args.summary_json, "w", encoding="utf-8") as f:
                json.dump(combined_summary, f, indent=2, ensure_ascii=False)

        return 0 if combined_summary["failed"] == 0 else 2

    if args.cmd == "inspect":
        try:
            result = inspect_window(
                backend="uia",
                window_title_re=args.window_title_re,
                max_controls=int(args.max_controls),
                query=args.query,
                include_invisible=bool(args.include_invisible),
                include_disabled=not bool(args.exclude_disabled),
            )

            paths = write_inspect_outputs(result, out_dir=args.out)

            if args.emit_elements_yaml:
                out_yaml = emit_elements_yaml_stateful(
                    result,
                    out_path=args.emit_elements_yaml,
                    window_name=args.emit_window_name,
                    state=args.state,
                    merge=args.merge,
                )
                paths["elements_yaml"] = out_yaml

            print(json.dumps({
                "status": "ok",
                "outputs": paths,
                "controls": len(result.get("controls", [])),
            }, indent=2, ensure_ascii=False))
            return 0
        except Exception as e:
            print(json.dumps({
                "status": "error",
                "error": f"{type(e).__name__}: {e}",
            }, indent=2), file=sys.stderr)
            return 1

    if args.cmd == "record":
        if not RECORDER_AVAILABLE:
            print("ERROR: Recording requires additional dependencies.", file=sys.stderr)
            print("Install with: pip install pynput comtypes", file=sys.stderr)
            return 1

        try:
            recorder = record_session(
                elements_yaml=args.elements,
                scenario_out=args.scenario_out,
                window_title_re=args.window_title_re,
                window_name=args.window_name,
                state=args.state,
                debug_json_out=args.debug_json_out,
            )
            return 0
        except KeyboardInterrupt:
            print("\nRecording interrupted by user.")
            return 0
        except Exception as e:
            print(f"Error during recording: {e}", file=sys.stderr)
            return 1

    if args.cmd == "validate":
        errors: List[str] = []

        if args.scenario and args.scenarios_dir:
            print("Error: --scenario and --scenarios-dir are mutually exclusive", file=sys.stderr)
            return 1
        if not args.scenario and not args.scenarios_dir:
            print("Error: one of --scenario or --scenarios-dir is required", file=sys.stderr)
            return 1

        try:
            repo = Repository(args.elements)
            print(f"+ Elements file is valid: {args.elements}")
            print(f"  - Windows: {len(repo.list_windows())}")
            print(f"  - Elements: {len(repo.list_elements())}")
        except Exception as e:
            errors.append(f"Elements file invalid: {e}")
            print(f"X Elements file is invalid: {e}", file=sys.stderr)

        scenario_paths = _resolve_scenario_paths(args.scenario, args.scenarios_dir, args.elements)
        if not scenario_paths:
            print("Error: no scenario files found", file=sys.stderr)
            return 1

        validation_results: List[Dict[str, Any]] = []
        try:
            import yaml as yaml_lib
            schema_path = args.schema or os.path.join(
                os.path.dirname(__file__), "schemas", "scenario.schema.json"
            )
            runner = Runner(repo, schema_path=schema_path)
        except Exception as e:
            errors.append(f"Scenario validation setup failed: {e}")
            print(f"X Scenario validation setup failed: {e}", file=sys.stderr)
            return 1

        for scenario_path in scenario_paths:
            try:
                with open(scenario_path, "r", encoding="utf-8") as f:
                    scenario = yaml_lib.safe_load(f)
                runner.validate(scenario)
                steps_count = len(scenario.get("steps", [])) if isinstance(scenario, dict) else 0
                print(f"+ Scenario file is valid: {scenario_path}")
                print(f"  - Steps: {steps_count}")
                validation_results.append({
                    "scenario_path": scenario_path,
                    "status": "valid",
                    "steps": steps_count,
                })
            except Exception as e:
                errors.append(f"Scenario file invalid: {scenario_path}: {e}")
                print(f"X Scenario file is invalid: {scenario_path}: {e}", file=sys.stderr)
                validation_results.append({
                    "scenario_path": scenario_path,
                    "status": "invalid",
                    "error": f"{type(e).__name__}: {e}",
                })

        if len(validation_results) > 1 or args.scenarios_dir:
            _print_validation_summary(validation_results)

        return 2 if errors else 0

    if args.cmd == "list-elements":
        try:
            repo = Repository(args.elements)
        except Exception as e:
            print(f"Error loading elements file: {e}", file=sys.stderr)
            return 1

        windows = repo.list_windows()
        print(f"Windows ({len(windows)}):")
        for name in windows:
            print(f"  - {name}")

        elements = repo.list_elements()
        print(f"\nElements ({len(elements)}):")

        by_window: Dict[str, List[str]] = {}
        for name in elements:
            spec = repo.get_element_spec(name)
            window = spec.get("window", "unknown")
            if window not in by_window:
                by_window[window] = []
            by_window[window].append(name)

        for window, elem_names in by_window.items():
            print(f"\n  [{window}]")
            for name in elem_names:
                print(f"    - {name}")

        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
