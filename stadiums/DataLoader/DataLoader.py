## built-ins ##

## external ##
import pandas as pd
import nfelodcm as dcm

class DataLoader:
    '''
    Handles the loading of external data for various package functions. Leverages
    a singleton pattern to allow for sharing of loaded data across functions without
    re-triggering data loads on each usage
    '''
    ## state ##
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        ## handle singleton pattern ##
        if self._initialized:
            return
        ## load data ##
        self.db = dcm.load(['games', 'qbelo', 'wt_ratings'])
        self.fastr_games = pd.read_csv(
            'https://raw.githubusercontent.com/nflverse/nfldata/refs/heads/master/data/games.csv'
        )
        self.apply_fastr_abbrs()
        self.add_qb_adjustments()
        self._initialized = True
        
    def apply_fastr_abbrs(self):
        '''
        Adds fastr style team abbreviations to the nfelodcm games dataframe
        '''
        ## load fastr team abbreviations ##
        ## merge ##
        self.db['games'] = pd.merge(
            self.db['games'],
            self.fastr_games.groupby(['game_id']).head(1)[[
                'game_id', 'home_team', 'away_team'
            ]].rename(
                columns={
                    'home_team': 'home_team_fastr',
                    'away_team': 'away_team_fastr'
                }
            ),
            on='game_id',
            how='left'
        )

    def add_qb_adjustments(self):
        '''
        Adds qb_adjustments to the nfelodcm games dataframe so they can
        be used in a simple power ranking model to calculate opponent adjusted
        home field advantage
        '''
        self.db['games'] = pd.merge(
            self.db['games'],
            self.db['qbelo'].groupby(['game_id']).head(1)[[
                'game_id', 'qb1_adj', 'qb2_adj'
            ]].rename(
                columns={
                    'qb1_adj': 'home_qb_adj',
                    'qb2_adj': 'away_qb_adj'
                }
            ),
            on='game_id',
            how='left'
        )
        self.db['games']['home_qb_adj'] = self.db['games']['home_qb_adj'].fillna(0)
        self.db['games']['away_qb_adj'] = self.db['games']['away_qb_adj'].fillna(0)
