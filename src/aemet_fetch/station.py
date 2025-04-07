"""List and get data from AEMET weather stations."""

import collections
import datetime
import pathlib
from typing import Tuple

import pandas as pd
import requests
import rich.console
import rich.table

import typer

app = typer.Typer(help="Get data from a set of AEMET weather stations")


def _list(api_key: str, api_url: str):
    """List weather stations.

    :param api_key: API key for AEMET Open Data Portal
    :param api_url: API URL for AEMET Open Data Portal

    :return: List of weather stations (tuple of tuples)
    """
    return [("1089U", "Ramales de la Victoria")]


@app.command(name="list")
def list_cmd(ctx: typer.Context):
    """List weather stations."""
    api_key = ctx.obj["api_key"]
    api_url = ctx.obj["api_url"]

    stations = _list(api_key, api_url)

    console = rich.console.Console()
    table = rich.table.Table(title="Weather Stations")
    table.add_column("ID", justify="left", style="cyan")
    table.add_column("Name", justify="left", style="magenta")
    table.add_column("Province", justify="left", style="yellow")
    table.add_column("Latitude", justify="right", style="green")
    table.add_column("Longitude", justify="right", style="green")

    for station_id, station_name in stations:
        table.add_row(station_id, station_name)

    console.print(table)


NON_DATA_FIELDS = ["fint", "idema", "lat", "lon", "alt", "ubi"]


def reorder_dict(data_dict, priority=NON_DATA_FIELDS):
    """Reorder a dictionary to have certain keys first."""
    other_keys = sorted([k for k in data_dict if k not in priority])

    # Combine the keys in desired order
    all_keys = priority + other_keys

    # Create and return new OrderedDict in the correct order
    return collections.OrderedDict(
        (k, data_dict[k]) for k in all_keys if k in data_dict
    )


def _latest(api_key: str, api_url: str, station_id: str) -> Tuple[list, dict]:
    """Get the latest data from a weather station.

    :param api_key: API key for AEMET Open Data Portal
    :param api_url: API URL for AEMET Open Data Portal
    :param station_id: ID of the weather station

    :return: Latest data (list) and metadata (dict)
    """
    url = f"{api_url}/observacion/convencional/datos/estacion/{station_id}"
    headers = {"Accept": "application/json", "api_key": api_key}
    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code != 200:
        print(f"Error!: {response.status_code} - {response.text}")
        raise typer.Exit(1)

    data_url = response.json().get("datos")
    metadata_url = response.json().get("metadatos")

    data = requests.get(data_url, headers=headers, timeout=10)
    metadata = requests.get(metadata_url, headers=headers, timeout=10)

    ordered_data = [reorder_dict(d) for d in data.json()]
    return ordered_data, metadata.json()


def write_to_file(data, output_file):
    """Write data to a file."""
    if output_file.exists():
        df = pd.read_csv(output_file, sep=";", index_col=0, encoding="utf-8")
        aux = pd.DataFrame(data)
        aux.set_index("fint", inplace=True)
        df.combine_first(aux)
    else:
        df = pd.DataFrame(data)
        df.set_index("fint", inplace=True)

    df.to_csv(
        output_file,
        sep=";",
        index=True,
        header=True,
        encoding="utf-8",
        date_format="%Y-%m-%d %H:%M:%S",
    )


@app.command()
def latest(
    ctx: typer.Context,
    station_id: str = typer.Argument(..., help="ID of the weather station"),
    long: bool = typer.Option(
        False, "--long", help="Show long format of metadata fields"
    ),
    save_to_file: bool = typer.Option(
        False,
        "--save-to-file",
        help="Save the data to a file, based on the weather station and the day where "
        "the data was collected. The file name is 'aemet-<station_id>_<date>.csv'. "
        "WARNING: the date for the file name is when the script is running, not "
        "the date of the observations!",
    ),
):
    """Get the latest data from a weather station."""
    api_key = ctx.obj["api_key"]
    api_url = ctx.obj["api_url"]

    data, metadata = _latest(api_key, api_url, station_id)

    if save_to_file:
        today = datetime.datetime.now().strftime("%Y%m%d")
        output_file = pathlib.Path(f"aemet-{station_id}_{today}.csv")
        write_to_file(data, output_file)
        raise typer.Exit(0)

    console = rich.console.Console()

    lat = data[0].get("lat")
    lon = data[0].get("lon")
    name = data[0].get("ubi")

    table = rich.table.Table(
        title=f"Latest Weather Data for: {station_id} ({lat}, {lon}) - {name}"
    )

    fields_from_data = data[0].keys()
    fields_from_metadata = {
        c["id"]: c["descripcion"] for c in metadata.get("campos", [])
    }
    for field in fields_from_data:
        color = "cyan" if field in NON_DATA_FIELDS else "magenta"
        if not long:
            table.add_column(field, justify="left", style=color)
        if long:
            table.add_column(fields_from_metadata[field], justify="left", style=color)

    for obs in data:
        vals = [str(i) for i in obs.values()]
        table.add_row(*vals)
    # fields = metadata.get("campos", [])
    # for field in fields:
    #     table.add_column(field["id"], justify="left", style="cyan")
    # table.add_column("Date", justify="left", style="cyan")
    # table.add_column("Temperature", justify="right", style="magenta")
    # table.add_column("Humidity", justify="right", style="yellow")
    # table.add_column("Wind Speed", justify="right", style="green")
    console.print(table)
