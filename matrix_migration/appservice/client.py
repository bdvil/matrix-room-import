from uuid import uuid4

from aiohttp import ClientResponse, ClientSession

from matrix_migration import LOGGER, matrix_api


def new_txn() -> str:
    return str(uuid4())


async def ping(
    hs_url: str,
    as_id: str,
    as_token: str,
    transaction_id: str | None = None,
) -> ClientResponse | None:
    url = matrix_api.ping(hs_url, as_id)
    headers = {
        "Authorization": f"Bearer {as_token}",
    }
    data = {}
    if transaction_id is not None:
        data["transaction_id"] = transaction_id
    async with ClientSession() as session:
        LOGGER.info("CLIENT ping")
        async with session.post(url, headers=headers, json=data) as response:
            data = await response.json()
            LOGGER.debug(
                "CLIENT ping data: %s",
                {"headers": response.headers, "body": data},
            )
            return response


async def whoami(
    hs_url: str, user_id: str, as_token: str
) -> ClientResponse | None:
    url = matrix_api.whoami(hs_url, user_id)
    headers = {
        "Authorization": f"Bearer {as_token}",
    }
    async with ClientSession() as session:
        LOGGER.info("CLIENT whoami")
        async with session.get(url, headers=headers, json={}) as response:
            data = await response.json()
            LOGGER.debug(
                "CLIENT whoami data: %s",
                {"headers": response.headers, "body": data},
            )
            return response


async def profile(
    hs_url: str, user_id: str, as_token: str
) -> ClientResponse | None:
    url = matrix_api.profile(hs_url, user_id)
    headers = {
        "Authorization": f"Bearer {as_token}",
    }
    async with ClientSession() as session:
        LOGGER.info("CLIENT profile")
        async with session.get(url, headers=headers, json={}) as response:
            data = await response.json()
            LOGGER.debug(
                "CLIENT profile data: %s",
                {"headers": response.headers, "body": data},
            )
            return response


async def set_displayname(
    hs_url: str, user_id: str, as_token: str, displayname: str
) -> ClientResponse | None:
    url = matrix_api.profile_displayname(hs_url, user_id)
    headers = {
        "Authorization": f"Bearer {as_token}",
    }
    async with ClientSession() as session:
        LOGGER.info("CLIENT set displayname")
        async with session.put(
            url, headers=headers, json={"displayname": displayname}
        ) as response:
            data = await response.json()
            LOGGER.debug(
                "CLIENT set displayname data: %s",
                {"headers": response.headers, "body": data},
            )
            return response


async def update_bot_profile(
    hs_url: str, user_id: str, as_token: str, displayname: str
) -> ClientResponse | None:
    response = await profile(hs_url, user_id, as_token)
    if response is None or response.status == 404:
        response = await set_displayname(
            hs_url, user_id, as_token, displayname
        )
    assert response is not None
    body = await response.json()
    if body["displayname"] != displayname:
        response = await set_displayname(
            hs_url, user_id, as_token, displayname
        )
    response = await profile(hs_url, user_id, as_token)
    return response


async def send_event(
    hs_url: str,
    as_token: str,
    event_type: str,
    room_id: str,
    body: str,
    txn_id: str | None = None,
) -> ClientResponse | None:
    txn_id = txn_id or new_txn()
    url = matrix_api.room_send_event(hs_url, room_id, event_type, txn_id)
    headers = {
        "Authorization": f"Bearer {as_token}",
    }
    async with ClientSession() as session:
        LOGGER.info("CLIENT send_event")
        async with session.put(
            url, headers=headers, json={"body": body, "msgtype": "m.text"}
        ) as response:
            if response.status == 200:
                data = await response.json()
                event_id = data["event_id"]
                LOGGER.debug(
                    "CLIENT send_event: %s",
                    {"headers": response.headers, "event_id": event_id},
                )
                return event_id
            else:
                data = await response.json()
                LOGGER.debug(
                    "CLIENT send_event error data: %s",
                    {"headers": response.headers, "body": data},
                )
                return response
