"""A command-line interface for metar-weather-bot."""
import json
import os
from datetime import datetime

import click
import pytz
import requests
import twitter
from metar import Metar
from retry import retry
from rich import print


@click.group()
def cli():
    """Download, parse and post weather data from LAX airport."""
    pass


@cli.command()
def tweet():
    """Post a tweet to @LAXWeatherReport."""
    print("🐦 Posting to @LAXWeatherReport on Twitter")

    # Read in data
    data = json.load(open("./latest.json"))

    # Format the message
    dt = datetime.strptime(data["local_time"], "%Y-%m-%d %H:%M:%S%z")
    message = f"LAX conditions at {dt.strftime('%-H:%M %p')}\n\n"

    if data["temperature"]:
        message += f"🌡️ {data['temperature']}\n"

    if data["dewpoint"]:
        message += f"🌫️ {data['dewpoint']} dew point\n"

    if data["wind"]:
        message += f"🌬️ {data['wind'].s.capitalize()}\n"

    if data["visibility"]:
        message += f"🔭 {data['visibility']} visibility\n"

    if data["sky"]:
        message += f"☁️ {data['sky'].s.capitalize()}\n"

    if data["pressure"]:
        message += f"⏱️ {data['pressure']} air pressure\n"

    if data["precipitation"]:
        s = data["precipitation"].s.capitalize()
        if "thunder" in s:
            message += f"⛈️ {s}\n"
        elif "drizzle" in s or "rain" in s:
            message += f"🌧️ {s}\n"
        elif "snow" in s or "ice" in s:
            message += f"🌨️ {s}\n"
        else:
            message += f"🌧️ {s}\n"

    # Add source URL
    message += "https://aviationweather.gov/adds/metars/index?submit=1&station_ids=KLAX&chk_metars=on&hoursStr=8&std_trans=translated\n"
            
    # Tack on some hashtags
    message += "\n#wx #metar #CAwx #klax"
    print(message)

    # Post the message
#    api = get_twitter_client()
#    io = open("latest.jpg", "rb")
#    media_id = api.UploadMediaSimple(io)
#    alt_text = "A screen capture from the @ABC7 web camera at LAX airport"
#    api.PostMediaMetadata(media_id, alt_text)
#    api.PostUpdate(message, media=[media_id])


@cli.command()
def metar():
    """Download the latest METAR weather report."""
    print("🌡️ Downloading METAR report")

    # Download the data
    url = "https://tgftp.nws.noaa.gov/data/observations/metar/stations/KLAX.TXT"
    r = _request(url)

    # Write out the raw report
    with open("./latest.txt", "w") as f:
        f.write(r.text)

    # Parse out the report
    obs = Metar.Metar(r.text.split("\n")[1])

    d = {}

    d["temperature"] = obs.temp.string("F")
    d["dewpoint"] = obs.dewpt.string("F")
    d["wind"] = obs.wind()
    d["visibility"] = obs.visibility()
    if obs.runway:
        d["runway"] = obs.runway_visual_range()
    else:
        d["runway"] = None
    d["pressure"] = obs.press.string("mb")
    d["sky"] = obs.sky_conditions()
    if obs.precip_1hr:
        d["precipitation"] = obs.precip_1hr.string("in")
    else:
        d["precipitation"] = None

    local_tz = pytz.timezone("America/Los_Angeles")
    local_time = obs.time.replace(tzinfo=pytz.utc).astimezone(local_tz)
    d["local_time"] = str(local_time)

    # Write it out
    json.dump(d, open("./latest.json", "w"), indent=2)


@cli.command()
def abc7():
    """Download the ABC7 live camera image."""
    print("📸 Downloading latest photo")

    # Download the data
    url = "https://cdns.abclocal.go.com/three/kabc/webcam/web1-2.jpg?w=630&r=16%3A9"
    r = _request(url, stream=True)

    # Write it out
    with open("./latest.jpg", "wb") as f:
        for chunk in r:
            f.write(chunk)


@retry(tries=3, delay=5, backoff=2)
def _request(url, **kwargs):
    r = requests.get(url, **kwargs)
    assert r.ok
    return r


def get_twitter_client():
    """Return a Twitter client ready to post to the API."""
    return twitter.Api(
        consumer_key=os.getenv("TWITTER_CONSUMER_KEY"),
        consumer_secret=os.getenv("TWITTER_CONSUMER_SECRET"),
        access_token_key=os.getenv("TWITTER_ACCESS_TOKEN_KEY"),
        access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
    )


if __name__ == "__main__":
    cli()
