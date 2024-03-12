from collections.abc import Sequence

from aiohttp import web

import matrix_room_import.appservice.types as types
from matrix_room_import import LOGGER, PROJECT_DIR
from matrix_room_import.appkeys import client_key, config_key, events_key
from matrix_room_import.appservice.client import Client
from matrix_room_import.appservice.types import (
    ClientEvent,
    JoinRoomBody,
    JoinRoomResponse,
    MembershipEnum,
    MsgType,
    RoomMember,
    RoomMessage,
)
from matrix_room_import.concurrency_events import ConcurrencyEvents
from matrix_room_import.config import Config
from matrix_room_import.stores import process_queue, room_stores, txn_store


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
                await handle_room_member(config, client, event, content)
            case "m.room.message" if event.room_id in room_stores:
                content = RoomMessage(**event.content)
                await handle_room_message(config, client, event, content)


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
    config: Config,
    client: Client,
    event: types.ClientEvent,
    content: RoomMember,
):
    bot_userid = f"@{config.as_id}:{config.server_name}"
    print("member event")
    print(event)
    if content.membership == MembershipEnum.invite and event.state_key == bot_userid:
        resp = await client.join_room(event.room_id, JoinRoomBody())
        if isinstance(resp, JoinRoomResponse):
            room_stores.append(resp.room_id)
            await client.send_event(
                "m.room.message",
                resp.room_id,
                RoomMessage(
                    msgtype=MsgType.text,
                    body="""Hello! Send me chat export files and I will import them back for you!

On element, go on ℹ️ "Room Info" on the top-lright, then "Export Chat".
Select the JSON format, "From the beginning" in Messages, a high size limit, and check
the "Include Attachments" box.
""",
                ),
                user_id=bot_userid,
            )

        LOGGER.debug(resp)


async def handle_room_message(
    config: Config,
    client: Client,
    event: types.ClientEvent,
    content: RoomMessage,
    concurrency: ConcurrencyEvents,
):
    bot_userid = f"@{config.as_id}:{config.server_name}"
    if event.sender == bot_userid:
        return
    if content.msgtype == MsgType.file and content.url is not None:
        print("Received message")
        print(event)
        download_path = PROJECT_DIR / "data" / content.body

        resp = await client.download_media(
            download_path, content.url, allow_redirect=False
        )
        if isinstance(resp, bool) and resp:
            process_queue.append(download_path)
            concurrency.num_export_process_sem.release()

        # resp = await client.send_event(
        #     "m.room.message",
        #     event.room_id,
        #     RoomMessage(
        #         msgtype=MsgType.text,
        #         body="",
        #     ),
        #     user_id=bot_userid,
        # )
        # print(resp)
