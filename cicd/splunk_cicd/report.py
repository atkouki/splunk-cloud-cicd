BLOCKING = ("failure", "error")


def summarize(report, allow_manual=False):
    summary = dict(report.get("summary") or {})
    failures = int(summary.get("failure", 0))
    errors = int(summary.get("error", 0))
    manual = int(summary.get("manual_check", 0))
    passed = failures == 0 and errors == 0 and (manual == 0 or allow_manual)
    return {
        "passed": passed,
        "failure": failures,
        "error": errors,
        "manual_check": manual,
        "warning": int(summary.get("warning", 0)),
        "success": int(summary.get("success", 0)),
        "future_failure": int(summary.get("future_failure", 0)),
    }


def findings(report, results=("failure", "error", "manual_check", "warning")):
    found = []
    for rep in report.get("reports") or []:
        for group in rep.get("groups") or []:
            for check in group.get("checks") or []:
                if check.get("result") in results:
                    messages = [m.get("message", "") for m in check.get("messages") or []]
                    found.append({"result": check["result"], "name": check.get("name"), "messages": messages})
    return found


def format_findings(report, results=("failure", "error", "manual_check")):
    lines = []
    for item in findings(report, results):
        head = f"[{item['result']}] {item['name']}"
        if item["messages"]:
            lines.append(f"{head}: {item['messages'][0][:300]}")
            lines.extend(f"    {m[:300]}" for m in item["messages"][1:5])
        else:
            lines.append(head)
    return "\n".join(lines)
