import pytest

from splunk_cicd.envs import load_env
from splunk_cicd.errors import CicdError


def write(tmp_path, text, name="dev.yml"):
    path = tmp_path / name
    path.write_text(text)
    return str(path)


def test_staging_resolution(tmp_path, monkeypatch):
    monkeypatch.delenv("ACS_SERVER", raising=False)
    env = load_env(write(tmp_path, "stack: mystack.stg\napp: myapp\n"))
    assert env.name == "dev"
    assert env.is_staging and env.stack_id == "mystack"
    assert env.resolved_acs_server() == "https://staging.admin.splunk.com"
    assert env.experience == "auto" and env.indexes == []


def test_prod_and_override(tmp_path, monkeypatch):
    env = load_env(write(tmp_path, "name: prod\nstack: mystack\napp: myapp\nexperience: victoria\nindexes:\n  - name: idx\n    searchableDays: 30\n", "p.yml"))
    monkeypatch.delenv("ACS_SERVER", raising=False)
    assert env.resolved_acs_server() == "https://admin.splunk.com" and env.stack_id == "mystack"
    monkeypatch.setenv("ACS_SERVER", "https://admin.splunkcloudgc.com/")
    assert env.resolved_acs_server() == "https://admin.splunkcloudgc.com"
    assert env.indexes[0]["searchableDays"] == 30


@pytest.mark.parametrize("text", ["app: x\n", "stack: s\napp: a\nexperience: nope\n", "stack: s\napp: a\nindexes:\n  - datatype: event\n"])
def test_invalid(tmp_path, text):
    with pytest.raises(CicdError):
        load_env(write(tmp_path, text))
