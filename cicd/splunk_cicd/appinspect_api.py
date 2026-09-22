import os
import time

import requests

from .errors import InspectError
from .report import format_findings, summarize

LOGIN_URL = "https://api.splunk.com/2.0/rest/login/splunk"
VALIDATE_URL = "https://appinspect.splunk.com/v1/app/validate"
STATUS_URL = "https://appinspect.splunk.com/v1/app/validate/status/{request_id}"
REPORT_URL = "https://appinspect.splunk.com/v1/app/report/{request_id}"
PENDING = ("PROCESSING", "PREPARING", "PENDING", "QUEUED")


class AppInspectClient:
    def __init__(self, user, password, session=None, sleep=time.sleep, timeout=120):
        self.user = user
        self.password = password
        self.session = session or requests.Session()
        self.sleep = sleep
        self.timeout = timeout
        self.token = None

    def login(self):
        if self.token:
            return self.token
        resp = self.session.get(LOGIN_URL, auth=(self.user, self.password), timeout=self.timeout)
        if resp.status_code != 200:
            hint = ""
            if resp.status_code in (400, 401):
                hint = " (splunk.com rejected the credentials: use the splunk.com username, not the email, on a non-SSO account)"
            raise InspectError(f"AppInspect login failed with HTTP {resp.status_code}{hint}")
        try:
            self.token = resp.json()["data"]["token"]
        except (ValueError, KeyError, TypeError) as exc:
            raise InspectError("AppInspect login returned no token") from exc
        return self.token

    def _headers(self, accept=None):
        headers = {"Authorization": f"bearer {self.login()}"}
        if accept:
            headers["Accept"] = accept
        return headers

    def submit(self, package_path, tags):
        data = [("included_tags", tag) for tag in tags]
        with open(package_path, "rb") as fh:
            files = {"app_package": (os.path.basename(package_path), fh, "application/octet-stream")}
            resp = self.session.post(VALIDATE_URL, headers=self._headers(), files=files, data=data, timeout=self.timeout)
        if resp.status_code != 200:
            raise InspectError(f"AppInspect submit failed with HTTP {resp.status_code}: {resp.text[:300]}")
        try:
            return resp.json()["request_id"]
        except (ValueError, KeyError, TypeError) as exc:
            raise InspectError("AppInspect submit returned no request_id") from exc

    def wait(self, request_id, timeout=1800, interval=15):
        deadline = time.monotonic() + timeout
        while True:
            resp = self.session.get(STATUS_URL.format(request_id=request_id), headers=self._headers(), timeout=self.timeout)
            if resp.status_code != 200:
                raise InspectError(f"AppInspect status failed with HTTP {resp.status_code}: {resp.text[:300]}")
            body = resp.json()
            status = str(body.get("status", "")).upper()
            if status and status not in PENDING:
                return body
            if time.monotonic() > deadline:
                raise InspectError(f"AppInspect validation {request_id} still {status or 'pending'} after {timeout}s")
            self.sleep(interval)

    def report(self, request_id, tags=()):
        params = [("included_tags", tag) for tag in tags]
        resp = self.session.get(REPORT_URL.format(request_id=request_id), headers=self._headers("application/json"),
                                params=params, timeout=self.timeout)
        if resp.status_code != 200:
            raise InspectError(f"AppInspect report failed with HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def validate(self, package_path, tags, allow_manual=False, timeout=1800, interval=15):
        request_id = self.submit(package_path, tags)
        status = self.wait(request_id, timeout=timeout, interval=interval)
        if str(status.get("status", "")).upper() == "ERROR":
            raise InspectError(f"AppInspect validation {request_id} ended in ERROR: {status}")
        report = self.report(request_id, tags)
        summary = summarize(report, allow_manual)
        summary["request_id"] = request_id
        if not summary["passed"]:
            raise InspectError(
                f"AppInspect API vetting failed ({request_id}): {summary['failure']} failure(s), "
                f"{summary['error']} error(s), {summary['manual_check']} manual check(s)\n{format_findings(report)}"
            )
        return summary, report
