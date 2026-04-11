"""Command line interface."""

from __future__ import annotations

import argparse
import json

from testpipe import bootstrap
from testpipe.core import PipelineCompiler, create_pipeline, list_pipelines
from testpipe.engine import TestEngine
from testpipe.loaders import TestCaseLoader
from testpipe.spec import EnvProfile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="testpipe")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a YAML test case")
    run_parser.add_argument("case_file")
    run_parser.add_argument("--output-root", default="runs")

    list_parser = subparsers.add_parser("list-pipelines", help="List registered pipelines")
    list_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    bootstrap()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list-pipelines":
        pipelines = list_pipelines()
        if args.json:
            print(json.dumps(pipelines, indent=2, ensure_ascii=False))
        else:
            for name in pipelines:
                print(name)
        return 0

    if args.command == "run":
        case = TestCaseLoader().load(args.case_file)
        pipeline = create_pipeline(case.pipeline)
        pipeline_spec = PipelineCompiler().compile(pipeline)
        summary = TestEngine(output_root=args.output_root).execute(
            case_spec=case,
            pipeline_spec=pipeline_spec,
            env_profile=EnvProfile.local_default(),
        )
        print(json.dumps(summary.to_dict(), indent=2, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
