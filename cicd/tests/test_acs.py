import pytest

from splunk_cicd.acs import AcsClient, acs_error_message
from splunk_cicd.errors import AcsError
from conftest import FakeResponse

BASE = "https://admin.splunk.com/stack/adminconfig/v2"


def client(session, no_sleep):
    return AcsClient("https://admin.splunk.com/", "stack", "tok", session=session, sleep=no_sleep[0])


def test_experience_from_status(session, no_sleep):
    session.add("GET", BASE + "/status", FakeResponse(200, {"infrastructure": {"stackType": "Victoria"}}))
    assert client(session, no_sleep).experience() == "victoria"
    assert session.last()[2]["headers"]["Authorization"] == "Bearer tok"


def test_experience_probe_fallback(session, no_sleep):
    session.add("GET", BASE + "/apps/victoria", FakeResponse(403, {"message": "nope"}))
    assert client(session, no_sleep).experience({}) == "classic"


def test_install_victoria_headers(session, no_sleep, tmp_path):
    pkg = tmp_path / "a.tar.gz"
    pkg.write_bytes(b"x")
    session.add("POST", BASE + "/apps/victoria", FakeResponse(202, {"status": "uploaded"}))
    body = client(session, no_sleep).install_private("victoria", str(pkg), "ai-token")
    assert body["status"] == "uploaded"
    kwargs = session.last("POST")[2]
    assert kwargs["headers"]["X-Splunk-Authorization"] == "ai-token"
    assert kwargs["headers"]["ACS-Legal-Ack"] == "Y"
    assert "package" in kwargs["files"] and kwargs["data"] is None


def test_install_classic_token_field_and_retry(session, no_sleep, tmp_path):
    pkg = tmp_path / "a.tar.gz"
    pkg.write_bytes(b"x")
    session.add("POST", BASE + "/apps", FakeResponse(424, {"message": "deployment task is still in progress"}), FakeResponse(200, {"name": "a"}))
    client(session, no_sleep).install_private("classic", str(pkg), "ai-token", backoff=5)
    posts = [c for c in session.calls if c[0] == "POST"]
    assert len(posts) == 2 and posts[-1][2]["data"] == {"token": "ai-token"}
    assert "X-Splunk-Authorization" not in posts[-1][2]["headers"]
    assert no_sleep[1] == [5]


def test_install_error_message(session, no_sleep, tmp_path):
    pkg = tmp_path / "a.tar.gz"
    pkg.write_bytes(b"x")
    session.add("POST", BASE + "/apps/victoria", FakeResponse(400, {"code": "400-bad", "message": "This app has failed AppInspect validation"}))
    with pytest.raises(AcsError, match="failed AppInspect validation"):
        client(session, no_sleep).install_private("victoria", str(pkg), "t", max_attempts=1)


def test_wait_installed(session, no_sleep):
    session.add("GET", BASE + "/apps/victoria/a", FakeResponse(404, {}), FakeResponse(200, {"status": "uploaded"}),
                FakeResponse(200, {"status": "installed", "version": "1.0.0"}))
    app = client(session, no_sleep).wait_installed("victoria", "a", timeout=60, interval=1, expected_version="1.0.0")
    assert app["version"] == "1.0.0" and len(no_sleep[1]) == 2


def test_wait_installed_failure(session, no_sleep):
    session.add("GET", BASE + "/apps/victoria/a", FakeResponse(200, {"status": "failed"}))
    with pytest.raises(AcsError, match="failed"):
        client(session, no_sleep).wait_installed("victoria", "a", timeout=5, interval=1)


def test_ensure_index_create(session, no_sleep):
    session.add("GET", BASE + "/indexes/idx", FakeResponse(404, {}), FakeResponse(200, {"name": "idx"}))
    session.add("POST", BASE + "/indexes", FakeResponse(202, {}))
    action, body = client(session, no_sleep).ensure_index({"name": "idx", "searchableDays": 30}, interval=1)
    assert action == "created" and body == {"name": "idx", "datatype": "event", "searchableDays": 30}
    assert session.last("POST")[2]["json"] == body


def test_ensure_index_unchanged_and_update(session, no_sleep):
    session.add("GET", BASE + "/indexes/idx", FakeResponse(200, {"name": "idx", "searchableDays": 30, "maxDataSizeMB": 0}))
    session.add("PATCH", BASE + "/indexes/idx", FakeResponse(202, {}))
    c = client(session, no_sleep)
    assert c.ensure_index({"name": "idx", "searchableDays": 30})[0] == "unchanged"
    action, changes = c.ensure_index({"name": "idx", "searchableDays": 90})
    assert action == "updated" and changes == {"searchableDays": 90}


def test_error_message_unwraps_nested_json():
    resp = FakeResponse(400, {"code": "x", "message": '{"messages":[{"type":"ERROR","text":"inner detail"}]}'})
    assert acs_error_message(resp) == "inner detail"
    assert acs_error_message(FakeResponse(500, text="plain")) == "plain"


def test_search_head_base(session, no_sleep):
    c = client(session, no_sleep).for_search_head("sh-i-abc")
    assert c.base == "https://admin.splunk.com/sh-i-abc.stack/adminconfig/v2"


def test_install_conflict_falls_back_to_patch(session, no_sleep, tmp_path):
    pkg = tmp_path / "a.tar.gz"
    pkg.write_bytes(b"x")
    session.add("POST", BASE + "/apps/victoria", FakeResponse(409, {"message": "object-already-exists"}))
    session.add("PATCH", BASE + "/apps/victoria/a", FakeResponse(202, {"status": "uploaded"}))
    body = client(session, no_sleep).install_private("victoria", str(pkg), "t", app_name="a")
    assert body["status"] == "uploaded"
    patch = session.last("PATCH")[2]
    assert patch["headers"]["X-Splunk-Authorization"] == "t" and "package" in patch["files"]
