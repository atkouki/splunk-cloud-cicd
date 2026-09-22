import json
import os
import time

import requests

from .errors import AcsError

APP_STATUS_DONE = ("installed", "ready", "success", "completed", "enabled")
APP_STATUS_FAILED = ("failed", "error")
RETRY_STATUSES = (424, 429, 503)
MUTABLE_INDEX_FIELDS = ("searchableDays", "maxDataSizeMB", "splunkArchivalRetentionDays", "selfStorageBucketPath")


def acs_error_message(response):
    try:
        body = response.json()
    except ValueError:
        return response.text.strip()[:500]
    if isinstance(body, dict):
        message = body.get("message") or body.get("error") or body.get("code")
        if isinstance(message, str):
            try:
                nested = json.loads(message)
            except ValueError:
                return message
            if isinstance(nested, dict) and nested.get("messages"):
                return "; ".join(str(m.get("text", "")) for m in nested["messages"])
            return message
        return json.dumps(body)[:500]
    return str(body)[:500]


def _raise(response, action):
    raise AcsError(f"ACS {action} failed with HTTP {response.status_code}: {acs_error_message(response)}",
                   status=response.status_code, body=response.text[:2000])


class AcsClient:
    def __init__(self, server, stack_id, token, session=None, sleep=time.sleep, timeout=120):
        self.server = server.rstrip("/")
        self.stack_id = stack_id
        self.token = token
        self.session = session or requests.Session()
        self.sleep = sleep
        self.timeout = timeout

    @property
    def base(self):
        return f"{self.server}/{self.stack_id}/adminconfig/v2"

    def for_search_head(self, search_head):
        return AcsClient(self.server, f"{search_head}.{self.stack_id}", self.token, self.session, self.sleep, self.timeout)

    def _headers(self, extra=None):
        headers = {"Authorization": f"Bearer {self.token}"}
        if extra:
            headers.update(extra)
        return headers

    def request(self, method, path, retries=6, backoff=10, **kwargs):
        headers = self._headers(kwargs.pop("headers", None))
        timeout = kwargs.pop("timeout", self.timeout)
        attempt = 0
        while True:
            resp = self.session.request(method, self.base + path, headers=headers, timeout=timeout, **kwargs)
            if resp.status_code in RETRY_STATUSES and attempt < retries:
                attempt += 1
                self.sleep(backoff * attempt)
                continue
            return resp

    def status(self):
        resp = self.request("GET", "/status")
        if resp.status_code != 200:
            _raise(resp, "status")
        return resp.json()

    def experience(self, status=None):
        status = status if status is not None else self.status()
        stack_type = str(((status.get("infrastructure") or {}).get("stackType")) or status.get("stackType") or "").lower()
        if stack_type in ("victoria", "classic"):
            return stack_type
        probe = self.request("GET", "/apps/victoria", retries=0)
        return "victoria" if probe.status_code == 200 else "classic"

    @staticmethod
    def apps_path(experience):
        return "/apps/victoria" if experience == "victoria" else "/apps"

    def list_apps(self, experience):
        resp = self.request("GET", self.apps_path(experience))
        if resp.status_code != 200:
            _raise(resp, "list apps")
        body = resp.json()
        return body.get("apps", []) if isinstance(body, dict) else body

    def describe_app(self, experience, name):
        resp = self.request("GET", f"{self.apps_path(experience)}/{name}")
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            _raise(resp, f"describe app {name}")
        return resp.json()

    def _upload(self, method, path, package_path, appinspect_token, experience, scope=None, max_attempts=30, backoff=20):
        params = {"scope": scope} if scope else None
        headers = {"ACS-Legal-Ack": "Y"}
        data = None
        if experience == "victoria":
            headers["X-Splunk-Authorization"] = appinspect_token
        else:
            data = {"token": appinspect_token}
        attempt = 0
        while True:
            attempt += 1
            with open(package_path, "rb") as fh:
                files = {"package": (os.path.basename(package_path), fh, "application/octet-stream")}
                resp = self.session.request(method, self.base + path, headers=self._headers(headers), params=params,
                                            files=files, data=data, timeout=max(self.timeout, 600))
            if resp.status_code in RETRY_STATUSES and attempt < max_attempts:
                self.sleep(backoff)
                continue
            return resp

    def install_private(self, experience, package_path, appinspect_token, app_name=None, scope=None,
                        max_attempts=30, backoff=20):
        path = self.apps_path(experience)
        resp = self._upload("POST", path, package_path, appinspect_token, experience, scope, max_attempts, backoff)
        if resp.status_code == 409 and app_name:
            resp = self._upload("PATCH", f"{path}/{app_name}", package_path, appinspect_token, experience, scope,
                                max_attempts, backoff)
        if resp.status_code not in (200, 201, 202):
            _raise(resp, f"install {os.path.basename(package_path)}")
        try:
            return resp.json()
        except ValueError:
            return {"status": "accepted", "http": resp.status_code}

    def wait_installed(self, experience, name, timeout=900, interval=10, expected_version=None):
        deadline = time.monotonic() + timeout
        last = None
        while True:
            app = self.describe_app(experience, name)
            if app is not None:
                last = app
                status = str(app.get("status", "")).lower()
                version_ok = expected_version is None or app.get("version") == expected_version
                if any(s in status for s in APP_STATUS_FAILED):
                    raise AcsError(f"ACS reports app {name} in status '{status}': {app}")
                if version_ok and (not status or any(s in status for s in APP_STATUS_DONE)):
                    return app
            if time.monotonic() > deadline:
                raise AcsError(f"timed out after {timeout}s waiting for {name} to be installed (last: {last})")
            self.sleep(interval)

    def uninstall(self, experience, name):
        resp = self.request("DELETE", f"{self.apps_path(experience)}/{name}")
        if resp.status_code not in (200, 202, 204):
            _raise(resp, f"uninstall {name}")
        return True

    def export_app(self, name, out_path, local=True, users=False, confs_only=False):
        params = {"local": str(local).lower(), "users": str(users).lower(), "confs_only": str(confs_only).lower()}
        resp = self.request("GET", f"/apps/victoria/export/download/{name}", params=params, stream=True, timeout=600)
        if resp.status_code != 200:
            _raise(resp, f"export {name}")
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "wb") as fh:
            for chunk in resp.iter_content(1 << 20):
                fh.write(chunk)
        return out_path

    def get_index(self, name):
        resp = self.request("GET", f"/indexes/{name}")
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            _raise(resp, f"describe index {name}")
        return resp.json()

    def ensure_index(self, spec, wait=True, timeout=600, interval=15):
        name = spec["name"]
        current = self.get_index(name)
        if current is None:
            body = {"name": name, "datatype": spec.get("datatype", "event")}
            for field in MUTABLE_INDEX_FIELDS:
                if field in spec:
                    body[field] = spec[field]
            resp = self.request("POST", "/indexes", json=body, headers={"Content-Type": "application/json"})
            if resp.status_code not in (200, 201, 202):
                _raise(resp, f"create index {name}")
            if wait:
                deadline = time.monotonic() + timeout
                while self.get_index(name) is None:
                    if time.monotonic() > deadline:
                        raise AcsError(f"index {name} not visible after {timeout}s")
                    self.sleep(interval)
            return "created", body
        changes = {f: spec[f] for f in MUTABLE_INDEX_FIELDS if f in spec and current.get(f) != spec[f]}
        if not changes:
            return "unchanged", current
        resp = self.request("PATCH", f"/indexes/{name}", json=changes, headers={"Content-Type": "application/json"})
        if resp.status_code not in (200, 202):
            _raise(resp, f"update index {name}")
        return "updated", changes

    def deployment_status(self, deployment_id=None):
        path = "/deployment/status" + (f"/{deployment_id}" if deployment_id else "")
        resp = self.request("GET", path)
        if resp.status_code != 200:
            _raise(resp, "deployment status")
        return resp.json()

    def deployment_retry(self):
        resp = self.request("POST", "/deployment/retry")
        if resp.status_code not in (200, 202):
            _raise(resp, "deployment retry")
        return resp.json() if resp.text else {}
