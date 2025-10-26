"""Content extraction and processing using trafilatura."""

import logging
from dataclasses import dataclass
from typing import Optional

import requests
import trafilatura
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class Article:
    """Represents an extracted article."""
    url: str
    title: str
    content_markdown: str
    content_html: str
    author: Optional[str] = None
    date: Optional[str] = None
    thumbnail_url: Optional[str] = None


class ContentExtractor:
    """Extracts and processes content from URLs."""

    def __init__(self, timeout: int = 30):
        """Initialize the content extractor.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def extract_article(self, url: str) -> Optional[Article]:
        """Extract article content from a URL.

        Args:
            url: The URL to extract content from

        Returns:
            Article object if successful, None otherwise
        """
        logger.info(f"Extracting content from: {url}")

        try:
            # Fetch the page
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            html = response.text

            # Extract main content using trafilatura
            # Use simple extract first
            markdown = trafilatura.extract(
                html,
                url=url,
                include_comments=False,
                include_tables=True,
                include_images=True,
                output_format='markdown'
            )

            if not markdown:
                logger.warning(f"No content extracted from {url}")
                return None

            # Get HTML version (we'll convert to XHTML later)
            html_content = trafilatura.extract(
                html,
                url=url,
                include_comments=False,
                include_tables=True,
                include_images=True,
                output_format='html'
            )

            if not html_content:
                html_content = f"<p>{markdown.replace('\n\n', '</p><p>')}</p>"

            # Extract metadata
            metadata = trafilatura.bare_extraction(
                html,
                url=url,
                with_metadata=True,
                include_comments=False,
                include_tables=False,
                include_images=False
            )

            # Get title and other metadata
            title = 'Untitled'
            author = None
            date = None

            if metadata:
                # Handle both dict and object responses
                if isinstance(metadata, dict):
                    title = metadata.get('title', 'Untitled')
                    author = metadata.get('author')
                    date = metadata.get('date')
                else:
                    # It's a Document object
                    title = getattr(metadata, 'title', 'Untitled') or 'Untitled'
                    author = getattr(metadata, 'author', None)
                    date = getattr(metadata, 'date', None)

            # Extract og:image for cover
            thumbnail = self._extract_thumbnail(html)

            article = Article(
                url=url,
                title=title,
                content_markdown=markdown,
                content_html=html_content,
                author=author,
                date=date,
                thumbnail_url=thumbnail
            )

            logger.info(f"Successfully extracted: {article.title}")
            return article

        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to extract content from {url}: {e}")
            return None

    def _extract_thumbnail(self, html: str) -> Optional[str]:
        """Extract og:image or other thumbnail URLs from HTML.

        Args:
            html: The HTML content

        Returns:
            Thumbnail URL if found, None otherwise
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Try og:image first
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                return og_image['content']

            # Try twitter:image
            twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
            if twitter_image and twitter_image.get('content'):
                return twitter_image['content']

            # Try finding first image in content
            img = soup.find('img')
            if img and img.get('src'):
                return img['src']

            return None

        except Exception as e:
            logger.debug(f"Failed to extract thumbnail: {e}")
            return None

    def extract_multiple(self, urls: list[str]) -> list[Article]:
        """Extract content from multiple URLs.

        Args:
            urls: List of URLs to extract

        Returns:
            List of successfully extracted Article objects
        """
        articles = []
        for url in urls:
            article = self.extract_article(url)
            if article:
                articles.append(article)

        logger.info(f"Successfully extracted {len(articles)} out of {len(urls)} articles")
        return articles

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
