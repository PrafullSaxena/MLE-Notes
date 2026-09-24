"""
Resilient asynchronous HTTP Fetcher module.
Implements polite pacing, concurrency control, exponential backoff with full jitter,
and status-code-aware error recovery.
"""

import asyncio
import logging
import random
from typing import Optional
import httpx
from config import ScraperConfig

logger = logging.getLogger("scraper.fetcher")


try:
    import h2
    HAS_HTTP2 = True
except ImportError:
    HAS_HTTP2 = False


class ResilientFetcher:
    """
    Production-grade HTTP client engine designed for high reliability and politeness.
    """

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrency)
        self.client: Optional[httpx.AsyncClient] = None
        self._inter_request_delay = 1.0 / max(0.1, config.requests_per_second)

    async def __aenter__(self):
        """Initializes the underlying HTTPX AsyncClient with HTTP/2 and connection pooling."""
        limits = httpx.Limits(
            max_keepalive_connections=self.config.max_concurrency,
            max_connections=self.config.max_concurrency * 2,
            keepalive_expiry=30.0,
        )
        self.client = httpx.AsyncClient(
            headers=self.config.headers,
            timeout=httpx.Timeout(self.config.timeout_seconds),
            follow_redirects=True,
            http2=HAS_HTTP2,
            limits=limits,
            proxy=self.config.proxy_url,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Safely disposes client connections."""
        if self.client:
            await self.client.aclose()

    async def fetch(self, url: str) -> Optional[str]:
        """
        Fetches the HTML content of the provided URL.
        Retries on transient server errors or network disconnects with exponential backoff and jitter.
        Returns the response text on success, or None on fatal failure.
        """
        if not self.client:
            raise RuntimeError("Fetcher must be used within an 'async with' context block.")

        async with self.semaphore:
            for attempt in range(1, self.config.max_retries + 1):
                try:
                    # 1. Polite pacing with randomized micro-jitter
                    pacing_jitter = random.uniform(0.05, 0.25)
                    await asyncio.sleep(self._inter_request_delay + pacing_jitter)

                    logger.debug(f"[FETCH START] {url} (Attempt {attempt})")
                    response = await self.client.get(url)

                    # Status 200 OK -> Immediate success
                    if response.status_code == 200:
                        logger.info(f"[200 OK] {url} ({len(response.content)} bytes)")
                        return response.text

                    # Status 429 Too Many Requests -> Respect Retry-After header
                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", 5.0))
                        logger.warning(
                            f"[429 RATE LIMIT] {url} - Server requested pause for {retry_after}s"
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    # Transient Server Errors (500, 502, 503, 504) -> Eligible for retry
                    if response.status_code in {500, 502, 503, 504}:
                        logger.warning(
                            f"[{response.status_code} TRANSIENT SERVER ERROR] {url} (Attempt {attempt}/{self.config.max_retries})"
                        )
                    elif response.status_code in {403, 404}:
                        # Client / Permissions error (Won't be fixed by retrying)
                        logger.error(
                            f"[{response.status_code} FATAL CLIENT ERROR] {url}. Aborting request."
                        )
                        return None
                    else:
                        logger.warning(
                            f"[{response.status_code} UNEXPECTED STATUS] {url} (Attempt {attempt}/{self.config.max_retries})"
                        )

                except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as net_err:
                    logger.warning(
                        f"[NETWORK TIMEOUT/ERROR] {url}: {net_err} (Attempt {attempt}/{self.config.max_retries})"
                    )
                except Exception as exc:
                    logger.error(
                        f"[UNEXPECTED EXCEPTION] {url}: {exc} (Attempt {attempt}/{self.config.max_retries})"
                    )

                # Exponential backoff with full randomized jitter:
                # delay = uniform(0.5, 1.0) * min(max_backoff, base * 2^(attempt - 1))
                backoff_cap = min(
                    self.config.max_backoff_seconds,
                    self.config.base_backoff_seconds * (2 ** (attempt - 1)),
                )
                jittered_delay = random.uniform(0.5, 1.0) * backoff_cap
                logger.info(f"Backing off for {jittered_delay:.2f}s before next attempt...")
                await asyncio.sleep(jittered_delay)

            logger.error(f"[FETCH FAILED] Exhausted all {self.config.max_retries} attempts for: {url}")
            return None
