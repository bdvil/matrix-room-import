from aiohttp.web import AppKey

from matrix_room_import.appservice.client import Client
from matrix_room_import.concurrency_events import ConcurrencyEvents
from matrix_room_import.config import Config

config_key = AppKey("config", Config)
client_key = AppKey("client", Client)
events_key = AppKey("events", ConcurrencyEvents)
