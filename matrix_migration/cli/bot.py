import click

from matrix_migration.config import load_config


@click.command("serve")
def serve():
    config = load_config()
    print(config.model_dump())
