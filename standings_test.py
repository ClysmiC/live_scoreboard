from scrape.mlb_scraper_mlb_api import MlbScraperMlbApi

mlb = MlbScraperMlbApi()

standings = mlb.getDivisionStandings(raw_input("Enter division: "));

# Example table with garbage data
#  _____________________________
# |  #  | Team|   W |   L |  GB |
# |=============================|
# |  1. | STL |  90 | 100 |  1.0|
# |  2. | CHI | 100 |  10 |-10.0|
# |  3. | PIT |   3 |   5 |  2.5|
#  -----------------------------

print(" _____________________________")
print("|  #  | Team|   W |   L |  GB |")
print("|=============================|")

for index, team in enumerate(standings):
    positionString = "|" + "{:3d}".format(index + 1) + ". |"
    rowString = positionString

    teamString = "{:>4s}".format(team["name"]) + " |"
    rowString += teamString

    winString = "{:4d}".format(team["wins"]) + " |"
    rowString += winString

    lossString = "{:4d}".format(team["losses"]) + " |"
    rowString += lossString

    gbString = "{:5.1f}".format(team["gb"])
    rowString += gbString + "|"
    
    print(rowString)

print(" -----------------------------")
