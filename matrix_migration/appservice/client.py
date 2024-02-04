from aiohttp import ClientResponse, ClientSession

from matrix_migration import LOGGER, matrix_api


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


async def create_profile_if_missing(
    hs_url: str, user_id: str, as_token: str, displayname: str
) -> ClientResponse | None:
    response = await profile(hs_url, user_id, as_token)
    if response is None or response.status == 404:
        response = await set_displayname(
            hs_url, user_id, as_token, displayname
        )
    response = await profile(hs_url, user_id, as_token)
    return response
