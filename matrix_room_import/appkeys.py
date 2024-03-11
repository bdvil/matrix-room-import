from aiohttp.web import AppKey

from matrix_room_import.appservice.client import Client
from matrix_room_import.config import Config
from matrix_room_import.store import Store

config_key = AppKey("config", Config)
client_key = AppKey("client", Client)
txn_store_key = AppKey("txn_store", Store)
