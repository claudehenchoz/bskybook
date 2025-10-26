"""Command-line interface for bskybook."""

import logging
from pathlib import Path
from typing import Optional

import click

from bskybook.bluesky import BlueSkyClient
from bskybook.content import ContentExtractor
from bskybook.cover import CoverGenerator
from bskybook.epub import EPUBGenerator
from bskybook.utils import extract_handle_from_url, setup_logging, sanitize_filename

logger = logging.getLogger(__name__)


@click.command()
@click.argument('profile')
@click.option(
    '--count', '-c',
    default=20,
    type=int,
    help='Number of posts to fetch (default: 20)'
)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    help='Output EPUB file path (default: <handle>.epub)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
def main(profile: str, count: int, output: Optional[Path], verbose: bool) -> None:
    """Create an EPUB ebook from a BlueSky feed.

    PROFILE can be either a BlueSky handle (e.g., 'republik.ch') or
    a full profile URL (e.g., 'https://bsky.app/profile/republik.ch').

    Examples:

        bskybook republik.ch

        bskybook https://bsky.app/profile/republik.ch --count 30

        bskybook republik.ch --output my-book.epub --verbose
    """
    # Setup logging
    setup_logging(verbose)

    # Extract handle from URL or use as-is
    handle = extract_handle_from_url(profile)
    logger.info(f"Processing feed for @{handle}")

    # Determine output path
    if output is None:
        safe_handle = sanitize_filename(handle)
        output = Path(f"{safe_handle}.epub")

    try:
        # Step 1: Fetch posts from BlueSky
        click.echo(f"Fetching {count} posts from @{handle}...")
        with BlueSkyClient() as client:
            posts = client.get_author_feed(handle, limit=count)

        if not posts:
            click.echo("No posts with links found.", err=True)
            return

        click.echo(f"Found {len(posts)} posts with links")

        # Step 2: Extract all unique links
        all_links = []
        for post in posts:
            all_links.extend(post.links)

        # Remove duplicates while preserving order
        unique_links = list(dict.fromkeys(all_links))
        click.echo(f"Extracting content from {len(unique_links)} unique links...")

        # Step 3: Extract article content
        with click.progressbar(
            unique_links,
            label='Extracting articles',
            show_pos=True
        ) as links:
            with ContentExtractor() as extractor:
                articles = []
                for link in links:
                    article = extractor.extract_article(link)
                    if article:
                        articles.append(article)

        if not articles:
            click.echo("No articles could be extracted.", err=True)
            return

        click.echo(f"Successfully extracted {len(articles)} articles")

        # Step 4: Generate cover
        click.echo("Generating cover image...")
        with CoverGenerator() as cover_gen:
            cover_data = cover_gen.generate_cover(
                articles,
                title=f"{handle} - BlueSky Book"
            )

        # Step 5: Create EPUB
        click.echo(f"Creating EPUB file: {output}")
        generator = EPUBGenerator()
        generator.create_epub(
            articles=articles,
            title=f"{handle} - BlueSky Book",
            author=f"@{handle}",
            cover_data=cover_data,
            output_path=output
        )

        click.echo(f"Successfully created: {output}")
        click.echo(f"  Articles: {len(articles)}")
        click.echo(f"  Size: {output.stat().st_size / 1024:.1f} KB")

    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        raise SystemExit(1)
    except Exception as e:
        logger.exception("An error occurred")
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
