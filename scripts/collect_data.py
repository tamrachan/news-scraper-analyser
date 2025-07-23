#!/usr/bin/env python3
"""
Generic Web Scraper for News Articles

This script scrapes full text from news articles based on configurations
in a .ini file and stores the content in a CSV file.
"""

import csv
import json
import re
import requests
import configparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import unicodedata
from dateutil import parser

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
        # Check for required keys in each section
        required_keys = ['homepage', 'article_link_selector', 'title_selector', 'content_selector']
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

    def _get_soup(self, url: str) -> BeautifulSoup:
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
                # Join relative URLs with the homepage to get absolute URLs
                full_url = urljoin(homepage, href)
                if full_url not in seen_links:
                    links.append(full_url)
                    seen_links.add(full_url)
        return links

    def clean_data(self, text: str) -> str:
        """Remove unwanted characters and fix encoding issues in the text."""

        # Replace common smart quotes and encoding artifacts
        replacements = {
            'â€œ': '"', 'â€': '"', 'â€˜': "'", 'â€™': "'", 'â€“': '', 'â€”': '-',
            'â€¦': '...', 'Â': '', 'Ã©': 'é', 'Ã': 'à', 'â€': '"',
            '–': '-',  # actual en dash
            '—': '-',  # actual em dash
            'â€¢': '',  # bullet
            'âž¤': '',  # rightwards arrow
        }

        for bad, good in replacements.items():
            text = text.replace(bad, good)
        
        # Unicode normalisation
        text = unicodedata.normalize('NFKC', text)
        # Remove any remaining non-printable or odd unicode chars, but keep quotes
        text = re.sub(r'[\u2026]', '', text) # text = re.sub(r'[\u2018\u2019\u201c\u201d\u2026]', '', text)

        # Optionally, remove any other non-ASCII chars (uncomment if needed)
        # text = text.encode('ascii', errors='ignore').decode()
        return text

    def standardise_date(self, text):
        try:
            # Step 1: Remove ordinal suffixes like 23rd → 23
            cleaned = re.sub(r'(\d{1,2})(st|nd|rd|th)', r'\1', text)

            # Step 2: Trim after the time, if there is noise like "- Score 80"
            cleaned = re.split(r'[-–](?!\d)', cleaned)[0]  # split on dashes not followed by time

            # Step 3: Let dateutil parse the cleaned text
            dt = parser.parse(cleaned.strip(), fuzzy=True)

            # Return standardized date
            return dt.strftime('%Y-%m-%d')

        except Exception as e:
            return f"Could not parse: {text} ({e})"

    def scrape_article(self, source: str, url: str) -> dict:
        """Scrape the title and content from a single article."""
        title_selector = self.config.get(source, 'title_selector')
        content_selector = self.config.get(source, 'content_selector')
        date_selector = self.config.get(source, 'date_selector')
        date_attribute = self.config.get(source, 'date_attribute', fallback=None)

        soup = self._get_soup(url)
        if not soup:
            return None
            
        title_element = soup.select_one(title_selector)
        content_element = soup.select(content_selector)
        date_element = soup.select_one(date_selector)

        if date_attribute:
            date = date_element.get(date_attribute)
        else:
            date = date_element.get_text(strip=True) if date_element else "Date not found"
        date = self.standardise_date(date)
        
        title = title_element.get_text(strip=True) if title_element else "Title not found"
        title = self.clean_data(title)
        
        if content_element:
            # Join the text from all found elements
            text_parts = [elem.get_text(separator=' ', strip=True) for elem in content_element]
            text = ' '.join(text_parts).split()
            text = ' '.join(text)
            text = self.clean_data(text)
        else:
            text = "Content not found"
        
        return {
            'source': source,
            'url': url,
            'date' : date,
            'title': title,
            'cleaned_text': text
        }

    def scrape_all_sites(self, output_name: str):
        """Scrape all websites defined in the config and save to CSV."""
        all_articles = []

        for source in self.config.sections():
            print(f"Scraping {source}...")
            links = self.find_article_links(source)
            if not links:
                print(f"  WARNING: No articles found for {source}.")
                return False  # Signal failure, do not write CSV
            else:
                print(f"Found {len(links)} articles.")
            # Get max_articles from config, default to 10
            max_articles = int(self.config.get(source, 'max_articles', fallback='10'))
            links_to_scrape = links[:max_articles]
            print(f"Scraping top {len(links_to_scrape)} articles.")
            for i, link in enumerate(links_to_scrape, 1):
                print(f"  [{i}/{len(links_to_scrape)}] Scraping: {link}")
                article_data = self.scrape_article(source, link)
                if article_data:
                    if not article_data['cleaned_text'] or article_data['cleaned_text'] == 'Content not found':
                        print(f"    WARNING: No content found for {link}.")
                    else:
                        all_articles.append(article_data)
                    
                else:
                    print(f"    WARNING: Failed to scrape article at {link}.")

        with open(output_name + ".json", "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=4)

        return all_articles

if __name__ == "__main__":
    """Runs the web scraper and returns the path to the output file."""
    # Use collect_example.ini, which can be copied to collect.ini
    config_file = 'examples/collect_example.ini' # TODO: Change to collect.ini
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file_name = f'scraped_articles_{timestamp}'
    
    try:
        scraper = WebScraper(config_file)
        scraper.scrape_all_sites(output_file_name)

        print(f"✓ Results saved to: {output_file_name}")
    except ValueError as ve:
        print(f"Config Error: {ve}")
    except Exception as e:
        print(f"An error occurred: {e}")