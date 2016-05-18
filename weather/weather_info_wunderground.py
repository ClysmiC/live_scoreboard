from urllib2 import urlopen

import json
import datetime

target = "http://api.wunderground.com/api/[API-KEY]/hourly/q/[STATE]/[CITY].json"

def hourlyForecast(cityName, stateInitials, apiKey):
    '''Returns a list with the next 24 hours of weather information.

    Args:
        cityName (str): The name of the city whose weather
            information you are retrieving. Any spaces in city name
            will be replaced with underscores automatically.

        stateInitials(str): The two-letter initialization of the state
            that cityName is in. E.g., 'WA' for Washington.

    Returns:
        list: list of 24 dicts, containing the weather
            information for each of the next 24 hours. Exception raised
            if an error occured.

    '''



    forecast = []
    urlString = target.replace("[API-KEY]", apiKey).replace("[STATE]", stateInitials).replace("[CITY]", cityName).replace(" ", "_")

    try:
        jsonString = urlopen(urlString).read().decode("utf-8")
        weather = json.loads(jsonString)

        for hour in weather["hourly_forecast"]:
            thisHour = {}
            
            time = hour["FCTTIME"]
            thisHourDatetime = datetime.datetime(int(time["year"]), int(time["mon_padded"]), int(time["mday_padded"]), int(time["hour"]), int(time["min"]))
            thisHour["time"] = thisHourDatetime

            thisHour["temp"] = hour["temp"]["english"]
            thisHour["tempFeelsLike"] = hour["feelslike"]["english"]
            thisHour["windSpeed"] = hour["wspd"]["english"]
            thisHour["condition"] = hour["condition"]

            forecast.append(thisHour)
    except Exception as e:
        # If we want to handle errors, do it here
        raise e

    return forecast
