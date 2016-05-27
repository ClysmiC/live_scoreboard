# -*- coding: latin-1 -*-

from scrape.mlb_scraper_mlb_api import MlbScraperMlbApi
from weather.weather_info_wunderground import hourlyForecast

from copy import deepcopy
from datetime import datetime, timedelta
import time
import Tkinter as tk
import tkFont

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


class LiveScoreboard:
    def __init__(self):
        # Store the time of when we last requested these things. This
        # is used to make our requests at a reasonable rate.
        self.weatherQueryMade = False         # (This hour)

        self.lastGameQueryTime = 0
        self.lastDivisionQueryTime = 0
        self.lastSwitchStandingsTime = 0

        self.weatherQueryMinuteMark    = 40   # Query at XX:40

        # Add a few seconds to some of the cooldowns to try to prevent
        # all the queries from happening in the same second and
        # lowering the framerate (since queries are synchronous)
        self.gameNonLiveQueryCooldown    = 302  # Once per 5 minutes
        self.gameAlmostLiveQueryCooldown = 60   # Once per minute
        self.gameLiveQueryCooldown       = 20   # Once per 20 seconds
        self.divisionQueryCooldown       = 907  # Once per 15 minutes

        # Both division and wildcard standings are queried during the
        # division query.  This timer determines how often the
        # division displays one before switching to the other.
        self.switchStandingsTime         = 15

        # Don't update the main preview to today's game until 4am.
        # That way, if I'm up late (i.e., 1 am) I can still see the
        # results for what I would consider to be "today"
        self.showTodaysGameHour = 4

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
        # self.boxScorePanel = BoxScorePanel(boxScorePanelX1, boxScorePanelY1, boxScorePanelWidth, boxScorePanelHeight)
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


        # TODO: Handle game status of "Postponed"

        # Update weather panel on the 40 minute mark
        if self.firstUpdate or now.minute >= self.weatherQueryMinuteMark and not self.weatherQueryMade:

            success = False

            try:
                weatherInfo = hourlyForecast(WEATHER_LOCATION[0], WEATHER_LOCATION[1], wundergroundApiKey)
                success = True
            except:
                success = False

            if success:
                weatherInfoToDisplay = []

                currTime = datetime.now()
                print("Weather request successfully made at {:02d}:{:02d}:{:02d}".format(currTime.hour, currTime.minute, currTime.second))

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
            else:
                self.weatherPanel.showError()
                currTime = datetime.now()
                print("Weather request failed at {:02d}:{:02d}:{:02d} .... error displayed".format(currTime.hour, currTime.minute, currTime.second))


        if now.minute < 40:
            self.weatherQueryMade = False


        #
        # NOTE: potential errors if first update had connection
        # problems and failed to produce a self.game. Ignoring this
        # for now since this only happens the first iteration of a
        # program that runs for days/weeks/months
        #


        gameAlmostStarted = False

        #
        # Determine if game is "almost started", in which case the
        # poll rate picks up
        #
        if not self.firstUpdate and self.game["status"] == "Pre":
            timeUntilGame = self.game["adjustedStartTime"] - datetime.now()
            if timeUntilGame.total_seconds() < self.gameNonLiveQueryCooldown:
                gameAlmostStarted = True

        
        #
        # Poll the game data!
        #
        if (self.firstUpdate) or (
            self.game["status"] == "Live" and executionTime - self.lastGameQueryTime >= self.gameLiveQueryCooldown) or (
            gameAlmostStarted and executionTime - self.lastGameQueryTime >= self.gameAlmostLiveQueryCooldown) or (
                executionTime - self.lastGameQueryTime >= self.gameNonLiveQueryCooldown):

            # Don't update to todays game until 4am. If it is
            # before 4am, show yesterday's game
            dateOfInterest = deepcopy(now)

            if now.hour < self.showTodaysGameHour:
                dateOfInterest -= timedelta(days=1)

            success = False
            try:
                self.game = mlb.getGameInfo(TEAM_OF_INTEREST, dateOfInterest)
                success = True
            except:
                success = False

            if success:
                currTime = datetime.now()
                print("Game request successful at {:02d}:{:02d}:{:02d}".format(currTime.hour, currTime.minute, currTime.second))

                #
                # Serves double duty. Holds the success of either the
                # preview of the upcoming game (today is a NoGame), or
                # the success of the next game preview when today's
                # game is Post. In both cases, failure means re-do the
                # query next time we get the chance.
                #
                previewFailed = False


                # If no game found for today, look ahead up to 10 days
                # until we find a game

                try:
                    lookaheadDays = 0
                    while self.game["status"] == "NoGame" and lookaheadDays < 10:
                        lookaheadDays += 1
                        dateOfInterest = dateOfInterest + timedelta(days=1)
                        self.game = mlb.getGameInfo(TEAM_OF_INTEREST, dateOfInterest)

                        currTime = datetime.now()
                        print("Lookahead {:d} day(s) request successful at {:02d}:{:02d}:{:02d}".format(lookaheadDays, currTime.hour, currTime.minute, currTime.second)) 
                    
                    previewFailed = False
                except:
                    previewFailed = True

                if not previewFailed:

                    #
                    # Game not yet started
                    #
                    if self.game["status"] == "Pre":
                        self.game["adjustedStartTime"] = getAdjustedStartTime(self.game)

                        self.gameScorePanel.hide()
                        self.gamePreviewPanel1.setPreview(self.game)
                        self.gamePreviewPanel1.update()

                        self.firstPitchCountdownPanel.setTargetTime(self.game["adjustedStartTime"])
                        self.firstPitchCountdownPanel.update()

                        self.pitcherPreviewPanel.setPitchers(self.game)
                        self.pitcherPreviewPanel.update()


                    #
                    # Game is live or finished
                    #
                    elif self.game["status"] in ("Live", "Post"):
                        self.gamePreviewPanel1.hide()
                        self.gameScorePanel.setScore(self.game)
                        self.gameScorePanel.update()


                        if self.game["status"] == "Live":
                            #
                            # Show situation in bottom middle
                            #
                            self.gamePreviewPanel2.hide()
                            self.situationPanel.setSituation(self.game)
                            self.situationPanel.update()

                        else:
                            #
                            # Preview next game in the bottom middle
                            #

                            # Look ahead until we find next game
                            lookaheadDays = 0
                            lookaheadGame = {}
                            lookaheadGame["status"] = "NoGame"
                            dateOfInterest = deepcopy(now)

                            if now.hour < self.showTodaysGameHour:
                                dateOfInterest -= timedelta(days=1)

                            try:
                                while lookaheadGame["status"] == "NoGame" and lookaheadDays < 10:
                                    lookaheadDays += 1
                                    dateOfInterest = dateOfInterest + timedelta(days=1)
                                    lookaheadGame = mlb.getGameInfo(TEAM_OF_INTEREST, dateOfInterest)
                                success = True
                            except:
                                success = False

                            if success:
                                currTime = datetime.now()
                                print("Lookahead {:d} day(s) request successful at {:02d}:{:02d}:{:02d}".format(lookaheadDays, currTime.hour, currTime.minute, currTime.second)) 

                                lookaheadGame["adjustedStartTime"] = getAdjustedStartTime(lookaheadGame)

                                self.situationPanel.hide()
                                self.pitcherPreviewPanel.hide()
                                self.gamePreviewPanel2.setPreview(lookaheadGame)
                                self.gamePreviewPanel2.update()

                            else:
                                previewFailed = True
                                self.situationPanel.hide()
                                self.pitcherPreviewPanel.hide()
                                self.gamePreviewPanel2.showError()
                                currTime = datetime.now()
                                print("Failed lookahead request at {:02d}:{:02d}:{:02d}".format(currTime.hour, currTime.minute, currTime.second))


                    #
                    # No Game found today or in lookahead loop
                    #
                    else:
                        # Game preview panel handles NoGame message
                        self.gameScorePanel.hide()
                        self.gamePreviewPanel1.setPreview(self.game)
                        self.gamePreviewPanel1.update()

                    #
                    # We know the main lookup didn't fail since we made it
                    # this far. But we want to make sure the preview
                    # lookup completed if today's game is over. If that
                    # one failed, we will not mark the time so that it
                    # will be re-queried next iteration. Only need to
                    # explicitly check if the preview failed.
                    #
                    if not previewFailed:
                        self.lastGameQueryTime = time.time()

            else:
                self.gameScorePanel.hide()
                self.gamePreviewPanel1.showError()

                # self.boxScorePanel.hide()
                self.firstPitchCountdownPanel.showError()

                currTime = datetime.now()
                print("Failed game or lookahead request at {:02d}:{:02d}:{:02d}".format(currTime.hour, currTime.minute, currTime.second))
                

        if self.firstUpdate or executionTime - self.lastDivisionQueryTime >= self.divisionQueryCooldown:
            
            success = False

            try:
                # TODO, request NLC and NLWC and toggle between the
                # two every 10-20 seconds
                divisionStandings = mlb.getDivisionStandings("NLC")
                wcStandings = mlb.getDivisionStandings("NLWC")
                success = True
            except:
                success = False

            if success:
                wcStandings = wcStandings[0:5] # Truncate wildcard to top 5 teams

                self.standingsPanel.setDivisionStandings("NL Central", divisionStandings)
                self.standingsPanel.setWildcardStandings("NL Wildcard", wcStandings)

                self.standingsPanel.update()
                currTime = datetime.now()
                print("Standings requests successful at {:02d}:{:02d}:{:02d}".format(currTime.hour, currTime.minute, currTime.second))

                self.lastDivisionQueryTime = time.time()
            else:
                self.standingsPanel.showError()
                currTime = datetime.now()
                print("Failed standings request at {:02d}:{:02d}:{:02d}".format(currTime.hour, currTime.minute, currTime.second))
                

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
        self.canvas.delete("updates")
        self.canvas.create_text((self.width//2, self.height//2), anchor=tk.CENTER, font=self.font, fill=fontColor, text="Error...", tags="updates")


class GameScorePanel():
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

        awayString   = " " * self.numLeadingSpacesForLogo + self.game["away"]["name"] + " {:2s}".format(self.game["away"]["runs"])
        awayLogo = self.scaledLogos[self.game["away"]["name"]]

        homeString   = " " * self.numLeadingSpacesForLogo + self.game["home"]["name"] + " {:2s}".format(self.game["home"]["runs"])
        homeLogo = self.scaledLogos[self.game["home"]["name"]]

        if self.game["status"] == "Live":
            inningString = self.game["inning"]["part"] + " " + self.game["inning"]["number"]
        else:
            totalInnings = len(self.game["away"]["scoreByInning"])
            if totalInnings == 9:
                inningString = "Final"
            else:
                inningString = "Final ({:d})".format(totalInnings)

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
            
            botString = "{:s} {:d}, {:02d}:{:02d}".format(months[ast.month], ast.day, ast.hour, ast.minute)

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
        self.xStart = (self.width - self.font.measure(exampleString)) // 2

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
        self.displayingWildcard = not self.displayingWildcard

        if self.displayingWildcard:
            self.titleString = self.wildcardName
            self.standings = self.wildcardStandings
        else:
            self.titleString = self.divisionName
            self.standings = self.divisionStandings

        self.update()

    def update(self):
        self.canvas.delete("updates")
        
        lineY = self.lineHeight # start 1 line in to have some padding on top        
        divisionX = (self.width - self.font.measure(self.divisionName)) // 2

        self.canvas.create_text((divisionX, lineY), anchor=tk.NW, text=self.titleString, font=self.underlinedFont, fill=fontColor, tags="updates")

        # Add a little spacing. No worries, this is why we left room for an extra line at the bottom
        lineY += 1.3 * self.lineHeight

        headerString  = "# " + self.logoString + "Team    W    L    GB"

        self.canvas.create_text((self.xStart, lineY), anchor=tk.NW, text=headerString, font=self.underlinedFont, fill=fontColor, tags="updates")
        lineY += 0.2 * self.lineHeight 

        for i, team in enumerate(self.standings):
            lineY += self.lineHeight
            
            teamString = "{:d} {:s} {:s}  {:3d}  {:3d}  {:4.1f}".format(i+1, self.logoString, team["name"], team["wins"], team["losses"], team["gb"])
            
            self.canvas.create_text((self.xStart, lineY), anchor=tk.NW, text=teamString, font=self.font, fill=fontColor, tags="updates")

            logoXMiddle = self.xStart + self.font.measure("1 ") + (self.font.measure(self.logoString) // 2)
            self.canvas.create_image((logoXMiddle, lineY + self.lineHeight // 2), anchor=tk.CENTER, image=self.scaledLogos[team["name"]], tags="updates")
            

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

        days = difference.days
        hours = difference.seconds // 3600
        mins = (difference.seconds % 3600) // 60
        seconds = (difference.seconds % 3600 % 60) + 1 # Add 1 to "round up" the milliseconds, to make the clock + this time equal start time

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

        xStart = (self.width - font.measure(longestString)) // 2
        lineY = (self.height - 2.5 * lineHeight) // 2

        self.canvas.create_text((xStart, lineY), anchor=tk.NW, text=awayPitcherString, font=font, fill=fontColor, tags="updates")
        lineY += 1.5 * lineHeight

        self.canvas.create_text((xStart, lineY), anchor=tk.NW, text=homePitcherString, font=font, fill=fontColor, tags="updates")

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

            if len(lastPlayString) > maxLastPlayStringLength:
                lastPlayString = lastPlayString[:maxLastPlayStringLength - 4] + " ..."

            bottomRightLines = 2
            bottomRightFont, bottomRightFontHeight = fontFit(fontName, lastPlayString[ : len(lastPlayString)//2], (self.width * self.rightWidthPercent * .9, self.height * self.botHeightPercent / bottomRightLines // lineHeightMultiplier))
            bottomRightLineHeight = bottomRightFontHeight * lineHeightMultiplier

            if bottomRightFont.measure(lastPlayString) > self.width * self.rightWidthPercent:
                lastPlayString = lastPlayString[ : len(lastPlayString)//2] + "\n" + lastPlayString[len(lastPlayString)//2 : ]

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

            
def exitTkinter(event):
    root.destroy()
    
def startScoreboard():
    scoreboard = LiveScoreboard()
    scoreboard.updatePerpetually()


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

backgroundString =  "#{:02x}{:02x}{:02x}".format(background[0], background[1], background[2])
bgCanvas = tk.Canvas(root, width=screenWidth, height=screenHeight, background=backgroundString, highlightthickness=0)
bgCanvas.place(x=0, y=0)

root.bind_all('<Escape>', exitTkinter)

startScoreboard()

root.mainloop()
