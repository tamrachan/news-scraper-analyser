"""
Generic Web Scraper for News Articles using newspaper3k and BeautifulSoup as a backup.

This script scrapes full text from news articles based on configurations
in a .ini file and stores the content in a JSON file.
"""

import json
import re
import requests
import configparser
from urllib.parse import urljoin
from datetime import datetime, date
from dateutil import parser
from newspaper import Article
from bs4 import BeautifulSoup

class WebScraper:
    """A class to scrape news articles from various websites."""
    
    def __init__(self, config_path: str):
        """Initialize the scraper with a configuration file."""
        self.config = configparser.ConfigParser()
        read_files = self.config.read(config_path)

        # Error handle config file

        if not read_files:
            raise ValueError(f"Config file '{config_path}' not found or is empty.")
        if not self.config.sections():
            raise ValueError(f"Config file '{config_path}' does not contain any sections.")

        # Check for required keys in each section - homepage and article_link_selector are vital for newspaper3k
        # The rest are required for beautiful soup as a back up web scraper when newspaper cannot find the content
        required_keys = ['homepage', 'article_link_selector', 'title_selector', 'date_selector', 'content_selector']
        for section in self.config.sections():
            for key in required_keys:
                if key not in self.config[section]:
                    raise ValueError(f"Config section [{section}] missing required key: '{key}'")
        
        # Requests setup
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/"
        })

    def _get_soup(self, url: str):
        """Fetch a URL and return a BeautifulSoup object."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'lxml')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}:\n{e}")
            return None

    def find_article_links(self, source: str) -> list:
        """Find all unique article links from a source's homepage, preserving order."""

        config_section = self.config[source]
        homepage = config_section.get('homepage')
        selector = config_section.get('article_link_selector')
        next_page_selector = config_section.get('next_page_selector')
        link_text_contains = config_section.get('link_text_contains')
        max_articles = int(self.config.get(source, 'max_articles', fallback='10'))

        print(f"Starting from homepage: {homepage}")
        # print(f"Using article link selector: {selector}")
        # print(f"Using next page selector: {next_page_selector}")
        # print(f"Using link text contains: {link_text_contains}")

        links = []
        seen_links = set()
        current_url = homepage
        pages_visited = 0

        while current_url and len(links) < max_articles:
            print(f"\nFetching page {pages_visited + 1}: {current_url}")
            soup = self._get_soup(current_url)
            if not soup:
                print("Failed to get soup, breaking loop.")
                break

            # Collect article links on current page
            # print("Finding article links...")
            new_links_found = 0
            for a in soup.select(selector):
                href = a.get('href')
                if href:
                    full_url = urljoin(current_url, href)
                    if full_url not in seen_links:
                        print(f"Found new article link: {full_url}")
                        if source == "Comms Dealer" and full_url == "https://www.comms-dealer.com/magazine/july-issue-2025":
                            print("-- Magazine link ignored")
                            continue
                        links.append(full_url)
                        seen_links.add(full_url)
                        new_links_found += 1
                        if len(links) >= max_articles:
                            print("Reached max_articles limit.")
                            return links
                    else:
                        print(f"Duplicate article link ignored: {full_url}")

            # Find next page URL
            next_url = None
            if new_links_found == 0:
                print(f"No new links found, stopping.")
                break

            # Try next_page_selector first
            if next_page_selector:
                next_link = soup.select_one(next_page_selector)
                if next_link and next_link.has_attr('href'):
                    next_url = urljoin(current_url, next_link['href'])
                    print(f"Next page found using selector: {next_url}")
                else:
                    print("No next page link found using selector.")

            # If not found, try link_text_contains fallback
            if not next_url and link_text_contains:
                next_link = soup.find('a', string=lambda t: t and link_text_contains in t)
                if next_link and next_link.has_attr('href'):
                    next_url = urljoin(current_url, next_link['href'])
                    print(f"Next page found using link text contains '{link_text_contains}': {next_url}")
                else:
                    print(f"No next page link found using link text contains '{link_text_contains}'.")

            if not next_url:
                print("No next page URL found, stopping pagination.")
                break  # No next page found, stop

            current_url = next_url
            pages_visited += 1

        print(f"\nTotal article links found: {len(links)}")
        return links


    def standardise_date(self, text: str) -> str:
        """Standardises the date so all dates are in the same format."""
        try:
            cleaned = re.sub(r'(\d{1,2})(st|nd|rd|th)', r'\1', text)
            cleaned = re.split(r'[-–](?!\d)', cleaned)[0]
            dt = parser.parse(cleaned.strip(), fuzzy=True)
            return dt.strftime('%d-%m-%Y')
        except Exception as e:
            return f"Could not parse: {text} ({e})"

    def scrape_article(self, source: str, url: str, today_flag: bool, date_range_flag: bool, start_date: datetime, end_date: datetime) -> dict:
        """Scrape title, publish date, and content using newspaper3k. If failed with newspaper3k, use BeautifulSoup as a backup"""

        article_failed = False

        try:
            article = Article(url)
            article.download()
            article.parse()
        except Exception as e:
            article_failed = True # Use Beautiful Soup
            print(f"Using BeautifulSoup to scrape {url}: {e}")

        soup = self._get_soup(url) # For backup

        if article_failed and not soup:
            return None # Both failed
        
        # Try get newspaper3k date first
        publish_date = article.publish_date
        if publish_date:
            article_date = publish_date.strftime('%d-%m-%Y')
        else:
            # If failed, try soup
            date_selector = self.config.get(source, 'date_selector')
            date_attribute = self.config.get(source, 'date_attribute', fallback=None)
            
            try:
                date_element = soup.select_one(date_selector)
                if date_attribute:
                    article_date = date_element.get(date_attribute)
                else:
                    article_date = date_element.get_text(strip=True) if date_element else "Date not found"
                article_date = self.standardise_date(article_date)
            except AttributeError:
                article_date = "Date not found"

        # Get today's date
        date_today = str(date.today().strftime("%d-%m-%Y"))

        # Compare dates
        print(f"Date today: {date_today} | Article date: {article_date}")
        if today_flag and (article_date != date_today):
            return False

        # Convert dates to datetime for comparison
        if date_range_flag:
            article_datetime = datetime.strptime(article_date, "%d-%m-%Y")

            if article_datetime < start_date or article_datetime > end_date:
                return False
        
        # Get article title
        if article.title: # Using newspaper3k
            title = article.title
        else: # Using soup
            title_selector = self.config.get(source, 'title_selector')
            title_element = soup.select_one(title_selector)
            title = title_element.get_text(strip=True) if title_element else "Title not found"

        # Get article content
        if article.text: # Using newspaper3k
            text = article.text
        else: # Using soup
            content_selector = self.config.get(source, 'content_selector')
            content_element = soup.select(content_selector)
            if content_element:
                # Join the text from all found elements
                text_parts = [elem.get_text(separator=' ', strip=True) for elem in content_element]
                text = ' '.join(text_parts).split()
                text = ' '.join(text)
            else:
                text = "Content not found"

        # Return article data
        return {
            'source': source,
            'url': url,
            'date': article_date,
            'title': title,
            'cleaned_text': text
        }

    def valid_date_flags(self, today_only_flag: bool, date_range_flag: bool, start_date: str, end_date: str) -> bool:
        """Checks if date flags are valid"""

        if today_only_flag:
            # today_only_flag True means date_range_flag must be False
            if date_range_flag:
                print("Error: The today_only_flag and date_range_flag cannot both be True")
                return False
            return True  # today_only_flag True and date_range_flag False is valid

        if date_range_flag:
            # date_range_flag True means today_only_flag must be False and start_date, end_date must be present
            if today_only_flag:
                print("Error: The date_range_flag and today_only_flag cannot both be True")
                return False
            if start_date is None or end_date is None:
                print("Error: start_date and end_date must not be None when date_range_flag is True")
                return False
            # Parse dates and check order
            try:
                start_dt = datetime.strptime(start_date, "%d-%m-%Y")
                end_dt = datetime.strptime(end_date, "%d-%m-%Y")
            except ValueError as e:
                print(f"Invalid date format: {e}")
                return False

            if end_dt < start_dt:
                print("Error: end_date cannot be before start_date")
                return False
            
            return True

        # If neither flag is True, or both are False, it is valid
        return True


    def scrape_all_sites(self, output_name: str, today_flag: bool = False, date_range_flag: bool = False, start_date: str = None, end_date: str = None) -> list:
        """Scrape all websites defined in the config and save to JSON."""

        if not self.valid_date_flags(today_flag, date_range_flag, start_date, end_date):
            return False
        if date_range_flag:
            start_date = datetime.strptime(start_date, "%d-%m-%Y")
            end_date = datetime.strptime(end_date, "%d-%m-%Y")

        all_articles = []

        for source in self.config.sections():
            print("\n----------------------------------------------------")
            print(f"Scraping {source}...")
            print("----------------------------------------------------")
            
            links_to_scrape = self.find_article_links(source)
            if not links_to_scrape:
                print(f"  WARNING: No articles found for {source}.")
                return False  # Signal failure, do not write JSON
            else:
                print(f"\nFound {len(links_to_scrape)} articles.")

            # Scrape all the links found
            print(f"Scraping top {len(links_to_scrape)} articles.")
            for i, link in enumerate(links_to_scrape, 1):
                print(f"  [{i}/{len(links_to_scrape)}] Scraping: {link}")
                article_data = self.scrape_article(source, link, today_flag, date_range_flag, start_date, end_date)
                if article_data:
                    if not article_data['cleaned_text'] or article_data['cleaned_text'] == 'Content not found':
                        print(f"    WARNING: No content found for {link}.")
                    else:
                        all_articles.append(article_data)
                elif article_data == False:
                    print(" -- Skipped rest of articles as not today's date or in date range specified")
                    break
                else:
                    print(f"    WARNING: Failed to scrape article at {link}. (May not be today's date)")
        
        # # To append to json?
        # appended_list = all_articles
        # # Append data
        # try:
        #     with open(output_name + ".json", "r", encoding="utf-8") as file:
        #         appended_list.extend(json.load(file))
        # except FileNotFoundError:
        #     print("File not found. Writing to file instead of appending.")

        # Save to json file
        with open(output_name + ".json", "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=4)

        return all_articles

def main():
    """Runs the web scraper and returns the path to the output file."""
    config_file = '../examples/collect_example.ini'  # TODO: Change to collect.ini
    TODAY_ONLY_FLAG = False
    DATE_RANGE_FLAG = False
    # start_date = "02-07-2025"
    # end_date = "05-08-2025"
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file_name = f'scraped_articles_{timestamp}'
    scraper = WebScraper(config_file)
    if scraper.scrape_all_sites(output_file_name, TODAY_ONLY_FLAG, DATE_RANGE_FLAG):
        print(f"\n✓ Results saved to: {output_file_name}.json")

if __name__ == "__main__":
    main()
