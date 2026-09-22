from .acs import APP_STATUS_DONE
from .errors import VerifyError


def verify_installed(acs, experience, app, expected_version=None):
    info = acs.describe_app(experience, app)
    if info is None:
        raise VerifyError(f"{app} is not installed on {acs.stack_id}")
    status = str(info.get("status", "")).lower()
    if status and not any(s in status for s in APP_STATUS_DONE):
        raise VerifyError(f"{app} is in status '{status}' on {acs.stack_id}")
    version = info.get("version")
    if expected_version and version != expected_version:
        raise VerifyError(f"{app} installed version is {version}, expected {expected_version}")
    return {"app": app, "version": version, "status": status or "installed", "stack": acs.stack_id}
