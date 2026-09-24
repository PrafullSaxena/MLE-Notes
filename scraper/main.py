"""
Main orchestrator and execution entry point for the production web scraper.
Coordinates the URL crawler loop, fetcher, parser, schema validation, and storage pipeline.

Usage:
    python main.py
    python main.py --pages 3 --concurrency 2
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

from config import ScraperConfig
from fetcher import ResilientFetcher
from parser import QuotesParser
from pipeline import JsonLinesPipeline

# Configure structured, human-readable logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)-15s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("scraper.main")


async def run_crawler(config: ScraperConfig):
    """
    Main crawling loop:
    1. Traverses pagination links safely.
    2. Enforces concurrency and politeness constraints.
    3. Parses and validates every extracted entity.
    4. Streams data directly to disk without memory buildup.
    """
    start_time = time.perf_counter()
    logger.info("=" * 60)
    logger.info("🚀 STARTING PRODUCTION SCRAPER RUN")
    logger.info(f"Target Base URL     : {config.base_url}")
    logger.info(f"Max Pages to Crawl  : {config.max_pages}")
    logger.info(f"Max Concurrency     : {config.max_concurrency}")
    logger.info(f"Rate Limit Pace     : {config.requests_per_second} req/s")
    logger.info(f"Output File         : {config.output_filepath}")
    logger.info("=" * 60)

    # Resolve output paths relative to this script directory
    script_dir = Path(__file__).parent
    jsonl_output_path = script_dir / config.output_filepath
    json_output_path = jsonl_output_path.with_suffix(".json")

    # If an existing output file exists, remove it for a clean run demonstration
    if jsonl_output_path.exists():
        jsonl_output_path.unlink()

    total_quotes_scraped = 0
    pages_visited = 0
    current_url = f"{config.base_url}/page/{config.start_page}/"

    # Instantiate async context managers
    async with ResilientFetcher(config) as fetcher:
        async with JsonLinesPipeline(str(jsonl_output_path)) as pipeline:

            while current_url and pages_visited < config.max_pages:
                pages_visited += 1
                logger.info(f"--- [PAGE {pages_visited}/{config.max_pages}] Crawling: {current_url} ---")

                # Step 1: Fetch HTML via resilient client
                html_body = await fetcher.fetch(current_url)
                if not html_body:
                    logger.warning(f"Failed to retrieve page {current_url}. Stopping crawl.")
                    break

                # Step 2: Parse and validate items using schema
                items, next_page_url = QuotesParser.parse_page(html_body, current_url)
                logger.info(f"Extracted {len(items)} validated items from page {pages_visited}.")

                # Step 3: Stream to disk via pipeline
                if items:
                    await pipeline.write_items(items)
                    total_quotes_scraped += len(items)

                # Step 4: Advance to next discovered pagination link
                if not next_page_url:
                    logger.info("No next page link found. Reached end of catalog.")
                    break

                current_url = next_page_url

    elapsed_time = time.perf_counter() - start_time

    # Export a formatted .json file alongside the .jsonl for convenience
    JsonLinesPipeline.export_to_standard_json(
        str(jsonl_output_path), str(json_output_path), indent=2
    )

    # Print final summary metrics
    logger.info("=" * 60)
    logger.info("🏁 SCRAPING JOB COMPLETE")
    logger.info(f"Total Pages Crawled : {pages_visited}")
    logger.info(f"Total Items Saved   : {total_quotes_scraped}")
    logger.info(f"Elapsed Time        : {elapsed_time:.2f} seconds")
    if elapsed_time > 0:
        logger.info(f"Throughput Rate     : {total_quotes_scraped / elapsed_time:.2f} items/second")
    logger.info(f"Streaming Output    : {jsonl_output_path}")
    logger.info(f"Formatted JSON      : {json_output_path}")
    logger.info("=" * 60)


def parse_cli_args() -> ScraperConfig:
    """Parses optional command-line flags to override default config."""
    parser = argparse.ArgumentParser(description="Production-Grade Web Scraper")
    parser.add_argument(
        "--pages",
        type=int,
        default=3,
        help="Number of pages to crawl (default: 3)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help="Maximum concurrent connections (default: 2)",
    )
    parser.add_argument(
        "--rps",
        type=float,
        default=2.0,
        help="Target requests per second (default: 2.0)",
    )
    args = parser.parse_args()

    cfg = ScraperConfig(
        max_pages=args.pages,
        max_concurrency=args.concurrency,
        requests_per_second=args.rps,
    )
    return cfg


if __name__ == "__main__":
    config = parse_cli_args()
    try:
        asyncio.run(run_crawler(config))
    except KeyboardInterrupt:
        logger.warning("\nScraper stopped by user. Existing saved items remain safely intact.")
