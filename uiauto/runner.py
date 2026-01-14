# uiauto/runner.py
from __future__ import annotations
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

import yaml
from jsonschema import Draft202012Validator

from .repository import Repository
from .session import Session
from .resolver import Resolver
from .actions import Actions
from .exceptions import UIAutoError


_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _substitute(value: Any, variables: Dict[str, Any]) -> Any:
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
        self.repo = repo
        self.schema_path = os.path.abspath(schema_path)
        self._schema = self._load_schema(self.schema_path)
        self._validator = Draft202012Validator(self._schema)

    @staticmethod
    def _load_yaml(path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError("Scenario must be a mapping at root")
        return data

    @staticmethod
    def _load_schema(path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def validate(self, scenario: Dict[str, Any]) -> None:
        errors = sorted(self._validator.iter_errors(scenario), key=lambda e: e.path)
        if errors:
            lines = ["Scenario schema validation failed:"]
            for e in errors:
                lines.append(f"- {list(e.path)}: {e.message}")
            raise ValueError("\n".join(lines))

    def run(
        self,
        scenario_path: str,
        app_path: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        report_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        scenario_path = os.path.abspath(scenario_path)
        scenario = self._load_yaml(scenario_path)
        self.validate(scenario)

        variables = variables or {}
        variables = dict(variables)  # copy
        scenario_vars = scenario.get("vars", {}) or {}
        if isinstance(scenario_vars, dict):
            variables = {**scenario_vars, **variables}

        steps: List[Dict[str, Any]] = scenario.get("steps", [])
        steps = _substitute(steps, variables)

        # Build session/resolver/actions
        sess = Session(
            backend=self.repo.app.backend,
            default_timeout=self.repo.app.default_timeout,
            polling_interval=self.repo.app.polling_interval,
        )

        start_ts = time.time()
        report: Dict[str, Any] = {
            "scenario": os.path.basename(scenario_path),
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "unknown",
            "steps": [],
            "errors": [],
        }

        try:
            # open_app step can exist; if app_path provided explicitly, we use it.
            # If scenario contains open_app, it will run. If not, and app_path is provided, we start immediately.
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

                step_rec = {"index": idx, "keyword": keyword, "args": args, "status": "running"}
                report["steps"].append(step_rec)

                try:
                    self._execute(keyword, args, sess, actions)
                    step_rec["status"] = "passed"
                except Exception as e:
                    step_rec["status"] = "failed"
                    step_rec["error"] = f"{type(e).__name__}: {e}"
                    raise

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
            # best-effort close
            try:
                sess.close_main_windows(timeout=3.0)
            except Exception:
                pass

            if report_path:
                os.makedirs(os.path.dirname(os.path.abspath(report_path)) or ".", exist_ok=True)
                with open(report_path, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2)

    def _execute(self, keyword: str, args: Dict[str, Any], sess: Session, actions: Actions) -> None:
        """
        @brief Execute single scenario step.
        @param keyword Step keyword
        @param args Step arguments
        @param sess Session instance
        @param actions Actions instance
        @throws ValueError if keyword unknown
        """
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
            actions.hover(args["element"], overrides=args. get("overrides"))
            return

        if keyword == "hotkey":
            actions.hotkey(args["keys"])
            return

        if keyword == "type": 
            actions.type(args["element"], text=args["text"], overrides=args.get("overrides"), clear=bool(args.get("clear", True)))
            return

        if keyword == "wait": 
            actions.wait_for(args["element"], state=args. get("state", "visible"), timeout=args.get("timeout"), overrides=args.get("overrides"))
            return

        if keyword == "assert": 
            actions.assert_state(args["element"], state=args. get("state", "visible"), overrides=args.get("overrides"))
            return

        if keyword == "assert_text_equals": 
            actions.assert_text_equals(args["element"], expected=args["expected"], overrides=args.get("overrides"))
            return

        if keyword == "assert_text_contains":
            actions.assert_text_contains(args["element"], substring=args["substring"], overrides=args.get("overrides"))
            return

        if keyword == "set_checkbox":
            actions.set_checkbox(args["element"], checked=args["checked"], overrides=args. get("overrides"))
            return

        if keyword == "assert_checkbox_state":
            actions. assert_checkbox_state(args["element"], checked=args["checked"], overrides=args.get("overrides"))
            return

        if keyword == "select_combobox":
            actions.select_combobox(args["element"], option=args["option"], by_index=bool(args.get("by_index", False)), overrides=args.get("overrides"))
            return

        if keyword == "select_list_item":
            actions.select_list_item(args["element"], item_text=args. get("item_text"), item_index=args.get("item_index"), overrides=args.get("overrides"))
            return

        if keyword == "assert_count":
            actions.assert_count(args["element"], expected=args["expected"], overrides=args. get("overrides"))
            return

        if keyword == "close_window": 
            actions.close_window(args["window"])
            return

        if keyword == "kill_app":
            sess.kill()
            return

        raise ValueError(f"Unknown keyword: {keyword}")
