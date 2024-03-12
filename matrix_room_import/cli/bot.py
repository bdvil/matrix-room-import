import asyncio
import json
from pathlib import Path
from zipfile import ZipFile

import click
from aiohttp import web
from aiohttp.web import Application

from matrix_room_import import LOGGER
from matrix_room_import.appkeys import client_key, config_key
from matrix_room_import.appservice import server
from matrix_room_import.appservice.client import Client
from matrix_room_import.appservice.types import (
    CreateRoomBody,
    CreateRoomResponse,
    CreationContent,
    RoomMessage,
    StateEvent,
)
from matrix_room_import.config import Config, load_config
from matrix_room_import.export_file_model import (
    ExportFile,
    GuestAccessEvent,
    HistoryVisibilityEvent,
    JoinRulesEvent,
    MemberEvent,
    MessageEvent,
    TopicEvent,
)


def get_room_id(data: ExportFile) -> str:
    for message in data.messages:
        return message.room_id
    raise ValueError("No message with room_id.")


def get_join_rule(data: ExportFile) -> str:
    for message in data.messages:
        if isinstance(message, JoinRulesEvent):
            return message.content.join_rule
    return "invite"


def get_topic(data: ExportFile) -> str | None:
    for message in data.messages:
        if isinstance(message, TopicEvent):
            return message.content.topic


def get_initial_state_events(data: ExportFile) -> list[StateEvent]:
    events: list[StateEvent] = []
    for message in data.messages:
        if isinstance(
            message, (JoinRulesEvent, HistoryVisibilityEvent, GuestAccessEvent)
        ):
            events.append(
                StateEvent(
                    content=message.content,
                    state_key=message.state_key,
                    type=message.type,
                )
            )
    return events


def get_room_creator_id(data: ExportFile) -> str:
    for message in data.messages:
        if (
            isinstance(message, MemberEvent)
            and message.content.displayname == data.room_creator
        ):
            return message.sender
    raise ValueError("No creator in the room")


def load_data(zip_path: Path) -> ExportFile:
    with ZipFile(zip_path) as zip:
        print(zip.namelist())
        export_path = f"{zip_path.stem}/export.json"
        with zip.open(export_path) as export_file:
            data = ExportFile.model_validate(json.loads(export_file.read()))
    return data


async def populate_message(client: Client, data: ExportFile, new_room_id: str):
    for message in data.messages:
        if isinstance(message, MessageEvent):
            if message.content.file is not None:
                continue
            await client.send_event(
                message.sender,
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
            )
        elif isinstance(message, MemberEvent):
            if message.sender == get_room_creator_id(data):
                continue
            await client.send_state_event(
                message.sender,
                message.type,
                new_room_id,
                message.content.model_dump(),
                message.state_key,
            )
            # Let time for the server to accept invite
            await asyncio.sleep(3)


async def http_server_task_runner(config: Config, client: Client):
    app = Application()
    app.add_routes(
        [web.put("/_matrix/app/v1/transactions/{txnId}", server.handle_transaction)]
    )
    app[config_key] = config
    app[client_key] = client

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=config.port)
    await site.start()
    await asyncio.Event().wait()


async def import_task_runner(client: Client, config: Config):
    await client.delete_rooms(config.delete_rooms)

    for room_data in config.path_to_import_files.iterdir():
        if room_data.suffix == ".zip":
            data = load_data(room_data)
            creator_id = get_room_creator_id(data)
            create_room_body = CreateRoomBody(
                initial_state=get_initial_state_events(data),
                creation_content=CreationContent(
                    federate=False,
                ),
                name=data.room_name,
                topic=get_topic(data),
            )
            room_resp = await client.create_room(create_room_body, creator_id)
            if isinstance(room_resp, CreateRoomResponse):
                await populate_message(client, data, room_resp.room_id)


async def main():
    config = load_config()
    LOGGER.debug("CONFIG: %s", config.model_dump())

    client = Client(config.homeserver_url, config.as_token, config.as_id)
    server_task = asyncio.create_task(http_server_task_runner(config, client))
    import_task = asyncio.create_task(import_task_runner(client, config))

    await server_task
    await import_task


@click.command("serve")
def serve():
    asyncio.run(main())
