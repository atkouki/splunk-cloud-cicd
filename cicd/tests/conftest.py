import json
import os
import textwrap

import pytest


class FakeResponse:
    def __init__(self, status_code=200, body=None, text=None, content=b""):
        self.status_code = status_code
        self._body = body
        self._text = text
        self.content = content

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body

    @property
    def text(self):
        if self._text is not None:
            return self._text
        return json.dumps(self._body) if self._body is not None else ""

    def iter_content(self, size):
        yield self.content


class FakeSession:
    def __init__(self):
        self.routes = {}
        self.calls = []

    def add(self, method, url, *responses):
        self.routes.setdefault((method.upper(), url), []).extend(responses)
        return self

    def request(self, method, url, **kwargs):
        key = (method.upper(), url)
        self.calls.append((method.upper(), url, kwargs))
        queue = self.routes.get(key)
        if not queue:
            raise AssertionError(f"unexpected {method} {url}")
        return queue.pop(0) if len(queue) > 1 else queue[0]

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def last(self, method=None):
        for call in reversed(self.calls):
            if method is None or call[0] == method.upper():
                return call
        raise AssertionError("no call recorded")


@pytest.fixture
def session():
    return FakeSession()


@pytest.fixture
def no_sleep():
    slept = []
    return slept.append, slept


@pytest.fixture
def app_dir(tmp_path):
    root = tmp_path / "myapp"
    (root / "default" / "data" / "ui" / "views").mkdir(parents=True)
    (root / "local").mkdir()
    (root / "bin").mkdir()
    (root / "metadata").mkdir()
    (root / "__pycache__").mkdir()
    (root / "default" / "app.conf").write_text(textwrap.dedent("""
        [id]
        name = myapp
        version = 1.2.3

        [package]
        id = myapp

        [launcher]
        version = 1.2.3
    """))
    (root / "default" / "props.conf").write_text("[st]\nSHOULD_LINEMERGE = false\n")
    (root / "default" / "data" / "ui" / "views" / "home.xml").write_text("<dashboard version=\"1.1\"/>")
    (root / "local" / "app.conf").write_text("[install]\nstate = enabled\n")
    (root / "bin" / "script.py").write_text("print('hi')\n")
    (root / "metadata" / "default.meta").write_text("[]\naccess = read : [ * ]\n")
    (root / "metadata" / "local.meta").write_text("[]\n")
    (root / ".DS_Store").write_bytes(b"\x00")
    (root / "__pycache__" / "x.pyc").write_bytes(b"\x00")
    (root / "default" / "._props.conf").write_bytes(b"\x00")
    os.chmod(root / "default" / "props.conf", 0o755)
    return root


def write_report(path, failure=0, error=0, manual=0, warning=0, checks=()):
    report = {
        "summary": {"failure": failure, "error": error, "manual_check": manual, "warning": warning, "success": 3},
        "reports": [{"groups": [{"checks": [
            {"name": name, "result": result, "messages": [{"message": msg}]} for name, result, msg in checks
        ]}]}],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh)
    return report
