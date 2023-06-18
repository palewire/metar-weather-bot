"""A command-line interface for metar-weather-bot."""
import json
import os
from datetime import datetime

import click
import pytz
import requests
import twitter
from mastodon import Mastodon
from metar import Metar
from retry import retry
from rich import print


@click.group()
def cli():
    """Download, parse and post weather data from LAX airport."""
    pass


@cli.command()
def post():
    """Post a tweet to @LAXWeatherBot on Twitter and @LAXWeather on Mastodon."""
    # Read in data
    metar = json.load(open("./latest.json"))
    aqi = json.load(open("./aqi.json"))

    # Format the metar message
    dt = datetime.strptime(metar["local_time"], "%Y-%m-%d %H:%M:%S%z")
    message = f"LAX at {dt.strftime('%-I:%M %p')}\n\n"

    if metar["temperature"]:
        message += f"🌡️ {metar['temperature']}\n"

    if metar["dewpoint"]:
        message += f"🌫️ {metar['dewpoint']} dew point\n"

    if metar["wind"]:
        message += f"🌬️ {_clean_wind(metar['wind'])}\n"

    if metar["visibility"]:
        message += f"🔭 {metar['visibility']} visibility\n"

    if metar["sky"]:
        message += f"☁️ {metar['sky'].capitalize()}\n"

    if metar["pressure"]:
        message += f"⏱️ {metar['pressure']} air pressure\n"

    if metar["precipitation"]:
        s = metar["precipitation"].capitalize()
        if "thunder" in s:
            message += f"⛈️ {s}\n"
        elif "drizzle" in s or "rain" in s:
            message += f"🌧️ {s}\n"
        elif "snow" in s or "ice" in s:
            message += f"🌨️ {s}\n"
        else:
            message += f"🌧️ {s}\n"

    # Add EPA air quality data
    try:
        pm25 = next(d for d in aqi if d["ParameterName"] == "PM2.5")
    except:
        print("EPA data retrieval failed")
        pm25 = None
    if pm25 and len(message) < 250:
        category = pm25["Category"]["Number"]
        if category == 1:
            message += f"🟩 {pm25['AQI']} AQI\n"
        elif category == 2:
            message += f"🟨 {pm25['AQI']} AQI\n"
        elif category == 3:
            message += f"🟧 {pm25['AQI']} AQI\n"
        elif category == 4:
            message += f"🟥 {pm25['AQI']} AQI\n"
        elif category == 5:
            message += f"🟪 {pm25['AQI']} AQI\n"
        elif category == 6:
            message += f"🟫 {pm25['AQI']} AQI\n"

    # Tack on some hashtags
    message += "\n#CAwx"

    # Post the message
    # print("🐦 Posting to @LAXWeatherBot on Twitter")
    # print(f"Tweet is {len(message)} characters long.")
    # tw = get_twitter_client()
    # io = open("latest.jpg", "rb")
    # media_id = tw.UploadMediaSimple(io)
    alt_text = "A screen capture from the @ABC7 web camera at LAX airport"
    # tw.PostMediaMetadata(media_id, alt_text)
    # tw.PostUpdate(message, media=[media_id])

    print("🐘 Posting to @LAXWeather on Mastodon")
    masto = get_mastodon_client()
    media_obj = masto.media_post("./latest.jpg", description=alt_text)
    masto.status_post(message, media_ids=media_obj['id'])


def _clean_wind(s):
    crosswalk = {
        "N": "North",
        "NNE": "North-northeast",
        "NE": "Northeast",
        "ENE": "East-northeast",
        "E": "East",
        "ESE": "East-southeast",
        "SE": "Southeast",
        "SSE": "South-southeast",
        "S": "South",
        "SSW": "South-southwest",
        "SW": "Southwest",
        "WSW": "West-southwest",
        "W": "West",
        "WNW": "West-Northwest",
        "NW": "Northwest",
        "NNW": "North-northwest",
    }
    for key, value in crosswalk.items():
        if s.startswith(key + " "):
            s = s.replace(key + " ", value + " ")
    return s.capitalize()


@cli.command()
def aqi():
    """Download Air Quality Index data from the EPA."""
    print("🏭 Downloading EPA air quality data")

    # Download the data
    api_key = os.getenv("EPA_API_KEY")
    url = f"https://www.airnowapi.org/aq/observation/zipCode/current/?format=application/json&zipCode=90045&distance=25&API_KEY={api_key}"
    r = _request(url)

    # Write it out
    json.dump(r.json(), open("./aqi.json", "w"), indent=2)


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
    try:
        assert r.ok
    except AssertionError:
        r.raise_for_status()
    return r


def get_twitter_client():
    """Return a Twitter client ready to post to the API."""
    return twitter.Api(
        consumer_key=os.getenv("TWITTER_CONSUMER_KEY"),
        consumer_secret=os.getenv("TWITTER_CONSUMER_SECRET"),
        access_token_key=os.getenv("TWITTER_ACCESS_TOKEN_KEY"),
        access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
    )


def get_mastodon_client():
    """Return a Mastodon client ready to post to the API."""
    return Mastodon(
        client_id=os.getenv("MASTODON_CLIENT_KEY"),
        client_secret=os.getenv("MASTODON_CLIENT_SECRET"),
        access_token=os.getenv("MASTODON_ACCESS_TOKEN"),
        api_base_url="https://mastodon.palewi.re",
    )


if __name__ == "__main__":
    cli()
