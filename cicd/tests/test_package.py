import os
import tarfile

import pytest

from splunk_cicd.errors import PackagingError
from splunk_cicd.package import build_package, list_package, read_manifest


def test_build_package_layout(app_dir, tmp_path):
    out = tmp_path / "dist"
    manifest = build_package(str(app_dir), str(out), expect_version="1.2.3")
    assert manifest["app"] == "myapp" and manifest["version"] == "1.2.3"
    assert os.path.basename(manifest["package"]) == "myapp-1.2.3.tar.gz"
    assert (out / "myapp-1.2.3.json").is_file()
    members = {name: (mode, is_dir) for name, mode, is_dir in list_package(manifest["package"])}
    assert "myapp" in members and members["myapp"][1]
    assert "myapp/default/app.conf" in members
    assert "myapp/default/data/ui/views/home.xml" in members
    assert "myapp/metadata/default.meta" in members
    assert not any(n.startswith("myapp/local") for n in members)
    assert "myapp/metadata/local.meta" not in members
    assert not any(".DS_Store" in n or "__pycache__" in n or "/._" in n for n in members)
    assert members["myapp/default/props.conf"][0] == 0o644
    assert members["myapp/bin/script.py"][0] == 0o755
    assert members["myapp/default"][0] == 0o755
    with tarfile.open(manifest["package"]) as tar:
        first = tar.getmembers()[0]
        assert first.name == "myapp" and first.isdir()
        assert all(m.uid == 0 and m.uname == "" for m in tar.getmembers())


def test_version_mismatch(app_dir, tmp_path):
    with pytest.raises(PackagingError):
        build_package(str(app_dir), str(tmp_path / "dist"), expect_version="9.9.9")


def test_dir_name_must_match_id(app_dir, tmp_path):
    renamed = app_dir.parent / "other"
    app_dir.rename(renamed)
    with pytest.raises(PackagingError):
        build_package(str(renamed), str(tmp_path / "dist"))


def test_read_manifest_fallback(app_dir, tmp_path):
    manifest = build_package(str(app_dir), str(tmp_path / "dist"))
    os.remove(tmp_path / "dist" / "myapp-1.2.3.json")
    parsed = read_manifest(manifest["package"])
    assert parsed["app"] == "myapp" and parsed["version"] == "1.2.3"
    assert parsed["sha256"] == manifest["sha256"]
