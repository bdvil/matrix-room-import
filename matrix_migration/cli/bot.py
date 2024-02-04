import click
from aiohttp import ClientResponse, ClientSession, web
from aiohttp.web import Application, Request, Response, run_app

from matrix_migration import LOGGER
from matrix_migration.config import Config, load_config


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


def check_headers(request: Request, hs_token: str) -> bool:
    return (
        "Authorization" in request.headers.keys()
        and request.headers["Authorization"] == f"Bearer {hs_token}"
    )


async def handle_ping(request: Request) -> Response:
    body = await request.json()
    LOGGER.debug(
        "SERVER ping data: %s",
        {"url": request.url, "headers": request.headers, "body": body},
    )
    config: Config = request.app["config"]
    if check_headers(request, config.hs_token):
        return web.json_response({}, status=200)
    return web.json_response({}, status=403)


async def handle(request: Request) -> Response:
    body = await request.json()
    LOGGER.debug(
        "SERVER request data: %s",
        {"url": request.url, "headers": request.headers, "body": body},
    )
    return web.json_response({}, status=200)


async def handle_log(request: Request) -> Response:
    body = await request.json()
    LOGGER.info(
        "SERVER ping: %s",
        {"url": request.url, "headers": request.headers, "body": body},
    )
    return web.json_response({}, status=200)


async def handle_test(request: Request) -> Response:
    try:
        config: Config = request.app["config"]
        resp = await ping(
            config.homeserver_from.url, config.as_id, config.as_token
        )
        LOGGER.info(
            "TEST success: %s",
            {
                "url": request.url,
                "headers": request.headers,
                "resp": resp,
            },
        )
    except Exception:
        LOGGER.info("TEST failure")
        return web.json_response({}, status=500)
    return web.json_response({}, status=200)


@click.command("serve")
def serve():
    config = load_config()
    LOGGER.debug("CONFIG: %s", config.model_dump())
    app = Application()
    app["config"] = config
    app.add_routes(
        [
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
        ]
    )
    run_app(app, port=config.port)
