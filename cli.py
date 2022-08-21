import click
import requests
from rich import progress


@click.group()
def cli():
    """A command-line interface for metar-weather-bot."""
    pass


@cli.command()
def abc7_camera():
    """
    Download the ABC7 live camera image.
    """
    print("📸 Downloading latest photo")
    r = requests.get("https://cdns.abclocal.go.com/three/kabc/webcam/web1-2.jpg?w=630&r=16%3A9", stream=True)
    assert r.ok
    with open("./latest.jpg", "wb") as f:
        for chunk in r:
            f.write(chunk)


if __name__ == "__main__":
    cli()
