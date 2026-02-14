# uiauto/runner.py
"""
@file runner.py
@brief Scenario runner for YAML-based test execution.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

import yaml
from jsonschema import Draft202012Validator

from .actions import Actions
from .config import TimeConfig
from .context import ActionContextManager
from .exceptions import UIAutoError
from .repository import Repository
from .resolver import Resolver
from .session import Session

_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _substitute(value: Any, variables: Dict[str, Any]) -> Any:
    """Substitute variables in step arguments."""
    if isinstance(value, str):

        def repl(m):
            key = m.group(1)
            if key not in variables:
                return m.group(0)
            return str(variables[key])

        return _VAR_PATTERN.sub(repl, value)
    if isinstance(value, list):
        return [_substitute(v, variables) for v in value]
    if isinstance(value, dict):
        return {k: _substitute(v, variables) for k, v in value.items()}
    return value


class Runner:
    """
    Loads scenario.yaml, validates, runs steps, emits report JSON.
    """

    def __init__(self, repo: Repository, schema_path: str):
        """
        @param repo Repository with element/window specs
        @param schema_path Path to JSON schema for scenario validation
        """
        self.repo = repo
        self.schema_path = os.path.abspath(schema_path)
        self._schema = self._load_schema(self.schema_path)
        self._validator = Draft202012Validator(self._schema)

    @staticmethod
    def _load_yaml(path: str) -> Dict[str, Any]:
        """Load and parse YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError("Scenario must be a mapping at root")
        return data

    @staticmethod
    def _load_schema(path: str) -> Dict[str, Any]:
        """Load JSON schema file."""
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def validate(self, scenario: Dict[str, Any]) -> None:
        """Validate scenario against JSON schema."""
        errors = sorted(self._validator.iter_errors(scenario), key=lambda e: e.path)
        if errors:
            lines = ["Scenario schema validation failed:"]
            for e in errors:
                lines.append(f"- {list(e.path)}: {e.message}")
            raise ValueError("\n".join(lines))

    def _build_time_config(
            self,
            *,
            preset: str = "default",
            overrides: Optional[Dict[str, Any]] = None,
        ) -> TimeConfig:
            """Build deterministic run-scope timing snapshot."""
            app_defaults = {
                "default_timeout": self.repo.app.default_timeout,
                "polling_interval": self.repo.app.polling_interval,
            }
            return TimeConfig.build_from(
                preset=preset,
                overrides=overrides or {},
                app_defaults=app_defaults,
            )

    def run(
        self,
        scenario_path: str,
        app_path: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        report_path: Optional[str] = None,
        timing_preset: str = "default",
        timing_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run a scenario file."""
        from .actionlogger import ACTION_LOGGER

        scenario_path = os.path.abspath(scenario_path)
        scenario = self._load_yaml(scenario_path)
        self.validate(scenario)

        variables = variables or {}
        variables = dict(variables)
        scenario_vars = scenario.get("vars", {}) or {}
        if isinstance(scenario_vars, dict):
            variables = {**scenario_vars, **variables}

        steps: List[Dict[str, Any]] = scenario.get("steps", [])
        steps = _substitute(steps, variables)
        
        run_time_config = self._build_time_config(
            preset=timing_preset,
            overrides=timing_overrides,
        )
        TimeConfig.install_run_config(run_time_config)

        # Build session/resolver/actions
        sess = Session(
            backend=self.repo.app.backend,
            default_timeout=self.repo.app.default_timeout,
            polling_interval=self.repo.app.polling_interval,
        )

        start_ts = time.time()
        run_id = str(uuid4())
        ACTION_LOGGER.set_run_id(run_id)
        report: Dict[str, Any] = {
            "run_id": run_id,
            "scenario": os.path.basename(scenario_path),
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "unknown",
            "steps": [],
            "errors": [],
        }

        try:
            resolver = Resolver(sess, self.repo)
            actions = Actions(resolver)

            if app_path:
                sess.start(app_path, wait_for_idle=False)

            for idx, step in enumerate(steps, start=1):
                if not isinstance(step, dict) or len(step) != 1:
                    raise ValueError(f"Invalid step format at index {idx}: {step}")

                keyword, args = next(iter(step.items()))
                args = args or {}
                if not isinstance(args, dict):
                    raise ValueError(f"Step args must be a mapping at index {idx}: {step}")

                step_rec = {
                    "index": idx,
                    "keyword": keyword,
                    "args": args,
                    "status": "running",
                    "started_at": time.time(),
                }
                report["steps"].append(step_rec)

                try:
                    ActionContextManager.clear()
                    
                    self._execute(keyword, args, sess, actions)
                    step_rec["status"] = "passed"
                except Exception as e:
                    step_rec["status"] = "failed"
                    step_rec["error"] = f"{type(e).__name__}: {e}"
                    
                    ctx = ActionContextManager.current()
                    if ctx:
                        step_rec["action_trace"] = ctx.format_trace()
                    
                    raise
                finally:
                    step_rec["duration_sec"] = round(time.time() - step_rec["started_at"], 3)
                    step_rec.pop("started_at", None)

            report["status"] = "passed"
            return report

        except UIAutoError as e:
            report["status"] = "failed"
            report["errors"].append(f"{type(e).__name__}: {e}")
            return report
        except Exception as e:
            report["status"] = "failed"
            report["errors"].append(f"{type(e).__name__}: {e}")
            return report
        finally:
            report["duration_sec"] = round(time.time() - start_ts, 3)
            
            ActionContextManager.clear()
            
            try:
                sess.close_main_windows(timeout=TimeConfig.current().window_close.timeout)
            except Exception:
                pass

            TimeConfig.clear_run_config()

            if report_path:
                os.makedirs(os.path.dirname(os.path.abspath(report_path)) or ".", exist_ok=True)
                with open(report_path, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2)

    def _execute(
        self,
        keyword: str,
        args: Dict[str, Any],
        sess: Session,
        actions: Actions,
    ) -> None:
        """Execute single scenario step."""
        if keyword == "open_app":
            path = args["path"]
            sess.start(path, wait_for_idle=bool(args.get("wait_for_idle", False)))
            return

        if keyword == "connect":
            sess.connect(**args)
            return

        if keyword == "click":
            actions.click(args["element"], overrides=args.get("overrides"))
            return

        if keyword == "double_click":
            actions.double_click(args["element"], overrides=args.get("overrides"))
            return

        if keyword == "right_click":
            actions.right_click(args["element"], overrides=args.get("overrides"))
            return

        if keyword == "hover":
            actions.hover(args["element"], overrides=args.get("overrides"))
            return

        if keyword == "hotkey":
            actions.hotkey(args["keys"])
            return

        if keyword == "type":
            actions.type(
                args["element"],
                text=args["text"],
                overrides=args.get("overrides"),
                clear=bool(args.get("clear", True))
            )
            return
        
        if keyword == "click_and_type":
            actions.click_and_type(
                args["element"],
                text=args["text"],
                clear=bool(args.get("clear", True)),
                overrides=args.get("overrides")
            )
            return

        if keyword == "wait":
            actions.wait_for(
                args["element"],
                state=args.get("state", "visible"),
                timeout=args.get("timeout"),
                overrides=args.get("overrides")
            )
            return

        if keyword == "wait_for_gone":
            actions.wait_for_gone(
                args["element"],
                timeout=args.get("timeout"),
                overrides=args.get("overrides")
            )
            return

        if keyword == "wait_for_any":
            actions.wait_for_any(
                args["elements"],
                timeout=args.get("timeout"),
                overrides=args.get("overrides")
            )
            return

        if keyword == "assert":
            actions.assert_state(
                args["element"],
                state=args.get("state", "visible"),
                overrides=args.get("overrides")
            )
            return

        if keyword == "assert_text_equals":
            actions.assert_text_equals(
                args["element"],
                expected=args["expected"],
                overrides=args.get("overrides")
            )
            return

        if keyword == "assert_text_contains":
            actions.assert_text_contains(
                args["element"],
                substring=args["substring"],
                overrides=args.get("overrides")
            )
            return

        if keyword == "set_checkbox":
            actions.set_checkbox(
                args["element"],
                checked=args["checked"],
                overrides=args.get("overrides")
            )
            return

        if keyword == "assert_checkbox_state":
            actions.assert_checkbox_state(
                args["element"],
                checked=args["checked"],
                overrides=args.get("overrides")
            )
            return

        if keyword == "select_combobox":
            actions.select_combobox(
                args["element"],
                option=args["option"],
                by_index=bool(args.get("by_index", False)),
                item_element=args.get("item_element"),  # NEW
                overrides=args.get("overrides")
            )
            return
        
        if keyword == "select_combobox_item":
            actions.select_combobox_item(
                combobox_element=args["combobox"],
                item_element=args["item"],
                overrides=args.get("overrides")
            )
            return

        if keyword == "select_list_item":
            actions.select_list_item(
                args["element"],
                item_text=args.get("item_text"),
                item_index=args.get("item_index"),
                overrides=args.get("overrides")
            )
            return

        if keyword == "assert_count":
            actions.assert_count(
                args["element"],
                expected=args["expected"],
                overrides=args.get("overrides")
            )
            return

        if keyword == "close_window":
            actions.close_window(args["window"])
            return

        if keyword == "kill_app":
            sess.kill()
            return

        # New v1.2.0 keywords
        if keyword == "click_if_exists":
            actions.click_if_exists(
                args["element"],
                timeout=args.get("timeout", TimeConfig.current().exists_wait.timeout),
                overrides=args.get("overrides")
            )
            return

        raise ValueError(f"Unknown keyword: {keyword}")