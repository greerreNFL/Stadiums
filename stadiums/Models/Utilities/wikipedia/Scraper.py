## built-in ##
import time
from datetime import datetime
from typing import Optional, Dict
import re
import pathlib
import os

## external ##
import requests
from bs4 import BeautifulSoup

## internal ##
from .Cache import WikipediaCache

class WikipediaScraper:
    '''
    A class for scraping stadium data from wikipedia with a built-in cache
    for faster/smarter retrieval

    To use, create an instance, and then call get_wikipedia_data with the
    stadium id and wikipedia url
    '''
    def __init__(self):
        self.cache = WikipediaCache()

    #####################
    ## PARSING HELPERS ##
    #####################
    def clean_text(self, text: str) -> Optional[str]:
        '''
        Clean and normalize text content from wikipedia, removing reference tags,
        and special unicode spaces

        Parameters:
        * text: str

        Returns:
        * str
        '''
        if not text:
            return None
        # Remove reference tags
        text = re.sub(r'\[\s*(?:\d+|citation[^]]*)\s*\]', '', text)
        # Remove special unicode spaces and normalize whitespace
        text = ' '.join(text.split())
        return text.strip()
    
    def parse_text_with_lists(self, element: BeautifulSoup) -> Optional[str]:
        '''
        Parse an element from bs4 that may contain lists
        '''
        ## handle lists ##
        list_items = element.find_all('li')
        if len(list_items) > 0:
            ## get the text of the list items ##
            text = ', '.join([li.get_text(' ', strip=True) for li in list_items])
        else:
            ## get raw text ##
            text = element.get_text(' ', strip=True)
        return text

    def parse_nicknames(self, nickname_div) -> Optional[str]:
        '''
        Parse nicknames handling quotes, brackets, and parentheses.
        '''
        if not nickname_div:
            return None
        ## replace line breaks first with commas ##
        for br in nickname_div.find_all('br'):
            br.replace_with(',')
        ## handle lists ##
        text = self.parse_text_with_lists(nickname_div)
        if not text:
            return None
        # First remove all bracketed and parenthetical content
        text = re.sub(r'\[.*?\]|\(.*?\)', '', text)
        # Replace quoted content with its unquoted version plus a comma for separation
        text = re.sub(r'[""]([^""]+)[""]', r'\1,', text)  # Handle fancy quotes
        text = re.sub(r'"([^"]+)"', r'\1,', text)         # Handle straight quotes
        # Now we can simply split on commas and newlines
        parts = re.split(r'\s*[,\n]\s*', text)
        # Clean and filter the results
        nicknames = [part.strip() for part in parts if part.strip()]
        return ', '.join(nicknames) if nicknames else None

    def extract_year(self, date_str: str) -> Optional[int]:
        '''
        Parse a date string and return its year

        Parameters:
        * date_str: str

        Returns:
        * year: int
        '''
        if not date_str:
            return None
        # Clean the date string
        date_str = self.clean_text(date_str)
        # Remove parenthetical content
        date_str = re.sub(r'\(.*?\)', '', date_str)
        # Common date patterns
        patterns = [
            r'(?P<month>\w+)\s+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})',  # August 15, 1971
            r'(?P<year>\d{4})',  # Just year
            r'(?P<month>\w+)\s+(?P<year>\d{4})'  # August 1971
        ]
        ## try each pattern ##
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                groups = match.groupdict()
                try:
                    if 'month' in groups and 'day' in groups:
                        parsed_date = datetime.strptime(f"{groups['month']} {groups['day']} {groups['year']}", '%B %d %Y').date()
                        return parsed_date.year
                    elif 'month' in groups:
                        parsed_date = datetime.strptime(f"{groups['month']} 1 {groups['year']}", '%B %d %Y').date()
                        return parsed_date.year
                    else:
                        parsed_date = datetime.strptime(f"January 1 {groups['year']}", '%B %d %Y').date()
                        return parsed_date.year
                except ValueError:
                    continue
        return None

    def extract_costs(self, value_cell) -> tuple[Optional[int], Optional[int]]:
        '''
        Extract both original construction cost and 2023 adjusted cost.
        Returns tuple of (original_cost, cost_2023)
        '''
        if not value_cell:
            return None, None
        # First replace <br> tags with newlines for easier splitting
        for br in value_cell.find_all('br'):
            br.replace_with('\n')
        # Get clean text
        text = self.clean_text(value_cell.get_text())
        if not text:
            return None, None
        # Split into lines and process
        lines = text.split('\n')
        original_cost = None
        cost_2023 = None
        for line in lines:
            # Skip renovation lines for original cost
            if 'renovation' in line.lower():
                continue
            # Look for 2023 cost
            if '2023' in line:
                match = re.search(r'(?:US)?[\$\s]*([\d,\.]+)[\s\xa0]*(million|billion)?\s+(?:dollars\s+)?in\s+2023', line)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        amount = float(amount_str)
                        multiplier = {
                            'million': 1_000_000,
                            'billion': 1_000_000_000
                        }.get(match.group(2), 1)
                        cost_2023 = int(amount * multiplier) if int(amount * multiplier) > 1000000 else None
                    except ValueError:
                        pass
            # Look for original cost if we haven't found it yet
            if not original_cost:
                # Handle both "$1 million" and "$600,000" formats
                match = re.search(r'(?:US)?[\$\s]*([\d,\.]+)[\s\xa0]*(million|billion)?', line)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        amount = float(amount_str)
                        multiplier = {
                            'million': 1_000_000,
                            'billion': 1_000_000_000
                        }.get(match.group(2), 1)
                        original_cost = int(amount * multiplier) if int(amount * multiplier) > 50000 else None
                    except ValueError:
                        pass
        ## return the costs ##
        return original_cost, cost_2023

    def extract_years(self, years_str: str) -> Optional[str]:
        '''
        Extract years from a string into a comma-separated list.

        Parameters:
        * years_str: str

        Returns:
        * years: str
        '''
        if not years_str:
            return None
        ## find all years in the string ##
        years = re.findall(r'\b(?:19|20)\d{2}\b', years_str)
        return ', '.join(years) if years else None

    ##################
    ## CORE SCRAPER ##
    ##################
    def get_wikipedia_data(self,
        stadium_id: str,
        wikipedia_url: str,
        force_rescrape: bool = False
    ) -> Optional[Dict]:
        '''
        Get stadium data from a Wikipedia url and parse the infobox HTML
        into a structured dictionary

        Parameters:
        * stadium_id: str -- id for cache lookup
        * wikipedia_url: str -- url to scrape
        * force_rescrape: bool -- if True, force rescrape the url

        Returns:
        * data: Dict
        '''
        ## request the html text ##
        html_text = self.cache.request_html_text(
            stadium_id,
            wikipedia_url,
            force_rescrape
        )
        ## handle response ##
        if html_text is None:
            return None
        ## parse the html ##
        soup = BeautifulSoup(html_text, 'html.parser')
        infobox = soup.find('table', class_='infobox')
        if not infobox:
            ## add future logging ##
            return None
        ## initialize data dictionary ##
        data = {
            'website': None,
            'nicknames': None,
            'img_logo_url': None,
            'img_shot_url': None,
            'owner': None,
            'operator': None,
            'capacity': None,
            'broke_ground': None,
            'opened': None,
            'closed': None,
            'demolished': None,
            'construction_cost': None,
            'construction_cost_2023': None,
            'renovation_years': None,
            'expansion_years': None,
            'architects': None
        }
        # Extract nickname(s)
        data['nicknames'] = self.parse_nicknames(infobox.find('div', class_='nickname'))
        # Process rows, which is where the data would be stored (if it is available)
        ## some state to handle data split across multiple rows ##
        last_header = None
        last_header_index = None
        for index, row in enumerate(infobox.find_all('tr')):
            ## first get the header ##
            header = row.find('th')
            ## update state ##
            if header:
                last_header = self.clean_text(header.get_text())
                last_header_index = index
            ## the data label is the text of the header, so if no header, skip ##
            if not header:
                ## however, some data takes up an entire row (ie class='infobox-full-data') with the header on
                ## the previous row. In this case, we need to reference state ##
                fd_tds = row.find_all('td', class_='infobox-full-data')
                if len(fd_tds) > 0:
                    td = fd_tds[0]
                    if last_header == 'Website' and last_header_index == index - 1:
                        anchor = td.find('a')
                        if anchor and anchor.has_attr('href'):
                            data['website'] = anchor['href']
                        else:
                            data['website'] = self.clean_text(td.get_text())
                ## images also take up the entire row, so we check based on the td class ##
                img_tds = row.find_all('td', class_='infobox-image')
                if len(img_tds) > 0 and index <= 3:
                    ## logos and heros are always at the top, so dont process images past here
                    td = img_tds[0]
                    ## get the img ##
                    img = td.find('img')
                    ## if img found, then get the src ##
                    if img:
                        ## fill logo and img urls if they have not yet been found ##
                        src = img.get('src')
                        url = 'https:{0}'.format(src)
                        if 'logo' in url.lower() and data['img_logo_url'] is None:
                            data['img_logo_url'] = url
                        elif data['img_shot_url'] is None:
                            data['img_shot_url'] = url
                ## if that is not the case, then just continue ##
                continue
            ## clean header text ##
            header_text = self.clean_text(header.get_text())
            ## handle Nones
            if header_text is None:
                continue
            header_text = header_text.lower()
            value_cell = row.find('td')
            ## if no value is found, we have no data to attach to this header ##
            if not value_cell:
                continue
            ## clean the value text ##
            value_text = self.clean_text(value_cell.get_text())
            # Map fields based on header text
            if 'owner' in header_text:
                data['owner'] = self.clean_text(self.parse_text_with_lists(value_cell))
            elif 'operator' in header_text:
                data['operator'] = self.clean_text(self.parse_text_with_lists(value_cell))
            elif 'capacity' in header_text:
                ## first handle any brs ##
                for br in value_cell.find_all('br'):
                    br.replace_with('\n')
                ## and reclean ##
                value_text = self.clean_text(value_cell.get_text())
                ## improved capacity parsing ##
                lines = [x.strip() for x in value_text.split('\n') if x.strip()]
                capacity_int = None
                for line in lines:
                    # Skip former capacity or list indicators
                    if any(skip in line.lower() for skip in ['former', 'list']):
                        continue
                    # Find first substantial number
                    digits = re.findall(r'\d{2,}', line.replace(',', ''))
                    if digits:
                        capacity_int = int(digits[0])
                        break
                data['capacity'] = capacity_int
            elif 'broke ground' in header_text:
                data['broke_ground'] = self.extract_year(value_text)
            elif header_text.startswith('opened'):
                # Handle multiple opening dates
                date_candidates = re.split(r'\s*\b(?:and|or|,|;|\n|\r)\s*', value_text)
                parsed_dates = []
                for chunk in date_candidates:
                    parsed_dt = self.extract_year(chunk)
                    if parsed_dt:
                        parsed_dates.append(parsed_dt)
                if parsed_dates:
                    data['opened'] = min(parsed_dates)  # Use earliest date
            elif header_text.startswith('closed'):
                data['closed'] = self.extract_year(value_text)
            elif 'demolished' in header_text:
                data['demolished'] = self.extract_year(value_text)
            elif 'construction cost' in header_text:
                orig_cost, cost_2023 = self.extract_costs(value_cell)
                data['construction_cost'] = orig_cost
                data['construction_cost_2023'] = cost_2023
            elif 'architect' in header_text:
                architects = [self.clean_text(a.get_text()) for a in value_cell.find_all(['a', 'div'])] or [value_text]
                data['architects'] = ', '.join(filter(None, architects))
            elif 'renovated' in header_text:
                data['renovation_years'] = self.extract_years(value_text)
            elif 'expanded' in header_text:
                data['expansion_years'] = self.extract_years(value_text)
        ## return the data ##
        return data
