"""
High-performance HTML parsing and schema extraction module.
Uses selectolax (C-based Modest/Lexbor engine, 10x-30x faster than BeautifulSoup)
and falls back gracefully to BeautifulSoup4 if needed.
"""

import logging
from typing import List, Optional, Tuple
from urllib.parse import urljoin
from models import QuoteItem

logger = logging.getLogger("scraper.parser")

# Attempt high-performance selectolax first; fallback to bs4
try:
    from selectolax.parser import HTMLParser
    HAS_SELECTOLAX = True
except ImportError:
    from bs4 import BeautifulSoup
    HAS_SELECTOLAX = False


class QuotesParser:
    """Extracts quotes and pagination links from HTML content."""

    @classmethod
    def parse_page(
        cls, html_content: str, base_url: str
    ) -> Tuple[List[QuoteItem], Optional[str]]:
        """
        Parses an HTML page, extracting:
        1. A list of validated QuoteItem objects.
        2. The URL of the next page (if pagination exists).
        """
        if HAS_SELECTOLAX:
            return cls._parse_with_selectolax(html_content, base_url)
        else:
            return cls._parse_with_beautifulsoup(html_content, base_url)

    @classmethod
    def _parse_with_selectolax(
        cls, html_content: str, base_url: str
    ) -> Tuple[List[QuoteItem], Optional[str]]:
        tree = HTMLParser(html_content)
        items: List[QuoteItem] = []

        # Find all quote cards
        cards = tree.css("div.quote")
        for card in cards:
            try:
                # Text node
                text_node = card.css_first("span.text")
                quote_text = text_node.text() if text_node else ""

                # Author node
                author_node = card.css_first("small.author")
                author_name = author_node.text() if author_node else ""

                # Author bio link
                bio_link_node = card.css_first("a[href*='/author/']")
                raw_author_url = bio_link_node.attributes.get("href", "") if bio_link_node else ""
                author_url = urljoin(base_url, raw_author_url)

                # Tags
                tag_nodes = card.css("div.tags a.tag")
                tags = [t.text() for t in tag_nodes if t.text()]

                # Validate and construct QuoteItem model
                item = QuoteItem(
                    quote_text=quote_text,
                    author_name=author_name,
                    author_url=author_url,
                    tags=tags,
                    source_page_url=base_url,
                )
                items.append(item)

            except Exception as err:
                logger.warning(f"Skipping malformed quote card: {err}")

        # Check for next page link
        next_button = tree.css_first("li.next a")
        next_page_url = None
        if next_button:
            href = next_button.attributes.get("href")
            if href:
                next_page_url = urljoin(base_url, href)

        return items, next_page_url

    @classmethod
    def _parse_with_beautifulsoup(
        cls, html_content: str, base_url: str
    ) -> Tuple[List[QuoteItem], Optional[str]]:
        soup = BeautifulSoup(html_content, "html.parser")
        items: List[QuoteItem] = []

        cards = soup.select("div.quote")
        for card in cards:
            try:
                text_elem = card.select_one("span.text")
                quote_text = text_elem.get_text() if text_elem else ""

                author_elem = card.select_one("small.author")
                author_name = author_elem.get_text() if author_elem else ""

                bio_elem = card.select_one("a[href*='/author/']")
                raw_bio = bio_elem["href"] if bio_elem and "href" in bio_elem.attrs else ""
                author_url = urljoin(base_url, raw_bio)

                tag_elems = card.select("div.tags a.tag")
                tags = [t.get_text() for t in tag_elems]

                item = QuoteItem(
                    quote_text=quote_text,
                    author_name=author_name,
                    author_url=author_url,
                    tags=tags,
                    source_page_url=base_url,
                )
                items.append(item)
            except Exception as err:
                logger.warning(f"Skipping malformed quote card: {err}")

        next_elem = soup.select_one("li.next a")
        next_page_url = None
        if next_elem and "href" in next_elem.attrs:
            next_page_url = urljoin(base_url, next_elem["href"])

        return items, next_page_url
