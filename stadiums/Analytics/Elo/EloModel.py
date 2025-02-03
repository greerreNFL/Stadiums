## built-ins ##
import json
import pathlib
import math

## external ##
import pandas as pd

## internal ##
from ...DataLoader import data

class EloModel:
    '''
    Simple Elo model to calculate expected team values for an opponent
    adjusted home field advantage
    '''
    def __init__(self):
        self.loc = pathlib.Path(__file__).parent.resolve()
        ## load conf ##
        self.conf = {}
        with open('{0}/conf.json'.format(self.loc), 'r') as f:
            self.conf = json.load(f)
        self.games = data.db['games'][
            ## played games with a stadium id only ##
            (~pd.isnull(data.db['games']['result'])) &
            (~pd.isnull(data.db['games']['stadium_id']))
        ].copy()
        self.pre_season_ratings = self.gen_ratings_dict(data.db['wt_ratings'].copy())
        self.teams = self.games['home_team'].unique().tolist()
        self.current_elos = self.init_elos()
        self.recs = []

    def init_elos(self):
        '''
        Initialize elos for all teams
        '''
        current_elos = {}
        for team in self.teams:
            current_elos[team] = {
                'elo' : self.conf['elo_init'],
                'last_game_season' : None,
                'last_game_week' : None
            }
        return current_elos

    def gen_ratings_dict(self, ratings):
        '''
        Generate a dictionary of win total ratings for each team/season combo
        for faster lookup
        '''
        ## create a key that combines team and season ##
        ratings['key'] = ratings['team'].astype(str) + ratings['season'].astype(str)
        ## isolate the key and rating, and output to dictionary ##
        return ratings[['key', 'wt_rating_elo']].set_index('key')['wt_rating_elo'].to_dict()

    def get_wt_rating(self, team, season):
        '''
        Get the win total rating for a team/season combo
        '''
        return self.pre_season_ratings.get(
            '{0}{1}'.format(team, season),
            self.conf['elo_init']
        )

    def off_season_reversion(self, team, elo, new_season):
        '''
        Handle the off season reversion of elo ratings
        '''
        ## get the win total rating for the season ##
        wt = self.get_wt_rating(team, new_season)
        ## get normalized weights for league average and wt ratings ##
        wt_weight = self.conf['wt_weight']
        league_weight = self.conf['reversion']
        current_weight = 1 - (wt_weight + league_weight)
        combined_weight = wt_weight + league_weight + current_weight
        wt_weight = wt_weight / combined_weight
        league_weight = league_weight / combined_weight
        current_weight = current_weight / combined_weight
        ## apply reversion ##
        return (
            wt_weight * wt +
            league_weight * self.conf['elo_init'] +
            current_weight * elo
        )

    def project(self, row):
        '''
        Project the result of a game. Takes a row from the games table and returns
        the row with an expected win probability attached
        '''
        ## create local variables for home and away for easier referencing ##
        home = row['home_team']
        away = row['away_team']
        ## get current elos for both ##
        home_elo = self.current_elos[home]['elo']
        away_elo = self.current_elos[away]['elo']
        ## handle off season reversion ##
        ## home ##
        if row['season'] != self.current_elos[home]['last_game_season']:
            home_elo = self.off_season_reversion(home, home_elo, row['season'])
        ## away ##
        if row['season'] != self.current_elos[away]['last_game_season']:
            away_elo = self.off_season_reversion(away, away_elo, row['season'])
        ## calc and elo dif ##
        elo_dif = (
            (home_elo + row['home_qb_adj']) -
            (away_elo + row['away_qb_adj'])
        )
        ## calc expected win probability ##
        wp = 1 / (
            1 + math.pow(
                10,
                -elo_dif / self.conf['z']
            )
        )
        ## get an expected margin ##
        margin = elo_dif / 25
        ## add elos, wp, and margin ##
        row['home_elo'] = home_elo
        row['away_elo'] = away_elo
        row['elo_dif'] = elo_dif
        row['home_wp'] = wp
        row['home_expected_margin'] = margin
        ## return the row ##
        return row
    
    def process(self, row):
        '''
        Process a row from a game that has been played ##
        '''
        ## get the projection error ##
        ## this represents how much better the home team did relative to
        ## an expected margin that does not account for home field advantage
        error = row['result'] - row['home_expected_margin']
        ## add to recs if non-neutral site ##
        if (row['location'] == 'Home') and (row['game_type'] == 'REG'):
            self.recs.append({
                'season' : row['season'],
                'week' : row['week'],
                'team' : row['home_team'],
                'stadium' : row['stadium_id'],
                'mov' : row['result'],
                'expected_mov' : round(row['home_expected_margin'], 3),
                'error' : round(error, 3)
            })
        ## update elos ##
        ## absolute point differential ##
        pd = abs(row['result'])
        ## home result expressed as a binary, with 0.5 being a tie ##
        home_result = 1.0 if row['result'] > 0 else 0 if row['result'] < 0 else 0.5
        ## MoV multiplier adjusted for autocorrelation ##
        mult = (
            math.log(max(pd, 1) + 1.0) *
            (self.conf['b'] / (
                ## if tie, then 1 ##
                1.0 if home_result == 0.5
                ## else, scale by expectation of a larger MoV, as defined by elo difference ##
                else (
                    ## set direction of multiplier based on win/loss ##
                    (
                        row['elo_dif'] if home_result == 1.0
                        else -row['elo_dif']
                    ) *
                    0.001 +
                    self.conf['b']
                )
            ))
        )
        ## create the home shift ##
        home_shift = (self.conf['k'] * mult) * (home_result - row['home_wp'])
        away_shift = -1 * home_shift
        ## update elos ##
        self.current_elos[row['home_team']]['elo'] += home_shift
        self.current_elos[row['away_team']]['elo'] += away_shift
        ## set state ##
        self.current_elos[row['home_team']]['last_game_season'] = row['season']
        self.current_elos[row['home_team']]['last_game_week'] = row['week']
        self.current_elos[row['away_team']]['last_game_season'] = row['season']
        self.current_elos[row['away_team']]['last_game_week'] = row['week']
    
    def run(self):
        '''
        Run the model
        '''
        for index, row in self.games.iterrows():
            ## project the game ##
            row = self.project(row) 
            ## process the game ##
            self.process(row)
        
    