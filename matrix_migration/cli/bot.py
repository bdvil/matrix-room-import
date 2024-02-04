import click
from aiohttp import web
from aiohttp.web import Application, Request, Response, run_app

import matrix_migration.appservice.client as client
import matrix_migration.appservice.server as server
from matrix_migration import LOGGER
from matrix_migration.config import Config, load_config


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
        resp = await client.whoami(
            config.homeserver_from.url, config.bot_user, config.as_token
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
            web.post("/_matrix/app/v1/ping", server.handle_ping),
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
