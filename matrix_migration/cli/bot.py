import click

from matrix_migration.config import load_config
from aiohttp import web


@click.command("serve")
def serve():
    config = load_config()
    print(config.model_dump())
    app = web.Application()
    app.add_routes([

    ])
    web.run_app(app, port=config.port)
