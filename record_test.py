from scrape.mlb_scraper_mlb_api import MlbScraperMlbApi

mlb = MlbScraperMlbApi()

wins, losses = mlb.getTeamRecord("WAS");

print("Record: " + str(wins) + "-" + str(losses))
