"""Utility functions for bskybook."""

import logging
import re
from typing import Optional
from urllib.parse import urlparse


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application.

    Args:
        verbose: If True, set logging level to DEBUG, otherwise INFO
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=level
    )


def extract_handle_from_url(url: str) -> str:
    """Extract BlueSky handle from a profile URL or return the handle as-is.

    Args:
        url: BlueSky profile URL or handle (e.g., 'https://bsky.app/profile/republik.ch' or 'republik.ch')

    Returns:
        The handle (e.g., 'republik.ch')

    Examples:
        >>> extract_handle_from_url('https://bsky.app/profile/republik.ch')
        'republik.ch'
        >>> extract_handle_from_url('republik.ch')
        'republik.ch'
    """
    # If it's already just a handle (no protocol), return it
    if not url.startswith(('http://', 'https://')):
        return url

    # Parse URL and extract handle from path
    parsed = urlparse(url)
    if 'bsky.app' in parsed.netloc and '/profile/' in parsed.path:
        handle = parsed.path.replace('/profile/', '').strip('/')
        return handle

    # If we can't parse it, return as-is and let the API handle it
    return url


def extract_links(text: str) -> list[str]:
    """Extract URLs from text.

    Args:
        text: Text that may contain URLs

    Returns:
        List of URLs found in the text
    """
    # Regular expression to match URLs
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    return url_pattern.findall(text)


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing or replacing invalid characters.

    Args:
        filename: The filename to sanitize

    Returns:
        A safe filename
    """
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to a maximum length, adding ellipsis if needed.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'
