import pytest

from splunk_cicd.deploy import Deployment
from splunk_cicd.envs import EnvConfig
from splunk_cicd.errors import AcsError
from splunk_cicd.package import build_package


class StubAcs:
    def __init__(self, existing=None, export_error=None):
        self.stack_id = "stack"
        self.existing = existing
        self.export_error = export_error
        self.calls = []

    def status(self):
        return {"infrastructure": {"stackType": "victoria", "version": "9.4"}}

    def experience(self, status=None):
        return "victoria"

    def ensure_index(self, spec, **kw):
        self.calls.append(("index", spec["name"]))
        return "created", spec

    def describe_app(self, experience, name):
        self.calls.append(("describe", name))
        return self.existing

    def for_search_head(self, sh):
        return self

    def export_app(self, name, out):
        if self.export_error:
            raise self.export_error
        self.calls.append(("export", out))
        return out

    def install_private(self, experience, package, token, app_name=None, **kw):
        self.calls.append(("install", experience, token, app_name))
        self.existing = {"status": "installed", "version": "1.2.3"}
        return {"status": "uploaded"}

    def wait_installed(self, experience, name, timeout, expected_version=None):
        self.calls.append(("wait", name))
        return self.existing


class StubInspect:
    def __init__(self):
        self.validated = []

    def login(self):
        return "AI"

    def validate(self, package, tags, allow_manual=False):
        self.validated.append((tags, allow_manual))
        return {"request_id": "rid", "warning": 0, "passed": True}, {}


@pytest.fixture
def package(app_dir, tmp_path):
    return build_package(str(app_dir), str(tmp_path / "dist"))["package"]


def env(**overrides):
    base = dict(name="dev", stack="s.stg", app="myapp", indexes=[{"name": "idx"}])
    base.update(overrides)
    return EnvConfig(**base)


def test_full_flow_upgrade_with_backup(package, tmp_path):
    acs = StubAcs(existing={"status": "installed", "version": "1.0.0"})
    inspect = StubInspect()
    result = Deployment(env(), package, backup_dir=str(tmp_path / "b"), log=lambda m: None, acs=acs, appinspect=inspect).run()
    steps = [s["step"] for s in result["steps"]]
    assert steps == ["stack", "index", "backup", "vetting", "install", "install", "verify"]
    assert result["ok"] and result["previous_version"] == "1.0.0" and result["experience"] == "victoria"
    assert inspect.validated == [(["private_victoria"], False)]
    assert ("install", "victoria", "AI", "myapp") in acs.calls
    assert result["steps"][4]["action"] == "upgrade"


def test_backup_skipped_when_export_fails(package, tmp_path):
    acs = StubAcs(existing={"version": "1.0.0"}, export_error=AcsError("nope", status=403))
    result = Deployment(env(), package, backup_dir=str(tmp_path), log=lambda m: None, acs=acs, appinspect=StubInspect()).run()
    assert [s for s in result["steps"] if s["step"] == "backup"][0]["status"] == "skipped"


def test_backup_required(package, tmp_path):
    acs = StubAcs(existing={"version": "1.0.0"}, export_error=AcsError("nope", status=403))
    with pytest.raises(AcsError):
        Deployment(env(require_backup=True), package, backup_dir=str(tmp_path), log=lambda m: None, acs=acs, appinspect=StubInspect()).run()


def test_fresh_install_skip_vetting_custom_tags(package, tmp_path):
    acs = StubAcs()
    inspect = StubInspect()
    result = Deployment(env(inspect_tags=["cloud"], experience="classic"), package, backup_dir=str(tmp_path),
                        skip_vetting=True, log=lambda m: None, acs=acs, appinspect=inspect).run()
    steps = [(s["step"], s["status"]) for s in result["steps"]]
    assert ("vetting", "skipped") in steps and ("backup", "ok") not in [s[:2] for s in steps]
    assert inspect.validated == [] and result["experience"] == "classic"
    assert result["steps"][-3]["action"] == "install"
