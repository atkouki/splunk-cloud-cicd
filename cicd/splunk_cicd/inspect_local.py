import json
import os
import subprocess

from .errors import InspectError
from .report import format_findings, summarize

DEFAULT_TAGS = ("cloud", "private_victoria", "private_classic")


def run_appinspect_cli(package_path, tags=DEFAULT_TAGS, report_path="reports/appinspect-local.json",
                       binary="splunk-appinspect", mode="precert"):
    os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
    cmd = [binary, "inspect", package_path, "--mode", mode, "--data-format", "json", "--output-file", report_path]
    for tag in tags:
        cmd += ["--included-tags", tag]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as exc:
        raise InspectError(f"cannot run {binary}: {exc}") from exc
    if not os.path.isfile(report_path):
        detail = (proc.stderr or proc.stdout or "").strip()[-800:]
        raise InspectError(f"AppInspect produced no report (exit {proc.returncode}): {detail}")
    with open(report_path, encoding="utf-8") as fh:
        return json.load(fh)


def check_report(report, allow_manual=False):
    summary = summarize(report, allow_manual)
    if not summary["passed"]:
        raise InspectError(
            f"AppInspect failed: {summary['failure']} failure(s), {summary['error']} error(s), "
            f"{summary['manual_check']} manual check(s)\n{format_findings(report)}"
        )
    return summary
