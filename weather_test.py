from weather.weather_info_wunderground import hourlyForecast

apiKey = open("weather_api_key.txt", 'r')
apiKey = apiKey.readline()
apiKey = apiKey.replace("\n", "")

weather = hourlyForecast("Saint Louis", "MO", apiKey)
months = ["NONE", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

for hour in weather:
    time = hour["time"]

    # print(type(time.month))
    
    hourString = "{:02d} ".format(time.day) + months[time.month] + ", " + "{:02d}{:02d}".format(time.hour, time.minute)

    hourString += " -- " + hour["temp"] + u'\N{DEGREE SIGN}' + " F" + " -- " + hour["condition"]
    
    print(hourString)
