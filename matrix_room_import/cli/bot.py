import asyncio
import json
from pathlib import Path
from zipfile import ZipFile

import click
from aiohttp import web
from aiohttp.web import Application

from matrix_room_import import LOGGER
from matrix_room_import.appkeys import client_key, config_key, sync_sem_key
from matrix_room_import.appservice import server
from matrix_room_import.appservice.client import Client
from matrix_room_import.appservice.types import (
    CreateMediaResponse,
    CreateRoomBody,
    CreateRoomResponse,
    CreationContent,
    ErrorResponse,
    ImageInfo,
    MsgType,
    RelatesTo,
    RoomMessage,
    RoomSendEventResponse,
    StateEvent,
)
from matrix_room_import.concurrency_events import SyncTaskSems
from matrix_room_import.config import Config, load_config
from matrix_room_import.export_file_model import (
    ExportFile,
    GuestAccessEvent,
    HistoryVisibilityEvent,
    JoinRulesEvent,
    MemberContent,
    MemberEvent,
    MessageEvent,
    SpaceChildContent,
    TopicEvent,
)
from matrix_room_import.stores import Process, process_queue, rooms_to_remove

FILE_CONTENT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "svg": "image/svg+xml",
    "pdf": "application/pdf",
}


def get_initial_ts(data: ExportFile) -> int:
    for message in data.messages:
        return message.origin_server_ts
    raise ValueError("No message with room_id.")


def get_room_id(data: ExportFile) -> str:
    for message in data.messages:
        return message.room_id
    raise ValueError("No message with room_id.")


def get_join_rule(data: ExportFile) -> str:
    for message in data.messages:
        if isinstance(message, JoinRulesEvent):
            return message.content.join_rule
    return "invite"


def get_room_creator_id(data: ExportFile) -> str:
    for message in data.messages:
        if (
            isinstance(message, MemberEvent)
            and message.content.displayname == data.room_creator
        ):
            return message.sender
    raise ValueError("No creator in the room")


async def signal_import_room_started(config: Config, process: Process, client: Client):
    bot_userid = f"@{config.as_id}:{config.server_name}"
    await client.send_event(
        "m.room.message",
        process.room_id,
        RoomMessage(
            msgtype=MsgType.text,
            body="Start importing room...",
            relates_to=RelatesTo(
                rel_type="m.thread", event_id=process.event_id, is_falling_back=True
            ),
        ),
        user_id=bot_userid,
    )


async def signal_import_ended(
    config: Config, process: Process, client: Client, new_room_id: str, old_room_id: str
):
    bot_userid = f"@{config.as_id}:{config.server_name}"
    await client.send_event(
        "m.room.message",
        process.room_id,
        RoomMessage(
            msgtype=MsgType.text,
            body=(
                f"Import finished. Here is the new room: \n{new_room_id}"
                '\n\nShould I remove the old room? (Send back "yes" in the thread).'
            ),
            relates_to=RelatesTo(
                rel_type="m.thread", event_id=process.event_id, is_falling_back=True
            ),
        ),
        user_id=bot_userid,
    )
    rooms_to_remove[process.event_id] = old_room_id


async def signal_import_failed(
    config: Config, process: Process, client: Client, error_resp: ErrorResponse
):
    bot_userid = f"@{config.as_id}:{config.server_name}"
    await client.send_event(
        "m.room.message",
        process.room_id,
        RoomMessage(
            msgtype=MsgType.text,
            body=(
                f"Import Failed with error: {error_resp.errcode} - {error_resp.error}"
            ),
            relates_to=RelatesTo(
                rel_type="m.thread", event_id=process.event_id, is_falling_back=True
            ),
        ),
        user_id=bot_userid,
    )


async def create_room(
    client: Client, data: ExportFile
) -> CreateRoomResponse | ErrorResponse:
    initial_state: list[StateEvent] = []
    creation_content = CreationContent(federate=False)
    ts: int | None = None
    user_id: str | None = None
    room_topic: str | None = None
    for message in data.messages:
        if (
            isinstance(message, MemberEvent)
            and message.content.displayname == data.room_creator
        ):
            user_id = message.sender
            ts = message.origin_server_ts
        elif isinstance(
            message, (JoinRulesEvent, HistoryVisibilityEvent, GuestAccessEvent)
        ):
            initial_state.append(
                StateEvent(
                    content=message.content,
                    state_key=message.state_key,
                    type=message.type,
                )
            )
        elif isinstance(message, TopicEvent):
            room_topic = message.content.topic
    create_room_body = CreateRoomBody(
        initial_state=initial_state,
        creation_content=creation_content,
        name=data.room_name,
        topic=room_topic,
    )
    return await client.create_room(create_room_body, user_id, ts)


def get_filename(name: str):
    parts = name.split(".")
    ext = parts[-1]
    stem = ".".join(parts[:-1])
    stem_parts = " at ".join(stem.split(" at ")[:-1]).split("-")[:-3]
    return "-".join(stem_parts) + "." + ext


def get_file_mimetype(data: ExportFile) -> dict[str, str]:
    mimetypes: dict[str, str] = {}
    for message in data.messages:
        if isinstance(message, MessageEvent):
            mimetype = message.content.info.get("mimetype", None)
            if mimetype is not None:
                mimetypes[message.content.body] = mimetype
    return mimetypes


def load_export_file(file_path: Path) -> ExportFile:
    with open(file_path) as export_file:
        data = ExportFile.model_validate(json.loads(export_file.read()))
    return data


def load_zip_export(
    zip_path: Path,
) -> tuple[ExportFile | None, dict[str, bytes]]:
    files: dict[str, bytes] = {}
    data: ExportFile | None = None
    with ZipFile(zip_path) as zip:
        print(zip.namelist())
        for name in zip.namelist():
            filepath = name.split("/")
            if len(filepath) < 2:
                continue
            if filepath[1] == "export.json":
                with zip.open(name) as export_file:
                    data = ExportFile.model_validate(json.loads(export_file.read()))
            elif (
                filepath[1] in ["images", "files"]
                and len(filepath) > 2
                and filepath[2] != ""
            ):
                with zip.open(name) as export_file:
                    filename = get_filename(filepath[2])
                    files[filename] = export_file.read()
            else:
                print(f"skipped {name}")

    return data, files


async def populate_message(
    client: Client,
    data: ExportFile,
    new_room_id: str,
    room_creator_id: str,
    file_paths: dict[str, str],
):
    new_event_ids: dict[str, str] = {}
    for message in data.messages:
        print(message.type)
        print(type(message))
        print(message.content)
        if isinstance(message, MemberEvent) and message.content.membership == "invite":
            print("INVITE")
            resp = await client.send_state_event(
                message.type,
                new_room_id,
                MemberContent(
                    membership="invite",
                    displayname=message.content.displayname,
                    avatar_url=message.content.avatar_url,
                ).model_dump(),
                message.state_key,
                user_id=message.sender,
                ts=message.origin_server_ts,
            )
            if isinstance(resp, RoomSendEventResponse):
                new_event_ids[message.event_id] = resp.event_id
        elif isinstance(message, MemberEvent) and message.content.membership == "join":
            if message.sender == room_creator_id:
                continue
            print("JOIN")
            resp = await client.send_state_event(
                message.type,
                new_room_id,
                MemberContent(
                    membership="join",
                    displayname=message.content.displayname,
                    avatar_url=message.content.avatar_url,
                ).model_dump(),
                message.state_key,
                user_id=message.sender,
                ts=message.origin_server_ts,
            )
            if isinstance(resp, RoomSendEventResponse):
                new_event_ids[message.event_id] = resp.event_id
        elif (
            isinstance(message, MessageEvent)
            and message.content.info.get("mimetype", None) is not None
            and message.content.body in file_paths
        ):
            print("FILE")
            image_h = message.content.info.get("h", None)
            image_mimetype = message.content.info.get("mimetype", None)
            image_size = message.content.info.get("size", None)
            image_w = message.content.info.get("w", None)
            resp = await client.send_event(
                message.type,
                new_room_id,
                RoomMessage(
                    msgtype=message.content.msgtype,
                    body=message.content.body,
                    url=file_paths[message.content.body],
                    info=ImageInfo(
                        h=image_h, mimetype=image_mimetype, size=image_size, w=image_w
                    ),
                    mentions=message.content.mentions,
                    relates_to=message.content.relates_to,
                ),
                user_id=message.sender,
                ts=message.origin_server_ts,
            )
            if isinstance(resp, RoomSendEventResponse):
                new_event_ids[message.event_id] = resp.event_id
        elif isinstance(message, MessageEvent) and message.content.file is None:
            print("MESSAGE")
            if message.content.relates_to is not None:
                if message.content.relates_to.event_id is not None:
                    message.content.relates_to.event_id = new_event_ids.get(
                        message.content.relates_to.event_id,
                        message.content.relates_to.event_id,
                    )
                if message.content.relates_to.in_reply_to is not None:
                    message.content.relates_to.in_reply_to.event_id = new_event_ids.get(
                        message.content.relates_to.in_reply_to.event_id,
                        message.content.relates_to.in_reply_to.event_id,
                    )

            resp = await client.send_event(
                message.type,
                new_room_id,
                RoomMessage(
                    msgtype=message.content.msgtype,
                    body=message.content.body,
                    format=message.content.format,
                    formatted_body=message.content.formatted_body,
                    mentions=message.content.mentions,
                    relates_to=message.content.relates_to,
                ),
                user_id=message.sender,
                ts=message.origin_server_ts,
            )
            if isinstance(resp, RoomSendEventResponse):
                new_event_ids[message.event_id] = resp.event_id


async def http_server_task_runner(
    config: Config, client: Client, sync_tasks_sem: SyncTaskSems
):
    app = Application()
    app.add_routes(
        [web.put("/_matrix/app/v1/transactions/{txnId}", server.handle_transaction)]
    )
    app[config_key] = config
    app[client_key] = client
    app[sync_sem_key] = sync_tasks_sem

    bot_userid = f"@{config.as_id}:{config.server_name}"
    await client.update_bot_profile(bot_userid, config.bot_displayname)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=config.port)
    await site.start()
    await asyncio.Event().wait()


async def import_task_runner(
    client: Client, config: Config, sync_tasks_sem: SyncTaskSems
):
    await client.delete_rooms(config.delete_rooms)

    while True:
        await sync_tasks_sem.num_export_process_sem.acquire()
        process = process_queue.pop(0)
        if process.path.suffix == ".zip" or process.path.suffix == ".json":
            if process.path.suffix == ".zip":
                data, files = load_zip_export(process.path)
            else:
                data = load_export_file(process.path)
                files: dict[str, bytes] = {}
            file_paths: dict[str, str] = {}

            print(data)
            if data is not None:
                old_room_id = get_room_id(data)
                room_creator_id = get_room_creator_id(data)

                mimetype_files = get_file_mimetype(data)
                print(mimetype_files)
                for filename, content in files.items():
                    mimetype = mimetype_files.get(filename, None)
                    resp = await client.create_and_upload_media(
                        content, filename, mimetype
                    )
                    if isinstance(resp, CreateMediaResponse):
                        file_paths[filename] = resp.content_uri
                print(file_paths)

                await signal_import_room_started(config, process, client)

                room_resp = await create_room(client, data)

                if isinstance(room_resp, CreateRoomResponse):
                    if config.space_id is not None:
                        print(f"Adding room to space {config.space_id}")
                        resp = await client.send_state_event(
                            "m.space.child",
                            config.space_id,
                            SpaceChildContent(
                                via=[config.server_name],
                            ).model_dump(exclude_defaults=True),
                            room_resp.room_id,
                            user_id=room_creator_id,
                        )
                        print(resp)

                    await populate_message(
                        client,
                        data,
                        room_resp.room_id,
                        room_creator_id,
                        file_paths,
                    )
                    await signal_import_ended(
                        config, process, client, room_resp.room_id, old_room_id
                    )
                else:
                    await signal_import_failed(config, process, client, room_resp)


async def main():
    config = load_config()
    LOGGER.debug("CONFIG: %s", config.model_dump())

    client = Client(
        config.homeserver_url, config.as_token, config.as_id, config.admin_token
    )

    sync_tasks_sem = SyncTaskSems()

    server_task = asyncio.create_task(
        http_server_task_runner(config, client, sync_tasks_sem)
    )
    import_task = asyncio.create_task(
        import_task_runner(client, config, sync_tasks_sem)
    )

    await server_task
    await import_task


@click.command("serve")
def serve():
    asyncio.run(main())
