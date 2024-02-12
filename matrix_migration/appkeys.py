from aiohttp.web import AppKey

from matrix_migration.appservice.client import Client
from matrix_migration.config import Config
from matrix_migration.store import Store

config_key = AppKey("config", Config)
client_key = AppKey("client", Client)
txn_store_key = AppKey("txn_store", Store)
