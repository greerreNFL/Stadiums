## built-ins ##
import pathlib
from typing import Optional

## external ##
import pandas as pd
import nfelodcm as dcm

## local ##
from .Models import StadiumCollection

def update_stadiums(
    force_rescrape: bool = False,
    force_reparse: bool = False,
    games: Optional[pd.DataFrame] = None
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
    ## if games were not passed, load using the dcm ##
    if games is None:
        db = dcm.load(['games'])
        games = db['games']
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