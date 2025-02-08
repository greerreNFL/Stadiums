# NFL Stadiums Dataset
NFL stadium metadata and analytics for joining with nflfastR datasets.

## Data Files
### Stadium Data (`data/stadiums.csv`)
Metadata for all NFL stadiums:
- PFR ID is the unique identifier for each stadium, with stadium name, turf, roof, etc populated from nflfastR's games data
- Location data (latitude, longitude, altitude, heading, timezone) are manullay populated using Google Earth
- Wikipedia URL is manually set and then scraped to add additional metadata

### Team Stadium Mappings (`data/team_stadiums.csv`)
Maps teams to their home stadiums with:
- Combines the Stadium entity in the /stadiums.csv with each team that has played a home game in that stadium
- The is_current boolean flag is set based on the most common stadium for the team in the most recent season of data available
- This file contains the team abbreviation used by both nfelo and nflfastR along with stadium ID as a primary key for each record
- Stadium metadata from /stadiums.csv is already joined
- A snapshot of the last record in the rolling HFA data is also joined

### Rolling Analytics (`data/rolling_team_analytics.csv` & `data/rolling_league_analytics.csv`) 
Rolling win/loss records and home field advantage metrics calculated using Elo ratings:
- Basic win/loss and margin of victory metrics are provided on a rolling basis by week for 16, 80, and all-time windows
- Windows are set by league weeks elapsed, not home games played (ie a team may only have 8 games captured in their 16 game window)
- To account for team quality and opponent quality, HFA is calcualted using an Elo model. For rating accuracy, the model uses pre-season priors from betting market win totals and accounts for QB injuries uing the QB Elo dataset.
- However, the model does not account for location (expected margin of victory assumes a neutral site). Thus, homefield advantage is calculated as the error between the actual and expected home margin of victory

### Assets
Stadium satellite images are stored in `stadiums/Assets/SatelliteImg/` with filenames matching stadium IDs.

## Data Sources
- Game data from [Lee Sharpe's nfldata](https://github.com/nflverse/nfldata/blob/master/data/games.csv) and is used for determining the set of stadiums that have hosted a game, schedules, home/away team, margin of victory, win/loss, field type, and roof type.
- Location data is manually set using Google Earth.
- Stadium details from Wikipedia

## Updates
Stadium entities will be automatically created when new stadiums hit the nfldata/games.csv dataset, but will require manual setting of location data and wikipedia links for the rest of the data to populate


