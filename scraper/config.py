"""
Configuration module for the production web scraper.
Controls target URLs, concurrency limits, politeness delays, backoff parameters, and browser headers.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ScraperConfig:
    """Production scraper configuration parameters."""

    # Target & Pagination
    base_url: str = "https://quotes.toscrape.com"
    start_page: int = 1
    max_pages: int = 5  # Safe default for testing; set higher for full crawl

    # Concurrency & Politeness Rate Limiting
    # Never DDoS a website: Keep concurrency reasonable (2-5)
    max_concurrency: int = 3
    # Target requests per second across all workers
    requests_per_second: float = 2.0

    # Network Timeouts & Resilience
    timeout_seconds: float = 15.0
    max_retries: int = 4
    base_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 16.0

    # Storage Settings
    output_filepath: str = "scraped_quotes.jsonl"
    flush_every_n_items: int = 5

    # Optional Proxy (e.g. "http://username:password@proxy.example.com:8080")
    proxy_url: Optional[str] = None

    # Realistic Browser Headers (mimics Google Chrome on macOS)
    # Note: Do NOT manually set 'Accept-Encoding' in httpx or requests,
    # as the HTTP client automatically negotiates and decompresses gzip/deflate/brotli.
    headers: Dict[str, str] = field(
        default_factory=lambda: {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
    )
