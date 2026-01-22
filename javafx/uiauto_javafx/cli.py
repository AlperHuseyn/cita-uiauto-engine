# javafx/uiauto_javafx/cli.py
"""Command-line interface for JavaFX UI automation."""

from __future__ import annotations
import argparse
import json
import os
import sys

from uiauto_core import Repository, Runner

from .session import JavaFXSession
from .resolver import JavaFXResolver
from .actions import JavaFXActions
from .inspector import inspect_window, write_inspect_outputs, emit_elements_yaml


def main(argv=None) -> int:
    """Main CLI entry point."""
    argv = argv or sys.argv[1:]
    p = argparse.ArgumentParser(
        prog="uiauto-javafx",
        description="JavaFX UI automation engine using Java Access Bridge."
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    
    # -------------------------
    # run
    # -------------------------
    runp = sub.add_parser("run", help="Run a YAML scenario using an elements.yaml object map")
    runp.add_argument("--elements", required=True, help="Path to elements.yaml (object map)")
    runp.add_argument("--scenario", required=True, help="Path to scenario.yaml")
    runp.add_argument("--schema", 
                     default=os.path.join(os.path.dirname(__file__), "..", "..", "core", "uiauto_core", "schemas", "scenario.schema.json"),
                     help="Path to scenario schema JSON")
    runp.add_argument("--app", default=None, help="Optional app path to start (jar or main class)")
    runp.add_argument("--vars", default=None, help="Optional vars JSON file")
    runp.add_argument("--report", default="report.json", help="Report output path (JSON)")
    runp.add_argument("--jvm-path", default=None, help="Optional path to JVM")
    
    # -------------------------
    # inspect
    # -------------------------
    insp = sub.add_parser("inspect", help="Inspect JavaFX window using Java Access Bridge")
    insp.add_argument("--window-title", default=None, help="Window title to inspect (partial match)")
    insp.add_argument("--jvm-path", default=None, help="Optional path to JVM")
    insp.add_argument("--out", default="reports", help="Output directory for inspect reports")
    insp.add_argument("--max-depth", type=int, default=10, help="Maximum tree traversal depth")
    insp.add_argument("--include-invisible", action="store_true", help="Include invisible elements")
    insp.add_argument("--emit-elements-yaml", default=None, help="Optional: write generated elements.yaml to this path")
    insp.add_argument("--emit-window-name", default="main", help="Window name used in generated elements.yaml")
    
    args = p.parse_args(argv)
    
    if args.cmd == "run":
        repo = Repository(args.elements)
        
        # Find schema path (try multiple locations)
        schema_path = args.schema
        if not os.path.exists(schema_path):
            # Try relative to core package
            alt_paths = [
                os.path.join(os.path.dirname(__file__), "..", "..", "core", "uiauto_core", "schemas", "scenario.schema.json"),
                os.path.join(os.getcwd(), "core", "uiauto_core", "schemas", "scenario.schema.json"),
            ]
            for alt in alt_paths:
                if os.path.exists(alt):
                    schema_path = alt
                    break
        
        runner = Runner(repo, schema_path=schema_path)
        
        variables = {}
        if args.vars:
            with open(args.vars, "r", encoding="utf-8") as f:
                variables = json.load(f)
            if not isinstance(variables, dict):
                raise ValueError("--vars must be a JSON object mapping")
        
        # Create factory functions for JavaFX components
        def session_factory():
            return JavaFXSession(
                jvm_path=args.jvm_path,
                default_timeout=repo.app.default_timeout,
                polling_interval=repo.app.polling_interval,
            )
        
        def resolver_factory(sess, repo):
            return JavaFXResolver(sess, repo)
        
        def actions_factory(resolver):
            return JavaFXActions(resolver)
        
        report = runner.run(
            scenario_path=args.scenario,
            session_factory=session_factory,
            resolver_factory=resolver_factory,
            actions_factory=actions_factory,
            app_path=args.app,
            variables=variables,
            report_path=args.report,
        )
        
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report.get("status") == "passed" else 2
    
    if args.cmd == "inspect":
        result = inspect_window(
            jvm_path=args.jvm_path,
            window_title=args.window_title,
            max_depth=args.max_depth,
            include_invisible=args.include_invisible,
        )
        
        paths = write_inspect_outputs(result, out_dir=args.out)
        
        if args.emit_elements_yaml:
            yaml_path = emit_elements_yaml(
                result,
                out_path=args.emit_elements_yaml,
                window_name=args.emit_window_name,
            )
            paths["elements_yaml"] = yaml_path
        
        print(json.dumps({
            "status": "ok",
            "outputs": paths,
            "controls": len(result.get("controls", []))
        }, indent=2, ensure_ascii=False))
        return 0
    
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
