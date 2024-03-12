from collections.abc import Sequence

from aiohttp import web

import matrix_room_import.appservice.types as types
from matrix_room_import import LOGGER, PROJECT_DIR
from matrix_room_import.appkeys import client_key, config_key, sync_sem_key
from matrix_room_import.appservice.client import Client
from matrix_room_import.appservice.types import (
    ClientEvent,
    DeleteRoomBody,
    JoinRoomBody,
    JoinRoomResponse,
    MembershipEnum,
    MsgType,
    RelatesTo,
    RoomMember,
    RoomMessage,
)
from matrix_room_import.concurrency_events import SyncTaskSems
from matrix_room_import.config import Config
from matrix_room_import.stores import (
    Process,
    process_queue,
    room_stores,
    rooms_to_remove,
    txn_store,
)


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
    sync_tasks_sem: SyncTaskSems,
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
                await handle_room_message(
                    config, client, event, content, sync_tasks_sem
                )


async def handle_transaction(request: web.Request) -> web.Response:
    config = request.app[config_key]
    client = request.app[client_key]
    sync_tasks_sem = request.app[sync_sem_key]

    if not check_headers(request, config.hs_token):
        LOGGER.debug("Forbidden transaction.")
        return web.json_response({}, status=403)

    txn_id = request.match_info["txnId"]

    if txn_id in txn_store:
        LOGGER.debug("Transaction already handled.")
        return web.json_response({}, status=200)

    data = await request.json()
    events = types.ClientEvents(**data)
    await handle_events(client, config, events.events, txn_id, sync_tasks_sem)

    return web.json_response({}, status=200)


async def send_help_message(config: Config, client: Client, room_id: str, user_id: str):
    await client.send_event(
        "m.room.message",
        room_id,
        RoomMessage(
            msgtype=MsgType.text,
            body=f"""Hello! Send me chat export files and I will import them back for you!

On element, go on ℹ️ "Room Info" on the top-lright, then "Export Chat".
Select the JSON format, "From the beginning" in Messages, a high size limit, and check
the "Include Attachments" box.

Commands:
* `space-id !roomId:{config.server_name}`: set space to import rooms into. (Currently: {config.space_id}).
* `set-admin-token syt_Ysddjk...`: set admin access-token so that old rooms can be deleted.
""",
            format="org.matrix.custom.html",
            formatted_body=f"""Hello! Send me chat export files and I will import them back for you!<br>
<br>
On element, go on ℹ️ "Room Info" on the top-lright, then "Export Chat".
Select the JSON format, "From the beginning" in Messages, a high size limit, and check
the "Include Attachments" box.<br>
<br>
Commands:
<ul>
    <li><code>space-id !roomId:{config.server_name}</code>: set space to import rooms into. (Currently: {config.space_id}).</li>
    <li><code>set-admin-token syt_Ysddjk...</code>: set admin access-token so that old rooms can be deleted.</li>
<ul>
""",
        ),
        user_id=user_id,
    )


async def handle_room_member(
    config: Config,
    client: Client,
    event: types.ClientEvent,
    content: RoomMember,
):
    bot_userid = f"@{config.as_id}:{config.server_name}"
    print("member event")
    print(event)
    if event.sender not in config.bot_allow_users:
        return
    if content.membership == MembershipEnum.invite and event.state_key == bot_userid:
        resp = await client.join_room(event.room_id, JoinRoomBody())
        if isinstance(resp, JoinRoomResponse):
            room_stores.append(resp.room_id)
            await send_help_message(config, client, resp.room_id, bot_userid)

        LOGGER.debug(resp)


async def handle_room_message(
    config: Config,
    client: Client,
    event: types.ClientEvent,
    content: RoomMessage,
    concurrency: SyncTaskSems,
):
    bot_userid = f"@{config.as_id}:{config.server_name}"
    if event.sender == bot_userid or event.sender not in config.bot_allow_users:
        return

    if content.body.lower()[:15] == "set-admin-token":
        config.admin_token = content.body.split(" ")[1]
        await client.redact_message(
            event.room_id,
            event.event_id,
            reason="Security",
            user_id=bot_userid,
        )
        resp = await client.send_event(
            "m.room.message",
            event.room_id,
            RoomMessage(
                msgtype=MsgType.text,
                body="Changed Admin Access Token.",
            ),
            user_id=bot_userid,
        )
        return

    if content.body.lower() == "help":
        await send_help_message(config, client, event.room_id, bot_userid)
        return

    if content.body.lower()[:8] == "space-id":
        config.space_id = content.body.split(" ")[1]
        resp = await client.send_event(
            "m.room.message",
            event.room_id,
            RoomMessage(
                msgtype=MsgType.text,
                body="Following imported rooms will be put in this space.\nNote: this also affects the queued import jobs.",
            ),
            user_id=bot_userid,
        )
        return

    if (
        event.content.get("m.relates_to") is not None
        and event.content["m.relates_to"]["event_id"] in rooms_to_remove
        and "yes" in content.body.lower()
    ):
        relates_to = event.content["m.relates_to"]
        print("Deleting room")
        room_id = rooms_to_remove[relates_to["event_id"]]
        await client.delete_room(room_id, DeleteRoomBody(purge=True))
        del rooms_to_remove[relates_to["event_id"]]

        resp = await client.send_event(
            "m.room.message",
            event.room_id,
            RoomMessage(
                msgtype=MsgType.text,
                body="Deleted.",
                relates_to=RelatesTo(
                    rel_type="m.thread",
                    event_id=event.event_id,
                    is_falling_back=True,
                ),
            ),
            user_id=bot_userid,
        )
        return

    if content.msgtype == MsgType.file and content.url is not None:
        print("Received message")
        print(event)
        download_path = PROJECT_DIR / "data" / content.body

        resp = await client.send_event(
            "m.room.message",
            event.room_id,
            RoomMessage(
                msgtype=MsgType.text,
                body="Downloading...",
                relates_to=RelatesTo(
                    rel_type="m.thread", event_id=event.event_id, is_falling_back=True
                ),
            ),
            user_id=bot_userid,
        )

        resp = await client.download_media(
            download_path, content.url, allow_redirect=False
        )
        if isinstance(resp, bool) and resp:
            process_queue.append(
                Process(
                    path=download_path,
                    room_id=event.room_id,
                    event_id=event.event_id,
                )
            )

            resp = await client.send_event(
                "m.room.message",
                event.room_id,
                RoomMessage(
                    msgtype=MsgType.text,
                    body="Downloaded. Adding to queue.",
                    relates_to=RelatesTo(
                        rel_type="m.thread",
                        event_id=event.event_id,
                        is_falling_back=True,
                    ),
                ),
                user_id=bot_userid,
            )
            concurrency.num_export_process_sem.release()
        return
