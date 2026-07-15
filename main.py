from flask import Flask, render_template, request
from requests.exceptions import RequestException

from weather_service import (
    geocode_city,
    get_current_conditions,
    get_forecast,
)


app = Flask(__name__)


@app.route("/")
def home():
    city = request.args.get("city", "").strip()

    weather = None
    forecast = []
    error_message = None

    if city:
        # Browser validation can be bypassed, so we also validate in Python.
        if len(city) < 2:
            error_message = (
                "Please enter at least two characters for the city name."
            )

        elif len(city) > 100:
            error_message = (
                "The city name is too long. Please enter 100 characters or fewer."
            )

        else:
            try:
                location = geocode_city(city)

                conditions = get_current_conditions(
                    location["latitude"],
                    location["longitude"],
                )

                forecast = get_forecast(
                    location["latitude"],
                    location["longitude"],
                )

                weather = {
                    **location,
                    **conditions,
                }

            except ValueError as error:
                # Used for an unknown city or missing observation station.
                error_message = str(error)

            except RequestException:
                # Record technical information in the server terminal.
                app.logger.exception(
                    "An external weather API request failed."
                )

                # Give the visitor a useful message without technical details.
                error_message = (
                    "We couldn't contact the weather service. "
                    "Please wait a moment and try again."
                )

            except (KeyError, TypeError):
                # Handles missing or unexpectedly structured JSON values.
                app.logger.exception(
                    "A weather API returned incomplete data."
                )

                error_message = (
                    "The weather service returned incomplete data. "
                    "Please try another city or try again later."
                )

    return render_template(
        "index.html",
        title="Cloud Weather Dashboard",
        city=city,
        weather=weather,
        forecast=forecast,
        error=error_message,
    )


if __name__ == "__main__":
    app.run(debug=True) 