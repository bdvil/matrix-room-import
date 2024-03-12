import asyncio
import json
from pathlib import Path
from zipfile import ZipFile

import click
from aiohttp import web
from aiohttp.web import Application

from matrix_room_import import LOGGER
from matrix_room_import.appkeys import client_key, config_key, events_key
from matrix_room_import.appservice import server
from matrix_room_import.appservice.client import Client
from matrix_room_import.appservice.types import (
    CreateRoomBody,
    CreateRoomResponse,
    CreationContent,
    ErrorResponse,
    RoomMessage,
    StateEvent,
)
from matrix_room_import.concurrency_events import ConcurrencyEvents
from matrix_room_import.config import Config, load_config
from matrix_room_import.export_file_model import (
    ExportFile,
    GuestAccessEvent,
    HistoryVisibilityEvent,
    JoinRulesEvent,
    MemberContent,
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


def get_room_creator_id(data: ExportFile) -> str:
    for message in data.messages:
        if (
            isinstance(message, MemberEvent)
            and message.content.displayname == data.room_creator
        ):
            return message.sender
    raise ValueError("No creator in the room")


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


def load_data(zip_path: Path) -> ExportFile:
    with ZipFile(zip_path) as zip:
        print(zip.namelist())
        export_path = f"{zip_path.stem}/export.json"
        with zip.open(export_path) as export_file:
            data = ExportFile.model_validate(json.loads(export_file.read()))
    return data


async def populate_message(
    client: Client,
    data: ExportFile,
    new_room_id: str,
    events: ConcurrencyEvents,
    room_creator_id: str,
):
    for message in data.messages:
        if isinstance(message, MessageEvent):
            if message.content.file is not None:
                continue
            await client.send_event(
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
            print("Sending join request")
        elif (
            isinstance(message, MemberEvent) and message.content.membership == "invite"
        ):
            if message.sender == room_creator_id:
                continue
            client.should_accept_memberships.append((message.state_key, new_room_id))
            await client.send_state_event(
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
        elif isinstance(message, MemberEvent) and message.content.membership == "join":
            if message.sender == room_creator_id:
                continue
            events.should_accept_invite.set()
            print("Awaiting join request")
            await events.has_accepted_invite.wait()
            events.has_accepted_invite.clear()


async def http_server_task_runner(
    config: Config, client: Client, events: ConcurrencyEvents
):
    app = Application()
    app.add_routes(
        [web.put("/_matrix/app/v1/transactions/{txnId}", server.handle_transaction)]
    )
    app[config_key] = config
    app[client_key] = client
    app[events_key] = events

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=config.port)
    await site.start()
    await asyncio.Event().wait()


async def import_task_runner(client: Client, config: Config, events: ConcurrencyEvents):
    await client.delete_rooms(config.delete_rooms)

    for room_data in config.path_to_import_files.iterdir():
        if room_data.suffix == ".zip":
            data = load_data(room_data)
            room_resp = await create_room(client, data)
            room_creator_id = get_room_creator_id(data)
            if isinstance(room_resp, CreateRoomResponse):
                await populate_message(
                    client, data, room_resp.room_id, events, room_creator_id
                )


async def main():
    config = load_config()
    LOGGER.debug("CONFIG: %s", config.model_dump())

    client = Client(config.homeserver_url, config.as_token, config.as_id)

    concurreny_events = ConcurrencyEvents()

    server_task = asyncio.create_task(
        http_server_task_runner(config, client, concurreny_events)
    )
    import_task = asyncio.create_task(
        import_task_runner(client, config, concurreny_events)
    )

    await server_task
    await import_task


@click.command("serve")
def serve():
    asyncio.run(main())
