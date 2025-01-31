import os
import time
import pathlib
import requests
from typing import Optional

class WikipediaCache:
    '''
    A cache utility for handling io of wikipedia html text
    '''
    def __init__(self):
        self.cache_dir = '{0}/cache'.format(pathlib.Path(__file__).parent.resolve())
        # Ensure cache directory exists
        if not pathlib.Path(self.cache_dir).exists():
            pathlib.Path(self.cache_dir).mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, stadium_id: str) -> pathlib.Path:
        '''
        Get the full path for a cached page based on stadium id
        '''
        return '{0}/{1}.txt'.format(
            self.cache_dir,
            stadium_id
        )

    def read_cache(self, stadium_id: str) -> Optional[str]:
        '''
        Read HTML content from cache if it exists
        '''
        cache_path = self.get_cache_path(stadium_id)
        try:
            if os.path.exists(cache_path):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            print('Cache read error: {0}'.format(e))
            pass
            ## log in the future ##
        return None

    def write_cache(self, stadium_id: str, content: str) -> bool:
        '''
        Write HTML content to cache
        '''
        cache_path = self.get_cache_path(stadium_id)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            pass
            ## log in the future ##
        return False

    def request_html_text(self,
        stadium_id: str,
        wikipedia_url: str,
        force_rescrape: bool = False,
        retry_count: int = 3,
        initial_delay: float = 0.5
    ) -> Optional[str]:
        '''
        Request HTML for a Wikipedia URL with caching and exponential backoff.
        
        Parameters:
        * stadium_id: str -- id for cache lookup
        * wikipedia_url: str -- url to scrape
        * force_rescrape: bool -- if True, force rescrape the url
        * retry_count: int -- number of retries on failure
        * initial_delay: float -- initial delay between retries in seconds
        
        Returns:
        * html: Optional[str]
        '''
        ## Check cache first unless force_rescrape is True
        if not force_rescrape:
            cached_content = self.read_cache(stadium_id)
            if cached_content is not None:
                return cached_content
        ## attempt to get html, with exponential backoff
        delay = initial_delay
        for attempt in range(retry_count):
            ## sleep w/ backoff ##
            if attempt > 0:
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            ## request the html ##
            response = requests.get(
                wikipedia_url,
                headers={'User-Agent': 'Stadium Data Research Bot/1.0'}
            )
            ## handle response ##
            if response.status_code == 200:
                # Success - write to cache and return
                self.write_cache(stadium_id, response.text)
                return response.text
            if response.status_code == 404:
                ## if not found, no need to retry
                return None
            ## otherwise retry ##
            if attempt < retry_count - 1:
                continue
            ## unless we are out of retries, in which break ##
            break
        ## and then return None post break ##
        return None
