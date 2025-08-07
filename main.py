#!/usr/bin/env python3
"""
Main script to orchestrate the web scraping and analysis process.
"""

import sys
import json
from scripts.collect_data import WebScraper
from scripts.add_summaries import AnalyseData
from scripts.convert_json_to_csv import convert_json_to_csv
import os

COLLECT_CONFIG_PATH = "examples/collect_example.ini" # TODO: Change to collect.ini
ANALYSE_CONFIG_PATH = "examples/summary_example.ini" # TODO: Change to analyse.ini
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Path to main.py
FILE_NAME = os.path.join(BASE_DIR, "data", "all_articles")
UPDATE_TODAY_ONLY = True
DATE_RANGE_FLAG = False

def run_collect_data():
    print("--- Starting Data Collection ---")
    # Get output file name
    scraped_data_file = FILE_NAME

    try:
        scraper = WebScraper(COLLECT_CONFIG_PATH)
        all_articles = scraper.scrape_all_sites(scraped_data_file, UPDATE_TODAY_ONLY, DATE_RANGE_FLAG)

        print(f"✓ Results saved to: {scraped_data_file}")
    except ValueError as ve:
        print(f"Config Error: {ve}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}\nData collection failed. Exiting.")
        sys.exit(1)

    # Ask the user if they want to save the web scraped .json as a .csv
    save_to_csv = ""
    while save_to_csv.lower() not in ['y', 'n']:
        save_to_csv = input("Would you to save the initial web scrapped .json as a .csv? (y/n): ")

    if save_to_csv.lower() == 'y':
        # Save as a .csv
        print("--- Saving Data Collection to csv format ---")
        convert_json_to_csv(all_articles, scraped_data_file + ".csv", False) # Always re-write file


    print("\n--- Data Collection Complete ---")
    return scraped_data_file

def run_analysis(scraped_data_file):
    print("\n--- Starting Analysis ---")
    try:
        # Pass the scraped file directly to the analysis class
        analyser = AnalyseData(input_json=scraped_data_file, config_path=ANALYSE_CONFIG_PATH)
        analysed_json = analyser.run()
        print("\n--- ✓ Analysis Complete ---")
    except Exception as e:
        print(f"An error occurred during analysis: {e}")
        sys.exit(1)

    print("\n--- Converting to CSV format ---")
    try:
        with open(analysed_json, "r", encoding="utf-8") as f:
            analysed_data = json.load(f)  # e.g. a list of JSON objects
        csv_output_name = analysed_json[:-5] + ".csv"
        convert_json_to_csv(analysed_data, csv_output_name, UPDATE_TODAY_ONLY)

        print(f"✓ All results saved to {csv_output_name}")
    except Exception as e:
        print(f"An error occurred during converting json to csv format: {e}")
        sys.exit(1)

def main():
    """
    This script first runs the web scraper to collect articles,
    and then asks the user if they want to proceed with analysing the results.
    """

    # Run news article web scraping
    web_scraped_json = run_collect_data()

    # Ask the user if they want to analyse the results
    analyse = ""
    while analyse.lower() not in ['y', 'n']:
        analyse = input("Would you like AWS Bedrock (AI) to analyse the results? (y/n): ")

    if analyse.lower() == 'n':
        print("Exiting.")
        sys.exit(0)

    # Run analysis of web scrapped file
    run_analysis(web_scraped_json)
    

if __name__ == "__main__":
    main()