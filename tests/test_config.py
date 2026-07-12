import json

from spotify_scheduler_pro.config import AppConfig, ConfigManager


def test_non_object_config_falls_back_to_defaults(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps([]), encoding="utf-8")

    assert ConfigManager(path).load() == AppConfig()
