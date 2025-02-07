## built-in ##
import pathlib

## external ##
import pandas as pd
import numpy

## internal ##
## from ..DataLoader import data
from .Elo import EloModel

def gen_hfa():
    '''
    Generates rolling HFA metrics for each team and stadium using a
    simple elo model
    '''
    ## generate records ##
    elo = EloModel()
    elo.run()
    ## create a df from the records ##
    df = pd.DataFrame(elo.recs)
    df = df.sort_values(
        by=['team', 'stadium', 'season', 'week'],
        ascending=[True, True, True, True]
    ).reset_index(drop=True)
    ## set games played ##
    df['games_played'] = df.groupby(['team', 'stadium']).cumcount() + 1
    ## set wins, losses, and ties ##
    df['win'] = numpy.where(df['mov'] > 0, 1, 0)
    df['loss'] = numpy.where(df['mov'] < 0, 1, 0)
    df['tie'] = numpy.where(df['mov'] == 0, 1, 0)
    ## create rolling metrics ##
    windows = [16,80,'all']
    ## for windows, calc across all weeks, not just the home games ##
    ## to do this, each stadium needs a row for each possible week ##
    ## get all possible weeks ##
    weeks = df[['season', 'week']].drop_duplicates().reset_index(drop=True)
    ## add unique team/stadium pairs ##
    weeks = weeks.merge(
        df[['team', 'stadium']].drop_duplicates().reset_index(drop=True),
        how='cross'
    )
    ## add week and season to df ##
    df = weeks.merge(
        df,
        on=['season', 'week', 'team', 'stadium'],
        how='left'
    )
    ## re-sort ##
    df = df.sort_values(
        by=['team', 'stadium', 'season', 'week' ],
        ascending=[True, True, True, True]
    ).reset_index(drop=True)
    ## remove records played between the first and last home game of the stadium ##
    ## by finding the row number of the first and last home game of the stadium ##
    ## and keep all rows between them ##
    ## create temp row number for each rec ##
    df['row_num'] = range(len(df))
    df['row_num_played'] = numpy.where(~pd.isna(df['mov']), df['row_num'], numpy.nan)
    ## filter ##
    df = df[
        (df['row_num'] >= df.groupby(['team', 'stadium'])['row_num_played'].transform(lambda x: x.min())) &
        (df['row_num'] <= df.groupby(['team', 'stadium'])['row_num_played'].transform(lambda x: x.max()))
    ].copy()
    ## remove temp row number ##
    df = df.drop(columns=['row_num', 'row_num_played'])
    for window in windows:
        ## handle all case ##
        if window == 'all':
            df['wins_all_time'] = df.groupby(['team', 'stadium'])['win'].transform(lambda x: x.expanding().sum())
            df['losses_all_time'] = df.groupby(['team', 'stadium'])['loss'].transform(lambda x: x.expanding().sum())
            df['ties_all_time'] = df.groupby(['team', 'stadium'])['tie'].transform(lambda x: x.expanding().sum())
            df['mov_all_time'] = numpy.round(df.groupby(['team', 'stadium'])['mov'].transform(lambda x: x.expanding().mean()), 3)
            df['hfa_all_time'] = numpy.round(df.groupby(['team', 'stadium'])['error'].transform(lambda x: x.expanding().mean()), 3)
        else:
            df['wins_l{0}'.format(window)] = df.groupby(['team', 'stadium'])['win'].transform(lambda x: x.rolling(window, min_periods=1).sum())
            df['losses_l{0}'.format(window)] = df.groupby(['team', 'stadium'])['loss'].transform(lambda x: x.rolling(window, min_periods=1).sum())
            df['ties_l{0}'.format(window)] = df.groupby(['team', 'stadium'])['tie'].transform(lambda x: x.rolling(window, min_periods=1).sum())
            df['mov_l{0}'.format(window)] = numpy.round(df.groupby(['team', 'stadium'])['mov'].transform(lambda x: x.rolling(window, min_periods=1).mean()), 3)
            df['hfa_l{0}'.format(window)] = numpy.round(df.groupby(['team', 'stadium'])['error'].transform(lambda x: x.rolling(window, min_periods=1).mean()), 3)
    ## calculate for league ##
    league = pd.DataFrame(elo.recs)
    league = league.sort_values(
        by=['season', 'week'],
        ascending=[True, True]
    ).reset_index(drop=True)
    league['win'] = numpy.where(league['mov'] > 0, 1, 0)
    league['loss'] = numpy.where(league['mov'] < 0, 1, 0)
    league['tie'] = numpy.where(league['mov'] == 0, 1, 0)
    ## translate league df in a unique on week and season ##
    ## so it can be joined and compared on an apples to apples basis ##
    league = league.groupby(['season', 'week']).agg(
        win = ('win', 'sum'),
        loss = ('loss', 'sum'),
        tie = ('tie', 'sum'),
        mov = ('mov', 'mean'),
        error = ('error', 'mean')
    ).reset_index()
    league['mov'] = numpy.round(league['mov'], 3)
    league['error'] = numpy.round(league['error'], 3)
    ## calculate rolling metrics ##
    for window in windows:
        if window == 'all':
            league['wins_all_time'] = league['win'].expanding().sum()
            league['losses_all_time'] = league['loss'].expanding().sum()
            league['ties_all_time'] = league['tie'].expanding().sum()
            league['mov_all_time'] = numpy.round(league['mov'].expanding().mean(), 3)
            league['hfa_all_time'] = numpy.round(league['error'].expanding().mean(), 3)
        else:
            league['wins_l{0}'.format(window)] = league['win'].rolling(window).sum()
            league['losses_l{0}'.format(window)] = league['loss'].rolling(window).sum()
            league['ties_l{0}'.format(window)] = league['tie'].rolling(window).sum()
            league['mov_l{0}'.format(window)] = numpy.round(league['mov'].rolling(window).mean(), 3)
            league['hfa_l{0}'.format(window)] = numpy.round(league['error'].rolling(window).mean(), 3)
    ## return df and league, but league is 
    return df, league

def calc_analytics():
    '''
    Generates analytics files for the stadiums project
    '''
    ## output loc ##
    output_loc = '{0}/data'.format(
        pathlib.Path(__file__).parent.parent.parent.resolve()
    )
    team_hfa, league_hfa = gen_hfa()
    ## save ##
    team_hfa.to_csv('{0}/rolling_team_hfa.csv'.format(output_loc), index=False)
    league_hfa.to_csv('{0}/rolling_league_hfa.csv'.format(output_loc), index=False)
    ## return ##
    return team_hfa, league_hfa
