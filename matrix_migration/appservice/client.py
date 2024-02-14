from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any
from uuid import uuid4

from aiohttp import ClientResponse, ClientSession

from matrix_migration import LOGGER, matrix_api
from matrix_migration.appservice.types import (
    ErrorResponse,
    JoinRoomBody,
    JoinRoomResponse,
    LoginBody,
    LoginResponse,
    LoginType,
    MsgType,
    PingBody,
    PingResponse,
    PresenceEnum,
    ProfileDisplayNameBody,
    ProfileDisplayNameResponse,
    ProfileResponse,
    QueryKeysBody,
    QueryKeysResponse,
    RoomMessage,
    RoomSendEventResponse,
    SyncResponse,
    UserIdentifierUser,
    WhoAmIResponse,
)
from matrix_migration.store import BotInfos


def new_txn() -> str:
    return str(uuid4())


class HTTPMethod(str, Enum):
    post = "POST"
    put = "PUT"
    get = "GET"
    delete = "DELETE"


class Client:
    def __init__(self, hs_url: str, as_token: str, as_id: str, db_conninfo: str):
        self.hs_url = hs_url
        self.as_token = as_token
        self.as_id = as_id
        self.headers = {
            "Authorization": f"Bearer {as_token}",
        }

        self.bot_infos = BotInfos(db_conninfo)

    async def request(
        self, url: str, method: HTTPMethod, body: Any = None
    ) -> tuple[ClientResponse, Any]:
        if body is None:
            body = {}
        async with ClientSession(headers=self.headers) as session:
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

    async def join_room(self, room_id: str) -> JoinRoomResponse | ErrorResponse:
        url = matrix_api.room_join(self.hs_url, room_id)
        LOGGER.info("CLIENT join_room")
        response, data = await self.request(
            url, HTTPMethod.post, JoinRoomBody().model_dump()
        )
        if response.status == 200:
            return JoinRoomResponse(**data)
        return ErrorResponse(**data)

    async def login(self, user_id_or_localpart: str) -> LoginResponse | ErrorResponse:
        url = matrix_api.login(self.hs_url)
        await self.bot_infos.sync()

        LOGGER.info(f"CLIENT login {url}")

        LOGGER.debug(f"device_id pre login: {self.bot_infos.device_id}")
        body = LoginBody(
            device_id=self.bot_infos.device_id,
            type=LoginType.application_service,
            identifier=UserIdentifierUser(user=user_id_or_localpart),
        )
        response, data = await self.request(
            url, HTTPMethod.post, body.model_dump(exclude_none=True)
        )
        if response.status == 200:
            data = LoginResponse(**data)
            LOGGER.debug(data)
            await self.bot_infos.set_device_id(data.device_id)
            await self.bot_infos.set_access_token(data.access_token)
            return data
        data = ErrorResponse(**data)
        LOGGER.debug(data)
        return data

    async def query_keys(
        self, device_keys: Mapping[str, Sequence[str]], timeout: int = 10_000
    ) -> QueryKeysResponse | ErrorResponse:
        url = matrix_api.query_key(self.hs_url)
        LOGGER.info(f"CLIENT query_keys {url}")
        body = QueryKeysBody(device_keys=device_keys, timeout=timeout).model_dump()
        response, data = await self.request(url, HTTPMethod.post, body)
        if response.status == 200:
            data = QueryKeysResponse(**await response.json())
            return data
        return ErrorResponse(**await response.json())

    async def get_self_keys(
        self, device_keys: Mapping[str, Sequence[str]], timeout: int = 10_000
    ):
        data = await self.query_keys(device_keys, timeout)
        LOGGER.debug(data)

    async def send_event(
        self,
        event_type: str,
        room_id: str,
        body: str,
        txn_id: str | None = None,
    ) -> RoomSendEventResponse | ErrorResponse:
        txn_id = txn_id or new_txn()
        url = matrix_api.room_send_event(self.hs_url, room_id, event_type, txn_id)
        LOGGER.info("CLIENT send_event")
        req_body = RoomMessage(body=body, msgtype=MsgType.text)
        response, data = await self.request(
            url, HTTPMethod.put, req_body.model_dump(exclude_defaults=True)
        )

        if response.status == 200:
            data = RoomSendEventResponse(**data)
            LOGGER.debug(
                "CLIENT send_event: %s",
                {"headers": response.headers, "event_id": data.event_id},
            )
            return data
        data = ErrorResponse(**await response.json())
        LOGGER.debug(
            "CLIENT send_event error data: %s",
            {"headers": response.headers, "body": data},
        )
        return data

    async def sync(
        self,
        filter: str | None = None,
        full_state: bool = False,
        set_presence: PresenceEnum | None = None,
        since: str | None = None,
        timeout: int = 0,
        user_id: str | None = None,
    ) -> SyncResponse | ErrorResponse:
        url = matrix_api.sync(
            self.hs_url, filter, full_state, set_presence, since, timeout, user_id
        )
        LOGGER.info(f"CLIENT sync {url}")
        response, data = await self.request(url, HTTPMethod.get)
        if response.status == 200:
            return SyncResponse(**data)
        return ErrorResponse(**data)
