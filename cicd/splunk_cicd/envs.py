import os
from dataclasses import dataclass, field

import yaml

from .errors import CicdError

STAGING_ACS = "https://staging.admin.splunk.com"
PROD_ACS = "https://admin.splunk.com"
EXPERIENCES = ("auto", "victoria", "classic")


@dataclass
class EnvConfig:
    name: str
    stack: str
    app: str
    experience: str = "auto"
    acs_server: str = ""
    search_head: str = ""
    indexes: list = field(default_factory=list)
    inspect_tags: list = field(default_factory=list)
    allow_manual_checks: bool = False
    install_timeout: int = 900
    backup_before_install: bool = True
    require_backup: bool = False
    path: str = ""

    @property
    def stack_id(self):
        return self.stack[: -len(".stg")] if self.stack.endswith(".stg") else self.stack

    @property
    def is_staging(self):
        return self.stack.endswith(".stg") or "-shw" in self.stack or self.stack.startswith("stg-")

    def resolved_acs_server(self):
        server = os.environ.get("ACS_SERVER") or self.acs_server
        if server:
            return server.rstrip("/")
        return STAGING_ACS if self.is_staging else PROD_ACS


def load_env(path):
    if not os.path.isfile(path):
        raise CicdError(f"environment file not found: {path}")
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    missing = [key for key in ("stack", "app") if not data.get(key)]
    if missing:
        raise CicdError(f"{path}: missing required keys {', '.join(missing)}")
    experience = str(data.get("experience", "auto")).lower()
    if experience not in EXPERIENCES:
        raise CicdError(f"{path}: experience must be one of {', '.join(EXPERIENCES)}")
    indexes = data.get("indexes") or []
    for index in indexes:
        if not isinstance(index, dict) or not index.get("name"):
            raise CicdError(f"{path}: every index needs a name")
    return EnvConfig(
        name=str(data.get("name") or os.path.splitext(os.path.basename(path))[0]),
        stack=str(data["stack"]),
        app=str(data["app"]),
        experience=experience,
        acs_server=str(data.get("acs_server") or ""),
        search_head=str(data.get("search_head") or ""),
        indexes=indexes,
        inspect_tags=list(data.get("inspect_tags") or []),
        allow_manual_checks=bool(data.get("allow_manual_checks", False)),
        install_timeout=int(data.get("install_timeout", 900)),
        backup_before_install=bool(data.get("backup_before_install", True)),
        require_backup=bool(data.get("require_backup", False)),
        path=path,
    )


def require_secret(name):
    value = os.environ.get(name)
    if not value:
        raise CicdError(f"missing environment variable {name}")
    return value
