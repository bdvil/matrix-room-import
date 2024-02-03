import asyncio
import click

from uuid import uuid4

from matrix_migration.config import load_config
from aiohttp import ClientSession, web


async def ping(hs_url: str, as_id: str, as_token: str):
    ping_url = hs_url + f"/_matrix/client/v1/appservice/{as_id}/ping"
    headers = {"Authorization": f"Bearer {as_token}"}
    data = {"transaction_id": f"mami-{uuid4()}"}
    async with ClientSession(headers=headers) as session:
        async with session.post(ping_url, json=data) as response:
            print(response)


async def handle(request: web.Request) -> web.Response:
    print(request.query_string)
    return web.Response()


@click.command("serve")
def serve():
    config = load_config()
    print(config.model_dump())
    asyncio.run(ping(config.homeserver_from.url, config.as_id, config.as_token))
    app = web.Application()
    app.add_routes([
        web.put("/_matrix/app/v1/transactions/{txnId}", handle),
        web.post("/_matrix/app/v1/ping", handle),
        web.get("/_matrix/app/v1/users/{userId}", handle),
        web.get("/_matrix/app/v1/rooms/{roomAlias}", handle),
        web.get("/_matrix/app/v1/thirdparty/location", handle),
        web.get("/_matrix/app/v1/thirdparty/location/{protocol}", handle),
        web.get("/_matrix/app/v1/thirdparty/protocol/{protocol}", handle),
        web.get("/_matrix/app/v1/thirdparty/user", handle),
        web.get("/_matrix/app/v1/thirdparty/user/{protocol}", handle),
    ])
    web.run_app(app, port=config.port)
