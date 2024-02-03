import click

from matrix_migration.config import load_config
from aiohttp import web


async def handle(request: web.Request) -> web.Response:
    print(request.query_string)
    return web.Response()


@click.command("serve")
def serve():
    config = load_config()
    print(config.model_dump())
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
