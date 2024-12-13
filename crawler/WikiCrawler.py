#!/usr/bin/python3
"""
A crawler to get data from wikipedia.

:Copyright:
    Copyright 2023 A-Insights.  All Rights Reserved.
"""
import os
import logging
import time
import mariadb
import requests
from bs4 import BeautifulSoup


LOGGER_NAME = "wiki_crawler"


class WikiCrawler:
    """
    A crawler that extracts data from Wikipedia pages then saves the data in MariaDB.
    """
    def __init__(self):
        """
        Initialize the WikiCrawler.
        """
        self._logger = logging.getLogger(LOGGER_NAME)
        logging.basicConfig(level=logging.INFO)

    @staticmethod
    def get_crawl_list():
        # Sleep for 10 seconds in case the crawler starts too fast while MariaDB is not ready.
        time.sleep(10)
        return [
            'https://en.wikipedia.org/wiki/Winged_Victory_of_Samothrace',
            'https://en.wikipedia.org/wiki/Girl_with_a_Pearl_Earring',
            'https://en.wikipedia.org/wiki/Elden_Ring'
        ]

    def crawl(self, url):
        """
        Main crawling function, get the title, summary (first paragraph), and the main image URL of the Wikipedia page.

        :param url: The URL of the Wikipedia page to crawl
        :return: A dictionary with title, summary, and images or None if an error occurs
        """
        try:
            response = requests.get(url, timeout=10)  # Set timeout for request
            response.raise_for_status()  # Raise exception for HTTP errors
        except requests.RequestException as e:
            self._logger.error(f"Failed to fetch URL {url}: {e}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Get main title
        main_title = soup.find("h1", {"id": "firstHeading"})
        if main_title:
            main_title = main_title.get_text(strip=True)
        else:
            self._logger.warning(f"Title not found for {url}")
            main_title = "Unknown Title"

        # Get summary (the first paragraph)
        mw_parser_output = soup.select_one("div.mw-parser-output")
        stop_div = mw_parser_output.find("div", class_="mw-heading mw-heading2") if mw_parser_output else None

        paragraphs_before = []
        if mw_parser_output and stop_div:
            # Iterate through elements until we reach stop_div
            for element in mw_parser_output.children:
                if element == stop_div:
                    break
                if element.name == 'p':
                    text = element.get_text(strip=True)
                    if text:
                        paragraphs_before.append(text)
        else:
            # If no stop_div is found, fall back to grabbing all paragraphs
            paragraphs = soup.select("div.mw-parser-output > p")
            paragraphs_before = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]

        summary_text = "\n".join(paragraphs_before)

       
        # Get the main image from the infobox if present
        main_image_url = None
        infobox = soup.find('table', class_='infobox')
        if infobox:
            img = infobox.find('img')
            if img and img.get('src'):
                main_image_url = img['src']
                if main_image_url.startswith('//'):
                    main_image_url = 'https:' + main_image_url

        images = [main_image_url] if main_image_url else []

        self._logger.info(f"Crawled data from {url}")
        return {"title": main_title, "summary": summary_text, "images": images}

    def save(self, article):
        """
        Save the Wikipedia data to the table 'wiki_articles'

        :param article: A dictionary containing article data
        """
        if not article:
            self._logger.error("No article data to save.")
            return
        
        # Fetch database credentials from environment variables
        db_user = os.getenv("MARIADB_USER", "crawler")
        db_password = os.getenv("MARIADB_PASSWORD", "a-insights")
        db_host = os.getenv("MARIADB_HOST", "mariadb") 
        db_name = os.getenv("MARIADB_DATABASE", "crawler_dev")

        conn = None  # Initialize conn to None

        try:
            conn = mariadb.connect(
                user=db_user,
                password=db_password,
                host=db_host,
                port=3306,
                database=db_name
            )
            cursor = conn.cursor()

            # Insert the article data
            # Join images with a newline if there are multiple, but here we generally expect only one main image.
            cursor.execute("""
                INSERT INTO wiki_articles (title, summary, image_url)
                VALUES (?, ?, ?)
            """, (article["title"], article["summary"], "\n".join(article["images"])))

            conn.commit()
            self._logger.info(f"Saved article '{article['title']}' to the database.")
        except mariadb.Error as e:
            self._logger.error(f"Database error: {e}")
        finally:
            if conn:
                conn.close()

    def run(self):
        """
        Start the WikiCrawler.
        """
        crawl_list = self.get_crawl_list()

        for url in crawl_list:
            article = self.crawl(url)
            if article:
                self.save(article)


if __name__ == '__main__':
    crawler = WikiCrawler()
    crawler.run()
