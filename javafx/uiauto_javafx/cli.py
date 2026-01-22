# javafx/uiauto_javafx/cli.py
"""CLI entry point for uiauto-javafx."""
from __future__ import annotations

import argparse
import json
import os
import sys

from uiauto_core.repository import Repository
from uiauto_core.runner import Runner

from .session import JavaFXSession
from .resolver import JavaFXResolver
from .actions import JavaFXActions
from .inspector import inspect_javafx_window, write_inspect_outputs


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    p = argparse.ArgumentParser(prog="uiauto-javafx", description="JavaFX UI automation runner (Java Access Bridge).")
    sub = p.add_subparsers(dest="cmd", required=True)

    # -------------------------
    # run
    # -------------------------
    runp = sub.add_parser("run", help="Run a YAML scenario using an elements.yaml object map")
    runp.add_argument("--elements", required=True, help="Path to elements.yaml (object map)")
    runp.add_argument("--scenario", required=True, help="Path to scenario.yaml")
    runp.add_argument("--schema", default=None, help="Path to scenario schema JSON (optional)")
    runp.add_argument("--app", default=None, help="Optional app JAR/executable to start")
    runp.add_argument("--vars", default=None, help="Optional vars JSON file")
    runp.add_argument("--report", default="report.json", help="Report output path (JSON)")
    runp.add_argument("--jvm-path", default=None, help="Optional path to JVM library")
    runp.add_argument("--java-args", default=None, help="Additional Java arguments (comma-separated)")
    runp.add_argument("--app-args", default=None, help="Application arguments (comma-separated)")

    # -------------------------
    # inspect
    # -------------------------
    insp = sub.add_parser("inspect", help="Inspect JavaFX application UI elements")
    insp.add_argument("--app", required=True, help="Path to JavaFX application JAR/executable")
    insp.add_argument("--out", default="reports", help="Output directory for inspect reports")
    insp.add_argument("--max-controls", type=int, default=3000, help="Max number of controls to scan")
    insp.add_argument("--include-invisible", action="store_true", help="Include invisible controls")
    insp.add_argument("--jvm-path", default=None, help="Optional path to JVM library")
    insp.add_argument("--java-args", default=None, help="Additional Java arguments (comma-separated)")
    insp.add_argument("--wait-seconds", type=int, default=5, help="Seconds to wait after starting app")

    args = p.parse_args(argv)

    if args.cmd == "run":
        repo = Repository(args.elements)
        
        # Use default schema path if not provided
        if args.schema is None:
            import uiauto_core
            core_dir = os.path.dirname(uiauto_core.__file__)
            args.schema = os.path.join(core_dir, "schemas", "scenario.schema.json")
        
        runner = Runner(repo, schema_path=args.schema)

        variables = {}
        if args.vars:
            with open(args.vars, "r", encoding="utf-8") as f:
                variables = json.load(f)
            if not isinstance(variables, dict):
                raise ValueError("--vars must be a JSON object mapping")

        # Parse Java/app args
        java_args = []
        if args.java_args:
            java_args = [arg.strip() for arg in args.java_args.split(",")]
        
        app_args = []
        if args.app_args:
            app_args = [arg.strip() for arg in args.app_args.split(",")]

        # Create JavaFX-specific instances
        session = JavaFXSession(
            jvm_path=args.jvm_path,
            default_timeout=repo.app.default_timeout,
            polling_interval=repo.app.polling_interval,
        )
        resolver = JavaFXResolver(session, repo)
        actions = JavaFXActions(resolver)

        # Start app if provided
        if args.app:
            session.start(
                args.app,
                wait_for_idle=False,
                java_args=java_args,
                app_args=app_args,
            )
            # Note: Setting root context would require additional JAB integration
            # For now, this is a placeholder

        # Run scenario with instances
        report = runner.run(
            scenario_path=args.scenario,
            session=session,
            resolver=resolver,
            actions=actions,
            app_path=None,  # Already started above
            variables=variables,
            report_path=args.report,
        )

        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report.get("status") == "passed" else 2

    if args.cmd == "inspect":
        # Parse Java args
        java_args = []
        if args.java_args:
            java_args = [arg.strip() for arg in args.java_args.split(",")]

        # Start session and app
        session = JavaFXSession(jvm_path=args.jvm_path)
        
        print(f"Starting application: {args.app}")
        session.start(args.app, wait_for_idle=False, java_args=java_args)
        
        # Wait for app to initialize
        import time
        print(f"Waiting {args.wait_seconds} seconds for application to initialize...")
        time.sleep(args.wait_seconds)
        
        # Get root context (would need proper JAB integration)
        # For now, this is a placeholder
        window_context = session.root_context
        
        if window_context is None:
            print("WARNING: Could not obtain root context. Inspection may be incomplete.", file=sys.stderr)
            print("Note: Full JavaFX inspection requires proper Java Access Bridge setup.", file=sys.stderr)
            # Create dummy result
            result = {"controls": [], "total_count": 0}
        else:
            result = inspect_javafx_window(
                bridge=session.bridge,
                window_context=window_context,
                max_controls=args.max_controls,
                include_invisible=args.include_invisible,
            )
        
        paths = write_inspect_outputs(result, out_dir=args.out)
        
        print(json.dumps({
            "status": "ok",
            "outputs": paths,
            "controls": len(result.get("controls", []))
        }, indent=2, ensure_ascii=False))
        
        # Clean up
        session.kill()
        
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
