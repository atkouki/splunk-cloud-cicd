import pytest

from splunk_cicd.appconf import app_id, app_version, normalize_tag_version
from splunk_cicd.errors import PackagingError


def test_id_and_version(app_dir):
    assert app_id(str(app_dir)) == "myapp"
    assert app_version(str(app_dir)) == "1.2.3"


def test_invalid_version(app_dir):
    (app_dir / "default" / "app.conf").write_text("[launcher]\nversion = Beta\n")
    with pytest.raises(PackagingError):
        app_version(str(app_dir))


def test_missing_app_conf(tmp_path):
    with pytest.raises(PackagingError):
        app_id(str(tmp_path))


@pytest.mark.parametrize("tag,expected", [("v1.0.0", "1.0.0"), ("refs/tags/v2.1.0", "2.1.0"), ("3.0.0", "3.0.0")])
def test_normalize_tag(tag, expected):
    assert normalize_tag_version(tag) == expected
