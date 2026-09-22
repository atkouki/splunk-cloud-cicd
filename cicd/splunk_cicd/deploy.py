import os
import time

from .acs import AcsClient
from .appinspect_api import AppInspectClient
from .envs import require_secret
from .errors import AcsError
from .package import read_manifest
from .verify import verify_installed


def make_acs(env):
    return AcsClient(env.resolved_acs_server(), env.stack_id, require_secret("ACS_TOKEN"))


def make_appinspect():
    return AppInspectClient(require_secret("SPLUNKCOM_USER"), require_secret("SPLUNKCOM_PASSWORD"))


def resolve_experience(env, acs, status=None):
    if env.experience != "auto":
        return env.experience
    return acs.experience(status)


class Deployment:
    def __init__(self, env, package_path, backup_dir=None, skip_vetting=False, log=print,
                 acs=None, appinspect=None):
        self.env = env
        self.package_path = package_path
        self.backup_dir = backup_dir
        self.skip_vetting = skip_vetting
        self.log = log
        self.acs = acs or make_acs(env)
        self.appinspect = appinspect or make_appinspect()
        self.manifest = read_manifest(package_path)
        self.result = {
            "env": env.name,
            "stack": env.stack,
            "app": self.manifest["app"],
            "version": self.manifest["version"],
            "package": os.path.basename(package_path),
            "sha256": self.manifest.get("sha256"),
            "steps": [],
            "ok": False,
        }

    def step(self, kind, outcome, **detail):
        entry = {"step": kind, "status": outcome, "at": int(time.time())}
        entry.update({k: v for k, v in detail.items() if k not in entry})
        self.result["steps"].append(entry)
        extra = " ".join(f"{k}={v}" for k, v in detail.items() if v not in (None, ""))
        self.log(f"[{outcome}] {kind} {extra}".rstrip())
        return entry

    def run(self):
        app = self.manifest["app"]
        version = self.manifest["version"]
        status = self.acs.status()
        experience = resolve_experience(self.env, self.acs, status)
        self.result["experience"] = experience
        self.step("stack", "ok", experience=experience, version=(status.get("infrastructure") or {}).get("version"))

        for spec in self.env.indexes:
            action, _ = self.acs.ensure_index(spec)
            self.step("index", "ok", name=spec["name"], action=action)

        existing = self.acs.describe_app(experience, app)
        self.result["previous_version"] = existing.get("version") if existing else None
        if existing and experience == "victoria" and self.env.backup_before_install and self.backup_dir:
            backup = os.path.join(self.backup_dir, f"{app}-{existing.get('version') or 'unknown'}-{int(time.time())}.tar.gz")
            client = self.acs.for_search_head(self.env.search_head) if self.env.search_head else self.acs
            try:
                client.export_app(app, backup)
                self.step("backup", "ok", path=backup)
            except AcsError as exc:
                if self.env.require_backup:
                    raise
                self.step("backup", "skipped", reason=str(exc)[:200])

        tags = list(self.env.inspect_tags) or [f"private_{experience}"]
        appinspect_token = self.appinspect.login()
        if self.skip_vetting:
            self.step("vetting", "skipped")
        else:
            summary, _ = self.appinspect.validate(self.package_path, tags, allow_manual=self.env.allow_manual_checks)
            self.step("vetting", "ok", request_id=summary["request_id"], warnings=summary["warning"])

        self.acs.install_private(experience, self.package_path, appinspect_token, app_name=app)
        self.step("install", "submitted", action="upgrade" if existing else "install")
        installed = self.acs.wait_installed(experience, app, timeout=self.env.install_timeout, expected_version=version)
        self.step("install", "ok", status=installed.get("status"), version=installed.get("version"))

        verified = verify_installed(self.acs, experience, app, version)
        self.step("verify", "ok", version=verified["version"], app_status=verified["status"])
        self.result["ok"] = True
        return self.result
