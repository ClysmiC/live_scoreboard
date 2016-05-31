from bs4 import BeautifulSoup
from urllib2 import urlopen

import datetime
import json

# Game Statuses: NoGame, Pre, Live, Post, Postponed
# InningParts: Top Mid Bot End


class MlbScraperMlbApi():
    def __init__(self):

        self.gameScrapeTarget = "http://gd2.mlb.com/components/game/mlb/"

        self.initializeTeamsAndDivisions()

        # Couldn't find this in all one concentrated location in the
        # MLB API, and the MLB website had to load javascript. Espn
        # loads the info just fine though
        self.standingsScrapeTarget = "http://espn.go.com/mlb/standings"
        self.wildcardStandingsScrapeTarget = "http://espn.go.com/mlb/standings/_/view/wild-card"
                
        
    def getGameInfo(self, team, date=None):
        team = self.getTeamNick(team)
        
        if team is None:
            raise ValueError("Invalid team name.")

        if date is None:
            date = datetime.date.today()

        dateString = "year_" +  str(date.year).zfill(4) + "/month_" + str(date.month).zfill(2) + "/day_" + str(date.day).zfill(2) + "/master_scoreboard.json"

        jsonString = urlopen(self.gameScrapeTarget + dateString, timeout=5).read().decode("utf-8")
        
        scoreboard = json.loads(jsonString)

        game = {}
        game["status"] = "NoGame"
        
        for gameData in scoreboard["data"]["games"]["game"]:
            if gameData["home_name_abbrev"] == team or gameData["away_name_abbrev"] == team:

                game["away"] = {}
                game["home"] = {}
                
                game["away"]["name"] = self.getTeamNick(gameData["away_team_name"])
                game["home"]["name"] = self.getTeamNick(gameData["home_team_name"])

                statusString = gameData["status"]["status"]
                
                # TODO: check the api when there are rainouts or rain
                # delays. I suspect that these are shown in this
                # status attribute.
                if statusString in ("Pre-Game", "Warmup", "Preview"):
                    game["status"] = "Pre"
                elif statusString in ("In Progress", "Manager Challenge"):
                    game["status"] = "Live"
                elif statusString in ("Final", "Game Over"):
                    game["status"] = "Post"
                elif statusString == "Postponed":
                    game["status"] = "Postponed"
                else:
                    raise Exception("Unknown status string: " + statusString)
                

                if game["status"] == "Pre":
                    game["startTime"] = {}
                    rawHomeTime = gameData["home_time"]
                    hour, minute = rawHomeTime.split(":")
                    hour = int(hour)
                    minute = int(minute)
                    
                    # Convert to 24 hour time
                    if hour < 10:
                        hour += 12
                        
                    game["startTime"]["time"] = datetime.datetime(date.year, date.month, date.day, hour, minute)
                    game["startTime"]["timeZone"] = gameData["home_time_zone"]

                    game["away"]["starter"] = {}
                    game["home"]["starter"] = {}

                    if gameData["away_probable_pitcher"]["name_display_roster"] != "":
                        game["away"]["starter"]["name"] = gameData["away_probable_pitcher"]["name_display_roster"]
                        game["away"]["starter"]["wins"] = gameData["away_probable_pitcher"]["wins"]
                        game["away"]["starter"]["losses"] = gameData["away_probable_pitcher"]["losses"]
                        game["away"]["starter"]["era"] = gameData["away_probable_pitcher"]["era"]
                    else:
                        game["away"]["starter"]["name"] = "???"
                        game["away"]["starter"]["wins"] = "0"
                        game["away"]["starter"]["losses"] = "0"
                        game["away"]["starter"]["era"] = "0.00"
                        
                    if gameData["home_probable_pitcher"]["name_display_roster"] != "":
                        game["home"]["starter"]["name"] = gameData["home_probable_pitcher"]["name_display_roster"]
                        game["home"]["starter"]["wins"] = gameData["home_probable_pitcher"]["wins"]
                        game["home"]["starter"]["losses"] = gameData["home_probable_pitcher"]["losses"]
                        game["home"]["starter"]["era"] = gameData["home_probable_pitcher"]["era"]
                    else:
                        game["home"]["starter"]["name"] = "???"
                        game["home"]["starter"]["wins"] = "0"
                        game["home"]["starter"]["losses"] = "0"
                        game["home"]["starter"]["era"] = "0.00"
                    
                
                if game["status"] == "Live":

                    # Determine inning, and part of inning
                    game["inning"] = {}
                    game["inning"]["number"] = gameData["status"]["inning"]

                    isTopInningString = gameData["status"]["top_inning"]
                    
                    if isTopInningString == "Y":
                        
                        if gameData["status"]["inning_state"] == "Middle":
                            game["inning"]["part"] = "Mid"
                        else:
                            game["inning"]["part"] = "Top"
                            
                    else:
                        
                        if gameData["status"]["inning_state"] == "End":
                            game["inning"]["part"] = "End"
                        else:
                            game["inning"]["part"] = "Bot"

                            
                    game["situation"] = {}

                    # Store baserunner names in list. Empty string
                    # means no runner on.
                    game["situation"]["runners"] = []
                    game["situation"]["pitcher"] = {}
                    game["situation"]["batter"] = {}

                    # If you want first + last name, use a string like this:
                    # gameData["pitcher"]["first"] + " " + gameData["pitcher"]["last"]
                    game["situation"]["batter"]["name"] = gameData["batter"]["name_display_roster"]
                    game["situation"]["batter"]["avg"] = gameData["batter"]["avg"]

                    game["situation"]["pitcher"]["name"] = gameData["pitcher"]["name_display_roster"]
                    game["situation"]["pitcher"]["era"] = gameData["pitcher"]["era"]

                    if "pbp" in gameData and "last" in gameData["pbp"] and gameData["pbp"]["last"] != "":
                        game["situation"]["lastPlay"] = gameData["pbp"]["last"]

                    # Mlb leaves "dangling" data between innings
                    # (Mid/End), such as the b/s/o, batter, pticher
                    # until the next inning starts (is in the
                    # Top/Bot). Between innings, I want b/s/o set to 0
                    # and I want to peek ahead to the upcoming batter
                    # and pitcher
                    if game["inning"]["part"] in ("Top", "Bot"):
                        game["situation"]["balls"]   = int(gameData["status"]["b"])
                        game["situation"]["strikes"] = int(gameData["status"]["s"])
                        game["situation"]["outs"]    = int(gameData["status"]["o"])

                        if "runner_on_1b" in gameData["runners_on_base"]:
                            game["situation"]["runners"].append(gameData["runners_on_base"]["runner_on_1b"]["name_display_roster"])
                        else:
                            game["situation"]["runners"].append("")

                        if "runner_on_2b" in gameData["runners_on_base"]:
                            game["situation"]["runners"].append(gameData["runners_on_base"]["runner_on_2b"]["name_display_roster"])
                        else:
                            game["situation"]["runners"].append("")

                        if "runner_on_3b" in gameData["runners_on_base"]:
                            game["situation"]["runners"].append(gameData["runners_on_base"]["runner_on_3b"]["name_display_roster"])
                        else:
                            game["situation"]["runners"].append("")


                            
                    # Inning is in Mid/End, peek ahead and put that
                    # data as the situation
                    else:
                        game["situation"]["batter"]["name"] = gameData["due_up_batter"]["name_display_roster"]
                        game["situation"]["batter"]["avg"]  = gameData["due_up_batter"]["avg"]
                        
                        game["situation"]["pitcher"]["name"] = gameData["opposing_pitcher"]["name_display_roster"]
                        game["situation"]["pitcher"]["era"]  = gameData["opposing_pitcher"]["era"]
                        
                        game["situation"]["balls"]   = 0
                        game["situation"]["strikes"] = 0
                        game["situation"]["outs"]    = 0
                        game["situation"]["runners"].append("")
                        game["situation"]["runners"].append("")
                        game["situation"]["runners"].append("")

                    

                # Add pitcher information for finished games.  This
                # includes winning, losing, and saving pitcher, and
                # their relevant updated stats (wins, losses, saves,
                # save opportunities).
                if game["status"] == "Post":
                    game["pitcherResults"] = {}
                    game["pitcherResults"]["win"]  = {}
                    game["pitcherResults"]["loss"] = {}
                    
                    game["pitcherResults"]["win"]["name"]          = gameData["winning_pitcher"]["name_display_roster"]
                    game["pitcherResults"]["win"]["updatedWins"]   = gameData["winning_pitcher"]["wins"]
                    game["pitcherResults"]["win"]["updatedLosses"] = gameData["winning_pitcher"]["losses"]

                    game["pitcherResults"]["loss"]["name"]          = gameData["losing_pitcher"]["name_display_roster"]
                    game["pitcherResults"]["loss"]["updatedWins"]   = gameData["losing_pitcher"]["wins"]
                    game["pitcherResults"]["loss"]["updatedLosses"] = gameData["losing_pitcher"]["losses"]

                    if gameData["save_pitcher"]["name_display_roster"] != "":
                        game["pitcherResults"]["save"] = {}
                        game["pitcherResults"]["save"]["name"] = gameData["save_pitcher"]["name_display_roster"]
                        game["pitcherResults"]["save"]["updatedSaves"] = gameData["save_pitcher"]["saves"]
                        game["pitcherResults"]["save"]["updatedSaveOpportunities"] = gameData["save_pitcher"]["svo"]


                # Add score by inning for home and away teams. Fill
                # not-yet-completed innings with '-', and unnecessary
                # bottom of the last inning with 'X'
                if game["status"] in ("Live", "Post"):
                    game["away"]["hits"]   = gameData["linescore"]["h"]["away"]
                    game["home"]["hits"]   = gameData["linescore"]["h"]["home"]
                    game["away"]["runs"]   = gameData["linescore"]["r"]["away"]
                    game["home"]["runs"]   = gameData["linescore"]["r"]["home"]
                    game["away"]["errors"] = gameData["linescore"]["e"]["away"]
                    game["home"]["errors"] = gameData["linescore"]["e"]["home"]

                    awayScoreByInning = []
                    homeScoreByInning = []

                    # If in first inning, linescore->inning directly
                    # describes first inning.  Otherwise
                    # linescore->inning is an array, with each entry
                    # describing an inning. Dumb... but I need to work
                    # around it.
                    if type(gameData["linescore"]["inning"]) is list:
                        inningArray = gameData["linescore"]["inning"]
                    elif type(gameData["linescore"]["inning"]) is dict:
                        inningArray = []
                        inningArray.append(gameData["linescore"]["inning"])
                    else:
                        raise Exception('''Unexpected type of game["linescore"]["inning"]: ''' + str(type(gameData["linescore"]["inning"])))
                    
                    for inning in inningArray:
                        # Inning is live-- I (think) string is only
                        # empty during live inning with no runs
                        # yet. So let's just insert 0.
                        if inning["away"] == "":
                            awayScoreByInning.append("0")
                        else:
                            awayScoreByInning.append(inning["away"])

                        if "home" in inning:
                            if inning["home"] == "":
                                homeScoreByInning.append("0")
                            else:
                                homeScoreByInning.append(inning["home"])
                                
                        elif game["status"] == "Post":
                            # Should only occur in inning 9 or beyond
                            homeScoreByInning.append("X")
                            # Else we leave blank, and autofill in with - below

                    # Pad unplayed innings with dashes
                    while len(awayScoreByInning) < 9:
                        awayScoreByInning.append("-")

                    # In extras, this length may be > 9 but still less
                    # than the number of innings the away team has
                    # played, so check against that number as well.
                    while len(homeScoreByInning) < 9 or len(homeScoreByInning) < len(awayScoreByInning):
                        homeScoreByInning.append("-")
                        
                    game["away"]["scoreByInning"] = awayScoreByInning
                    game["home"]["scoreByInning"] = homeScoreByInning
                
                # Breaking out of looping over all games. Since our
                # game was found and the data was filled out, we
                # shouldn't be able to find another game with our team
                # name.
                #
                # TODO: Look at the API output when there is a
                # double-header... see what the info looks like and
                # figure out how we handle that. We might have to
                # _not_ break out of the loop and figure out which
                # game(s) are active, and which to display ?
                break

        return game


    def getTeamRecord(self, team):
        team = self.getTeamNick(team)
        
        if team is None:
            raise ValueError("Invalid team name.")

        html = urlopen(self.standingsScrapeTarget, timeout=5)
        
        soup = BeautifulSoup(html, "lxml")

        if(team == "WAS"):
            team = "WSH" # ESPN site uses WSH

        tags = soup.find("abbr", text=team)
        row = tags.find_parent(class_ = "standings-row")
        columns = row.find_all("td")

        wins = int(columns[1].string)
        losses = int(columns[2].string)
        
        return wins, losses
        
    def getDivisionStandings(self, divisionAbbrev):
        wildCardQuery = False
        
        if type(divisionAbbrev) is not str:
            raise TypeError("Division name must be a string.")

        divisionAbbrev = self.getDivisionNick(divisionAbbrev)
        
        if divisionAbbrev is None:
            raise ValueError("Invalid division name.")

        if divisionAbbrev[0:2] == "AL":
            league = "American League"
        else:
            league = "National League"
                
        if divisionAbbrev[-2:] == "WC":
            wildCardQuery = True
            target = self.wildcardStandingsScrapeTarget
            division = ""
            
        else:
            target = self.standingsScrapeTarget

            if divisionAbbrev[2] == "W":
                division = "West"
            elif divisionAbbrev[2] == "C":
                division = "Central"
            else:
                division = "East"

        html = urlopen(target, timeout=5)
        
        soup = BeautifulSoup(html, "lxml")

        tableHeader = soup.find(class_="long-caption", text=league).parent
        table = tableHeader.find_next_sibling(class_="responsive-table-wrap")
        divisionHeader = table.find("span", text=division)

        divisionHeader = divisionHeader.find_parent(class_="standings-categories")
        rowsToGet = (12 if wildCardQuery else 5)
        
        divisionRows = divisionHeader.find_next_siblings(class_="standings-row", limit=rowsToGet)

        standings = []

        for row in divisionRows:
            entry = {}

            # get team nick should convert any different abbreviations to our
            # standard set
            entry["name"] = self.getTeamNick(str(row.find("abbr").string))

            columns = row.find_all("td")
            entry["wins"] = int(columns[1].string)
            entry["losses"] = int(columns[2].string)

            gamesBackString = columns[4].string

            if gamesBackString[0] == "+":
                entry["gb"] = -float(gamesBackString[1:])
            elif gamesBackString[0] == "-":
                entry["gb"] = float(0)
            else:
                entry["gb"] = float(gamesBackString)

            standings.append(entry)

        return standings

    def getTeamNick(self, teamName):
        '''Returns the 2 or 3 letter nickname of the team.

        Args: 
        teamName (str): The name of the team (not including
        city). Some alternate names are recognized too, such
        as "Cards" or "Buccos". Capitalization does not matter

        Returns:
        string: The 2 or 3 letter nickname of the team, or
        None if the team is not found.'''

        teamName = teamName.upper()

        if teamName in self.validTeams:
            return teamName
        
        if teamName not in self.teamNames:
            return None
        else:
            return self.teamNames[teamName]

    def getDivisionNick(self, divisionName):
        '''Returns the 3 or 4 letter nickname of the division.

        Args:
        divisionName (str): The name of the division. Accepts
        many forms, such as "NL Central", "National League
        Central", "National Central". Capitalization does not
        matter.

        Returns:
        string: The 3 or 4 letter nickname of the division, or
        None if the team is not found.'''

        if type(divisionName) is not str:
            raise TypeError("Division name must be a string.")

        divisionName = divisionName.upper()

        if divisionName in self.validDivisions:
            return divisionName
        
        if divisionName not in self.divisionNames:
            return None
        else:
            return self.divisionNames[divisionName]


    def initializeTeamsAndDivisions(self):
        self.validTeams = []
        self.validTeams.append("ARI")
        self.validTeams.append("ATL")
        self.validTeams.append("BAL")
        self.validTeams.append("BOS")
        self.validTeams.append("CHC")
        self.validTeams.append("CHW")
        self.validTeams.append("CIN")
        self.validTeams.append("CLE")
        self.validTeams.append("COL")
        self.validTeams.append("DET")
        self.validTeams.append("HOU")
        self.validTeams.append("KC")
        self.validTeams.append("LAA")
        self.validTeams.append("LAD")
        self.validTeams.append("MIA")
        self.validTeams.append("MIL")
        self.validTeams.append("MIN")
        self.validTeams.append("NYM")
        self.validTeams.append("NYY")
        self.validTeams.append("OAK")
        self.validTeams.append("PHI")
        self.validTeams.append("PIT")
        self.validTeams.append("SD")
        self.validTeams.append("SEA")
        self.validTeams.append("SF")
        self.validTeams.append("STL")
        self.validTeams.append("TB")
        self.validTeams.append("TEX")
        self.validTeams.append("TOR")
        self.validTeams.append("WSH")

        for team in self.validTeams:
            assert len(team) == 2 or len(team) == 3

            self.validDivisions = []
        self.validDivisions.append("ALW")
        self.validDivisions.append("ALC")
        self.validDivisions.append("ALE")
        self.validDivisions.append("NLW")
        self.validDivisions.append("NLC")
        self.validDivisions.append("NLE")

        # NOTE: These are not "true" divisions, but they may be passed
        # to the getDivisionStandings(..) method to return the
        # wild-card race standings, which can be displayed the same
        # way as normal divisions.
        self.validDivisions.append("ALWC")
        self.validDivisions.append("NLWC")

        # Names and nicknames that map to the corresponding 2 or 3
        # letter codes. All input to methods get transformed to the
        # codes for uniformity.
        self.teamNames = {}
        self.teamNames["DIAMONDBACKS"]       = "ARI"
        self.teamNames["DIAMOND BACKS"]      = "ARI"
        self.teamNames["DBACKS"]             = "ARI"
        self.teamNames["D-BACKS"]            = "ARI"
        self.teamNames["BRAVES"]             = "ATL"
        self.teamNames["ORIOLES"]            = "BAL"
        self.teamNames["RED SOX"]            = "BOS"
        self.teamNames["REDSOX"]             = "BOS"
        self.teamNames["CUBS"]               = "CHC"
        self.teamNames["WHITESOX"]           = "CHW"
        self.teamNames["WHITE SOX"]          = "CHW"
        self.teamNames["REDS"]               = "CIN"
        self.teamNames["INDIANS"]            = "CLE"
        self.teamNames["TRIBE"]              = "CLE"
        self.teamNames["ROCKIES"]            = "COL"
        self.teamNames["TIGERS"]             = "DET"
        self.teamNames["ASTROS"]             = "HOU"
        self.teamNames["ROYALS"]             = "KC"
        self.teamNames["ANGELS"]             = "LAA"
        self.teamNames["DODGERS"]            = "LAD"
        self.teamNames["MARLINS"]            = "MIA"
        self.teamNames["BREWERS"]            = "MIL"
        self.teamNames["TWINS"]              = "MIN"
        self.teamNames["METS"]               = "NYM"
        self.teamNames["YANKEES"]            = "NYY"
        self.teamNames["ATHLETICS"]          = "OAK"
        self.teamNames["A'S"]                = "OAK"
        self.teamNames["AS"]                 = "OAK"
        self.teamNames["PHILLIES"]           = "PHI"
        self.teamNames["PIRATES"]            = "PIT"
        self.teamNames["BUCS"]               = "PIT"
        self.teamNames["BUCCOS"]             = "PIT"
        self.teamNames["PADRES"]             = "SD"
        self.teamNames["MARINERS"]           = "SEA"
        self.teamNames["GIANTS"]             = "SF"
        self.teamNames["CARDINALS"]          = "STL"
        self.teamNames["CARDS"]              = "STL"
        self.teamNames["REDBIRDS"]           = "STL"
        self.teamNames["RAYS"]               = "TB"
        self.teamNames["DEVIL RAYS"]         = "TB"
        self.teamNames["DEVILRAYS"]          = "TB"
        self.teamNames["RANGERS"]            = "TEX"
        self.teamNames["BLUE JAYS"]          = "TOR"
        self.teamNames["BLUEJAYS"]           = "TOR"
        self.teamNames["JAYS"]               = "TOR"
        self.teamNames["NATIONALS"]          = "WSH"
        self.teamNames["NATS"]               = "WSH"


        for key, value in self.teamNames.items():
            try:
                assert value in self.validTeams
            except AssertionError as e:
                e.args += (key,)
                raise

        # Valid names for the various divisions, that get mapped to
        # the codes that the methods involving divisions operate on.
        self.divisionNames = {}
        self.divisionNames["AL WEST"] = "ALW"
        self.divisionNames["AMERICAN LEAGUE WEST"] = "ALW"
        self.divisionNames["AMERICAN WEST"] = "ALW"
        self.divisionNames["AL CENTRAL"] = "ALC"
        self.divisionNames["AMERICAN LEAGUE CENTRAL"] = "ALC"
        self.divisionNames["AMERICAN CENTRAL"] = "ALC"
        self.divisionNames["AL EAST"] = "ALE"
        self.divisionNames["AMERICAN LEAGUE EAST"] = "ALE"
        self.divisionNames["AMERICAN EAST"] = "ALE"

        self.divisionNames["NL WEST"] = "NLW"
        self.divisionNames["NATIONAL LEAGUE WEST"] = "NLW"
        self.divisionNames["NATIONAL WEST"] = "NLW"
        self.divisionNames["NL CENTRAL"] = "NLC"
        self.divisionNames["NATIONAL LEAGUE CENTRAL"] = "NLC"
        self.divisionNames["NATIONAL CENTRAL"] = "NLC"
        self.divisionNames["NL EAST"] = "NLE"
        self.divisionNames["NATIONAL LEAGUE EAST"] = "NLE"
        self.divisionNames["NATIONAL EAST"] = "NLE"

        self.divisionNames["AL WC"] = "ALWC"
        self.divisionNames["AL WILDCARD"] = "ALWC"
        self.divisionNames["AL WILD CARD"] = "ALWC"
        self.divisionNames["AL WILD-CARD"] = "ALWC"             
        self.divisionNames["AMERICAN LEAGUE WC"] = "ALWC"
        self.divisionNames["AMERICAN LEAGUE WILDCARD"] = "ALWC"
        self.divisionNames["AMERICAN LEAGUE WILD CARD"] = "ALWC"
        self.divisionNames["AMERICAN LEAGUE WILD-CARD"] = "ALWC"     
        self.divisionNames["AMERICAN WC"] = "ALWC"
        self.divisionNames["AMERICAN WILDCARD"] = "ALWC"
        self.divisionNames["AMERICAN WILD CARD"] = "ALWC"
        self.divisionNames["AMERICAN WILD-CARD"] = "ALWC"

        self.divisionNames["NL WC"] = "NLWC"
        self.divisionNames["NL WILDCARD"] = "NLWC"
        self.divisionNames["NL WILD CARD"] = "NLWC"
        self.divisionNames["NL WILD-CARD"] = "NLWC"               
        self.divisionNames["NATIONAL LEAGUE WC"] = "NLWC"
        self.divisionNames["NATIONAL LEAGUE WILDCARD"] = "NLWC"
        self.divisionNames["NATIONAL LEAGUE WILD CARD"] = "NLWC"
        self.divisionNames["NATIONAL LEAGUE WILD-CARD"] = "NLWC"     
        self.divisionNames["NATIONAL WC"] = "NLWC"
        self.divisionNames["NATIONAL WILDCARD"] = "NLWC"
        self.divisionNames["NATIONAL WILD CARD"] = "NLWC"
        self.divisionNames["NATIONAL WILD-CARD"] = "NLWC"

        for key, value in self.divisionNames.items():
            try:
                assert value in self.validDivisions
            except AssertionError as e:
                e.args += (key,)
                raise
