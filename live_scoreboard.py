# -*- coding: latin-1 -*-

from scrape.mlb_scraper_mlb_api import MlbScraperMlbApi
from weather.weather_info_wunderground import hourlyForecast

from copy import deepcopy
from datetime import datetime, timedelta
import time
import Tkinter as tk
import tkFont

import threading

from PIL import Image, ImageTk
from urllib2 import URLError
from socket import timeout as TimeoutError

# Eastern Time
# RASPBERRY_PI_TIMEZONE = "ET"

# Central Time
# RASPBERRY_PI_TIMEZONE = "CT"

# Mountain Time
# RASPBERRY_PI_TIMEZONE = "MST"

# Pacific Time
RASPBERRY_PI_TIMEZONE = "PT"

TEAM_OF_INTEREST = "STL"
DIVISION_OF_INTEREST = "NLC"
WILDCARD_DIVISION_OF_INTEREST = "NLWC"

WEATHER_LOCATION = ("Seattle", "WA")

TWENTY_FOUR_HOUR_CLOCK = True

timezones = ["PT", "MST", "CT", "ET"]

months = ["NONE", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# 0 = Monday for some reason in datetime module
daysOfWeek = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

wundergroundApiKey = open("weather_api_key.txt", 'r')
wundergroundApiKey = wundergroundApiKey.readline()
wundergroundApiKey = wundergroundApiKey.replace("\n", "")

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

#
# Store unscaled logos in variable so panels have access to the raw
# images, which they can scale and use.
#
for __team in mlbTeams:
    mlbLogos[__team] = Image.open("scrape/logos/" + __team + ".png")


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


def loadAndResizeImage(filePath, newSize):
    im = Image.open(filePath)
    im = im.resize((int(newSize[0]), int(newSize[1])))
    return ImageTk.PhotoImage(im) # Image format compatible w/ tkinter

def getAdjustedStartTime(game):
    # Adjust game time to the current timezone
    rawDateTime = game["startTime"]["time"]
    hoursToAdjust = timezones.index(RASPBERRY_PI_TIMEZONE) - timezones.index(game["startTime"]["timeZone"])
    adjustedStartTime = rawDateTime + timedelta(hours=hoursToAdjust)
    return adjustedStartTime

def toTwelveHourClock(time):
    newHour = time.hour
    suffix = "PM"

    if (newHour > 12):
        newHour -= 12
    else:
        if(newHour == 0):
            newHour = 12

        suffix = "AM"

    return newHour, suffix

class AsyncRequester:
    def __init__(self):
        # Don't update the main preview to today's game until 4am.
        # That way, if I'm up late (i.e., 1 am) I can still see the
        # results for what I would consider to be "today"
        self.showTodaysGameHour = 4

        self.lastRequestedGameQueryTime     = 0
        self.lastRequestedDivisionQueryTime = 0
        self.lastRequestedWeatherQueryTime  = 0

        self.lastSuccessfulGameQueryTime     = 0
        self.lastSuccessfulDivisionQueryTime = 0
        self.lastSuccessfulWeatherQueryTime  = 0

        self.newGameDataAvailable     = False
        self.newDivisionDataAvailable = False
        self.newWeatherDataAvailable  = False

        self.__game = None
        self.__nextGame = None
        self.__weatherInfo = None
        self.__divisionStandings = None
        self.__wildcardStandings = None

        self.__weatherThread = None
        self.__gameThread = None
        self.__divisionThread = None

        self.__isAlive = True


    def stopAllThreads(self):
        self.__isAlive = False


    def getWeatherData(self):
        if self.newWeatherDataAvailable:
            self.newWeatherDataAvailable = False
            return self.__weatherInfo
        else:
            return None

    def getGameData(self):
        if self.newGameDataAvailable:
            self.newGameDataAvailable = False
            return self.__game, self.__nextGame
        else:
            return None

    def getDivisionData(self):
        if self.newDivisionDataAvailable:
            self.newDivisionDataAvailable = False
            return self.__divisionStandings, self.__wildcardStandings
        else:
            return None

    def requestWeatherData(self):
        # If internet has been out for an hour, there is already a
        # thread still running trying to get the data
        if self.__weatherThread is None or not self.__weatherThread.isAlive():
            self.__weatherThread = threading.Thread(target=self.__asyncRequestWeatherData)
            self.__weatherThread.start()
        
    def requestGameData(self):
        if self.__gameThread is None or not self.__gameThread.isAlive():
            self.__gameThread = threading.Thread(target=self.__asyncRequestGameData)
            self.__gameThread.start()

    def requestDivisionData(self):
        if self.__divisionThread is None or not self.__divisionThread.isAlive():
            self.__divisionThread = threading.Thread(target=self.__asyncRequestDivisionData)
            self.__divisionThread.start()

    def __asyncRequestWeatherData(self):
        success = False

        self.lastRequestedWeatherQueryTime = time.time()

        while not success:
            if not self.__isAlive:
                return

            try:
                self.__weatherInfo = hourlyForecast(WEATHER_LOCATION[0], WEATHER_LOCATION[1], wundergroundApiKey)
                success = True
            except:
                success = False
                currTime = datetime.now()
                print("FAIL: Weather request at {:02d}:{:02d}:{:02d}".format(currTime.hour, currTime.minute, currTime.second))

        currTime = datetime.now()
        print("SUCCESS: Weather request at {:02d}:{:02d}:{:02d}".format(currTime.hour, currTime.minute, currTime.second))

        self.lastSuccessfulWeatherQueryTime = time.time()
        self.newWeatherDataAvailable = True

    def __asyncRequestGameData(self):
        self.lastRequestedGameQueryTime = time.time()

        success = False

        while not success:
            if not self.__isAlive:
                return

            dateOfInterest = datetime.now()
            if datetime.now().hour < self.showTodaysGameHour:
                dateOfInterest -= timedelta(days=1)

            try:
                self.__game = mlb.getGameInfo(TEAM_OF_INTEREST, dateOfInterest)
                success = True
            except:
                currTime = datetime.now()
                print("FAIL: Game request at {:02d}:{:02d}:{:02d}".format(currTime.hour, currTime.minute, currTime.second))
                continue


            # If no game found for today, look ahead up to 10 days
            # until we find a 
            if self.__game["status"] == "NoGame":
                lookaheadDays = 0
                while success and self.__game["status"] == "NoGame" and lookaheadDays < 10:
                    if not self.__isAlive:
                        return

                    lookaheadDays += 1
                    dateOfInterest = dateOfInterest + timedelta(days=1)

                    try:
                        self.__game = mlb.getGameInfo(TEAM_OF_INTEREST, dateOfInterest)
                    except:
                        success = False
                        currTime = datetime.now()
                        print("FAIL: Game request at {:02d}:{:02d}:{:02d}".format(currTime.hour, currTime.minute, currTime.second))

                if not success:
                    continue

            elif self.__game["status"] == "Post":
                #
                # Preview next game in the bottom middle
                #

                # Look ahead until we find next game
                lookaheadDays = 0
                self.__nextGame = {}
                self.__nextGame["status"] = "NoGame"

                while success and self.__nextGame["status"] == "NoGame" and lookaheadDays < 10:
                    if not self.__isAlive:
                        return

                    lookaheadDays += 1
                    dateOfInterest = dateOfInterest + timedelta(days=1)

                    try:
                        self.__nextGame = mlb.getGameInfo(TEAM_OF_INTEREST, dateOfInterest)
                    except:
                        success = False
                        currTime = datetime.now()
                        print("FAIL: Game request at {:02d}:{:02d}:{:02d}".format(currTime.hour, currTime.minute, currTime.second))

                if not success:
                    continue

        currTime = datetime.now()
        print("SUCCESS: Game request at {:02d}:{:02d}:{:02d}".format(currTime.hour, currTime.minute, currTime.second))

        self.lastSuccessfulGameQueryTime = time.time()
        self.newGameDataAvailable = True


    def __asyncRequestDivisionData(self):        
        success = False

        self.lastRequestedDivisionQueryTime = time.time()

        while not success:
            if not self.__isAlive:
                return

            try:
                self.__divisionStandings = mlb.getDivisionStandings(DIVISION_OF_INTEREST)
                self.__wildcardStandings = mlb.getDivisionStandings(WILDCARD_DIVISION_OF_INTEREST)
                success = True
            except:
                currTime = datetime.now()
                print("FAIL: Standings request at {:02d}:{:02d}:{:02d}".format(currTime.hour, currTime.minute, currTime.second))
                success = False

        currTime = datetime.now()
        print("SUCCESS: Standings request at {:02d}:{:02d}:{:02d}".format(currTime.hour, currTime.minute, currTime.second))

        self.lastSuccessfulDivisionQueryTime = time.time()
        self.newDivisionDataAvailable = True

class LiveScoreboard:
    def __init__(self):
        # Store the time of when we last requested these things. This
        # is used to make our requests at a reasonable rate.
        self.weatherQueryMade = False         # (This hour)

        self.lastSwitchStandingsTime = 0

        self.weatherQueryMinuteMark    = 40   # Query at XX:40

        # Add a few seconds to some of the cooldowns to try to prevent
        # all the queries from happening in the same second and
        # lowering the framerate (since queries are synchronous)
        self.gameNonLiveQueryCooldown    = 302  # Once per 5 minutes
        self.gameAlmostLiveQueryCooldown = 60   # Once per minute
        self.gameLiveQueryCooldown       = 20   # Once per 20 seconds
        self.divisionQueryCooldown       = 907  # Once per 15 minutes

        # Number of seconds after async request gets made before
        # considering an error to have occurred.
        self.timeBeforeError = 30

        # Both division and wildcard standings are queried during the
        # division query.  This timer determines how often the
        # division displays one before switching to the other.
        self.switchStandingsTime         = 15


        self.asyncRequester = AsyncRequester()


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


        timePanelX1     = columns[1]
        timePanelY1     = rows[1]
        timePanelX2     = columns[13]
        timePanelY2     = rows[6]
        timePanelWidth  = timePanelX2 - timePanelX1
        timePanelHeight = timePanelY2 - timePanelY1

        weatherPanelX1     = columns[1]
        weatherPanelY1     = rows[7]
        weatherPanelX2     = columns[9]
        weatherPanelY2     = rows[19]
        weatherPanelWidth  = weatherPanelX2 - weatherPanelX1
        weatherPanelHeight = weatherPanelY2 - weatherPanelY1

        gameScorePanelX1     = columns[14]
        gameScorePanelY1     = rows[1]
        gameScorePanelX2     = columns[29]
        gameScorePanelY2     = rows[6]
        gameScorePanelWidth  = gameScorePanelX2 - gameScorePanelX1
        gameScorePanelHeight = gameScorePanelY2 - gameScorePanelY1

        #
        # There are 2 possible positions for the game preview
        # panel. When we are previewing today's game, the upper right
        # panel has the preview. When today's game is finished,
        # display the preview of tomorrow's game in the bottom middle
        # panel.
        #
        # Since the rendering logic is independent of the panel
        # width/height, we make each an instance of the
        # GamePreviewPanel class, and simply store them as panel #1            
        # and panel #2
        #
        gamePreviewPanel1X1     = gameScorePanelX1
        gamePreviewPanel1Y1     = gameScorePanelY1
        gamePreviewPanel1X2     = gameScorePanelX2
        gamePreviewPanel1Y2     = gameScorePanelY2
        gamePreviewPanel1Width  = gameScorePanelWidth  
        gamePreviewPanel1Height = gameScorePanelHeight

        gamePreviewPanel2X1     = columns[10]
        gamePreviewPanel2Y1     = rows[14]
        gamePreviewPanel2X2     = columns[21]
        gamePreviewPanel2Y2     = rows[19]
        gamePreviewPanel2Width  = gamePreviewPanel2X2 - gamePreviewPanel2X1 
        gamePreviewPanel2Height = gamePreviewPanel2Y2 - gamePreviewPanel2Y1

        boxScorePanelX1      = columns[10]
        boxScorePanelY1      = rows[7] 
        boxScorePanelX2      = columns[29]
        boxScorePanelY2      = rows[13]
        boxScorePanelWidth   = boxScorePanelX2 - boxScorePanelX1 
        boxScorePanelHeight  = boxScorePanelY2 - boxScorePanelY1
        
        firstPitchCountdownPanelX1      = boxScorePanelX1
        firstPitchCountdownPanelY1      = boxScorePanelY1
        firstPitchCountdownPanelX2      = boxScorePanelX2
        firstPitchCountdownPanelY2      = boxScorePanelY2
        firstPitchCountdownPanelWidth   = firstPitchCountdownPanelX2 - firstPitchCountdownPanelX1 
        firstPitchCountdownPanelHeight  = firstPitchCountdownPanelY2 - firstPitchCountdownPanelY1

        pitcherPreviewPanelX1      = gamePreviewPanel2X1
        pitcherPreviewPanelY1      = gamePreviewPanel2Y1
        pitcherPreviewPanelX2      = gamePreviewPanel2X2
        pitcherPreviewPanelY2      = gamePreviewPanel2Y2
        pitcherPreviewPanelWidth   = pitcherPreviewPanelX2 - pitcherPreviewPanelX1 
        pitcherPreviewPanelHeight  = pitcherPreviewPanelY2 - pitcherPreviewPanelY1

        situationPanelX1      = gamePreviewPanel2X1
        situationPanelY1      = gamePreviewPanel2Y1
        situationPanelX2      = gamePreviewPanel2X2
        situationPanelY2      = gamePreviewPanel2Y2
        situationPanelWidth   = situationPanelX2 - situationPanelX1 
        situationPanelHeight  = situationPanelY2 - situationPanelY1

        standingsPanelX1      = columns[22]
        standingsPanelY1      = rows[14]
        standingsPanelX2      = columns[29]
        standingsPanelY2      = rows[19]
        standingsPanelWidth   = standingsPanelX2 - standingsPanelX1 
        standingsPanelHeight  = standingsPanelY2 - standingsPanelY1


        self.timePanel = TimePanel(timePanelX1, timePanelY1, timePanelWidth, timePanelHeight)
        self.weatherPanel = WeatherPanel(weatherPanelX1, weatherPanelY1, weatherPanelWidth, weatherPanelHeight)
        self.gameScorePanel = GameScorePanel(gameScorePanelX1, gameScorePanelY1, gameScorePanelWidth, gameScorePanelHeight)
        self.gamePreviewPanel1 = GamePreviewPanel(gamePreviewPanel1X1, gamePreviewPanel1Y1, gamePreviewPanel1Width, gamePreviewPanel1Height)
        self.gamePreviewPanel2 = GamePreviewPanel(gamePreviewPanel2X1, gamePreviewPanel2Y1, gamePreviewPanel2Width, gamePreviewPanel2Height)
        self.boxScorePanel = BoxScorePanel(boxScorePanelX1, boxScorePanelY1, boxScorePanelWidth, boxScorePanelHeight)
        self.firstPitchCountdownPanel = FirstPitchCountdownPanel(firstPitchCountdownPanelX1, firstPitchCountdownPanelY1, firstPitchCountdownPanelWidth, firstPitchCountdownPanelHeight)
        self.pitcherPreviewPanel = PitcherPreviewPanel(pitcherPreviewPanelX1, pitcherPreviewPanelY1, pitcherPreviewPanelWidth, pitcherPreviewPanelHeight)
        self.situationPanel = SituationPanel(situationPanelX1, situationPanelY1, situationPanelWidth, situationPanelHeight)
        self.standingsPanel = StandingsPanel(standingsPanelX1, standingsPanelY1, standingsPanelWidth, standingsPanelHeight)

        self.game = {}
        self.game["status"] = "NoGame"

        self.firstUpdate = True
        self.lastUpdateTime = datetime.now()

    def updatePerpetually(self):
        now = datetime.now()
        executionTime = time.time() # NOT wall clock

        if now.minute < self.weatherQueryMinuteMark:
            self.weatherQueryMade = False

        # TODO: Handle game status of "Postponed"


        #
        # Request weather data at the 40 minute mark
        #
        if self.firstUpdate or now.minute >= self.weatherQueryMinuteMark and not self.weatherQueryMade:
            self.asyncRequester.requestWeatherData()
            self.weatherQueryMade = True


        #
        # Determine if game is "almost started", in which case the
        # poll rate picks up
        #
        gameAlmostStarted = False

        if not self.firstUpdate and self.game["status"] == "Pre":
            timeUntilGame = self.game["adjustedStartTime"] - datetime.now()
            if timeUntilGame.total_seconds() < self.gameNonLiveQueryCooldown:
                gameAlmostStarted = True


        #
        # Request game data
        #
        if (self.firstUpdate) or (
            self.game["status"] == "Live" and executionTime - self.asyncRequester.lastSuccessfulGameQueryTime >= self.gameLiveQueryCooldown) or (
            gameAlmostStarted and executionTime - self.asyncRequester.lastSuccessfulGameQueryTime >= self.gameAlmostLiveQueryCooldown) or (
                executionTime - self.asyncRequester.lastSuccessfulGameQueryTime >= self.gameNonLiveQueryCooldown):
            
            self.asyncRequester.requestGameData()


        #
        # Request division data
        #
        if self.firstUpdate or executionTime - self.asyncRequester.lastSuccessfulDivisionQueryTime >= self.divisionQueryCooldown:
            self.asyncRequester.requestDivisionData()


            
        #
        # Get updated weather info, show on panel
        #
        if self.asyncRequester.newWeatherDataAvailable:
            weatherInfo = self.asyncRequester.getWeatherData()

            weatherInfoToDisplay = []

            currTime = datetime.now()

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


        #
        # Get updated game info, show on panel
        #
        if self.asyncRequester.newGameDataAvailable:
            # Note: lookaheadGame is only displayed when game is in
            # "post" and we want to show tomorrow's game
            self.game, lookaheadGame = self.asyncRequester.getGameData()

            #
            # Game not yet started
            #
            if self.game["status"] == "Pre":
                self.game["adjustedStartTime"] = getAdjustedStartTime(self.game)

                self.gameScorePanel.hide()
                self.gamePreviewPanel1.setPreview(self.game)
                self.gamePreviewPanel1.update()

                self.boxScorePanel.hide()
                self.firstPitchCountdownPanel.setTargetTime(self.game["adjustedStartTime"])
                self.firstPitchCountdownPanel.update()

                self.situationPanel.hide()
                self.pitcherPreviewPanel.setPitchers(self.game)
                self.pitcherPreviewPanel.update()


            #
            # Game is live or finished
            #
            elif self.game["status"] in ("Live", "Post"):
                self.gamePreviewPanel1.hide()
                self.gameScorePanel.setScore(self.game)
                self.gameScorePanel.update()

                self.firstPitchCountdownPanel.hide()
                self.boxScorePanel.setGame(self.game)
                self.boxScorePanel.update()

                if self.game["status"] == "Live":
                    #
                    # Show situation in bottom middle
                    #
                    self.gamePreviewPanel2.hide()
                    self.situationPanel.setSituation(self.game)
                    self.situationPanel.update()

                else:

                    lookaheadGame["adjustedStartTime"] = getAdjustedStartTime(lookaheadGame)

                    self.situationPanel.hide()
                    self.pitcherPreviewPanel.hide()
                    self.gamePreviewPanel2.setPreview(lookaheadGame)
                    self.gamePreviewPanel2.update()


        #
        # Get updated division info, show on panel
        #
        if self.asyncRequester.newDivisionDataAvailable:
            divisionStandings, wcStandings = self.asyncRequester.getDivisionData()

            self.standingsPanel.setDivisionStandings("NL Central", divisionStandings)
            self.standingsPanel.setWildcardStandings("NL Wildcard", wcStandings)

            self.standingsPanel.update()
            currTime = datetime.now()




        #
        # Handle weather request error
        #
        if self.asyncRequester.lastRequestedWeatherQueryTime > self.asyncRequester.lastSuccessfulWeatherQueryTime:
            requestTimeElapsed = time.time() - self.asyncRequester.lastRequestedWeatherQueryTime

            if requestTimeElapsed > self.timeBeforeError:
                self.weatherPanel.showError()


        #
        # Handle game request error
        #
        if self.asyncRequester.lastRequestedGameQueryTime > self.asyncRequester.lastSuccessfulGameQueryTime:
            requestTimeElapsed = time.time() - self.asyncRequester.lastRequestedGameQueryTime
        
            if requestTimeElapsed > self.timeBeforeError:
                self.gameScorePanel.hide()
                self.gamePreviewPanel1.showError()

                self.boxScorePanel.hide()

                self.situationPanel.hide()
                self.pitcherPreviewPanel.hide()

                # Don't show these errors if it is still pre-game,
                # because these panel are countdown and starting
                # pitchers, which likely won't be changed at all
                if self.game["status"] != "Pre":
                    self.firstPitchCountdownPanel.showError()
                    self.gamePreviewPanel2.showError()


        #
        # Handle division request error
        #
        if self.asyncRequester.lastRequestedDivisionQueryTime > self.asyncRequester.lastSuccessfulDivisionQueryTime:
            requestTimeElapsed = time.time() - self.asyncRequester.lastRequestedDivisionQueryTime
        
            if requestTimeElapsed > self.timeBeforeError:                
                self.standingsPanel.showError()


        #
        # Switch standings panel between main division and wildcard
        #
        if executionTime - self.lastSwitchStandingsTime >= self.switchStandingsTime:
            self.standingsPanel.switchStandingsDisplay()
            self.lastSwitchStandingsTime = time.time()

        # Update the time panel
        if self.firstUpdate or self.lastUpdateTime.second != now.second:
            self.timePanel.setTime(now)
            self.timePanel.update()

            # Update the first pitch countdown panel
            if self.game is not None and self.game["status"] == "Pre":
                self.firstPitchCountdownPanel.update()


        self.firstUpdate = False
        self.lastUpdateTime = now
        root.after(200, self.updatePerpetually)


    def stopAllThreads(self):
        self.asyncRequester.stopAllThreads()



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

        if TWENTY_FOUR_HOUR_CLOCK:
            string2 = "{:02d}:{:02d}:{:02d}".format(self.dateAndTime.hour, self.dateAndTime.minute, self.dateAndTime.second)
        else:
            hour, suffix = toTwelveHourClock(self.dateAndTime)
            string2 = "{:02d}:{:02d}:{:02d} {:s}".format(hour, self.dateAndTime.minute, self.dateAndTime.second, suffix)

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

        if not TWENTY_FOUR_HOUR_CLOCK:
            exampleString = " 10:00 AM - 100  F  "

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
        iconSize = (self.fontHeight, self.fontHeight)    
        
        self.weatherIcons["Clear"] = loadAndResizeImage("weather/icons/clear.png", iconSize)
        self.weatherIcons["Partly Cloudy"] = loadAndResizeImage("weather/icons/partly_cloudy.png", iconSize)
        self.weatherIcons["Mostly Cloudy"] = self.weatherIcons["Partly Cloudy"]
        self.weatherIcons["Overcast"] = loadAndResizeImage("weather/icons/cloudy.png", iconSize)
        self.weatherIcons["Chance of Rain"] = loadAndResizeImage("weather/icons/chance_rain.png", iconSize)
        self.weatherIcons["Rain"] = loadAndResizeImage("weather/icons/rain.png", iconSize)
        self.weatherIcons["Chance of a Thunderstorm"] = loadAndResizeImage("weather/icons/chance_tstorm.png", iconSize)
        self.weatherIcons["Thunderstorm"] = loadAndResizeImage("weather/icons/tstorm.png", iconSize)

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

            if TWENTY_FOUR_HOUR_CLOCK:
                hourString = " {:02d}:{:02d}".format(time.hour, time.minute) + " - " + "{:>3s}".format(hour["temp"]) + " F "
            else:
                timeHour, suffix = toTwelveHourClock(time)
                hourString = " {:02d}:{:02d} {:s}".format(timeHour, time.minute, suffix) + " - " + "{:>3s}".format(hour["temp"]) + " F "

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
        self.canvas.delete("updates")
        self.canvas.create_text((self.width//2, self.height//2), anchor=tk.CENTER, font=self.font, fill=fontColor, text="Error...", tags="updates")


class GameScorePanel:
    def __init__(self, x, y, panelWidth, panelHeight):
        self.width = panelWidth
        self.height = panelHeight
        self.x = x
        self.y = y

        self.canvas = tk.Canvas(root, width=self.width, height=self.height, background=panelBackground, highlightthickness=0)
        self.canvas.place(x=self.x, y=self.y)
        
        lineHeightMultiplier = 1.2

        # Leading spaces leave room for logo
        self.numLeadingSpacesForLogo = 4
        exampleString = " " * self.numLeadingSpacesForLogo +  "STL 10"
        self.font, self.fontHeight = fontFit(fontName, exampleString, (panelWidth * .5 * .8, panelHeight * 0.8 / 2 // lineHeightMultiplier))
        
        self.lineHeight = self.fontHeight * 1.2

        # Center 2 lines of text vertically
        self.lineYStart = (self.height - 2 * self.lineHeight) // 2

        # Center left half strings horizontally
        self.leftHalfX = (self.width * .5 - self.font.measure(exampleString)) // 2

        # Center right half strings horizontally
        self.rightHalfX = self.width * .5 + (self.width * .5 - self.font.measure("Top 10")) // 2
        
        self.scaledLogos = {}
        self.logoLinePortion = 0.9 # logo takes up this % of line height

        # Initialize list of MLB team logos
        for key, logo in mlbLogos.items():
            logoHeight = logo.size[1]
            logoWidth = logo.size[0]
            scale = self.lineHeight * self.logoLinePortion / logoHeight

            self.scaledLogos[key] = ImageTk.PhotoImage(logo.resize((int(scale * logoWidth), int(scale * logoHeight))))
        

    def setScore(self, game):
        self.game = game

    def update(self):
        self.canvas.delete("updates")
        self.show()

        awayString   = " " * self.numLeadingSpacesForLogo + "{:3s}".format(self.game["away"]["name"]) + " {:2s}".format(self.game["away"]["runs"])
        awayLogo = self.scaledLogos[self.game["away"]["name"]]

        homeString   = " " * self.numLeadingSpacesForLogo + "{:3s}".format(self.game["home"]["name"]) + " {:2s}".format(self.game["home"]["runs"])
        homeLogo = self.scaledLogos[self.game["home"]["name"]]

        if self.game["status"] == "Live":
            inningString = self.game["inning"]["part"] + " " + self.game["inning"]["number"]
        else:
            totalInnings = len(self.game["away"]["scoreByInning"])
            if totalInnings == 9:
                inningString = "Final"
            else:
                inningString = "F ({:d})".format(totalInnings)

        lineY = self.lineYStart

        logoSpace = " " * self.numLeadingSpacesForLogo
        logoSpaceWidth = self.font.measure(logoSpace)
        awayLogoOffset = (logoSpaceWidth - awayLogo.width()) // 2
        homeLogoOffset = (logoSpaceWidth - homeLogo.width()) // 2
        
        self.canvas.create_image((self.leftHalfX + awayLogoOffset, lineY + self.lineHeight * 0.5 * (1 - self.logoLinePortion)), anchor=tk.NW, image=awayLogo, tags="updates")
        self.canvas.create_text((self.leftHalfX, lineY), anchor=tk.NW, text=awayString, fill=fontColor, font=self.font, tags="updates")
        self.canvas.create_text((self.rightHalfX, lineY), anchor=tk.NW, text=inningString, fill=fontColor, font=self.font, tags="updates")

        lineY += self.lineHeight

        self.canvas.create_image((self.leftHalfX + homeLogoOffset, lineY + self.lineHeight * 0.5 * (1 - self.logoLinePortion)), anchor=tk.NW, image=homeLogo, tags="updates")
        self.canvas.create_text((self.leftHalfX, lineY), anchor=tk.NW, text=homeString, fill=fontColor, font=self.font, tags="updates")

    def hide(self):
        #
        # Cheap trick to hide canvas. Apparently setting state to
        # "hidden" is invalid despite docs saying you can do so...
        #
        self.canvas.place(x=-self.width - 100, y=-self.height - 100)

    def show(self):
        self.canvas.place(x=self.x, y=self.y)

class GamePreviewPanel:
    def __init__(self, x, y, panelWidth, panelHeight):
        self.width = panelWidth
        self.height = panelHeight
        self.x = x
        self.y = y

        self.canvas = tk.Canvas(root, width=self.width, height=self.height, background=panelBackground, highlightthickness=0)
        self.canvas.place(x=self.x, y=self.y)

        lineHeightMultiplier = 1.2

        exampleTopString = "CHC @ STL"
        exampleBotString = "May 12, 15:28"

        if not TWENTY_FOUR_HOUR_CLOCK:
            exampleBotString = "May 12, 10:28 AM"

        self.font, self.fontHeight = fontFit(fontName, exampleBotString, (self.width * .5, self.height * 0.8 / 2 // lineHeightMultiplier))

        self.lineHeight = self.fontHeight * lineHeightMultiplier

        # Center 2 lines of text vertically
        self.lineYStart = (self.height - 2 * self.lineHeight) // 2

        # Center top line horizontally
        self.topX = (self.width - self.font.measure(exampleTopString)) // 2
        
        # Center bot line horizontally
        self.botX = (self.width - self.font.measure(exampleBotString)) // 2
        
        self.scaledLogos = {}

        self.awayLogoRegion = Rect(0, 0, self.width * .25, self.height)
        self.homeLogoRegion = Rect(self.width * .75, 0, self.width * .25, self.height)
        
        # Initialize list of MLB team logos
        for key, logo in mlbLogos.items():
            logoHeight = logo.size[1]
            logoWidth = logo.size[0]
            scale = min(self.awayLogoRegion.height * 0.8 / logoHeight,
                        self.awayLogoRegion.width * 0.8 / logoWidth)

            self.scaledLogos[key] = ImageTk.PhotoImage(logo.resize((int(scale * logoWidth), int(scale * logoHeight))))            

    def setPreview(self, game):
        self.game = game

    def update(self):
        self.canvas.delete("updates")
        self.show()

        if self.game["status"] == "Pre":
            topString = "{:3s} @ {:3s}".format(self.game["away"]["name"], self.game["home"]["name"])

            ast = self.game["adjustedStartTime"]

            
            if TWENTY_FOUR_HOUR_CLOCK:
                botString = "{:s} {:d}, {:02d}:{:02d}".format(months[ast.month], ast.day, ast.hour, ast.minute)
            else:
                hour, suffix = toTwelveHourClock(ast)
                botString = "{:s} {:d}, {:02d}:{:02d} {:s}".format(months[ast.month], ast.day, hour, ast.minute, suffix)


            awayLogo = self.scaledLogos[self.game["away"]["name"]]
            homeLogo = self.scaledLogos[self.game["home"]["name"]]

            # Center logo
            awayLogoXOffset = (self.awayLogoRegion.width - awayLogo.width()) // 2
            awayLogoYOffset = (self.awayLogoRegion.height - awayLogo.height()) // 2
            
            homeLogoXOffset = (self.homeLogoRegion.width - homeLogo.width()) // 2
            homeLogoYOffset = (self.homeLogoRegion.height - homeLogo.height()) // 2

            lineY = self.lineYStart

            self.canvas.create_image((self.awayLogoRegion.left + awayLogoXOffset, self.awayLogoRegion.top + awayLogoYOffset), anchor=tk.NW, image=awayLogo, tags="updates")
            self.canvas.create_image((self.homeLogoRegion.left + homeLogoXOffset, self.homeLogoRegion.top + homeLogoYOffset), anchor=tk.NW, image=homeLogo, tags="updates")
            
            self.canvas.create_text((self.topX, lineY), anchor=tk.NW, text=topString, font=self.font, fill=fontColor, tags="updates")

            lineY += self.lineHeight

            self.canvas.create_text((self.botX, lineY), anchor=tk.NW, text=botString, font=self.font, fill=fontColor, tags="updates")
        else:
            self.canvas.create_text((self.width // 2, self.height //2), anchor=tk.CENTER, text="No games found...", font=self.font, fill=fontColor, tags="updates")

    def showError(self):
        self.canvas.delete("updates")
        self.canvas.create_text((self.width//2, self.height//2), anchor=tk.CENTER, font=self.font, fill=fontColor, text="Error...", tags="updates")

    def hide(self):
        #
        # Cheap trick to hide canvas. Apparently setting state to
        # "hidden" is invalid despite docs saying you can do so...
        #
        self.canvas.place(x=-self.width - 100, y=-self.height - 100)

    def show(self):
        self.canvas.place(x=self.x, y=self.y)

class StandingsPanel:
    def __init__(self, x, y, panelWidth, panelHeight):
        self.width = panelWidth
        self.height = panelHeight
        self.x = x
        self.y = y

        self.canvas = tk.Canvas(root, width=self.width, height=self.height, background=panelBackground, highlightthickness=0)
        self.canvas.place(x=self.x, y=self.y)

        # Extra space before name for logo
        self.logoString = "    "
        exampleString = "1 " + self.logoString + " STL  100   62  -10.0"

        numLines = 9 # 1 for division name, 5 for teams, 2 for padding
        lineHeightMultiplier = 1.2 # Multiply font height by this to get line height

        self.font, self.fontHeight = fontFit(fontName, exampleString, (self.width * 0.9, self.height // (numLines * lineHeightMultiplier)))
        self.underlinedFont = tkFont.Font(family=fontName, size=-self.fontHeight, underline=1)

        self.lineHeight = self.fontHeight * lineHeightMultiplier

        # Center horizontally
        self.startX = (self.width - self.font.measure(exampleString)) // 2

        logoRegionWidth = self.font.measure(self.logoString)
        logoRegionHeight = self.fontHeight

        self.scaledLogos = {}

        # Initialize list of MLB team logos
        for key, logo in mlbLogos.items():
            logoHeight = logo.size[1]
            logoWidth = logo.size[0]
            scale = min(logoRegionHeight / float(logoHeight),
                        logoRegionWidth / float(logoWidth))

            self.scaledLogos[key] = ImageTk.PhotoImage(logo.resize((int(scale * logoWidth), int(scale * logoHeight))))                    

        self.displayingWildcard = False
        self.initiallySet = False

    def setDivisionStandings(self, divisionName, standings):
        self.divisionName = divisionName
        self.divisionStandings = standings

        if not self.initiallySet:
            self.titleString = divisionName
            self.standings = standings
            self.initiallySet = True

    def setWildcardStandings(self, wildcardName, standings):
        self.wildcardName = wildcardName
        self.wildcardStandings = standings

        if not self.initiallySet:
            self.titleString = wildcardName
            self.standings = standings
            self.initiallySet = True

    #
    # Switch between showing division and WC standings
    #
    def switchStandingsDisplay(self):
        if not self.initiallySet:
            return

        self.displayingWildcard = not self.displayingWildcard

        if self.displayingWildcard:
            self.titleString = self.wildcardName
            self.standings = self.wildcardStandings
        else:
            self.titleString = self.divisionName
            self.standings = self.divisionStandings

        self.update()

    def update(self):
        if not self.initiallySet:
            return

        self.canvas.delete("updates")
        
        lineY = self.lineHeight # start 1 line in to have some padding on top        
        divisionX = (self.width - self.font.measure(self.divisionName)) // 2

        self.canvas.create_text((divisionX, lineY), anchor=tk.NW, text=self.titleString, font=self.underlinedFont, fill=fontColor, tags="updates")

        # Add a little spacing. No worries, this is why we left room for an extra line at the bottom
        lineY += 1.3 * self.lineHeight

        headerString  = "# " + self.logoString + "Team    W    L    GB"

        self.canvas.create_text((self.startX, lineY), anchor=tk.NW, text=headerString, font=self.underlinedFont, fill=fontColor, tags="updates")
        lineY += 0.2 * self.lineHeight 

        teamOfInterestIndex = -1
        for i, team in enumerate(self.standings):
            if team["name"] == TEAM_OF_INTEREST:
                teamOfInterestIndex = i
                break
        
        for i, team in enumerate(self.standings[:5]):

            lineY += self.lineHeight

            #
            # Last iteration and team of interest hasn't been listed yet (maybe they are 7th for
            # WC). List team of interest instead of the 5th team and draw a line above, indicating
            # that the list has been broken up
            #
            if i == 4 and teamOfInterestIndex > 4:
                teamOfInterest = self.standings[teamOfInterestIndex]

                teamString = "{:d} {:s} {:<3s}  {:3d}  {:3d}  {:4.1f}".format(teamOfInterestIndex+1, self.logoString, teamOfInterest["name"], teamOfInterest["wins"], teamOfInterest["losses"], teamOfInterest["gb"])
                logo = self.scaledLogos[teamOfInterest["name"]]

                dividerY = lineY - (self.lineHeight - self.fontHeight) // 2
                self.canvas.create_line((self.startX, dividerY, self.startX + self.font.measure(teamString), dividerY), fill=fontColor, tags="updates")
            else:
                teamString = "{:d} {:s} {:<3s}  {:3d}  {:3d}  {:4.1f}".format(i+1, self.logoString, team["name"], team["wins"], team["losses"], team["gb"])
                logo = self.scaledLogos[team["name"]]

            logoXMiddle = self.startX + self.font.measure("1 ") + (self.font.measure(self.logoString) // 2)
            self.canvas.create_text((self.startX, lineY), anchor=tk.NW, text=teamString, font=self.font, fill=fontColor, tags="updates")


            self.canvas.create_image((logoXMiddle, lineY + self.lineHeight // 2), anchor=tk.CENTER, image=logo, tags="updates")
            

    def showError(self):
        self.canvas.delete("updates")
        self.canvas.create_text((self.width//2, self.height//2), anchor=tk.CENTER, font=self.font, fill=fontColor, text="Error...", tags="updates")
        

class FirstPitchCountdownPanel:
    def __init__(self, x, y, panelWidth, panelHeight):
        self.width = panelWidth
        self.height = panelHeight
        self.x = x
        self.y = y

        self.canvas = tk.Canvas(root, width=self.width, height=self.height, background=panelBackground, highlightthickness=0)
        self.canvas.place(x=self.x, y=self.y)

        self.topString   = "First pitch in..."
        exampleBotString = "0:00:00:00"

        lineHeightMultiplier = 1.2
        self.font, self.fontHeight = fontFit(fontName, self.topString, (panelWidth * .7, panelHeight * 0.8 / 2 // lineHeightMultiplier))

        self.lineHeight = self.fontHeight * lineHeightMultiplier

        self.lineYStart = (panelHeight - 2 * self.lineHeight) // 2
        self.topX = (panelWidth - self.font.measure(self.topString)) // 2
        self.botX = (panelWidth - self.font.measure(exampleBotString)) // 2

    def setTargetTime(self, targetTime):
        self.targetTime = targetTime

    def update(self):
        self.canvas.delete("updates")
        self.show()

        lineY = self.lineYStart
        now = datetime.now()
        difference = self.targetTime - now

        # Don't let the delta be negative if the game starts slightly
        # late.
        zerotime = timedelta(0, 0, 0, 0)

        if difference >= zerotime:
            days = difference.days
            hours = difference.seconds // 3600
            mins = (difference.seconds % 3600) // 60
            seconds = (difference.seconds % 3600 % 60) + 1 # Add 1 to "round up" the milliseconds, to make the clock + this time equal start time
        else:
            days = 0
            hours = 0
            mins = 0
            seconds = 0

        botString = "{:d}:{:02d}:{:02d}:{:02d}".format(days, hours, mins, seconds)

        self.canvas.create_text((self.topX, lineY), anchor=tk.NW, text=self.topString, font=self.font, fill=fontColor, tags="updates")
        lineY += self.lineHeight

        self.canvas.create_text((self.botX, lineY), anchor=tk.NW, text=botString, font=self.font, fill=fontColor, tags="updates")


    def showError(self):
        self.canvas.delete("updates")
        self.canvas.create_text((self.width//2, self.height//2), anchor=tk.CENTER, font=self.font, fill=fontColor, text="Error...", tags="updates")

    def hide(self):
        #
        # Cheap trick to hide canvas. Apparently setting state to
        # "hidden" is invalid despite docs saying you can do so...
        #
        self.canvas.place(x=-self.width - 100, y=-self.height - 100)

    def show(self):
        self.canvas.place(x=self.x, y=self.y)

class PitcherPreviewPanel:
    def __init__(self, x, y, panelWidth, panelHeight):
        self.width = panelWidth
        self.height = panelHeight
        self.x = x
        self.y = y

        self.canvas = tk.Canvas(root, width=self.width, height=self.height, background=panelBackground, highlightthickness=0)
        self.canvas.place(x=self.x, y=self.y)

    def setPitchers(self, game):
        self.game = game

    def update(self):
        self.canvas.delete("updates")
        self.show()

        #
        # Calculate font size in the update method since it will
        # depend on the pitcher's name length.
        #
        awayPitcherString = "{:3s}: {:s} ({:s}-{:s}, {:s})".format(
            self.game["away"]["name"],
            self.game["away"]["starter"]["name"],
            self.game["away"]["starter"]["wins"],
            self.game["away"]["starter"]["losses"],
            self.game["away"]["starter"]["era"])

        homePitcherString = "{:3s}: {:s} ({:s}-{:s}, {:s})".format(
            self.game["home"]["name"],
            self.game["home"]["starter"]["name"],
            self.game["home"]["starter"]["wins"],
            self.game["home"]["starter"]["losses"],
            self.game["home"]["starter"]["era"])

        if len(awayPitcherString) > len(homePitcherString):
            longestString = awayPitcherString
        else:
            longestString = homePitcherString

        lineHeightMultiplier = 1.2

        # Divide height by 2.5 because we have 2 lines of text with a half line of spacing between
        font, fontHeight = fontFit(fontName, longestString, (self.width * .9, self.height * .8 / 2.5 // lineHeightMultiplier))
        lineHeight = fontHeight * lineHeightMultiplier

        startX = (self.width - font.measure(longestString)) // 2
        lineY = (self.height - 2.5 * lineHeight) // 2

        self.canvas.create_text((startX, lineY), anchor=tk.NW, text=awayPitcherString, font=font, fill=fontColor, tags="updates")
        lineY += 1.5 * lineHeight

        self.canvas.create_text((startX, lineY), anchor=tk.NW, text=homePitcherString, font=font, fill=fontColor, tags="updates")

    def hide(self):
        #
        # Cheap trick to hide canvas. Apparently setting state to
        # "hidden" is invalid despite docs saying you can do so...
        #
        self.canvas.place(x=-self.width - 100, y=-self.height - 100)

    def show(self):
        self.canvas.place(x=self.x, y=self.y)

class SituationPanel:
    def __init__(self, x, y, panelWidth, panelHeight):
        self.width = panelWidth
        self.height = panelHeight
        self.x = x
        self.y = y

        self.canvas = tk.Canvas(root, width=self.width, height=self.height, background=panelBackground, highlightthickness=0)
        self.canvas.place(x=self.x, y=self.y)

        # Situation panel layout:
        #
        # 1 = B/S/O, 2 = diamond, 3 = current hitter/pitcher, 4 = last play (Play by play)
        #
        # 1111 2222
        # 1111 2222
        # 1111 2222
        #
        # 3333 4444
        # 3333 4444

        self.topHeightPercent = .65
        self.botHeightPercent = 1 - self.topHeightPercent

        self.leftWidthPercent = .5
        self.rightWidthPercent = 1 - self.leftWidthPercent

        # Image will be resized to character size and placed
        # inline, as if they were characters
        exampleTopString = " B: * * * * "

        topNumLines = 3 # balls, strikes, outs
        lineHeightMultiplier = 1.2

        self.topFont, self.topFontHeight = fontFit(fontName, exampleTopString, (self.width * self.leftWidthPercent, self.height * self.topHeightPercent / topNumLines // lineHeightMultiplier))
        self.topLineHeight = self.topFontHeight * lineHeightMultiplier

        self.topLeftStartX = ((self.width * self.leftWidthPercent) - self.topFont.measure(exampleTopString)) // 2
        self.topLeftStartY = self.topFontHeight * .2

        self.topCharacterWidth = self.topFont.measure("#")
        iconSize = (self.topCharacterWidth, self.topCharacterWidth)

        self.bsoIcons = []
        self.bsoIcons.append(loadAndResizeImage("img/situationIcons/ball.png", iconSize))
        self.bsoIcons.append(loadAndResizeImage("img/situationIcons/strike.png", iconSize))
        self.bsoIcons.append(loadAndResizeImage("img/situationIcons/out.png", iconSize))


        self.diamondCenter = (self.width * self.leftWidthPercent + self.width * self.rightWidthPercent // 2,
                              self.height * self.topHeightPercent // 2)

        diamondSize = min(self.width * self.rightWidthPercent * .9, self.height * self.topHeightPercent * .9)
        diamondSize = (diamondSize, diamondSize)

        self.diamondIcons = {}

        for i in range(0, 8):
            suffix = ""

            if i % 2 == 1:
                suffix += "1"
            else:
                suffix += "0"

            if i // 2 % 2 == 1:
                suffix += "1"
            else:
                suffix += "0"

            if i // 4 % 2 == 1:
                suffix += "1"
            else:
                suffix += "0"

            self.diamondIcons[suffix] = loadAndResizeImage("img/situationIcons/diamond" + suffix + ".png", diamondSize)

    def setSituation(self, game):
        self.game = game

    def update(self):
        self.canvas.delete("updates")
        self.show()

        lineY = self.topLeftStartY

        self.canvas.create_text((self.topLeftStartX, lineY), anchor=tk.NW, text=" B: ", font=self.topFont, fill=fontColor, tags="updates")

        iconStartX = self.topLeftStartX + self.topFont.measure(" B: ") + self.topCharacterWidth // 2 # plus half character so we can anchor in center

        #
        # BALLS
        #
        iconX = iconStartX
        iconY = lineY + self.topLineHeight // 2

        for i in range(0, self.game["situation"]["balls"]):
            self.canvas.create_image((iconX, iconY), anchor=tk.CENTER, image=self.bsoIcons[0], tags="updates")
            iconX += self.topCharacterWidth * 2 # times 2 because we are also adding a space

        lineY += self.topLineHeight

        #
        # STRIKES
        #
        self.canvas.create_text((self.topLeftStartX, lineY), anchor=tk.NW, text=" S: ", font=self.topFont, fill=fontColor, tags="updates")

        iconX = iconStartX
        iconY = lineY + self.topLineHeight // 2

        for i in range(0, self.game["situation"]["strikes"]):
            self.canvas.create_image((iconX, iconY), anchor=tk.CENTER, image=self.bsoIcons[1], tags="updates")
            iconX += self.topCharacterWidth * 2

        lineY += self.topLineHeight

        #
        # OUTS
        #
        self.canvas.create_text((self.topLeftStartX, lineY), anchor=tk.NW, text=" O: ", font=self.topFont, fill=fontColor, tags="updates")

        iconX = iconStartX
        iconY = lineY + self.topLineHeight // 2

        for i in range(0, self.game["situation"]["outs"]):
            self.canvas.create_image((iconX, iconY), anchor=tk.CENTER, image=self.bsoIcons[2], tags="updates")
            iconX += self.topCharacterWidth * 2


        #
        # RUNNERS ON DIAMOND
        #
        runnerString = ""
        
        for runner in self.game["situation"]["runners"]:
            if runner != "":
                runnerString += "1"
            else:
                runnerString += "0"

        self.canvas.create_image(self.diamondCenter, anchor=tk.CENTER, image=self.diamondIcons[runnerString], tags="updates")


        #
        # CURRENT BATTER AND PITCHER
        #
        batterString = "H: {:s} ({:s})".format(self.game["situation"]["batter"]["name"], self.game["situation"]["batter"]["avg"])
        pitcherString = "P: {:s} ({:s})".format(self.game["situation"]["pitcher"]["name"], self.game["situation"]["pitcher"]["era"])

        longestStringLen = max(len(batterString), len(pitcherString))

        lineHeightMultiplier = 1.2
        bottomLeftFont, bottomLeftFontHeight = fontFit(fontName, "#" * longestStringLen, (self.width * self.leftWidthPercent * .8, self.height * self.botHeightPercent / 2 // lineHeightMultiplier))
        bottomLeftLineHeight = bottomLeftFontHeight * lineHeightMultiplier

        combinedString = batterString + "\n" + pitcherString
        bottomLeftCenter= (self.width * self.leftWidthPercent // 2,
                           self.height * self.topHeightPercent + self.height * self.botHeightPercent // 2)

        self.canvas.create_text(bottomLeftCenter, anchor=tk.CENTER, text=combinedString, font=bottomLeftFont, fill=fontColor, tags="updates")

        
        #
        # LAST PLAY
        #
        if "lastPlay" in self.game["situation"]:
            maxLastPlayStringLength = 60
            lastPlayString = self.game["situation"]["lastPlay"]
            lastPlayString = lastPlayString.replace("  ", " ") # MLB uses double spaces after period *facepalm*

            if len(lastPlayString) > maxLastPlayStringLength:
                lastSpaceIndex = lastPlayString.rfind(" ", 0, maxLastPlayStringLength)
                lastPlayString = lastPlayString[0:lastSpaceIndex] + " ..."
            
            #
            # Find the first space before and after the midpoint of
            # the string. Whichever is closest to the string midpoint
            # gets replaced by a new-line
            #
            spaceBeforeMidpointIndex = lastPlayString.rfind(" ", 0, len(lastPlayString)//2)
            spaceAfterMidpointIndex = lastPlayString.find(" ", len(lastPlayString)//2, len(lastPlayString))

            
            spaceIndex = len(lastPlayString) // 2

            #
            # -1 means space not found. Highly, *highly* unlikely that
            # string has no spaces, but lets check anyways.
            #
            if spaceBeforeMidpointIndex != -1 or spaceAfterMidpointIndex != -1:
                if spaceBeforeMidpointIndex == -1:
                    spaceIndex = spaceAfterMidpointIndex
                if spaceAfterMidpointIndex == -1:
                    spaceIndex = spaceBeforeMidpointIndex

                beforeDistance = len(lastPlayString) // 2 - spaceBeforeMidpointIndex
                afterDistance = spaceAfterMidpointIndex - len(lastPlayString) // 2

                if afterDistance < beforeDistance:
                    spaceIndex = spaceAfterMidpointIndex
                else:
                    spaceIndex = spaceBeforeMidpointIndex

                # Replace space with \n
                lastPlayString = lastPlayString[:spaceIndex] + "\n" + lastPlayString[spaceIndex + 1:]

            longestStringLength = spaceIndex

            if spaceIndex < len(lastPlayString) // 2:
                longestStringLength = len(lastPlayString) - spaceIndex

            bottomRightLines = 2
            bottomRightFont, bottomRightFontHeight = fontFit(fontName, "#" * longestStringLength, (self.width * self.rightWidthPercent * .9, self.height * self.botHeightPercent / bottomRightLines // lineHeightMultiplier))
            bottomRightLineHeight = bottomRightFontHeight * lineHeightMultiplier

            bottomRightCenter = (self.width * self.leftWidthPercent + self.width * self.rightWidthPercent // 2,
                                 self.height * self.topHeightPercent + self.height * self.botHeightPercent // 2)

            self.canvas.create_text(bottomRightCenter, anchor=tk.CENTER, text=lastPlayString, font=bottomRightFont, fill=fontColor, tags="updates")


    def hide(self):
        #
        # Cheap trick to hide canvas. Apparently setting state to
        # "hidden" is invalid despite docs saying you can do so...
        #
        self.canvas.place(x=-self.width - 100, y=-self.height - 100)

    def show(self):
        self.canvas.place(x=self.x, y=self.y)


class BoxScorePanel:
    def __init__(self, x, y, panelWidth, panelHeight):
        self.width = panelWidth
        self.height = panelHeight
        self.x = x
        self.y = y

        self.canvas = tk.Canvas(root, width=self.width, height=self.height, background=panelBackground, highlightthickness=0)
        self.canvas.place(x=self.x, y=self.y)

        self.topHeightPercent = 0.85 # main box score
        self.botHeightPercent = 1 - self.topHeightPercent # win/loss/save pitcher info, post game

        #                         1  2  3  4  5  6  7  8  9   R  H  E
        exampleString = "*  STL  10 10 10 10 10 10 10 10 10  10 10 10"

        topNumLines = 3
        lineHeightMultiplier = 1.2

        self.topFont, self.topFontHeight = fontFit(fontName, exampleString, (self.width * .9, self.height * self.topHeightPercent // topNumLines // lineHeightMultiplier))
        self.topLineHeight = self.topFontHeight * lineHeightMultiplier
        self.topUnderlinedFont = tkFont.Font(family=fontName, size=-self.topFontHeight, underline=1)

        self.topStartLineY = (self.height * self.topHeightPercent - self.topLineHeight * topNumLines) // 2
        self.topStartX = (self.width - self.topFont.measure(exampleString)) // 2
        

    def setGame(self, game):
        self.game = game

    def update(self):
        self.canvas.delete("updates")
        self.show()

        # If game is in extras, "shift" displayed innings to the left so The current inning is the
        # last one displayed.
        firstInningIndexToDisplay = len(self.game["away"]["scoreByInning"]) - 9

        topString = "       "

        for i in range(firstInningIndexToDisplay, firstInningIndexToDisplay + 9):
            topString += "{:>2d}".format(i + 1)
            topString += " "

        topString += "  R  H  E"

        if (self.game["status"]) == "Live":
            if (self.game["inning"]["part"]) in ("End", "Top"):
                awayString = "* "
                homeString = "  "
            else:
                awayString = "  "
                homeString = "* "
        else:
            awayString = "  "
            homeString = "  "


        awayString += "{:>3s}".format(self.game["away"]["name"])
        awayString += "  "

        for inningRuns in self.game["away"]["scoreByInning"][firstInningIndexToDisplay : firstInningIndexToDisplay + 9]:
            awayString += "{:>2s}".format(inningRuns)
            awayString += " "

        awayString += " {:>2s} {:>2s} {:>2s}".format(self.game["away"]["runs"], self.game["away"]["hits"], self.game["away"]["errors"])


        homeString += "{:3s}".format(self.game["home"]["name"])
        homeString += "  "

        for inningRuns in self.game["home"]["scoreByInning"][firstInningIndexToDisplay : firstInningIndexToDisplay + 9]:
            homeString += "{:>2s}".format(inningRuns)
            homeString += " "

        homeString += " {:>2s} {:>2s} {:>2s}".format(self.game["home"]["runs"], self.game["home"]["hits"], self.game["home"]["errors"])


        lineY = self.topStartLineY

        self.canvas.create_text((self.topStartX, lineY), anchor=tk.NW, text=topString, font=self.topUnderlinedFont, fill=fontColor, tags="updates")
        lineY += self.topLineHeight

        self.canvas.create_text((self.topStartX, lineY), anchor=tk.NW, text=awayString, font=self.topFont, fill=fontColor, tags="updates")
        lineY += self.topLineHeight

        self.canvas.create_text((self.topStartX, lineY), anchor=tk.NW, text=homeString, font=self.topFont, fill=fontColor, tags="updates")


        #
        # Display win/loss/save pitchers
        #
        if (self.game["status"]) == "Post":
            spaceBetweenPitchers = "     "
            botString = "W: {:s} ({:s}-{:s}){:s}L: {:s} ({:s}-{:s})".format(
                self.game["pitcherResults"]["win"]["name"],
                self.game["pitcherResults"]["win"]["updatedWins"],
                self.game["pitcherResults"]["win"]["updatedLosses"],
                spaceBetweenPitchers,
                self.game["pitcherResults"]["loss"]["name"],
                self.game["pitcherResults"]["loss"]["updatedWins"],
                self.game["pitcherResults"]["loss"]["updatedLosses"])

            if "save" in self.game["pitcherResults"]:
                botString += "{:s}S: {:s} ({:s})".format(
                    spaceBetweenPitchers,
                    self.game["pitcherResults"]["save"]["name"],
                    self.game["pitcherResults"]["save"]["updatedSaves"])

            lineHeightMultiplier = 1.5
            botFont, botFontHeight = fontFit(fontName, botString, (self.width * .9, self.height * self.botHeightPercent // lineHeightMultiplier))
            
            botMidX = self.width // 2
            botMidY = self.height * self.topHeightPercent + self.height * self.botHeightPercent // 2

            self.canvas.create_text((botMidX, botMidY), anchor=tk.CENTER, text=botString, font=botFont, fill=fontColor, tags="updates")


    def hide(self):
        #
        # Cheap trick to hide canvas. Apparently setting state to
        # "hidden" is invalid despite docs saying you can do so...
        #
        self.canvas.place(x=-self.width - 100, y=-self.height - 100)

    def show(self):
        self.canvas.place(x=self.x, y=self.y)
    
            
def exitTkinter(event):
    global scoreboard
    scoreboard.stopAllThreads()
    root.destroy()
    


class Rect():
    def __init__(self, left, top, width, height):
        self.left = left
        self.top = top
        self.width = width
        self.height = height

root = tk.Tk()

root.attributes('-fullscreen', True)
screenWidth = root.winfo_screenwidth()
screenHeight = root.winfo_screenheight()

backgroundColorString =  "#{:02x}{:02x}{:02x}".format(background[0], background[1], background[2])
bgCanvas = tk.Canvas(root, width=screenWidth, height=screenHeight, background=backgroundColorString, highlightthickness=0)
bgCanvas.place(x=0, y=0)

root.bind_all('<Escape>', exitTkinter)

scoreboard = LiveScoreboard()
scoreboard.updatePerpetually()


root.mainloop()

