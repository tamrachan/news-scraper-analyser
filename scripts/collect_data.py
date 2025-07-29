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

class WebScraper:
    """A class to scrape news articles from various websites."""
    
    def __init__(self, config_path: str):
        """Initialize the scraper with a configuration file."""
        self.config = configparser.ConfigParser()
        read_files = self.config.read(config_path)

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
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/"
        })

    def _get_soup(self, url: str):
        """Fetch a URL and return a BeautifulSoup object."""
        from bs4 import BeautifulSoup
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'lxml')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}:\n{e}")
            return None

    def find_article_links(self, source: str) -> list:
        """Find all unique article links from a source's homepage, preserving order."""
        homepage = self.config.get(source, 'homepage')
        selector = self.config.get(source, 'article_link_selector')
        soup = self._get_soup(homepage)
        if not soup:
            return []
            
        links = []
        seen_links = set()
        for a in soup.select(selector):
            href = a.get('href')
            if href:
                full_url = urljoin(homepage, href)
                if full_url not in seen_links:
                    links.append(full_url)
                    seen_links.add(full_url)
        return links

    def standardise_date(self, text: str) -> str:
        try:
            cleaned = re.sub(r'(\d{1,2})(st|nd|rd|th)', r'\1', text)
            cleaned = re.split(r'[-–](?!\d)', cleaned)[0]
            dt = parser.parse(cleaned.strip(), fuzzy=True)
            return dt.strftime('%d-%m-%Y')
        except Exception as e:
            return f"Could not parse: {text} ({e})"

    def scrape_article(self, source: str, url: str, today_flag: bool) -> dict:
        """Scrape title, publish date, and content using newspaper3k."""
        article_failed = False
        try:
            article = Article(url)
            article.download()
            article.parse()
        except Exception as e:
            article_failed = True
            print(f"Using BeautifulSoup to scrape {url}: {e}")

        soup = self._get_soup(url)
        if not soup and article_failed:
            return None
        
        # Try get newspaper3k date first
        publish_date = article.publish_date
        if publish_date:
            article_date = publish_date.strftime('%d-%m-%Y')
        else:
            # If failed to get newspaper3k date, try soup
            date_selector = self.config.get(source, 'date_selector')
            date_attribute = self.config.get(source, 'date_attribute', fallback=None)
            date_element = soup.select_one(date_selector)
            try:
                if date_attribute:
                    article_date = date_element.get(date_attribute)
                else:
                    article_date = date_element.get_text(strip=True) if date_element else "Date not found"
                article_date = self.standardise_date(article_date)
            except AttributeError:
                article_date = "Date not found"

        date_today = str(date.today().strftime("%d-%m-%Y"))

        print(f"Date today: {date_today} Article date: {article_date}")
        if today_flag and (article_date != date_today):
            return False
        
        if article.title:
            title = article.title
        else:
            title_selector = self.config.get(source, 'title_selector')
            title_element = soup.select_one(title_selector)
            title = title_element.get_text(strip=True) if title_element else "Title not found"

        if article.text:
            text = article.text
        else:
            content_selector = self.config.get(source, 'content_selector')
            content_element = soup.select(content_selector)
            if content_element:
                # Join the text from all found elements
                text_parts = [elem.get_text(separator=' ', strip=True) for elem in content_element]
                text = ' '.join(text_parts).split()
                text = ' '.join(text)
            else:
                text = "Content not found"

        return {
            'source': source,
            'url': url,
            'date': article_date,
            'title': title,
            'cleaned_text': text
        }

    def scrape_all_sites(self, output_name: str, today_flag: bool = False) -> list:
        """Scrape all websites defined in the config and save to JSON."""
        
        all_articles = []

        for source in self.config.sections():
            print(f"Scraping {source}...")
            links = self.find_article_links(source)
            if not links:
                print(f"  WARNING: No articles found for {source}.")
                return False  # Signal failure, do not write JSON
            else:
                print(f"Found {len(links)} articles.")
            max_articles = int(self.config.get(source, 'max_articles', fallback='10'))
            links_to_scrape = links[:max_articles]
            print(f"Scraping top {len(links_to_scrape)} articles.")
            for i, link in enumerate(links_to_scrape, 1):
                print(f"  [{i}/{len(links_to_scrape)}] Scraping: {link}")
                article_data = self.scrape_article(source, link, today_flag)
                if article_data:
                    if not article_data['cleaned_text'] or article_data['cleaned_text'] == 'Content not found':
                        print(f"    WARNING: No content found for {link}.")
                    else:
                        # Add source info for consistency
                        all_articles.append(article_data)
                elif article_data == False:
                    print(" --Skipped rest of articles as not today's date")
                    break
                else:
                    print(f"    WARNING: Failed to scrape article at {link}. (May not be today's date)")
        
        with open(output_name + ".json", "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=4)

        return all_articles

def main():
    """Runs the web scraper and returns the path to the output file."""
    config_file = '../examples/collect_example.ini'  # TODO: Change to collect.ini
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file_name = f'scraped_articles_{timestamp}'
    scraper = WebScraper(config_file)
    scraper.scrape_all_sites(output_file_name, False)

    print(f"✓ Results saved to: {output_file_name}")

if __name__ == "__main__":
    main()
