import json

from splunk_cicd.cli import main


def test_package_command(app_dir, tmp_path, capsys):
    assert main(["package", "--app", str(app_dir), "--out", str(tmp_path / "dist"), "--expect-version", "v1.2.3"]) == 0
    out = capsys.readouterr().out
    assert json.loads(out)["version"] == "1.2.3"


def test_package_version_mismatch_exit_code(app_dir, tmp_path, capsys):
    assert main(["package", "--app", str(app_dir), "--out", str(tmp_path / "dist"), "--expect-version", "v9.0.0"]) == 2
    assert "does not match" in capsys.readouterr().err


def test_deploy_requires_secret(tmp_path, monkeypatch, capsys):
    (tmp_path / "dev.yml").write_text("stack: s\napp: a\n")
    (tmp_path / "a-1.0.0.tar.gz").write_bytes(b"")
    monkeypatch.delenv("ACS_TOKEN", raising=False)
    assert main(["deploy", "--env", str(tmp_path / "dev.yml"), "--package", str(tmp_path / "a-1.0.0.tar.gz")]) == 1
    assert "ACS_TOKEN" in capsys.readouterr().err
