"""
Storage pipeline module.
Implements streaming, append-only JSON Lines (.jsonl) persistence with periodic flushing,
plus an export utility to convert .jsonl to standard formatted .json.
"""

import json
import logging
from pathlib import Path
from typing import List
import aiofiles
from models import QuoteItem

logger = logging.getLogger("scraper.pipeline")


class JsonLinesPipeline:
    """
    Streaming storage engine writing newline-delimited JSON (JSON Lines).
    Key Advantages:
    1. Append-only O(1) writes - zero memory overhead even for millions of items.
    2. Crash-resilient - if the scraper is stopped at any time, previously written rows remain valid.
    3. Direct compatibility with PySpark, Pandas, and Milvus vector ingestion pipelines.
    """

    def __init__(self, filepath: str, flush_interval: int = 5):
        self.filepath = Path(filepath)
        self.flush_interval = flush_interval
        self._file = None
        self.total_written = 0

    async def __aenter__(self):
        # Open file in append mode with UTF-8 encoding
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self._file = await aiofiles.open(self.filepath, mode="a", encoding="utf-8")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._file:
            await self._file.flush()
            await self._file.close()
            logger.info(f"Closed pipeline file: {self.filepath} (Total: {self.total_written} items)")

    async def write_items(self, items: List[QuoteItem]) -> int:
        """Writes a batch of validated items to disk."""
        if not self._file:
            raise RuntimeError("Pipeline must be opened using 'async with JsonLinesPipeline(...)'.")

        for item in items:
            # model_dump_json serializes Pydantic model directly to JSON string
            line = item.model_dump_json() + "\n"
            await self._file.write(line)
            self.total_written += 1

        # Periodic flush to ensure data is physically committed to OS disk cache
        if self.total_written % self.flush_interval == 0:
            await self._file.flush()

        return len(items)

    @staticmethod
    def export_to_standard_json(jsonl_path: str, json_path: str, indent: int = 2) -> int:
        """
        Utility method to convert a streaming .jsonl file into a pretty-printed standard .json array.
        """
        records = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=indent, ensure_ascii=False)

        logger.info(f"Exported {len(records)} records from {jsonl_path} -> {json_path}")
        return len(records)
