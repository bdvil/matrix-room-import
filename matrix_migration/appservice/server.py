from aiohttp import web

import matrix_migration.appservice.types as types
from matrix_migration import LOGGER
from matrix_migration.config import Config
from matrix_migration.store import Store


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
    print("oui")
    config: Config = request.app["config"]
    if not check_headers(request, config.hs_token):
        return web.json_response({}, status=403)
    txn_id = request.match_info["txnId"]
    txn_store: Store = request.app["txn_store"]

    if txn_id in txn_store:
        return web.json_response({}, status=200)

    events = types.ClientEvents(**await request.json())
    for event in events.events:
        LOGGER.debug(f"Transaction {txn_id} type= {event.type}")
        LOGGER.debug("%s", event.content)

    txn_store.append(txn_id)
    return web.json_response({}, status=200)
