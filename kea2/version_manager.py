import os
import json
import shutil

from pathlib import Path
from packaging.version import Version
from typing import List, Set, TypedDict
from importlib.metadata import version

from .utils import getLogger, getProjectRoot

logger = getLogger(__name__)


CompatibilityInfo = TypedDict('CompatibilityInfo', {
    "name": str,
    "description": str,
    "from": str,
    "to": str,
})
VersionInfo = TypedDict('VersionInfo', {
    "compatibility infos": List[CompatibilityInfo],
})


def ls_files(dir_path: Path) -> Set[Path]:
    """list all files in the directory"""
    return set(f for f in dir_path.rglob('*') if f.is_file())


def check_config_compatibility():
    config_version_sanitizer = ConfigVersionSanitizer()
    config_version_sanitizer.check_config_compatibility()
    config_version_sanitizer.config_auto_update()


def get_cur_version():
    return version("Kea2-python")


class ConfigVersionSanitizer:
    def __init__(self):
        self._version_infos = None
        self._config_version = None
        self.user_config_path = getProjectRoot() / "configs"
        self.kea2_assets_path = Path(__file__).parent / "assets"
        self.kea2_version = get_cur_version()

    @property
    def version_infos(self) -> VersionInfo:
        if self._version_infos is None:
            with open(self.kea2_assets_path / "config_version.json") as fp:
                self._version_infos = json.load(fp)
        return self._version_infos

    @property
    def config_version(self):
        if self._config_version is not None:
            return self._config_version

        user_version_json = self.user_config_path / "version.json"
        if not user_version_json.exists():
            self._config_version = "0.3.6"
        else:
            with open(user_version_json) as fp:
                self._config_version = json.load(fp)["version"]
        return self._config_version

    def check_config_compatibility(self):
        """Check if the user config version is compatible with the current Kea2 version.""" 
        update_infos = []
        for info in self.version_infos["compatibility infos"]:
            if Version(info["from"]) > Version(self.config_version):
                update_infos.append(info)

        if not update_infos:
            return

        logger.warning("Configuration update required! Please update your configuration files.")
        logger.warning(f"Current kea2 version {self.kea2_version}. Current config version {self.config_version}.")
        for info in update_infos:
            logger.info(
                f"Since version {info['from']}: {info['description']}"
            )
    
    def config_auto_update(self):
        self._copy_new_configs()
    
    def _copy_new_configs(self):
        src = self.kea2_assets_path / "fastbot_configs"
        dst = self.user_config_path
        
        src_files = set(os.listdir(src))
        dst_files = set(os.listdir(dst))
        
        new_files = src_files - dst_files
        
        for file in new_files:
            src_path = src / file
            dst_path = dst / file
            logger.info(f"Copying new config file: {file}")
            shutil.copy2(src_path, dst_path)
