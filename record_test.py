from scrape.mlb_scraper_mlb_api import MlbScraperMlbApi

mlb = MlbScraperMlbApi()

wins, losses = mlb.getTeamRecord("STL");

print("Record: " + str(wins) + "-" + str(losses))
