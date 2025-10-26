"""BlueSky API client for fetching posts."""

import logging
from typing import Any, Optional
from dataclasses import dataclass

import requests

from bskybook.utils import extract_links

logger = logging.getLogger(__name__)


@dataclass
class Post:
    """Represents a BlueSky post."""
    uri: str
    text: str
    links: list[str]
    created_at: str
    author: str


class BlueSkyClient:
    """Client for interacting with the BlueSky public API."""

    API_BASE = "https://public.api.bsky.app/xrpc"

    def __init__(self, timeout: int = 30):
        """Initialize the BlueSky client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'bskybook/0.1.0'
        })

    def get_author_feed(self, handle: str, limit: int = 20) -> list[Post]:
        """Fetch posts from an author's feed.

        Args:
            handle: The BlueSky handle (e.g., 'republik.ch')
            limit: Maximum number of posts to fetch (default 20)

        Returns:
            List of Post objects

        Raises:
            requests.RequestException: If the API request fails
        """
        logger.info(f"Fetching {limit} posts from @{handle}")

        url = f"{self.API_BASE}/app.bsky.feed.getAuthorFeed"
        params = {
            "actor": handle,
            "limit": limit
        }

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            posts = []
            feed_items = data.get("feed", [])

            logger.info(f"Retrieved {len(feed_items)} posts from API")

            for item in feed_items:
                post_data = item.get("post", {})
                record = post_data.get("record", {})

                # Extract text content
                text = record.get("text", "")

                # Extract links from text
                links = extract_links(text)

                # Also check for embedded links
                embed = record.get("embed", {})
                if embed and "external" in embed:
                    external_uri = embed["external"].get("uri")
                    if external_uri and external_uri not in links:
                        links.append(external_uri)

                # Skip posts without links
                if not links:
                    logger.debug(f"Skipping post without links: {text[:50]}...")
                    continue

                post = Post(
                    uri=post_data.get("uri", ""),
                    text=text,
                    links=links,
                    created_at=record.get("createdAt", ""),
                    author=handle
                )
                posts.append(post)

            logger.info(f"Found {len(posts)} posts with links")
            return posts

        except requests.RequestException as e:
            logger.error(f"Failed to fetch posts from @{handle}: {e}")
            raise

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
