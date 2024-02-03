from aiohttp.web import Application, Request, Response, run_app
import click

from uuid import uuid4

from matrix_migration.config import Config, load_config
from aiohttp import ClientResponse, ClientSession, web


async def ping(hs_url: str, as_id: str, as_token: str) -> ClientResponse | None:
    # ping_url = hs_url + f"/_matrix/client/v1/appservice/{as_id}/ping"
    ping_url = "http://localhost:8181/log"
    headers = {"Authorization": f"Bearer {as_token}"}
    data = {"transaction_id": "mami"}
    async with ClientSession() as session:
        print(f"POSTING here: {ping_url})")
        async with session.post(ping_url, headers=headers, json=data) as response:
            print("PING RESP")
            print(response)
            data = await response.json()
            print("DATA")
            print(data)
            return response


def check_headers(request: Request, hs_token: str) -> bool:
    print(request.headers)
    return ("Authorization" in request.headers.keys()
            and request.headers["Authorization"] == f"Bearer {hs_token}")


async def handle_ping(request: Request) -> Response:
    print("HANDLE PING")
    config: Config = request.app["config"]
    if check_headers(request, config.hs_token):
        return Response(status=200)
    return Response(status=403)


async def handle(request: Request) -> Response:
    print("HANDLE")
    print(request.url)
    return Response()


async def handle_log(request: Request) -> Response:
    print("HANDLE LOG")
    print(request.url)
    print(request.headers)
    data = await request.json()
    print(data)
    return Response()


async def handle_test(request: Request) -> Response:
    try:
        config: Config = request.app["config"]
        resp = await ping(config.homeserver_from.url, config.as_id, config.as_token)
        print("TEST - RESP")
        print(resp)
    except: 
        return Response(status=500)
    return Response(status=200)


@click.command("serve")
def serve():
    config = load_config()
    print(config.model_dump())
    app = Application()
    app["config"] = config
    app.add_routes([
        web.get("/test", handle_test),
        web.post("/log", handle_log),
        web.put("/_matrix/app/v1/transactions/{txnId}", handle),
        web.post("/_matrix/app/v1/ping", handle_ping),
        web.get("/_matrix/app/v1/users/{userId}", handle),
        web.get("/_matrix/app/v1/rooms/{roomAlias}", handle),
        web.get("/_matrix/app/v1/thirdparty/location", handle),
        web.get("/_matrix/app/v1/thirdparty/location/{protocol}", handle),
        web.get("/_matrix/app/v1/thirdparty/protocol/{protocol}", handle),
        web.get("/_matrix/app/v1/thirdparty/user", handle),
        web.get("/_matrix/app/v1/thirdparty/user/{protocol}", handle),
    ])
    run_app(app, port=config.port)
