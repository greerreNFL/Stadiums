## built-ins ##
import pathlib
from typing import Optional

## external ##
import pandas as pd

## local ##
from .DataLoader import data
from .Models import StadiumCollection
from .Analytics import calc_analytics
def update_stadiums(
    force_rescrape: bool = False,
    force_reparse: bool = False
) -> None:
    '''
    Primary script for updating stadium meta data

    Parameters:
    * force_rescrape: bool - if True, will rescrape wikipedia data even if it already exists
    * games: pd.DataFrame - optionally pass a preloaded games dataframe

    Returns:
    * None
    '''
    ## initialize the stadium collection ##
    stadium_collection = StadiumCollection()
    ## if a local stadiums file exists, load it ##
    stadium_loc = '{0}/data/stadiums.csv'.format(
        pathlib.Path(__file__).parent.parent.resolve()
    )
    ## if a file exists, pre-load the stadium collection
    if pathlib.Path(stadium_loc).exists():
        stadium_collection.populate_from_csv(stadium_loc)
    ## retrieve the games dataframe ##
    games = data.db['games'].copy()
    ## isolate the stadiums from the games ##
    stadiums = games.groupby('stadium_id').tail(1).copy()[[
        'stadium_id', 'stadium'
    ]].rename(columns={
        'stadium': 'stadium_name'
    }).to_dict(orient='records')
    ## update the stadium collection ##
    stadium_collection.extend_from_recs(stadiums)
    ## add fastr meta data ##
    stadium_collection.add_fastr_meta()
    ## update the stadium data ##
    stadium_collection.update_stadium_data(
        force_reparse=force_reparse,
        force_rescrape=force_rescrape
    )
    ## save the stadium collection ##
    stadium_collection.to_csv(stadium_loc)
    ## calculate analytics ##
    calc_analytics()