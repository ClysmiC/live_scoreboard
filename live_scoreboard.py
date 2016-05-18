# -*- coding: latin-1 -*-

from scrape.mlb_scraper_mlb_api import MlbScraperMlbApi
from weather.weather_info_wunderground import hourlyForecast

import PIL
from datetime import datetime, timedelta
import time
import Tkinter as tk
import tkFont

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

background = (50, 50, 200) # royal, dark/ish blue

panelBgAlpha = 120
panelBg = (0, 0, 0)
alphaFraction = 120 / 256

panelBackground = (alphaFraction * panelBg[0] + (1 - alphaFraction) * background[0],
                   alphaFraction * panelBg[1] + (1 - alphaFraction) * background[1],
                   alphaFraction * panelBg[2] + (1 - alphaFraction) * background[2])

panelBackground = "#{:x}{:x}{:x}".format(panelBackground[0], panelBackground[1], panelBackground[2])

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

    print("Final font size" + str(fontSize))
    return font


class TimePanel:
    def __init__(self, x, y, panelWidth, panelHeight):
        self.width = panelWidth
        self.height = panelHeight
        self.x = x
        self.y = y

        self.canvas = tk.Canvas(root, width=self.width, height=self.height, background=panelBackground)
        self.canvas.place(x=self.x, y=self.y)
        self.dateAndTime = datetime.now()
        
        self.font = fontFit(fontName, "Thu, May 12", (self.width * 0.8, self.height / 2 * 0.8))

    def setTime(self, time):
        self.dateAndTime = time

    def update(self):
        self.canvas.create_rectangle((0, 0, self.width, self.height), fill=panelBackground, outline=panelBackground)
        
        string1 = daysOfWeek[self.dateAndTime.weekday()] + ", " + months[self.dateAndTime.month] + " " + str(self.dateAndTime.day)
        string2 = "{:02d}:{:02d}:{:02d}".format(self.dateAndTime.hour, self.dateAndTime.minute, self.dateAndTime.second)

        self.canvas.create_text((self.width // 2, self.height * .30), text=string1, fill=fontColor, font=self.font)
        self.canvas.create_text((self.width // 2, self.height * .70), text=string2, fill=fontColor, font=self.font)



root = tk.Tk()
root.attributes('-fullscreen', True)
screenWidth = root.winfo_screenwidth()
screenHeight = root.winfo_screenheight()

def exitTkinter(event):
    root.destroy()

root.bind_all('<Escape>', exitTkinter)



# Split the screen up into these virtual rows and columns. Use these
# to determine where to position each element. This lets the elements
# automatically resize on different sized monitors
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

timePanel = TimePanel(timePanelX1, timePanelY1, timePanelWidth, timePanelHeight)
timePanel.update()

root.mainloop()
print("Program complete")
