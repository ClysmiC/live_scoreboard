import sys
import os
import datetime
import time

from scrape.mlb_scraper_mlb_api import MlbScraperMlbApi

mlb = MlbScraperMlbApi()

argError = False
date = None
team = None

if len(sys.argv) > 3:
    argError = True

if len(sys.argv) > 1:
    sys.argv[1] = sys.argv[1].replace("-", "")
    if sys.argv[1].isdigit():
        try:
            date = datetime.date(int(sys.argv[1][0:4]), int(sys.argv[1][4:6]), int(sys.argv[1][6:8]))
        except:
            argError = True
    else:
        team = sys.argv[1]
        
if len(sys.argv) > 2:
    sys.argv[2] = sys.argv[2].replace("-", "")
    if sys.argv[2].isdigit():
        if date is None:
            try:
                date = datetime.date(int(sys.argv[2][0:4]), int(sys.argv[2][4:6]), int(sys.argv[2][6:8]))
            except:
                argError = True
        else:
            argError = True
    else:
        if team is None:
            team = sys.argv[2]
        else:
            argError = True
    
if argError:
    print("Usage:")
    print("\tmlb_scoreboard.py [team] [date]")
    print("Examples:")
    print("\tmlb_scoreboard.py")
    print("\tmlb_scoreboard.py STL")
    print("\tmlb_scoreboard.py 2016-07-17")
    print("\tmlb_scoreboard.py STL 2016-07-17")
    print("\tmlb_scoreboard.py Cardinals 20160717")
    exit()
    
if team is None:
    team = raw_input("\nEnter team name or initials (e.g., \"STL\"): ")

if date is None:
    date = raw_input("\nEnter date in following form: \"2016-07-17\n(Dashes optional, leave blank for current date): ")
    date = date.replace("-", "")
    if len(date) == 0:
        # mlb_scraper defaults to today when date is omitted or None
        date = None
    else:
        try:
            date = datetime.date(int(date[0:4]), int(date[4:6]), int(date[6:8]))
        except:
            print("Invalid date. Exiting...")
            exit()

while(True):
    try:
        game = mlb.getGameInfo(team, date)
    except Exception as e:
        print("Error. Perhaps you typed an invalid team name?")
        raise e # NOTE: only for dev / debugging purposes do we re-raise
                # error

    if type(game) is int and game == -1:
        print("Error opening url. Check internet connection.")
    else:
        print("")

        if(game["status"] == "NoGame"):
            print("No game today.")

        elif(game["status"] == "Pre"):
            print(game["away"]["name"] + " vs. " + game["home"]["name"])
            print("Game Time: " + "{:02d}:{:02d}".format(game["startTime"]["time"].hour, game["startTime"]["time"].hour) + " " + game["startTime"]["timeZone"])
            print("")
            print("Probable Starters")
            print(game["away"]["name"] + ": " + game["away"]["starter"]["name"] + " ({:s}-{:s}, {:s})".format(game["away"]["starter"]["wins"], game["away"]["starter"]["losses"], game["away"]["starter"]["era"]))
            print(game["home"]["name"] + ": " + game["home"]["starter"]["name"] + " ({:s}-{:s}, {:s})".format(game["home"]["starter"]["wins"], game["home"]["starter"]["losses"], game["home"]["starter"]["era"]))

        else:
            if(game["status"] == "Live"):
                print("--" + game["inning"]["part"].name + " " + game["inning"]["number"] + "--")
            if(game["status"] == "Post"):
                print("--FINAL--")

            print(game["away"]["name"] + ": " + game["away"]["runs"])
            print(game["home"]["name"] + ": " + game["home"]["runs"])

            if(game["status"] == "Post"):
                print("")
                print("W: " + game["pitcherResults"]["win"]["name"] + " ({:s}-{:s})".format(game["pitcherResults"]["win"]["updatedWins"], game["pitcherResults"]["win"]["updatedLosses"]))

                print("L: " + game["pitcherResults"]["loss"]["name"] + " ({:s}-{:s})".format(game["pitcherResults"]["loss"]["updatedWins"], game["pitcherResults"]["loss"]["updatedLosses"]))

                if("save" in game["pitcherResults"]):
                    print("S: " + game["pitcherResults"]["save"]["name"] + " ({:s})".format(game["pitcherResults"]["save"]["updatedSaves"]))

            print("")
            inningString    = "         "
            underlineString = "---------------------"

            for i in range(1, max(10, len(game["away"]["scoreByInning"]) + 1)):
                inningString += "{:2d}".format(i) + "   "
                underlineString += "-----"

            inningString += " R    H    E"

            print(inningString)
            print(underlineString)

            if game["status"] == "Live":
                if game["inning"]["part"] in (InningPart.Top, InningPart.End):
                    awayString = " * "
                    homeString = "   "
                else:
                    awayString = "   "
                    homeString = " * "
            else:
                awayString = "   "
                homeString = "   "

            awayString += game["away"]["name"] + (" " * (3 - len(game["away"]["name"])))
            for inningScore in game["away"]["scoreByInning"]:
                awayString += (" " * (5 - len(inningScore))) + inningScore

            awayString += " |" + (" " * (3 - len(game["away"]["runs"]))) + game["away"]["runs"]
            awayString += " |" + (" " * (3 - len(game["away"]["hits"]))) + game["away"]["hits"]
            awayString += " |" + (" " * (3 - len(game["away"]["errors"]))) + game["away"]["errors"]

            homeString += game["home"]["name"] + (" " * (3 - len(game["home"]["name"])))
            for inningScore in game["home"]["scoreByInning"]:
                homeString += (" " * (5 - len(inningScore))) + inningScore

            homeString += " |" + (" " * (3 - len(game["home"]["runs"]))) + game["home"]["runs"]
            homeString += " |" + (" " * (3 - len(game["home"]["hits"]))) + game["home"]["hits"]
            homeString += " |" + (" " * (3 - len(game["home"]["errors"]))) + game["home"]["errors"]

            print(awayString)
            print(homeString)

            if game["status"] == "Live":
                # Example situation output
                #
                # B: ***         o          P: Wacha
                # S: *         *   *       AB: Cruz
                # O: **          o            

                numBalls = int(game["situation"]["balls"])
                numStrikes = int(game["situation"]["strikes"])
                numOuts = int(game["situation"]["outs"])
                runners = game["situation"]["runners"]

                string1 = "B: " + ("*" * numBalls) + (" " * (10 - numBalls))
                string1 += "  "
                string1 += ("o" if runners[1] == "" else "*")
                string1 += "          P: " + game["situation"]["pitcher"]["name"] + " ({:s})".format(game["situation"]["pitcher"]["era"])


                string2 = "S: " + ("*" * numStrikes) + (" " * (10 - numStrikes))
                string2 += ("o" if runners[2] == "" else "*")
                string2 += "   "
                string2 += ("o" if runners[0] == "" else "*")
                string2 += "       AB: " + game["situation"]["batter"]["name"] + " ({:s})".format(game["situation"]["batter"]["avg"])

                string3 = "O: " + ("*" * numOuts) + (" " * (10 - numOuts))
                string3 += "  "
                string3 += "o"

                print("")
                print(string1)
                print(string2)
                print(string3)
                if "lastPlay" in game["situation"]:
                   print("")
                   print("Last Play: " + game["situation"]["lastPlay"])

    time.sleep(20)
