## built-ins ##
import pathlib

## external ##
import pandas as pd
import numpy

## internal ##
from ..Models import StadiumCollection
from ..DataLoader import data


def fastr_team(df: pd.DataFrame, team_col: str):
    '''
    Utility to change team abbreviations back to the fastr style
    '''
    ## create a base mapping of fastr names that need to change based on ##
    ## current team name used by nfelo ##
    current_map = {
        'OAK': 'LV',
        'LAR': 'LA',
    }
    ## creates maps for each season where there is a different change ##
    ## 2019 was the last year for Oakland, so remove from the map ##
    map_2019 = current_map.copy()
    map_2019.pop('OAK')
    ## 2016 was the last year for SD, so change LAC to SD ##
    map_2016 = map_2019.copy()
    map_2016['LAC'] = 'SD'
    ## 2015 was the last year for STL, so change LAR to STL ##
    map_2015 = map_2016.copy()
    map_2015['LAR'] = 'STL'
    ## apply ##
    df['{0}_fastr'.format(team_col)] = numpy.where(
        df['season'] <= 2015,
        df[team_col].replace(map_2015),
        numpy.where(
            df['season'] <= 2016,
            df[team_col].replace(map_2016),
            numpy.where(
                df['season'] <= 2019,
                df[team_col].replace(map_2019),
                df[team_col].replace(current_map)
            )
        )
    )
    return df['{0}_fastr'.format(team_col)]

def gen_team_stadiums(
    stadium_collection: StadiumCollection,
    analytics: pd.DataFrame
):
    '''
    Creates an aggregated dataframe for each teams home stadium. This is a
    stadium collection with team<>stadium as a composite key vs just stadium.

    Additionally, it adds analytics to the dataframe for record and HFA.
    '''
    ## get unique stadiums ##
    stadium_collection.update_df()
    stadiums = stadium_collection.stadium_df.copy()
    ## get unique team <> game combinations ##
    games = data.db['games'].copy()
    ## add a fastr team column ##
    games['team_fastr'] = fastr_team(games, 'home_team')
    combos = games[
        (games['location'] == 'Home')
    ][[
        'home_team', 'team_fastr', 'stadium_id'
    ]].copy().rename(columns={
        'home_team': 'team',
    }).drop_duplicates()
    ## determine if stadium is current for the team ##
    ## the current stadium is the one where the team has played,
    ## or is scheduled to play the most games in the most recent season
    currents = games[
        (games['location'] == 'Home')
    ].groupby(['season', 'home_team', 'stadium_id']).agg(
        games=('game_id', 'nunique')
    ).reset_index().sort_values(
        by=['season', 'home_team', 'games'],
        ascending=[False, True, False]
    ).groupby(['home_team']).head(1)[[
        'home_team', 'stadium_id'
    ]].copy().rename(columns={
        'home_team': 'team',
    }).drop_duplicates()
    ## add a "True" column for current ##
    currents['is_current'] = True
    ## merge ##
    combos = pd.merge(
        combos,
        currents[['team', 'stadium_id', 'is_current']],
        on=['team', 'stadium_id'],
        how='left'
    )
    ## fill ##
    combos['is_current'] = combos['is_current'].fillna(False)
    ## add stadium metadata ##
    combos = pd.merge(
        combos,
        stadiums,
        on='stadium_id',
        how='left'
    )
    ## add analytics ##
    combos = pd.merge(
        combos.rename(columns={
            'stadium_id': 'stadium'
        }),
        ## snapshot of the most recent analytics record ##
        analytics.groupby(['team', 'stadium']).tail(1).drop(columns=[
            ## remove the data unique to the last game (ie not a rolling snapshot)
            'season', 'week', 'mov', 'expected_mov', 'error',
            'games_played', 'win', 'loss', 'tie'
        ]),
        on=['team', 'stadium'],
        how='left'
    )
    ## return ##
    ## sort and save ##
    combos = combos.sort_values(
        by=['is_current', 'team'],
        ascending=[False, True]
    ).reset_index(drop=True)
    combos.to_csv('{0}/data/team_stadiums.csv'.format(
        pathlib.Path(__file__).parent.parent.parent.resolve()
    ), index=False)
    return combos
