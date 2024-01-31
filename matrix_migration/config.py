import shutil
import yaml
from pydantic import BaseModel

from matrix_migration import PROJECT_DIR


class HomeServer(BaseModel):
    # The address to connect to the homeserver
    url: str
    server_name: str

    bot_user: str


class Config(BaseModel):
    homeserver_from: HomeServer
    homeserver_to: HomeServer

    # Rooms with these user id will not be migrated (e.g. rooms from bridges)
    filter_room_with: list[str]


def load_config() -> Config:
    default_config_path = PROJECT_DIR / "example-config.yaml"
    config_path = PROJECT_DIR / "config.yaml"
    if not config_path.exists():
        shutil.copyfile(default_config_path, config_path)
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return Config(**data)
