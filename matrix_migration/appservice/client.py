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
