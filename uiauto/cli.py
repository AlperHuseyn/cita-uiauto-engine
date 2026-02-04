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
from typing import Any, Dict, List, Optional

from .repository import Repository
from .runner import Runner
from .config import TimeConfig, TimeoutSettings, configure_for_ci, configure_for_local_dev
from .context import ActionContextManager

from .inspector import (
    inspect_window,
    write_inspect_outputs,
    emit_elements_yaml_stateful,
)

# Import recorder conditionally to avoid hard dependency on optional packages
try:
    from .recorder import record_session
    RECORDER_AVAILABLE = True
except ImportError:
    RECORDER_AVAILABLE = False
    record_session = None


def _apply_timeout_config(args: argparse.Namespace) -> None:
    """Apply timeout configuration based on CLI arguments."""
    if getattr(args, 'ci', False):
        configure_for_ci()
    elif getattr(args, 'fast', False):
        configure_for_local_dev()
    
    timeout = getattr(args, 'timeout', None)
    if timeout is not None:
        config = TimeConfig.default()
        config.element_wait = TimeoutSettings(timeout=timeout, interval=0.2)
        config.window_wait = TimeoutSettings(timeout=timeout * 2, interval=0.5)
        config.visibility_wait = TimeoutSettings(timeout=timeout, interval=0.2)
        config.enabled_wait = TimeoutSettings(timeout=timeout / 2, interval=0.2)


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI."""
    argv = argv or sys.argv[1:]
    p = argparse.ArgumentParser(
        prog="uiauto",
        description="cita-uiauto-engine - Production-ready Windows UI automation framework"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # -------------------------
    # run
    # -------------------------
    runp = sub.add_parser("run", help="Run a YAML scenario using an elements.yaml object map")
    runp.add_argument("--elements", "-e", required=True, help="Path to elements.yaml (object map)")
    runp.add_argument("--scenario", "-s", required=True, help="Path to scenario.yaml")
    runp.add_argument("--schema", default=os.path.join(os.path.dirname(__file__), "schemas", "scenario.schema.json"), help="Path to scenario schema JSON")
    runp.add_argument("--app", "-a", default=None, help="Optional app path to start (can also use open_app step)")
    runp.add_argument("--vars", default=None, help="Optional vars JSON file")
    runp.add_argument("--var", "-v", action="append", help="Variable in KEY=VALUE format (can be used multiple times)")
    runp.add_argument("--report", "-r", default="report.json", help="Report output path (JSON)")
    runp.add_argument("--timeout", "-t", type=float, default=None, help="Override default timeout in seconds")
    runp.add_argument("--ci", action="store_true", help="Use CI-optimized timeout settings")
    runp.add_argument("--fast", action="store_true", help="Use fast timeout settings for local development")
    runp.add_argument("--verbose", action="store_true", help="Show detailed step output")

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
        # Apply timeout configuration
        _apply_timeout_config(args)
        
        # Clear any stale action context
        ActionContextManager.clear()
        
        try:
            repo = Repository(args.elements)
        except Exception as e:
            print(f"Error loading elements file: {e}", file=sys.stderr)
            return 1
        
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

        report = runner.run(
            scenario_path=args.scenario,
            app_path=args.app,
            variables=variables,
            report_path=args.report,
        )

        # Print summary
        print("\n" + "=" * 60)
        print(f"Scenario: {report.get('scenario', 'unknown')}")
        print(f"Status:   {report.get('status', 'unknown').upper()}")
        print(f"Duration: {report.get('duration_sec', 0):.2f}s")
        
        # Print step details if verbose or failed
        if args.verbose or report.get('status') == 'failed':
            print("\nStep Details:")
            for step in report.get('steps', []):
                status_icon = "+" if step['status'] == 'passed' else "X"
                print(f"  {status_icon} [{step['index']}] {step['keyword']}: {step['status']} ({step.get('duration_sec', 0):.2f}s)")
                if step['status'] == 'failed' and 'error' in step:
                    print(f"      Error: {step['error']}")
        
        # Print errors
        if report.get('errors'):
            print("\nErrors:")
            for error in report['errors']:
                print(f"  - {error}")
        
        print("=" * 60)
        
        # Also print JSON for machine parsing if verbose
        if args.verbose:
            print("\nFull Report (JSON):")
            print(json.dumps(report, indent=2, ensure_ascii=False))
        
        return 0 if report.get("status") == "passed" else 2

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
                "controls": len(result.get("controls", []))
            }, indent=2, ensure_ascii=False))
            return 0
        except Exception as e:
            print(json.dumps({
                "status": "error",
                "error": f"{type(e).__name__}: {e}"
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
        errors = []
        
        try:
            repo = Repository(args.elements)
            print(f"+ Elements file is valid: {args.elements}")
            print(f"  - Windows: {len(repo.list_windows())}")
            print(f"  - Elements: {len(repo.list_elements())}")
        except Exception as e:
            errors.append(f"Elements file invalid: {e}")
            print(f"X Elements file is invalid: {e}", file=sys.stderr)
        
        if args.scenario:
            try:
                import yaml as yaml_lib
                schema_path = args.schema or os.path.join(
                    os.path.dirname(__file__), "schemas", "scenario.schema.json"
                )
                runner = Runner(repo, schema_path=schema_path)
                with open(args.scenario, 'r', encoding='utf-8') as f:
                    scenario = yaml_lib.safe_load(f)
                runner.validate(scenario)
                steps_count = len(scenario.get('steps', []))
                print(f"+ Scenario file is valid: {args.scenario}")
                print(f"  - Steps: {steps_count}")
            except Exception as e:
                errors.append(f"Scenario file invalid: {e}")
                print(f"X Scenario file is invalid: {e}", file=sys.stderr)
        
        return 1 if errors else 0

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
            window = spec.get('window', 'unknown')
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