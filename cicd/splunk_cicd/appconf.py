import configparser
import os
import re

from .errors import PackagingError

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+([.-][0-9A-Za-z]+)*$")


def read_app_conf(app_dir):
    path = os.path.join(app_dir, "default", "app.conf")
    if not os.path.isfile(path):
        raise PackagingError(f"missing default/app.conf in {app_dir}")
    parser = configparser.RawConfigParser(strict=False, allow_no_value=True, interpolation=None)
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    return parser


def app_id(app_dir, conf=None):
    conf = conf or read_app_conf(app_dir)
    for section in ("package", "id"):
        if conf.has_option(section, "id"):
            return conf.get(section, "id").strip()
        if section == "id" and conf.has_option(section, "name"):
            return conf.get(section, "name").strip()
    return os.path.basename(os.path.abspath(app_dir))


def app_version(app_dir, conf=None):
    conf = conf or read_app_conf(app_dir)
    for section in ("launcher", "id"):
        if conf.has_option(section, "version"):
            version = conf.get(section, "version").strip()
            if not VERSION_RE.match(version):
                raise PackagingError(f"invalid version '{version}' in [{section}] of app.conf")
            return version
    raise PackagingError("no version found in [launcher] or [id] of app.conf")


def normalize_tag_version(tag):
    tag = tag.rsplit("/", 1)[-1]
    return tag[1:] if tag.startswith("v") else tag
