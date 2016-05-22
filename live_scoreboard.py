# -*- coding: latin-1 -*-

from scrape.mlb_scraper_mlb_api import MlbScraperMlbApi
from weather.weather_info_wunderground import hourlyForecast

from datetime import datetime, timedelta
import time
import Tkinter as tk
import tkFont

from PIL import Image, ImageTk

# Eastern Time
# RASPBERRY_PI_TIMEZONE = "ET"

# Central Time
# RASPBERRY_PI_TIMEZONE = "CT"

# Mountain Time
# RASPBERRY_PI_TIMEZONE = "MST"

# Pacific Time
RASPBERRY_PI_TIMEZONE = "PT"

TEAM_OF_INTEREST = "STL"
WEATHER_LOCATION = ("Seattle", "WA")

timezones = ["PT", "MST", "CT", "ET"]

months = ["NONE", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# 0 = Monday for some reason in datetime module
daysOfWeek = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

wundergroundApiKey = "6d48850a7f579fe7"

background = (40, 40, 80) # royal, dark/ish blue
panelBgAlpha = 120
panelBg = (0, 0, 0)
alphaFraction = 120 / 256.0

panelBackground = (int(alphaFraction * panelBg[0] + (1 - alphaFraction) * background[0]),
                   int(alphaFraction * panelBg[1] + (1 - alphaFraction) * background[1]),
                   int(alphaFraction * panelBg[2] + (1 - alphaFraction) * background[2]))

panelBackground = "#{:02x}{:02x}{:02x}".format(panelBackground[0], panelBackground[1], panelBackground[2])

fontName = "Monospace"
fontColor = "#BCBCBC"

mlb = MlbScraperMlbApi()
mlbTeams = mlb.validTeams
mlbLogos = {}


def fontFit(name, stringToFit, dimensionsToFit):
    fontSize = 1
    font = tkFont.Font(family=name, size=-fontSize) # Note: negative means font is that high, in pixels
    
    while True:
        fontSize += 1
        biggerFont = tkFont.Font(family=name, size=-fontSize)

        if fontSize >= dimensionsToFit[1] or font.measure(stringToFit) >= dimensionsToFit[0]:
            break

        font = biggerFont

    return font, (fontSize - 1)

class LiveScoreboard:
    def __init__(self):
        self.updateCount = 0

        #
        # Split the screen up into these virtual rows and columns. Use these
        # to determine where to position each element. This lets the elements
        # automatically resize on different sized monitors
        #
        numColumns = 30
        numRows = 20

        columns = []
        rows = []

        for i in range(numColumns):
            columns.append(int(screenWidth) / numColumns * i)

            for i in range(numRows):
                rows.append(int(screenHeight) / numRows * i)


        timePanelX1 = columns[1]
        timePanelY1 = rows[1]
        timePanelX2 = columns[13]
        timePanelY2 = rows[6]
        timePanelWidth = timePanelX2 - timePanelX1
        timePanelHeight = timePanelY2 - timePanelY1

        weatherPanelX1 = columns[1]
        weatherPanelY1 = rows[7]
        weatherPanelX2 = columns[9]
        weatherPanelY2 = rows[19]
        weatherPanelWidth = weatherPanelX2 - weatherPanelX1
        weatherPanelHeight = weatherPanelY2 - weatherPanelY1

        self.timePanel = TimePanel(timePanelX1, timePanelY1, timePanelWidth, timePanelHeight)
        self.weatherPanel = WeatherPanel(weatherPanelX1, weatherPanelY1, weatherPanelWidth, weatherPanelHeight)

        self.lastTime = datetime.now()
        self.weatherQueryMade = False

    def updatePerpetually(self):
        now = datetime.now()

        firstUpdate = (self.updateCount == 0)

        # Update the time panel
        if firstUpdate or self.lastTime.second != now.second:
            self.timePanel.setTime(now)
            self.timePanel.update()

        # Update weather panel on the 40 minute mark
        if firstUpdate or now.minute > 40 and not self.weatherQueryMade:
            try:
                weatherInfo = hourlyForecast(WEATHER_LOCATION[0], WEATHER_LOCATION[1], wundergroundApiKey)
                weatherInfoToDisplay = []

                perfTime = datetime.now()
                print("Weather request successfully made at {:02d}:{:02d}:{:02d}".format(perfTime.hour, perfTime.minute, perfTime.second))

                # Only display up to 12 hours, using the following rules.
                #
                # 1. Next 3 hours are always displayed
                # 2. Only even hours are displayed (except when rule 1)
                # 3. 00:00 - 05:59 are not displayed (except when rule 1)
                for i, hour in enumerate(weatherInfo):
                    if len(weatherInfoToDisplay) == 12:
                        break

                    if i < 3:
                        weatherInfoToDisplay.append(hour)
                    elif hour["time"].hour % 2 == 0 and hour["time"].hour > 5:
                        weatherInfoToDisplay.append(hour)

                self.weatherPanel.setWeather(weatherInfoToDisplay)
                self.weatherPanel.update()

                self.weatherQueryMade = True
            except:
                self.weatherPanel.showError()
                perfTime = datetime.now()
                print("Weather request failed at {:02d}:{:02d}:{:02d} .... error displayed".format(perfTime.hour, perfTime.minute, perfTime.second))


        perfTime = datetime.now()

        if now.minute < 40:
            self.weatherQueryMade = False

        self.lastTime = now
        self.updateCount += 1

        perfTime = datetime.now()
        root.after(200, self.updatePerpetually)


class TimePanel:
    def __init__(self, x, y, panelWidth, panelHeight):
        self.width = panelWidth
        self.height = panelHeight
        self.x = x
        self.y = y

        self.canvas = tk.Canvas(root, width=self.width, height=self.height, background=panelBackground, highlightthickness=0)

        self.canvas.place(x=self.x, y=self.y)
        self.dateAndTime = datetime.now()
        
        self.font, self.fontHeight = fontFit(fontName, "Thu, May 12", (self.width * 0.8, self.height / 2 * 0.8))

    def setTime(self, time):
        self.dateAndTime = time

    def update(self):
        self.canvas.delete("updates")

        string1 = daysOfWeek[self.dateAndTime.weekday()] + ", " + months[self.dateAndTime.month] + " " + str(self.dateAndTime.day)
        string2 = "{:02d}:{:02d}:{:02d}".format(self.dateAndTime.hour, self.dateAndTime.minute, self.dateAndTime.second)

        self.canvas.create_text((self.width // 2, self.height * .30), text=string1, fill=fontColor, font=self.font, tags="updates")
        self.canvas.create_text((self.width // 2, self.height * .70), text=string2, fill=fontColor, font=self.font, tags="updates")


class WeatherPanel:
    def __init__(self, x, y, panelWidth, panelHeight):
        self.width = panelWidth
        self.height = panelHeight
        self.x = x
        self.y = y

        self.canvas = tk.Canvas(root, width=self.width, height=self.height, background=panelBackground, highlightthickness=0)
        self.canvas.place(x=self.x, y=self.y)

        # Get width of example string w/ 3 digit temperature, and
        # space alloted for weather icons.  This width will be used
        # when centering text in panel.
        exampleString = " 00:00 - 100  F  "

        numLines = 18
        lineHeightMultiplier = 1.2 # Multiply font height by this to get line height
        self.font, self.fontHeight = fontFit(fontName, exampleString, (panelWidth * 0.8, panelHeight // (numLines * lineHeightMultiplier)))
        self.underlinedFont = tkFont.Font(family=fontName, size=-self.fontHeight, underline=1)

        self.lineHeight = self.fontHeight * lineHeightMultiplier

        self.textY = 0

        stringWidth = self.font.measure(exampleString)
        self.textX = (panelWidth - stringWidth) // 2

        self.iconX = self.textX + self.font.measure(exampleString)

        self.weatherIcons = {}
        iconSize = self.fontHeight

        def loadAndResizeIcon(iconName, filePath):
            im = Image.open(filePath);
            im = im.resize((iconSize, iconSize))
            self.weatherIcons[iconName] = ImageTk.PhotoImage(im) # Image format compatible w/ tkinter
    
        
        loadAndResizeIcon("Clear", "weather/icons/clear.png")
        loadAndResizeIcon("Partly Cloudy", "weather/icons/partly_cloudy.png")
        self.weatherIcons["Mostly Cloudy"] = self.weatherIcons["Partly Cloudy"]
        loadAndResizeIcon("Overcast", "weather/icons/cloudy.png")
        loadAndResizeIcon("Chance of Rain", "weather/icons/chance_rain.png")
        loadAndResizeIcon("Rain", "weather/icons/rain.png")
        loadAndResizeIcon("Chance of a Thunderstonm", "weather/icons/chance_tstorm.png")
        loadAndResizeIcon("Thunderstorm", "weather/icons/tstorm.png")

    def setWeather(self, weather):
        self.weather = weather

    def update(self):
        self.canvas.delete("updates")

        self.textY = 0
        lastDateLabelDay = None
        firstHour = True

        for hour in self.weather:
            time = hour["time"]
            if time.day != lastDateLabelDay:
                dayString = months[time.month] + " " + str(time.day)
                
                # New lines
                if lastDateLabelDay is not None:
                    self.textY += self.lineHeight

                self.textY += self.lineHeight

                dayTextOffset = self.font.measure("  ")
                textPosition = (max(0, self.textX - dayTextOffset), self.textY)
                self.canvas.create_text(textPosition, anchor=tk.NW, text=dayString, font=self.underlinedFont, fill=fontColor, tags="updates")

                self.textY += self.lineHeight * 1.2 # just a little extra padding here looks better
                lastDateLabelDay = time.day

            hourString = " {:02d}:{:02d}".format(time.hour, time.minute) + " - " + "{:>3s}".format(hour["temp"]) + " F "

            hourFontColor = fontColor
            if firstHour:
                hourFontColor = "black"

                # draw a yellowish highlight on the current hour
                highlightColor = '#FFFF99'

                highlightX1 = self.textX
                highlightY1 = self.textY - ((self.lineHeight - self.fontHeight) / 2)
                highlightX2 = highlightX1 + self.font.measure(hourString)
                highlightY2 = highlightY1 + self.lineHeight

                self.canvas.create_rectangle((highlightX1, highlightY1, highlightX2, highlightY2), fill=highlightColor, tags="updates")

            self.canvas.create_text((self.textX, self.textY), anchor=tk.NW, text=hourString, font=self.font, fill=hourFontColor, tags="updates")


            icon = self.weatherIcons[hour["condition"]]
            self.canvas.create_image((self.iconX, self.textY), anchor=tk.NW, image=icon, tags="updates")

            self.textY += self.lineHeight
            firstHour = False

    def showError(self):
        self.canvas.create_text((self.width//2, self.height//2), anchor=tk.CENTER, font=self.font, fill=fontColor, text="Error retreiving weather info...", tags="updates")

def exitTkinter(event):
    root.destroy()
    
def startScoreboard():
    scoreboard = LiveScoreboard()
    scoreboard.updatePerpetually()

weatherQueryMinuteMark = 40

root = tk.Tk()

root.attributes('-fullscreen', True)
screenWidth = root.winfo_screenwidth()
screenHeight = root.winfo_screenheight()

backgroundString =  "#{:02x}{:02x}{:02x}".format(background[0], background[1], background[2])
bgCanvas = tk.Canvas(root, width=screenWidth, height=screenHeight, background=backgroundString, highlightthickness=0)
bgCanvas.place(x=0, y=0)

root.bind_all('<Escape>', exitTkinter)

startScoreboard()

root.mainloop()
