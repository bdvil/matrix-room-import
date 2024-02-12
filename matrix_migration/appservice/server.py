from collections.abc import Sequence

from aiohttp import web

import matrix_migration.appservice.types as types
from matrix_migration import LOGGER
from matrix_migration.appkeys import client_key, config_key, txn_store_key
from matrix_migration.appservice.client import Client
from matrix_migration.appservice.types import (
    ClientEvent,
    Event,
    MembershipEnum,
    RoomMember,
    RoomMessage,
    ToDeviceEvent,
)
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


async def handle_events(
    client: Client, config: Config, events: Sequence[ClientEvent], txn_id: str
):
    for event in events:
        LOGGER.debug(f"Transaction {txn_id} type= {event.type}")
        LOGGER.debug("%s", event)

        match event.type:
            case "m.room.member":
                content = RoomMember(**event.content)
                await handle_room_member(client, event, content)
            case "m.room.message":
                content = RoomMessage(**event.content)
                await handle_room_message_event(
                    client, event, content, config.bot_username
                )


async def handle_ephemeral_events(
    client: Client, config: Config, events: Sequence[Event], txn_id: str
):
    for event in events:
        LOGGER.debug(f"Transaction ephemeral {txn_id} type= {event.type}")
        LOGGER.debug("%s", event)


async def handle_to_device_events(
    client: Client, config: Config, events: Sequence[ToDeviceEvent], txn_id: str
):
    for event in events:
        LOGGER.debug(f"Transaction to-device {txn_id} type= {event.type}")
        LOGGER.debug("%s", event)


async def handle_transaction(request: web.Request) -> web.Response:
    config = request.app[config_key]
    client = request.app[client_key]

    if not check_headers(request, config.hs_token):
        LOGGER.debug("Forbidden transaction.")
        return web.json_response({}, status=403)

    txn_id = request.match_info["txnId"]
    txn_store = request.app[txn_store_key]

    if txn_id in txn_store:
        LOGGER.debug("Transaction already handled.")
        return web.json_response({}, status=200)

    data = await request.json()
    events = types.ClientEvents(**data)
    await handle_events(client, config, events.events, txn_id)
    if events.ephemeral is not None:
        await handle_ephemeral_events(client, config, events.ephemeral, txn_id)
    if events.to_device is not None:
        await handle_to_device_events(client, config, events.to_device, txn_id)

    txn_store.append(txn_id)
    return web.json_response({}, status=200)


async def handle_room_member(
    client: Client, event: types.ClientEvent, content: RoomMember
):
    if content.membership == MembershipEnum.invite:
        resp = await client.join_room(event.room_id)
        LOGGER.debug(resp)
        # query_key_resp = await client.query_keys({event.sender: []})
        # LOGGER.debug(query_key_resp)


async def handle_room_message_event(
    client: Client,
    event: types.ClientEvent,
    content: RoomMessage,
    bot_username: str,
):
    if event.sender != bot_username and content.body == "hi":
        resp = await client.send_event(
            "m.room.message",
            event.room_id,
            "hello!",
        )
        LOGGER.debug(resp)
