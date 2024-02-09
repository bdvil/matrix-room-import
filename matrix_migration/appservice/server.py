from aiohttp import web

import matrix_migration.appservice.types as types
from matrix_migration import LOGGER
from matrix_migration.appservice.client import Client
from matrix_migration.appservice.types import MembershipEnum, RoomMember, RoomMessage
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
    config: Config = request.app["config"]
    client: Client = request.app["client"]

    if not check_headers(request, config.hs_token):
        return web.json_response({}, status=403)

    txn_id = request.match_info["txnId"]
    txn_store: Store = request.app["txn_store"]

    if txn_id in txn_store:
        return web.json_response({}, status=200)

    events = types.ClientEvents(**await request.json())
    for event in events.events:
        LOGGER.debug(f"Transaction {txn_id} type= {event.type}")
        LOGGER.debug("%s", event)
        LOGGER.debug("%s", event.content)

        match event.type:
            case "m.room.member":
                content = RoomMember(**event.content)
                await handle_room_member(client, event, content)
            case "m.room.message":
                content = RoomMessage(**event.content)
                await handle_room_message_event(client, event, content, config.bot_user)

    txn_store.append(txn_id)
    return web.json_response({}, status=200)


async def handle_room_member(
    client: Client, event: types.ClientEvent, content: RoomMember
):
    if content.membership == MembershipEnum.invite:
        resp = await client.join_room(event.room_id)
        LOGGER.debug(resp)


async def handle_room_message_event(
    client: Client,
    event: types.ClientEvent,
    content: RoomMessage,
    bot_user: str,
):
    if event.sender != bot_user and content.body == "hi":
        resp = await client.send_event(
            "m.room.message",
            event.room_id,
            "hello!",
        )
        LOGGER.debug(resp)
