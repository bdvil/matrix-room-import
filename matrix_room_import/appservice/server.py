from collections.abc import Sequence

from aiohttp import web

import matrix_room_import.appservice.types as types
from matrix_room_import import LOGGER
from matrix_room_import.appkeys import client_key, config_key, events_key
from matrix_room_import.appservice.client import Client
from matrix_room_import.appservice.types import (
    ClientEvent,
    MembershipEnum,
    RoomMember,
)
from matrix_room_import.concurrency_events import ConcurrencyEvents
from matrix_room_import.config import Config
from matrix_room_import.stores import txn_store


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
    client: Client,
    config: Config,
    events: Sequence[ClientEvent],
    txn_id: str,
    concurrency_events: ConcurrencyEvents,
):
    for event in events:
        LOGGER.debug(f"Transaction {txn_id} type= {event.type}")
        LOGGER.debug("%s", event)

        match event.type:
            case "m.room.member":
                content = RoomMember(**event.content)
                await handle_room_member(client, event, content, concurrency_events)


async def handle_transaction(request: web.Request) -> web.Response:
    config = request.app[config_key]
    client = request.app[client_key]
    concurrency_events = request.app[events_key]

    if not check_headers(request, config.hs_token):
        LOGGER.debug("Forbidden transaction.")
        return web.json_response({}, status=403)

    txn_id = request.match_info["txnId"]

    if txn_id in txn_store:
        LOGGER.debug("Transaction already handled.")
        return web.json_response({}, status=200)

    data = await request.json()
    events = types.ClientEvents(**data)
    await handle_events(client, config, events.events, txn_id, concurrency_events)

    return web.json_response({}, status=200)


async def handle_room_member(
    client: Client,
    event: types.ClientEvent,
    content: RoomMember,
    concurrency_events: ConcurrencyEvents,
):
    if content.membership == MembershipEnum.invite:
        removed_id = None
        for k, (user_id, room_id) in enumerate(client.should_accept_memberships):
            if user_id == event.state_key and room_id == event.room_id:
                await concurrency_events.should_accept_invite.wait()
                resp = await client.join_room(event.room_id)
                LOGGER.debug(resp)
                removed_id = k
                concurrency_events.should_accept_invite.clear()
                break
        if removed_id is not None:
            client.should_accept_memberships.pop(removed_id)
            concurrency_events.has_accepted_invite.set()
