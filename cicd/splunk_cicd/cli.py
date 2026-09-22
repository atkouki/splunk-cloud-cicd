import argparse
import glob
import json
import os
import sys

from . import __version__
from .appconf import normalize_tag_version
from .deploy import Deployment, make_acs, make_appinspect, resolve_experience
from .envs import load_env
from .errors import CicdError
from .inspect_local import DEFAULT_TAGS, check_report, run_appinspect_cli
from .package import build_package, list_package, read_manifest
from .report import findings, summarize
from .verify import verify_installed


def _expand_package(value):
    matches = sorted(glob.glob(value))
    if len(matches) != 1:
        raise CicdError(f"expected exactly one package matching {value}, found {len(matches)}")
    return matches[0]


def _write_json(path, data):
    if not path:
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def cmd_package(args):
    expect = normalize_tag_version(args.expect_version) if args.expect_version else None
    manifest = build_package(args.app, args.out, expect_version=expect, extra_excludes=args.exclude or ())
    print(json.dumps(manifest, indent=2))
    if args.list:
        for name, mode, is_dir in list_package(manifest["package"]):
            print(f"{oct(mode)[-3:]} {'d' if is_dir else 'f'} {name}")
    return 0


def cmd_inspect_local(args):
    package = _expand_package(args.package)
    tags = args.tags.split(",") if args.tags else list(DEFAULT_TAGS)
    report = run_appinspect_cli(package, tags, args.report, binary=args.binary)
    summary = summarize(report, args.allow_manual)
    print(json.dumps(summary, indent=2))
    for item in findings(report, ("warning",)):
        print(f"[warning] {item['name']}: {item['messages'][0][:200] if item['messages'] else ''}")
    check_report(report, args.allow_manual)
    return 0


def cmd_inspect_api(args):
    package = _expand_package(args.package)
    tags = args.tags.split(",")
    client = make_appinspect()
    summary, report = client.validate(package, tags, allow_manual=args.allow_manual, timeout=args.timeout)
    _write_json(args.report, report)
    print(json.dumps(summary, indent=2))
    return 0


def _env_and_acs(args):
    env = load_env(args.env)
    return env, make_acs(env)


def cmd_acs_status(args):
    env, acs = _env_and_acs(args)
    status = acs.status()
    print(json.dumps({"stack": env.stack, "acs_server": env.resolved_acs_server(),
                      "experience": resolve_experience(env, acs, status), "status": status}, indent=2))
    return 0


def cmd_acs_apps(args):
    env, acs = _env_and_acs(args)
    experience = resolve_experience(env, acs)
    if args.name:
        print(json.dumps(acs.describe_app(experience, args.name), indent=2))
    else:
        print(json.dumps(acs.list_apps(experience), indent=2))
    return 0


def cmd_acs_indexes(args):
    env, acs = _env_and_acs(args)
    results = []
    for spec in env.indexes:
        action, detail = acs.ensure_index(spec, wait=not args.no_wait)
        results.append({"name": spec["name"], "action": action, "detail": detail})
        print(f"[{action}] {spec['name']}")
    _write_json(args.report, results)
    return 0


def cmd_acs_install(args):
    env, acs = _env_and_acs(args)
    package = _expand_package(args.package)
    manifest = read_manifest(package)
    experience = resolve_experience(env, acs)
    token = os.environ.get("APPINSPECT_TOKEN") or make_appinspect().login()
    print(json.dumps(acs.install_private(experience, package, token, app_name=manifest["app"], scope=args.scope), indent=2))
    if not args.no_wait:
        app = acs.wait_installed(experience, manifest["app"], timeout=env.install_timeout,
                                 expected_version=manifest["version"])
        print(json.dumps(app, indent=2))
    return 0


def cmd_acs_uninstall(args):
    env, acs = _env_and_acs(args)
    acs.uninstall(resolve_experience(env, acs), args.name)
    print(f"uninstall of {args.name} submitted")
    return 0


def cmd_acs_export(args):
    env, acs = _env_and_acs(args)
    client = acs.for_search_head(args.search_head or env.search_head) if (args.search_head or env.search_head) else acs
    out = args.out or f"backups/{args.name}.tar.gz"
    client.export_app(args.name, out, local=not args.no_local, users=args.users)
    print(out)
    return 0


def cmd_acs_deployment(args):
    env, acs = _env_and_acs(args)
    print(json.dumps(acs.deployment_retry() if args.retry else acs.deployment_status(args.id), indent=2))
    return 0


def cmd_verify(args):
    env, acs = _env_and_acs(args)
    result = verify_installed(acs, resolve_experience(env, acs), args.app or env.app, args.version)
    print(json.dumps(result, indent=2))
    return 0


def cmd_deploy(args):
    env = load_env(args.env)
    package = _expand_package(args.package)
    deployment = Deployment(env, package, backup_dir=None if args.no_backup else args.backup_dir,
                            skip_vetting=args.skip_vetting)
    try:
        result = deployment.run()
    except CicdError as exc:
        deployment.result["error"] = str(exc)
        _write_json(args.report, deployment.result)
        raise
    _write_json(args.report, result)
    print(json.dumps(result, indent=2))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="splunk-cicd", description="Package, vet and deploy Splunk apps to Splunk Cloud")
    parser.add_argument("--version", action="version", version=f"splunk-cicd {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("package", help="build <app>-<version>.tar.gz from an app directory")
    p.add_argument("--app", required=True)
    p.add_argument("--out", default="dist")
    p.add_argument("--expect-version", help="version or git tag the app.conf version must match")
    p.add_argument("--exclude", action="append", help="extra exclude glob")
    p.add_argument("--list", action="store_true")
    p.set_defaults(func=cmd_package)

    p = sub.add_parser("inspect-local", help="run the AppInspect CLI on a package")
    p.add_argument("--package", required=True)
    p.add_argument("--tags", help="comma separated, default cloud,private_victoria,private_classic")
    p.add_argument("--report", default="reports/appinspect-local.json")
    p.add_argument("--binary", default="splunk-appinspect")
    p.add_argument("--allow-manual", action="store_true")
    p.set_defaults(func=cmd_inspect_local)

    p = sub.add_parser("inspect-api", help="vet a package through the AppInspect API")
    p.add_argument("--package", required=True)
    p.add_argument("--tags", default="private_victoria")
    p.add_argument("--report", default="reports/appinspect-api.json")
    p.add_argument("--allow-manual", action="store_true")
    p.add_argument("--timeout", type=int, default=1800)
    p.set_defaults(func=cmd_inspect_api)

    acs = sub.add_parser("acs", help="talk to the Admin Config Service").add_subparsers(dest="acs_command", required=True)
    for name, func in (("status", cmd_acs_status), ("apps", cmd_acs_apps), ("indexes", cmd_acs_indexes),
                       ("install", cmd_acs_install), ("uninstall", cmd_acs_uninstall), ("export", cmd_acs_export),
                       ("deployment", cmd_acs_deployment)):
        p = acs.add_parser(name)
        p.add_argument("--env", required=True, help="environment yaml, e.g. envs/dev.yml")
        p.set_defaults(func=func)
        if name == "apps":
            p.add_argument("--name")
        elif name == "indexes":
            p.add_argument("--no-wait", action="store_true")
            p.add_argument("--report")
        elif name == "install":
            p.add_argument("--package", required=True)
            p.add_argument("--scope")
            p.add_argument("--no-wait", action="store_true")
        elif name == "uninstall":
            p.add_argument("--name", required=True)
        elif name == "export":
            p.add_argument("--name", required=True)
            p.add_argument("--out")
            p.add_argument("--search-head")
            p.add_argument("--no-local", action="store_true")
            p.add_argument("--users", action="store_true")
        elif name == "deployment":
            p.add_argument("--id")
            p.add_argument("--retry", action="store_true")

    p = sub.add_parser("verify", help="check the installed app version on a stack")
    p.add_argument("--env", required=True)
    p.add_argument("--app")
    p.add_argument("--version")
    p.set_defaults(func=cmd_verify)

    for name in ("deploy", "rollback"):
        p = sub.add_parser(name, help="vet then install or upgrade a package on an environment")
        p.add_argument("--env", required=True)
        p.add_argument("--package", required=True)
        p.add_argument("--backup-dir", default="backups")
        p.add_argument("--no-backup", action="store_true", default=(name == "rollback"))
        p.add_argument("--skip-vetting", action="store_true")
        p.add_argument("--report", default=None)
        p.set_defaults(func=cmd_deploy)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except CicdError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
