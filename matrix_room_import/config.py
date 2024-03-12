import shutil
from collections.abc import Sequence
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from matrix_room_import import PROJECT_DIR


class Config(BaseModel):
    homeserver_url: str
    server_name: str

    hs_token: str
    as_token: str
    as_id: str
    as_localpart: str

    bot_displayname: str

    path_to_import_files: Path

    port: int

    delete_rooms: Sequence[str] = Field(default=[])


def load_config() -> Config:
    default_config_path = PROJECT_DIR / "example-config.yaml"
    config_path = PROJECT_DIR / "config.yaml"
    if not config_path.exists():
        shutil.copyfile(default_config_path, config_path)
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return Config(**data)
