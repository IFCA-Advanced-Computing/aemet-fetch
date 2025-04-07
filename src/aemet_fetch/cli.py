"""Command line interface for the application."""

import typer
from typing_extensions import Annotated

import aemet_fetch
from aemet_fetch import station


app = typer.Typer(help="Get data from a set of AEMET weather stations")
app.add_typer(station.app, name="station")


def version_callback(value: bool):
    """Display the version of the package."""
    if value:
        typer.echo(aemet_fetch.extract_version())
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    api_key: Annotated[
        str,
        typer.Option(
            "--api-key",
            prompt=True,
            envvar="AEMET_API_KEY",
            help="API key for AEMET Open Data Portal",
        ),
    ],
    api_url: Annotated[
        str, typer.Option("--api-url", help="API URL for AEMET Open Data Portal")
    ] = "https://opendata.aemet.es/opendata/api",
    version: bool = typer.Option(
        False,
        "-v",
        "--version",
        is_eager=True,
        callback=version_callback,
        help="Print the version and exit",
    ),
):
    """Command line interface for the application."""
    ctx.obj = {"api_key": api_key, "api_url": api_url}
