from aiohttp import ClientResponse, ClientSession

from matrix_migration import LOGGER


async def ping(
    hs_url: str,
    as_id: str,
    as_token: str,
    transaction_id: str | None = None,
) -> ClientResponse | None:
    ping_url = hs_url + f"/_matrix/client/v1/appservice/{as_id}/ping"
    headers = {
        "Authorization": f"Bearer {as_token}",
    }
    data = {}
    if transaction_id is not None:
        data["transaction_id"] = transaction_id
    async with ClientSession() as session:
        LOGGER.info("CLIENT ping")
        async with session.post(
            ping_url, headers=headers, json=data
        ) as response:
            data = await response.json()
            LOGGER.debug(
                "CLIENT ping data: %s",
                {"headers": response.headers, "body": data},
            )
            return response
