import pytest

from splunk_cicd.appinspect_api import LOGIN_URL, REPORT_URL, STATUS_URL, VALIDATE_URL, AppInspectClient
from splunk_cicd.errors import InspectError
from conftest import FakeResponse, write_report


def make(session, no_sleep):
    return AppInspectClient("user", "pw", session=session, sleep=no_sleep[0])


def test_login_ok(session, no_sleep):
    session.add("GET", LOGIN_URL, FakeResponse(200, {"data": {"token": "T"}}))
    c = make(session, no_sleep)
    assert c.login() == "T" and c.login() == "T"
    assert session.last()[2]["auth"] == ("user", "pw")
    assert len(session.calls) == 1


def test_login_rejected(session, no_sleep):
    session.add("GET", LOGIN_URL, FakeResponse(400, {"error": "invalid_grant"}))
    with pytest.raises(InspectError, match="splunk.com rejected"):
        make(session, no_sleep).login()


def test_validate_pass(session, no_sleep, tmp_path):
    pkg = tmp_path / "a.tar.gz"
    pkg.write_bytes(b"x")
    report = write_report(tmp_path / "r.json")
    session.add("GET", LOGIN_URL, FakeResponse(200, {"data": {"token": "T"}}))
    session.add("POST", VALIDATE_URL, FakeResponse(200, {"request_id": "rid"}))
    session.add("GET", STATUS_URL.format(request_id="rid"), FakeResponse(200, {"status": "PROCESSING"}), FakeResponse(200, {"status": "SUCCESS"}))
    session.add("GET", REPORT_URL.format(request_id="rid"), FakeResponse(200, report))
    summary, _ = make(session, no_sleep).validate(str(pkg), ["private_victoria"], interval=1)
    assert summary["passed"] and summary["request_id"] == "rid"
    post = session.last("POST")[2]
    assert post["data"] == [("included_tags", "private_victoria")] and "app_package" in post["files"]
    assert post["headers"]["Authorization"] == "bearer T"


def test_validate_fail(session, no_sleep, tmp_path):
    pkg = tmp_path / "a.tar.gz"
    pkg.write_bytes(b"x")
    report = write_report(tmp_path / "r.json", failure=1, checks=[("check_x", "failure", "bad thing")])
    session.add("GET", LOGIN_URL, FakeResponse(200, {"data": {"token": "T"}}))
    session.add("POST", VALIDATE_URL, FakeResponse(200, {"request_id": "rid"}))
    session.add("GET", STATUS_URL.format(request_id="rid"), FakeResponse(200, {"status": "SUCCESS"}))
    session.add("GET", REPORT_URL.format(request_id="rid"), FakeResponse(200, report))
    with pytest.raises(InspectError, match="check_x"):
        make(session, no_sleep).validate(str(pkg), ["private_victoria"])


def test_manual_checks_allowed(session, no_sleep, tmp_path):
    pkg = tmp_path / "a.tar.gz"
    pkg.write_bytes(b"x")
    report = write_report(tmp_path / "r.json", manual=2)
    session.add("GET", LOGIN_URL, FakeResponse(200, {"data": {"token": "T"}}))
    session.add("POST", VALIDATE_URL, FakeResponse(200, {"request_id": "rid"}))
    session.add("GET", STATUS_URL.format(request_id="rid"), FakeResponse(200, {"status": "SUCCESS"}))
    session.add("GET", REPORT_URL.format(request_id="rid"), FakeResponse(200, report))
    c = make(session, no_sleep)
    with pytest.raises(InspectError):
        c.validate(str(pkg), ["cloud"])
    assert c.validate(str(pkg), ["cloud"], allow_manual=True)[0]["manual_check"] == 2
