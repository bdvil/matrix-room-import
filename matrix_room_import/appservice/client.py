from collections.abc import Mapping, Sequence
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from aiohttp import ClientResponse, ClientSession

from matrix_room_import import LOGGER, matrix_api
from matrix_room_import.appservice.types import (
    CreateMediaResponse,
    CreateRoomBody,
    CreateRoomResponse,
    DeleteRoomResponse,
    ErrorResponse,
    InviteToRoomBody,
    InviteToRoomResponse,
    JoinRoomBody,
    JoinRoomResponse,
    PingBody,
    PingResponse,
    ProfileDisplayNameBody,
    ProfileDisplayNameResponse,
    ProfileResponse,
    RoomMessage,
    RoomSendEventResponse,
    UploadMediaResponse,
    WhoAmIResponse,
)


def new_txn() -> str:
    return str(uuid4())


class HTTPMethod(str, Enum):
    post = "POST"
    put = "PUT"
    get = "GET"
    delete = "DELETE"


class Client:
    def __init__(self, hs_url: str, as_token: str, as_id: str):
        self.hs_url = hs_url
        self.as_token = as_token
        self.as_id = as_id
        self.headers = {
            "Authorization": f"Bearer {as_token}",
        }
        self.admin_headers = {
            "Authorization": "Bearer syt_YWRtaW4_PTtQhsGasAXJEzsmDXMh_171xm4",
        }

        self.should_accept_memberships: list[tuple[str, str]] = []

    async def raw_request(
        self,
        url: str,
        method: HTTPMethod,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
        data: bytes | None = None,
    ) -> ClientResponse:
        if body is None:
            body = {}
        if headers is None:
            headers = self.headers
        if data is not None:
            body = None
        async with ClientSession(headers=headers) as session:
            async with session.request(
                method.value, url, data=data, json=body
            ) as response:
                return response

    async def request(
        self,
        url: str,
        method: HTTPMethod,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
        data: bytes | None = None,
    ) -> tuple[ClientResponse, Any]:
        response = await self.raw_request(url, method, body, headers, data)
        data = await response.json()
        return response, data

    async def ping(
        self,
        transaction_id: str | None = None,
    ) -> PingResponse | ErrorResponse:
        url = matrix_api.ping(self.hs_url, self.as_id)
        LOGGER.info(f"CLIENT ping {url}")

        body = PingBody(transaction_id=transaction_id)
        response, data = await self.request(
            url, HTTPMethod.post, body.model_dump(exclude_none=True)
        )
        LOGGER.debug(
            "CLIENT ping data: %s",
            {"headers": response.headers, "body": data},
        )
        if response.status == 200:
            return PingResponse(**data)
        return ErrorResponse(**data, statuscode=response.status)

    async def whoami(self, user_id: str) -> WhoAmIResponse | ErrorResponse:
        url = matrix_api.whoami(self.hs_url, user_id)
        LOGGER.info(f"CLIENT whoami {url}")
        response, data = await self.request(url, HTTPMethod.get)

        LOGGER.debug(
            "CLIENT whoami data: %s",
            {"headers": response.headers, "body": data},
        )
        if response.status == 200:
            return WhoAmIResponse(**data)
        return ErrorResponse(**data, statuscode=response.status)

    async def profile(self, user_id: str) -> ProfileResponse | ErrorResponse:
        url = matrix_api.profile(self.hs_url, user_id)
        LOGGER.info("CLIENT profile")
        response, data = await self.request(url, HTTPMethod.get)
        LOGGER.debug(
            "CLIENT profile data: %s",
            {"headers": response.headers, "body": data},
        )
        if response.status == 200:
            return ProfileResponse(**data)
        return ErrorResponse(**data, statuscode=response.status)

    async def set_displayname(
        self, user_id: str, displayname: str
    ) -> ProfileDisplayNameResponse | ErrorResponse:
        url = matrix_api.profile_displayname(self.hs_url, user_id)
        LOGGER.info("CLIENT set displayname")
        body = ProfileDisplayNameBody(displayname=displayname)
        response, data = await self.request(url, HTTPMethod.put, body.model_dump())
        if response.status == 200:
            return ProfileDisplayNameResponse(**data)
        return ErrorResponse(**data, statuscode=response.status)

    async def update_bot_profile(
        self, user_id: str, displayname: str
    ) -> ProfileResponse | ErrorResponse:
        profile = await self.profile(user_id)
        if isinstance(profile, ErrorResponse) and profile.statuscode == 404:
            await self.set_displayname(user_id, displayname)
        elif isinstance(profile, ProfileResponse):
            if profile.displayname != displayname:
                await self.set_displayname(user_id, displayname)
            return await self.profile(user_id)
        return profile

    async def invite(
        self,
        room_id: str,
        body: InviteToRoomBody,
        user_id: str | None = None,
        ts: int | None = None,
    ) -> InviteToRoomResponse | ErrorResponse:
        url = matrix_api.invite_room(self.hs_url, room_id, user_id, ts)
        LOGGER.info("CLIENT join_room")
        print(url)
        response, data = await self.request(
            url, HTTPMethod.post, body.model_dump(exclude_defaults=True)
        )
        if response.status == 200:
            print(data)
            return InviteToRoomResponse(**data)
        print(data)
        return ErrorResponse(**data, statuscode=response.status)

    async def join_room(
        self,
        room_id: str,
        body: JoinRoomBody,
        user_id: str | None = None,
        ts: int | None = None,
    ) -> JoinRoomResponse | ErrorResponse:
        url = matrix_api.room_join(self.hs_url, room_id, user_id, ts)
        LOGGER.info("CLIENT join_room")
        response, data = await self.request(
            url, HTTPMethod.post, body.model_dump(exclude_defaults=True)
        )
        if response.status == 200:
            return JoinRoomResponse(**data)
        return ErrorResponse(**data, statuscode=response.status)

    async def create_room(
        self, body: CreateRoomBody, user_id: str | None = None, ts: int | None = None
    ) -> CreateRoomResponse | ErrorResponse:
        url = matrix_api.create_room(self.hs_url, user_id, ts)
        LOGGER.info("CLIENT create_room")
        response, data = await self.request(
            url, HTTPMethod.post, body.model_dump(exclude_defaults=True)
        )
        if response.status == 200:
            resp = CreateRoomResponse(**data)
            LOGGER.debug(resp.room_id)
            return resp
        resp = ErrorResponse(**data, statuscode=response.status)
        LOGGER.debug(resp)
        return resp

    async def delete_room(self, room_id: str):
        url = matrix_api.delete_room(self.hs_url, room_id)
        LOGGER.info("CLIENT delete_room")
        response, data = await self.request(
            url, HTTPMethod.delete, headers=self.admin_headers
        )
        if response.status == 200:
            resp = DeleteRoomResponse(**data)
            LOGGER.debug(resp.delete_id)
            return resp
        resp = ErrorResponse(**data, statuscode=response.status)
        LOGGER.debug(resp)
        return resp

    async def delete_rooms(self, room_ids: Sequence[str]):
        for room_id in room_ids:
            await self.delete_room(room_id)

    async def send_event(
        self,
        event_type: str,
        room_id: str,
        room_message: RoomMessage,
        txn_id: str | None = None,
        user_id: str | None = None,
        ts: int | None = None,
    ) -> RoomSendEventResponse | ErrorResponse:
        txn_id = txn_id or new_txn()
        url = matrix_api.room_send_event(
            self.hs_url, room_id, event_type, txn_id, user_id, ts
        )
        LOGGER.info("CLIENT send_event")
        response, data = await self.request(
            url, HTTPMethod.put, room_message.model_dump(exclude_defaults=True)
        )

        if response.status == 200:
            data = RoomSendEventResponse(**data)
            LOGGER.debug(
                "CLIENT send_event: %s",
                {"headers": response.headers, "event_id": data.event_id},
            )
            return data
        data = ErrorResponse(**await response.json(), statuscode=response.status)
        LOGGER.debug(
            "CLIENT send_event error data: %s",
            {"headers": response.headers, "body": data},
        )
        return data

    async def send_state_event(
        self,
        event_type: str,
        room_id: str,
        room_message: Any,
        state_key: str = "",
        user_id: str | None = None,
        ts: int | None = None,
    ) -> RoomSendEventResponse | ErrorResponse:
        url = matrix_api.room_send_state_event(
            self.hs_url, room_id, event_type, state_key, user_id, ts
        )
        LOGGER.info("CLIENT send_state_event")
        response, data = await self.request(url, HTTPMethod.put, room_message)

        if response.status == 200:
            data = RoomSendEventResponse(**data)
            LOGGER.debug(
                "CLIENT send_state_event: %s",
                {"headers": response.headers, "event_id": data.event_id},
            )
            return data
        data = ErrorResponse(**await response.json(), statuscode=response.status)
        LOGGER.debug(
            "CLIENT send_event error data: %s",
            {"headers": response.headers, "body": data},
        )
        return data

    async def create_media(self) -> CreateMediaResponse | ErrorResponse:
        url = matrix_api.create_media(self.hs_url)
        LOGGER.info("CLIENT create_media")
        response, data = await self.request(url, HTTPMethod.post)

        if response.status == 200:
            data = CreateMediaResponse(**data)
            LOGGER.debug(data)
            return data
        data = ErrorResponse(**await response.json(), statuscode=response.status)
        LOGGER.debug(
            "CLIENT create_media error data: %s",
            {"headers": response.headers, "body": data},
        )
        return data

    async def upload_media(
        self,
        server_name: str,
        media_id: str,
        content: bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> UploadMediaResponse | ErrorResponse:
        url = matrix_api.upload_media(self.hs_url, server_name, media_id, filename)
        LOGGER.info("CLIENT upload_media")
        if content_type is None:
            content_type = "application/octet-stream"
        headers = {**self.headers, "Content-Type": content_type}
        response, data = await self.request(
            url, HTTPMethod.put, headers=headers, data=content
        )

        if response.status == 200:
            data = UploadMediaResponse(**data)
            LOGGER.debug(data)
            return data
        data = ErrorResponse(**await response.json(), statuscode=response.status)
        LOGGER.debug(
            "CLIENT upload_media error data: %s",
            {"headers": response.headers, "body": data},
        )
        return data

    async def create_and_upload_media(
        self,
        content: bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> CreateMediaResponse | ErrorResponse:
        resp = await self.create_media()
        if isinstance(resp, CreateMediaResponse):
            server_name, _, media_id = resp.content_uri[6:].partition("/")
            upload_resp = await self.upload_media(
                server_name, media_id, content, filename, content_type
            )
            if isinstance(upload_resp, ErrorResponse):
                return upload_resp
        return resp

    async def download_media(
        self,
        download_path: Path,
        media_url: str,
        allow_redirect: bool = False,
        allow_remote: bool = False,
        timeout_ms: int | None = None,
    ) -> bool | ErrorResponse:
        server_name, _, media_id = media_url[6:].partition("/")
        url = matrix_api.download_media(
            self.hs_url, server_name, media_id, allow_redirect, allow_remote, timeout_ms
        )
        LOGGER.info("CLIENT download media")
        response = await self.raw_request(url, HTTPMethod.get)

        if response.status == 200:
            data = await response.read()
            with open(download_path, "wb") as f:
                f.write(data)
            return True
        data = ErrorResponse(**await response.json(), statuscode=response.status)
        LOGGER.debug(
            "CLIENT download error data: %s",
            {"headers": response.headers, "body": data},
        )
        return data
