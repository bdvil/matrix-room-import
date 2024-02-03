import shutil
import yaml
from pydantic import BaseModel

from matrix_migration import PROJECT_DIR


class HomeServer(BaseModel):
    url: str
    server_name: str


class Config(BaseModel):
    homeserver_from: HomeServer
    homeserver_to: HomeServer

    as_token: str
    hs_token: str
    as_id: str

    # Rooms with these user id will not be migrated (e.g. rooms from bridges)
    filter_room_with: list[str]
    port: int


def load_config() -> Config:
    default_config_path = PROJECT_DIR / "example-config.yaml"
    config_path = PROJECT_DIR / "config.yaml"
    if not config_path.exists():
        shutil.copyfile(default_config_path, config_path)
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return Config(**data)
