"""
Data validation models using Pydantic V2.
Enforces strict schema validation, type safety, text cleaning, and metadata injection.
"""

from datetime import datetime, timezone
from typing import List
from pydantic import BaseModel, Field, HttpUrl, field_validator


class QuoteItem(BaseModel):
    """
    Schema representing a single extracted quote item.
    Guarantees that corrupt or malformed entries are caught before touching the storage pipeline.
    """

    quote_text: str = Field(
        ...,
        min_length=3,
        description="The clean quotation text without typographical marks",
    )
    author_name: str = Field(
        ...,
        min_length=2,
        description="Full name of the author",
    )
    author_url: HttpUrl = Field(
        ...,
        description="Absolute URL pointing to the author's biography page",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="List of topical category tags associated with the quote",
    )
    source_page_url: HttpUrl = Field(
        ...,
        description="The source web page where this record was extracted from",
    )
    scraped_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of extraction",
    )

    @field_validator("quote_text", mode="before")
    def sanitize_quote(cls, value: str) -> str:
        """Strip typographical quotation marks and normalize whitespace."""
        if isinstance(value, str):
            # Remove fancy unicode quotation marks and spaces
            cleaned = value.strip(" \t\n\r“”\"'«»")
            return " ".join(cleaned.split())
        return value

    @field_validator("author_name", mode="before")
    def sanitize_author(cls, value: str) -> str:
        """Trim and clean author string."""
        if isinstance(value, str):
            return " ".join(value.strip().split())
        return value

    @field_validator("tags", mode="before")
    def normalize_tags(cls, tags: List[str]) -> List[str]:
        """Deduplicate and clean tag tokens."""
        if isinstance(tags, list):
            cleaned_tags = []
            for t in tags:
                if isinstance(t, str):
                    clean_t = t.strip().lower()
                    if clean_t and clean_t not in cleaned_tags:
                        cleaned_tags.append(clean_t)
            return cleaned_tags
        return []
