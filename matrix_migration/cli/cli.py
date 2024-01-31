import click

from .bot import serve


@click.group()
def root():
    pass


root.add_command(serve)
