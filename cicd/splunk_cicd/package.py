import fnmatch
import hashlib
import io
import json
import os
import subprocess
import tarfile
import time

from .appconf import app_id, app_version, read_app_conf
from .errors import PackagingError

DEFAULT_EXCLUDES = (
    ".DS_Store",
    "._*",
    ".git",
    ".gitignore",
    ".gitattributes",
    ".vscode",
    ".idea",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.bak",
    "*.swp",
    "*.map",
    "node_modules",
    "Thumbs.db",
)
TOP_LEVEL_EXCLUDES = ("local", "metadata/local.meta")
EXECUTABLE_DIRS = ("bin",)


def _excluded(rel_path, name, excludes):
    if rel_path in TOP_LEVEL_EXCLUDES or rel_path.split("/", 1)[0] in TOP_LEVEL_EXCLUDES:
        return True
    return any(fnmatch.fnmatch(name, pattern) for pattern in excludes)


def _git_sha(app_dir):
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=app_dir, capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_app_files(app_dir, excludes=DEFAULT_EXCLUDES):
    for root, dirs, files in os.walk(app_dir):
        rel_root = os.path.relpath(root, app_dir)
        rel_root = "" if rel_root == "." else rel_root.replace(os.sep, "/")
        dirs[:] = sorted(
            d for d in dirs
            if not _excluded(f"{rel_root}/{d}".strip("/"), d, excludes)
            and not os.path.islink(os.path.join(root, d))
        )
        for name in sorted(files):
            rel = f"{rel_root}/{name}".strip("/")
            full = os.path.join(root, name)
            if _excluded(rel, name, excludes) or os.path.islink(full):
                continue
            yield rel, full


def build_package(app_dir, out_dir, expect_version=None, extra_excludes=(), mtime=None):
    app_dir = os.path.abspath(app_dir)
    if not os.path.isdir(app_dir):
        raise PackagingError(f"app directory not found: {app_dir}")
    conf = read_app_conf(app_dir)
    name = app_id(app_dir, conf)
    version = app_version(app_dir, conf)
    if expect_version and expect_version != version:
        raise PackagingError(
            f"app.conf version {version} does not match expected version {expect_version}"
        )
    if os.path.basename(app_dir) != name:
        raise PackagingError(
            f"app directory name '{os.path.basename(app_dir)}' must equal [package] id '{name}'"
        )
    excludes = tuple(DEFAULT_EXCLUDES) + tuple(extra_excludes)
    if mtime is None:
        mtime = int(os.environ.get("SOURCE_DATE_EPOCH", time.time()))
    os.makedirs(out_dir, exist_ok=True)
    package_path = os.path.join(out_dir, f"{name}-{version}.tar.gz")
    count = 0
    with tarfile.open(package_path, "w:gz", format=tarfile.PAX_FORMAT) as tar:
        root = tarfile.TarInfo(name)
        root.type = tarfile.DIRTYPE
        root.mode = 0o755
        root.mtime = mtime
        tar.addfile(root)
        seen_dirs = {""}
        for rel, full in iter_app_files(app_dir, excludes):
            parent = os.path.dirname(rel)
            parts = parent.split("/") if parent else []
            for i in range(1, len(parts) + 1):
                sub = "/".join(parts[:i])
                if sub not in seen_dirs:
                    seen_dirs.add(sub)
                    info = tarfile.TarInfo(f"{name}/{sub}")
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    info.mtime = mtime
                    tar.addfile(info)
            info = tar.gettarinfo(full, arcname=f"{name}/{rel}")
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = mtime
            info.mode = 0o755 if rel.split("/", 1)[0] in EXECUTABLE_DIRS else 0o644
            with open(full, "rb") as fh:
                tar.addfile(info, fh)
            count += 1
    if count == 0:
        raise PackagingError("package would be empty")
    manifest = {
        "app": name,
        "version": version,
        "package": package_path,
        "sha256": _sha256(package_path),
        "files": count,
        "git_sha": _git_sha(app_dir),
        "built_at": int(time.time()),
    }
    with open(os.path.join(out_dir, f"{name}-{version}.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    return manifest


def list_package(package_path):
    with tarfile.open(package_path, "r:gz") as tar:
        return [(m.name, m.mode, m.isdir()) for m in tar.getmembers()]


def read_manifest(package_path):
    manifest_path = package_path[: -len(".tar.gz")] + ".json"
    if os.path.isfile(manifest_path):
        with open(manifest_path, encoding="utf-8") as fh:
            return json.load(fh)
    with tarfile.open(package_path, "r:gz") as tar:
        top = tar.getmembers()[0].name.split("/", 1)[0]
        member = tar.extractfile(f"{top}/default/app.conf")
        if member is None:
            raise PackagingError(f"{package_path} has no default/app.conf")
        text = io.TextIOWrapper(member, encoding="utf-8").read()
    version = None
    section = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
        elif "=" in line and section in ("launcher", "id") and line.split("=", 1)[0].strip() == "version":
            version = line.split("=", 1)[1].strip()
    return {"app": top, "version": version, "package": package_path, "sha256": _sha256(package_path)}
