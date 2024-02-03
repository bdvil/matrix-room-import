import asyncio
from aiohttp.web import Application, Request, Response, run_app
import click

from uuid import uuid4

from matrix_migration.config import Config, load_config
from aiohttp import ClientSession, web


async def ping(hs_url: str, as_id: str, as_token: str):
    ping_url = hs_url + f"/_matrix/client/v1/appservice/{as_id}/ping"
    headers = {"Authorization": f"Bearer {as_token}"}
    data = {"transaction_id": f"mami-{uuid4()}"}
    async with ClientSession(headers=headers) as session:
        async with session.post(ping_url, json=data) as response:
            print(response)


def check_headers(request: Request, hs_token: str) -> bool:
    print(request.headers)
    return ("Authorization" in request.headers.keys()
            and request.headers["Authorization"] == f"Bearer {hs_token}")


async def handle_ping(request: Request) -> Response:
    config: Config = request.app["config"]
    if check_headers(request, config.hs_token):
        return Response(status=200)
    return Response(status=403)


async def handle(request: Request) -> Response:
    print(request.query_string)
    return Response()


@click.command("serve")
def serve():
    config = load_config()
    print(config.model_dump())
    asyncio.run(ping(config.homeserver_from.url, config.as_id, config.as_token))
    app = Application()
    app["config"] = config
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
    run_app(app, port=config.port)
