## built-ins ##
from typing import Dict, List, Optional

## external ##
import pandas as pd

## local ##
from .Stadium import Stadium
from .Utilities import add_fastr_meta

class StadiumCollection:
    '''
    A collection of Stadium objects that comes with utility functions
    for generating dataframes, updating 
    '''
    def __init__(self):
        self.stadiums: Dict[Stadium] = {}
        self.stadium_df: Optional[pd.DataFrame] = None
        self.stadium_properties: List[str] = [
            'stadium_id', 'stadium_name',
            'lat', 'lon', 'altitude', 'heading',
            'first_game_date', 'last_game_date', 'surface_type',
            'address', 'city', 'state', 'zipcode', 'country',
            'tz', 'tz_offset', 'wikipedia_url', 'img_sat_url',
            'img_logo_url', 'img_shot_url', 'website', 'nicknames',
            'owner', 'operator', 'capacity', 'broke_ground',
            'opened', 'closed', 'demolished', 'construction_cost',
            'construction_cost_2023', 'renovation_years', 'expansion_years',
            'architects'
        ]
    
    def add_stadium(self, stadium: Stadium):
        '''
        Add a stadium to the collection
        '''
        self.stadiums[stadium.stadium_id] = stadium
    
    def update_df(self):
        '''
        Update the stadium dataframe based on the current collection
        '''
        if len(self.stadiums) == 0:
            raise ValueError('Add stadiums in the collection before updating the dataframe')
        ## create the df ##
        self.stadium_df = pd.DataFrame(list(self.stadiums.values()))
    
    def populate_from_csv(self, csv_path: str):
        '''
        Load stadiums from a csv file

        Parameters:
        * csv_path: str

        Returns:
        * None
        '''
        ## load the df ##
        df = pd.read_csv(csv_path)
        ## validate that df has an id and name column ##
        if 'stadium_id' not in df.columns or 'stadium_name' not in df.columns:
            raise ValueError('CSV must have an stadium_id and stadium_name column')
        ## populate the collection ##
        for index, row in df.iterrows():
            record = {prop: row.get(prop) for prop in self.stadium_properties}
            stadium = Stadium(**record)
            self.add_stadium(stadium)

    def extend_from_recs(self, recs: List[Dict]):
        '''
        Parse a list of stadium records (id and name), and extend/ammend the
        collection

        Parameters:
        * recs: List[Dict]

        Returns:
        * None
        '''
        for rec in recs:
            ## validate the keys ##
            if 'stadium_id' not in rec or 'stadium_name' not in rec:
                raise ValueError('Stadium record must have a stadium_id and stadium_name to extend the collection')
            ## if the stadium exists in the collection, update the name ##
            if rec['stadium_id'] in self.stadiums:
                self.stadiums[rec['stadium_id']].stadium_name = rec['stadium_name']
            else:
                ## if the stadium does not exist in the collection, add it ##
                self.add_stadium(Stadium(
                    stadium_id=rec['stadium_id'],
                    stadium_name=rec['stadium_name']
                ))
    
    def add_fastr_meta(self):
        '''
        Add fastr meta data to the stadium collection
        '''
        add_fastr_meta(self)

    def update_stadium_data(self, force_rescrape: bool = False, force_reparse: bool = False):
        '''
        Updates the stadium data for all stadiums in the collection.
        To force rescraping, set force_rescrape to True. See Stadium.update_data
        for more information.
        '''
        for stadium in self.stadiums.values():
            stadium.add_wikipedia_data(
                force_rescrape=force_rescrape,
                force_reparse=force_reparse
            )
    
    def to_csv(self, csv_path: str):
        '''
        Write the stadium dataframe to a csv file

        Parameters:
        * csv_path: str

        Returns:
        * None
        '''
        self.update_df()
        self.stadium_df.to_csv(csv_path, index=False)
