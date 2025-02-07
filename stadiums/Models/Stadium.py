## built-ins ##
from dataclasses import dataclass, field, asdict
from typing import Optional
import pathlib
import os

## external imports ##
import pandas as pd

## internal imports ##
from .Utilities import WikipediaScraper

@dataclass
class Stadium:
    stadium_id: str
    stadium_name: str
    lat: Optional[float] = field(default=None)
    lon: Optional[float] = field(default=None)
    altitude: Optional[float] = field(default=None)
    heading: Optional[int] = field(default=None)
    first_game_date: Optional[str] = field(default=None)
    last_game_date: Optional[str] = field(default=None)
    surface_type: Optional[str] = field(default=None)
    roof_type: Optional[str] = field(default=None)
    address: Optional[str] = field(default=None)
    city: Optional[str] = field(default=None)
    state: Optional[str] = field(default=None)
    zipcode: Optional[str] = field(default=None)
    country: Optional[str] = field(default=None)
    tz: Optional[str] = field(default=None)
    tz_offset: Optional[int] = field(default=None)
    wikipedia_url: Optional[str] = field(default=None)
    img_sat_url: Optional[str] = field(default=None)
    img_logo_url: Optional[str] = field(default=None)
    img_shot_url: Optional[str] = field(default=None)
    website: Optional[str] = field(default=None)
    nicknames: Optional[str] = field(default=None)
    owner: Optional[str] = field(default=None)
    operator: Optional[str] = field(default=None)
    capacity: Optional[int] = field(default=None)
    broke_ground: Optional[int] = field(default=None)
    opened: Optional[int] = field(default=None)
    closed: Optional[int] = field(default=None)
    demolished: Optional[int] = field(default=None)
    construction_cost: Optional[int] = field(default=None)
    construction_cost_2023: Optional[int] = field(default=None)
    renovation_years: Optional[str] = field(default=None)
    expansion_years: Optional[str] = field(default=None)
    architects: Optional[str] = field(default=None)

    def __post_init__(self):
        '''
        Various post initialization logic
        '''
        ## get an asset URL if it exists in the pacakge and was not
        ## not provided in the constructor
        if pd.isnull(self.img_sat_url):
            asset_loc = '{0}/Assets/SatelliteImg/{1}.png'.format(
                pathlib.Path(__file__).parent.parent.resolve(),
                self.stadium_id
            )
            pathlib.Path(asset_loc)
            if pathlib.Path(asset_loc).exists():
                ## assume that if the asset exists in the package at run time,
                ## it is in the repo
                self.img_sat_url = 'https://raw.githubusercontent.com/greerrenfl/Stadiums/main/stadiums/Assets/SatelliteImg/{0}.png'.format(
                    self.stadium_id
                )
        
    def as_record(self) -> dict:
        return asdict(self)
    
    def has_wikipedia_data(self) -> bool:
        '''
        Returns True if any field from wikipedia is not None
        '''
        return any(
            not pd.isnull(getattr(self, field))
            for field in [
                'img_logo_url', 'img_shot_url',
                'website', 'nicknames', 'owner', 'operator',
                'capacity', 'broke_ground', 'opened', 'closed', 'demolished',
                'construction_cost', 'construction_cost_2023', 'renovation_years',
                'expansion_years', 'architects'
            ]
        )
    
    def add_wikipedia_data(self,
        update_existing: bool = True,
        override_existing: bool = False,
        force_rescrape: bool = False,
        force_reparse: bool = False
    ):
        '''
        Updates the stadium data from wikipedia

        Parameters:
        * update_existing: bool - if True, will update existing data with new data if it exists
        * override_existing: bool - if True, will update existing data regardless of whether new data exists
        * force_rescrape: bool - if True, will rescrape wikipedia data and reparse it even if there is a cache
        * force_reparse: bool - if True, will reparse wikipedia data from cache or scrape it if there is no cache
        '''
        ## if there is no wikipedia url, do nothing ##
        if self.wikipedia_url is None:
            return
        ## if wikipedia data exists, and there is no force rescrape, do nothing ##
        if self.has_wikipedia_data() and not force_rescrape and not force_reparse:
            return
        ## else scrape and update ##
        scraper = WikipediaScraper()
        wikipedia_data = scraper.get_wikipedia_data(
            stadium_id=self.stadium_id,
            wikipedia_url=self.wikipedia_url,
            force_rescrape=force_rescrape
        )
        for key, value in wikipedia_data.items():
            ## if override_existing is True, then update regardless of whether the value exists
            if override_existing:
                setattr(self, key, value)
                continue
            ## if the value is nullable, then do nothing, which either
            ## 1) preserves the existing value, or
            ## 2) skips a duplicative None write
            if pd.isnull(value):
                continue
            ## if update existing, then update with the new value
            ## if the current value is None, update regardless
            if update_existing or getattr(self, key) is None:
                setattr(self, key, value)
                continue

        


