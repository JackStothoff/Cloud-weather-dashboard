import requests


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
NWS_BASE_URL = "https://api.weather.gov"

# NWS requires applications to identify themselves.
# Replace the placeholder with an email belonging to your team.
NWS_HEADERS = {
    "User-Agent": "utsa-weather-dashboard/1.0 (jackstothoff@gmail.com)",
    "Accept": "application/geo+json",
}


def geocode_city(city):
    """Convert a US city name into latitude and longitude coordinates."""

    parameters = {
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json",
        "countryCode": "US",
    }

    # timeout prevents the application from waiting forever if the API is down.
    response = requests.get(
        GEOCODING_URL,
        params=parameters,
        timeout=10,
    )

    # Raise an exception for HTTP errors such as 404 or 500.
    response.raise_for_status()

    data = response.json()
    results = data.get("results", [])

    if not results:
        raise ValueError(f"No US city was found for '{city}'.")

    best_match = results[0]

    return {
        "name": best_match["name"],
        "state": best_match.get("admin1", ""),
        "latitude": best_match["latitude"],
        "longitude": best_match["longitude"],
    }


def get_current_conditions(latitude, longitude):
    """Retrieve the latest NWS observation near the coordinates."""

    # Step 1: Ask NWS which resources serve these coordinates.
    points_url = (
        f"{NWS_BASE_URL}/points/{latitude:.4f},{longitude:.4f}"
    )

    points_response = requests.get(
        points_url,
        headers=NWS_HEADERS,
        timeout=10,
    )
    points_response.raise_for_status()

    points_data = points_response.json()

    # NWS provides a URL containing nearby observation stations.
    stations_url = points_data["properties"]["observationStations"]

    # Step 2: Retrieve the available observation stations.
    stations_response = requests.get(
        stations_url,
        headers=NWS_HEADERS,
        timeout=10,
    )
    stations_response.raise_for_status()

    stations = stations_response.json().get("features", [])

    if not stations:
        raise ValueError("No NWS observation station was found nearby.")

    # Use the first station returned by NWS.
    station_id = stations[0]["properties"]["stationIdentifier"]

    # Step 3: Request the latest observation from that station.
    observation_url = (
        f"{NWS_BASE_URL}/stations/"
        f"{station_id}/observations/latest"
    )

    observation_response = requests.get(
        observation_url,
        headers=NWS_HEADERS,
        timeout=10,
    )
    observation_response.raise_for_status()

    observation = observation_response.json()["properties"]

    temperature_c = observation["temperature"]["value"]
    humidity = observation["relativeHumidity"]["value"]
    wind_kmh = observation["windSpeed"]["value"]

    # NWS observations use Celsius and kilometers per hour.
    temperature_f = (
        round((temperature_c * 9 / 5) + 32, 1)
        if temperature_c is not None
        else None
    )

    wind_mph = (
        round(wind_kmh * 0.621371, 1)
        if wind_kmh is not None
        else None
    )

    return {
        "station": station_id,
        "description": observation.get("textDescription") or "Unavailable",
        "temperature_f": temperature_f,
        "humidity": round(humidity, 1) if humidity is not None else None,
        "wind_mph": wind_mph,
        "timestamp": observation.get("timestamp"),
    }

def get_forecast(latitude, longitude, number_of_days=5):
    """Retrieve the next several daytime forecast periods."""

    # Ask NWS which forecast endpoint serves these coordinates.
    points_url = (
        f"{NWS_BASE_URL}/points/{latitude:.4f},{longitude:.4f}"
    )

    points_response = requests.get(
        points_url,
        headers=NWS_HEADERS,
        timeout=10,
    )
    points_response.raise_for_status()

    points_data = points_response.json()

    # NWS provides the appropriate forecast URL in the points response.
    forecast_url = points_data["properties"]["forecast"]

    forecast_response = requests.get(
        forecast_url,
        headers=NWS_HEADERS,
        timeout=10,
    )
    forecast_response.raise_for_status()

    periods = forecast_response.json()["properties"]["periods"]
    if not periods:
        raise ValueError("The NWS forecast is temporarily unavailable for this city.")
    daily_forecast = []

    for period in periods:
        # NWS normally supplies separate daytime and nighttime periods.
        # We use daytime periods to create a simple five-day forecast.
        if not period["isDaytime"]:
            continue

        precipitation_data = (
            period.get("probabilityOfPrecipitation") or {}
        )

        daily_forecast.append(
            {
                "name": period["name"],
                "temperature": period["temperature"],
                "temperature_unit": period["temperatureUnit"],
                "description": period["shortForecast"],
                "precipitation_probability": (
                    precipitation_data.get("value")
                ),
                "wind_speed": period.get("windSpeed"),
                "wind_direction": period.get("windDirection"),
            }
        )

        # Stop after collecting the requested number of days.
        if len(daily_forecast) == number_of_days:
            break
    if not daily_forecast:
        raise ValueError("No daytime forecast is currently available for this city.")
    return daily_forecast

def format_measurement(value, unit):
    """Format a measurement while allowing for missing NWS values."""

    if value is None:
        return "Unavailable"

    return f"{value}{unit}"


if __name__ == "__main__":
    city = input("Enter a US city: ").strip()

    location = geocode_city(city)

    print(
        f"\nLocation: {location['name']}, {location['state']}"
    )
    print(
        f"Coordinates: "
        f"{location['latitude']}, {location['longitude']}"
    )

    conditions = get_current_conditions(
        location["latitude"],
        location["longitude"],
    )

    print(f"Observation station: {conditions['station']}")
    print(f"Conditions: {conditions['description']}")
    print(
        "Temperature:",
        format_measurement(conditions["temperature_f"], " °F"),
    )
    print(
        "Humidity:",
        format_measurement(conditions["humidity"], "%"),
    )
    print(
        "Wind speed:",
        format_measurement(conditions["wind_mph"], " mph"),
    )
    print(f"Observation time: {conditions['timestamp']}")