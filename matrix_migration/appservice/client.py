from collections.abc import Mapping, Sequence
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
    PresenceEnum,
    QueryKeysBody,
    QueryKeysResponse,
    SyncResponse,
    UserIdentifierUser,
)


def new_txn() -> str:
    return str(uuid4())


class Client:
    def __init__(self, hs_url: str, as_token: str, as_id: str):
        self.hs_url = hs_url
        self.as_token = as_token
        self.as_id = as_id
        self.headers = {
            "Authorization": f"Bearer {as_token}",
        }

    async def ping(
        self,
        transaction_id: str | None = None,
    ) -> ClientResponse | None:
        url = matrix_api.ping(self.hs_url, self.as_id)
        data = {}
        if transaction_id is not None:
            data["transaction_id"] = transaction_id
            LOGGER.info("CLIENT ping")
            async with ClientSession(headers=self.headers) as session:
                async with session.post(url, json=data) as response:
                    data = await response.json()
                    LOGGER.debug(
                        "CLIENT ping data: %s",
                        {"headers": response.headers, "body": data},
                    )
                    return response

    async def whoami(self, user_id: str) -> ClientResponse | None:
        url = matrix_api.whoami(self.hs_url, user_id)
        LOGGER.info("CLIENT whoami")
        async with ClientSession(headers=self.headers) as session:
            async with session.get(url, json={}) as response:
                data = await response.json()
                LOGGER.debug(
                    "CLIENT whoami data: %s",
                    {"headers": response.headers, "body": data},
                )
                return response

    async def profile(self, user_id: str) -> ClientResponse | None:
        url = matrix_api.profile(self.hs_url, user_id)
        LOGGER.info("CLIENT profile")
        async with ClientSession(headers=self.headers) as session:
            async with session.get(url, json={}) as response:
                data = await response.json()
                LOGGER.debug(
                    "CLIENT profile data: %s",
                    {"headers": response.headers, "body": data},
                )
                return response

    async def set_displayname(
        self, user_id: str, displayname: str
    ) -> ClientResponse | None:
        url = matrix_api.profile_displayname(self.hs_url, user_id)
        LOGGER.info("CLIENT set displayname")
        async with ClientSession(headers=self.headers) as session:
            async with session.put(url, json={"displayname": displayname}) as response:
                data = await response.json()
                LOGGER.debug(
                    "CLIENT set displayname data: %s",
                    {"headers": response.headers, "body": data},
                )
                return response

    async def update_bot_profile(
        self, user_id: str, displayname: str
    ) -> ClientResponse | None:
        response = await self.profile(user_id)
        if response is None or response.status == 404:
            response = await self.set_displayname(user_id, displayname)
        assert response is not None
        body = await response.json()
        if body["displayname"] != displayname:
            response = await self.set_displayname(user_id, displayname)
        return await self.profile(user_id)

    async def join_room(self, room_id: str) -> JoinRoomResponse | ErrorResponse | None:
        url = matrix_api.room_join(self.hs_url, room_id)
        LOGGER.info("CLIENT join_room")
        async with ClientSession(headers=self.headers) as session:
            async with session.post(url, json=JoinRoomBody().model_dump()) as response:
                if response.status == 200:
                    data = JoinRoomResponse(**await response.json())
                    return data
                else:
                    data = ErrorResponse(**await response.json())
                    return data

    async def login(
        self, user_id_or_localpart: str
    ) -> LoginResponse | ErrorResponse | None:
        url = matrix_api.login(self.hs_url)
        LOGGER.info(f"CLIENT login {url}")
        body = LoginBody(
            type=LoginType.application_service,
            identifier=UserIdentifierUser(user=user_id_or_localpart),
        )
        print(body.model_dump())
        async with ClientSession(headers=self.headers) as session:
            async with session.post(
                url,
                json=body.model_dump(exclude_defaults=True),
            ) as response:
                if response.status == 200:
                    resp_data = await response.json()
                    LOGGER.debug(resp_data)
                    data = LoginResponse(**resp_data)
                    LOGGER.debug(data)
                    return data
                else:
                    data = ErrorResponse(**await response.json())
                    LOGGER.debug(data)
                    return data

    async def query_keys(
        self, device_keys: Mapping[str, Sequence[str]], timeout: int = 10_000
    ) -> QueryKeysResponse | ErrorResponse | None:
        url = matrix_api.query_key(self.hs_url)
        LOGGER.info(f"CLIENT query_keys {url}")
        async with ClientSession(headers=self.headers) as session:
            async with session.post(
                url,
                json=QueryKeysBody(
                    device_keys=device_keys, timeout=timeout
                ).model_dump(),
            ) as response:
                if response.status == 200:
                    data = QueryKeysResponse(**await response.json())
                    return data
                else:
                    data = ErrorResponse(**await response.json())
                    return data

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
    ) -> str | ErrorResponse | None:
        txn_id = txn_id or new_txn()
        url = matrix_api.room_send_event(self.hs_url, room_id, event_type, txn_id)
        LOGGER.info("CLIENT send_event")
        async with ClientSession(headers=self.headers) as session:
            async with session.put(
                url, json={"body": body, "msgtype": "m.text"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    event_id: str = data["event_id"]
                    LOGGER.debug(
                        "CLIENT send_event: %s",
                        {"headers": response.headers, "event_id": event_id},
                    )
                    return event_id
                else:
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
    ) -> SyncResponse | ErrorResponse | None:
        url = matrix_api.sync(
            self.hs_url, filter, full_state, set_presence, since, timeout, user_id
        )
        LOGGER.info(f"CLIENT sync {url}")
        async with ClientSession(headers=self.headers) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = SyncResponse(**await response.json())
                    return data
                else:
                    data = ErrorResponse(**await response.json())
                    return data
