import json
import pytz
import click
import requests
from rich import progress
from metar import Metar


@click.group()
def cli():
    """A command-line interface for metar-weather-bot."""
    pass


@cli.command()
def metar():
    """Download the latest METAR weather report."""
    print("🌡️ Downloading METAR report")

    # Download the data
    url = "https://tgftp.nws.noaa.gov/data/observations/metar/stations/KLAX.TXT"
    r = requests.get(url)
    assert r.ok

    # Write out the raw report
    with open("./latest.txt", "w") as f:
        f.write(r.text)

    # Parse out the report
    obs = Metar.Metar(r.text.split("\n")[1])

    d = {}

    d['temperature'] = obs.temp.string("F")
    d['dewpoint'] = obs.dewpt.string("F")
    d['wind'] = obs.wind()
    d['visibility'] = obs.visibility()
    if obs.runway:
        d['runway'] = obs.runway_visual_range()
    else:
        d['runway'] = None
    d['pressure'] = obs.press.string("mb")
    d['sky'] = obs.sky_conditions()
    if obs.precip_1hr:
        d['precipitation'] = obs.precip_1hr.string("in")
    else:
        d['precipitation'] = None

    local_tz = pytz.timezone("America/Los_Angeles")
    local_time = obs.time.replace(tzinfo=pytz.utc).astimezone(local_tz)
    d['local_time'] = str(local_time)

    # Write it out
    json.dump(d, open("./latest.json", "w"), indent=2)


@cli.command()
def abc7():
    """
    Download the ABC7 live camera image.
    """
    print("📸 Downloading latest photo")

    # Download the data
    url = "https://cdns.abclocal.go.com/three/kabc/webcam/web1-2.jpg?w=630&r=16%3A9"
    r = requests.get(url, stream=True)
    assert r.ok

    # Write it out
    with open("./latest.jpg", "wb") as f:
        for chunk in r:
            f.write(chunk)


if __name__ == "__main__":
    cli()
