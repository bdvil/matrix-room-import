from aiohttp import web

import matrix_migration.appservice.types as types
from matrix_migration import LOGGER
from matrix_migration.config import Config


def check_headers(request: web.Request, hs_token: str) -> bool:
    return (
        "Authorization" in request.headers.keys()
        and request.headers["Authorization"] == f"Bearer {hs_token}"
    )


async def handle_ping(request: web.Request) -> web.Response:
    body = await request.json()
    LOGGER.debug(
        "SERVER ping data: %s",
        {"url": request.url, "headers": request.headers, "body": body},
    )
    config: Config = request.app["config"]
    if not check_headers(request, config.hs_token):
        return web.json_response({}, status=403)
    return web.json_response({}, status=200)


async def handle_transaction(request: web.Request) -> web.Response:
    LOGGER.debug(
        "SERVER transaction data: %s",
        {"url": request.url, "headers": request.headers},
    )
    config: Config = request.app["config"]
    if not check_headers(request, config.hs_token):
        return web.json_response({}, status=403)
    txn_id = request.match_info["txnId"]
    events = types.ClientEvent(**await request.json())
    LOGGER.debug(f"Transaction {txn_id} type= {events.type}")

    return web.json_response({}, status=200)
