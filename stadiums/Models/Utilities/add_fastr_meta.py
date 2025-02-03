## external ##
import pandas as pd
import numpy as numpy

## local ##
from ...DataLoader import data
## from ..StadiumCollection import StadiumCollection
## Note, since StadiumCollection imports this utility, it cant be imported
## here for typing purposes

## field type map ##
field_map = {
    "fieldturf": "Turf",
    "fieldturf ": "Turf",
    "matrixturf": "Turf",
    "sportturf": "Turf",
    "astroturf": "Turf",
    "astroplay": "Turf",
    "a_turf": "Turf",
    "grass": "Grass",
    "dessograss": "Turf"
}
## roof map ##
roof_map = {
    "outdoors": "Outdoors",
    "dome": "Dome",
    "closed": "Retractable",
    "open": "Retractable"
}
## Neutral Sites ##
## list of international stadiums ##
## could make this dynamic in the future based
## on stadiums that only have neutral site games ##
neutral_sites = [
    'FRA00', 'GER00', 'LON00', 'LON01',
    'LON02', 'MEX00', 'SAO00'
]


def add_fastr_meta(stadium_collection):
    '''
    Calculates the fastr meta data (last game, is current, etc) for each stadium
    and add it to a stadium collection

    Parameters:
    * stadium_collection: StadiumCollection - the stadium collection to add the meta data to

    Returns:
    * None
    '''
    ## load the games ##
    games = data.db['games'].copy()
    ## map types ##
    games['surface_type'] = games['surface'].map(field_map).fillna('Turf')
    games['roof_type'] = games['roof'].map(roof_map).fillna('Outdoors')
    ## calculate general meta data ##
    general_meta = games.groupby(['stadium_id']).agg(
        first_game_date=('gameday', 'min'),
        last_game_date=('gameday', 'max'),
        surface_type=('surface_type', 'last'),
        roof_type=('roof_type', 'last')
    ).reset_index()
    ## calculate team X stadium data points ##
    games['home_team_stadium'] = numpy.where(
        (~numpy.isin(games['stadium_id'], neutral_sites)) &
        (games['location'] == 'Home'),
        games['home_team'],
        numpy.nan
    )
    teams = games.groupby(['stadium_id', 'home_team_stadium']).agg(
        games_played=('game_id', 'count'),
        last_game_date=('gameday', 'max')
    ).reset_index()
    ## for each stadium select the team with the most games played and set as primary team ##
    primary = teams.sort_values(
        by=['stadium_id', 'games_played'],
        ascending=[True, False]
    ).groupby('stadium_id').head(1)
    ## for each team, select the stadium with the most recent game as the current stadium ##
    current = teams.sort_values(
        by=['home_team_stadium', 'last_game_date'],
        ascending=[True, False]
    ).groupby('home_team_stadium').head(1)
    current['is_current'] = True
    ## merge data points ##
    ## primary team ##
    meta_final = pd.merge(
        general_meta,
        primary[['stadium_id', 'home_team_stadium']].rename(
            columns={
                'home_team_stadium': 'primary_team'
            }
        ),
        on='stadium_id',
        how='left'
    )
    ## is_current ##
    meta_final = pd.merge(
        meta_final,
        current[['stadium_id', 'home_team_stadium', 'is_current']].rename(
            columns={
                'home_team_stadium': 'primary_team'
            }
        ),
        on=['stadium_id', 'primary_team'],
        how='left'
    )
    ## fill is_current nas with false ##
    meta_final['is_current'] = meta_final['is_current'].fillna(False)
    ## create a map of stadium ids and their meta for faster lookups ##
    meta_map = meta_final.set_index('stadium_id').to_dict(orient='index')
    ## add the meta to the stadium collection ##
    for stadium_id, stadium in stadium_collection.stadiums.items():
        ## add the meta ##
        for field in ['first_game_date', 'last_game_date', 'surface_type', 'roof_type', 'primary_team', 'is_current']:
            setattr(stadium, field, meta_map[stadium_id][field])