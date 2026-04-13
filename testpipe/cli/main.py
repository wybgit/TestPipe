"""Command line interface."""

from __future__ import annotations

import argparse
import json

import yaml

from testpipe import bootstrap
from testpipe.core import PipelineCompiler, create_pipeline, list_pipelines
from testpipe.engine import TestEngine
from testpipe.loaders import EnvProfileLoader, StructuredLoader, TestCaseLoader
from testpipe.spec import EnvProfile
from testpipe.skills import SkillRunner, get_skill, list_skills
from testpipe.templates import get_template, list_templates
from testpipe.validation import CaseChecker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="testpipe")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a YAML test case")
    run_parser.add_argument("case_file")
    run_parser.add_argument("--output-root", default="runs")
    run_parser.add_argument("--env-profile", default=None, help="YAML/JSON env profile file; defaults to local_default")
    run_parser.add_argument("--debug", action="store_true", help="Write debug snapshots, step records, trace, and reproduce script")

    check_case_parser = subparsers.add_parser("check-case", help="Validate a YAML test case against its pipeline contract")
    check_case_parser.add_argument("case_file")
    check_case_parser.add_argument("--json", action="store_true")

    list_parser = subparsers.add_parser("list-pipelines", help="List registered pipelines")
    list_parser.add_argument("--json", action="store_true")

    list_templates_parser = subparsers.add_parser("list-templates", help="List built-in LLM templates")
    list_templates_parser.add_argument("--json", action="store_true")

    show_template_parser = subparsers.add_parser("show-template", help="Show a built-in LLM template")
    show_template_parser.add_argument("name")
    show_template_parser.add_argument("--json", action="store_true")

    list_skills_parser = subparsers.add_parser("list-skills", help="List built-in LLM skills")
    list_skills_parser.add_argument("--json", action="store_true")

    show_skill_parser = subparsers.add_parser("show-skill", help="Show a built-in LLM skill contract")
    show_skill_parser.add_argument("name")
    show_skill_parser.add_argument("--json", action="store_true")

    run_skill_parser = subparsers.add_parser("run-skill", help="Execute a built-in skill against a YAML/JSON template input")
    run_skill_parser.add_argument("name")
    run_skill_parser.add_argument("input_file")
    run_skill_parser.add_argument("--json", action="store_true")
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

    if args.command == "list-templates":
        templates = list_templates()
        if args.json:
            print(json.dumps(templates, indent=2, ensure_ascii=False))
        else:
            for name in templates:
                print(name)
        return 0

    if args.command == "show-template":
        template = get_template(args.name)
        if args.json:
            print(json.dumps(template.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(yaml.safe_dump(template.body, allow_unicode=True, sort_keys=False).rstrip())
        return 0

    if args.command == "list-skills":
        skills = list_skills()
        if args.json:
            print(json.dumps(skills, indent=2, ensure_ascii=False))
        else:
            for name in skills:
                print(name)
        return 0

    if args.command == "show-skill":
        skill = get_skill(args.name)
        if args.json:
            print(json.dumps(skill.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(yaml.safe_dump(skill.to_dict(), allow_unicode=True, sort_keys=False).rstrip())
        return 0

    if args.command == "run-skill":
        payload = StructuredLoader().load(args.input_file)
        result = SkillRunner().run(args.name, payload)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(yaml.safe_dump(result, allow_unicode=True, sort_keys=False).rstrip())
        return 0

    if args.command == "run":
        case = TestCaseLoader().load(args.case_file)
        pipeline = create_pipeline(case.pipeline)
        pipeline_spec = PipelineCompiler().compile(pipeline)
        env_profile = EnvProfile.local_default() if args.env_profile is None else EnvProfileLoader().load(args.env_profile)
        TestEngine(output_root=args.output_root, debug=args.debug).execute(
            case_spec=case,
            pipeline_spec=pipeline_spec,
            env_profile=env_profile,
        )
        return 0

    if args.command == "check-case":
        case = TestCaseLoader().load(args.case_file)
        pipeline = create_pipeline(case.pipeline)
        pipeline_spec = PipelineCompiler().compile(pipeline)
        report = CaseChecker().check(case, pipeline_spec)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(yaml.safe_dump(report.to_dict(), allow_unicode=True, sort_keys=False).rstrip())
        return 0 if report.status != "fail" else 2

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
