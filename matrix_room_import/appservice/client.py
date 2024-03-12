from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any
from uuid import uuid4

from aiohttp import ClientResponse, ClientSession

from matrix_room_import import LOGGER, matrix_api
from matrix_room_import.appservice.types import (
    CreateRoomBody,
    CreateRoomResponse,
    DeleteRoomResponse,
    ErrorResponse,
    JoinRoomBody,
    JoinRoomResponse,
    PingBody,
    PingResponse,
    ProfileResponse,
    RoomMessage,
    RoomSendEventResponse,
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

    async def request(
        self,
        url: str,
        method: HTTPMethod,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> tuple[ClientResponse, Any]:
        if body is None:
            body = {}
        if headers is None:
            headers = self.headers
        async with ClientSession(headers=headers) as session:
            async with session.request(method.value, url, json=body) as response:
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

    async def join_room(self, room_id: str) -> JoinRoomResponse | ErrorResponse:
        url = matrix_api.room_join(self.hs_url, room_id)
        LOGGER.info("CLIENT join_room")
        response, data = await self.request(
            url, HTTPMethod.post, JoinRoomBody().model_dump()
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
