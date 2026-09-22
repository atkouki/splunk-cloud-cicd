import pytest

from splunk_cicd.errors import InspectError
from splunk_cicd.inspect_local import check_report, run_appinspect_cli
from conftest import write_report


def test_run_and_check(tmp_path, monkeypatch):
    report_path = tmp_path / "r.json"
    recorded = {}

    def fake_run(cmd, capture_output, text):
        recorded["cmd"] = cmd
        write_report(report_path, warning=1, checks=[("check_w", "warning", "meh")])
        return type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr("splunk_cicd.inspect_local.subprocess.run", fake_run)
    report = run_appinspect_cli("pkg.tar.gz", ["cloud", "private_victoria"], str(report_path))
    assert recorded["cmd"][:3] == ["splunk-appinspect", "inspect", "pkg.tar.gz"]
    assert recorded["cmd"].count("--included-tags") == 2
    assert check_report(report)["passed"]


def test_no_report(tmp_path, monkeypatch):
    def fake_run(cmd, capture_output, text):
        return type("P", (), {"returncode": 2, "stdout": "", "stderr": "boom"})()

    monkeypatch.setattr("splunk_cicd.inspect_local.subprocess.run", fake_run)
    with pytest.raises(InspectError, match="boom"):
        run_appinspect_cli("pkg.tar.gz", ["cloud"], str(tmp_path / "missing.json"))


def test_check_report_fails(tmp_path):
    report = write_report(tmp_path / "r.json", failure=1, checks=[("check_bad", "failure", "nope")])
    with pytest.raises(InspectError, match="check_bad"):
        check_report(report)
