from aiohttp import web

from matrix_migration import LOGGER
from matrix_migration.config import Config


def check_headers(request: web.Request, hs_token: str) -> bool:
    return (
        "Authorization" in request.headers.keys()
        and request.headers["Authorization"] == f"Bearer {hs_token}"
    )


async def handle_ping(request: web.Request) -> web.Response:
    body = await request.json()
    LOGGER.debug(
        "SERVER ping data: %s",
        {"url": request.url, "headers": request.headers, "body": body},
    )
    config: Config = request.app["config"]
    if check_headers(request, config.hs_token):
        return web.json_response({}, status=200)
    return web.json_response({}, status=403)
