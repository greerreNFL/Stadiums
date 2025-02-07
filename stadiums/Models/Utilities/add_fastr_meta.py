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
    ## create a map of stadium ids and their meta for faster lookups ##
    meta_map = general_meta.set_index('stadium_id').to_dict(orient='index')
    ## add the meta to the stadium collection ##
    for stadium_id, stadium in stadium_collection.stadiums.items():
        ## add the meta ##
        for field in ['first_game_date', 'last_game_date', 'surface_type', 'roof_type']:
            setattr(stadium, field, meta_map[stadium_id][field])