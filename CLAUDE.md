# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

bskybook is a Python CLI tool that creates EPUB 2 ebooks from BlueSky feeds. It fetches posts from a BlueSky account, extracts links, scrapes article content, and generates a properly formatted EPUB with a mosaic cover generated from article thumbnails.

## Development Setup

Install dependencies and package:
```bash
pip install -r requirements.txt
pip install -e .
```

Run the tool:
```bash
# Basic usage
bskybook https://bsky.app/profile/republik.ch

# With options
bskybook republik.ch --count 30 --output my-book.epub --verbose
```

## Architecture

The codebase follows a modular pipeline architecture with five main stages:

### Core Modules

1. **cli.py**: Entry point using Click framework
   - Orchestrates the entire pipeline
   - Handles CLI arguments and progress display
   - Implements the main workflow: fetch → extract → generate cover → create EPUB

2. **bluesky.py**: BlueSky API client
   - Uses anonymous public API (no auth required)
   - Fetches posts via `app.bsky.feed.getAuthorFeed` endpoint
   - Extracts links from post text and embedded external links
   - Returns `Post` dataclass instances with filtered posts (only those with links)

3. **content.py**: Article extraction
   - Uses `trafilatura` library for content extraction
   - Extracts both markdown and HTML versions
   - Scrapes og:image meta tags for thumbnails
   - Returns `Article` dataclass with url, title, content, metadata, and thumbnail_url

4. **cover.py**: Cover image generation
   - Downloads thumbnail images from articles
   - Creates a 2-column mosaic layout (1264x1680 resolution for e-readers)
   - Uses center-crop strategy to fill cells completely with no whitespace
   - Adds title overlay with semi-transparent background at bottom
   - Falls back to simple text cover if no images available

5. **epub.py**: EPUB 2 file generation
   - Generates compliant EPUB 2 structure with proper XML namespaces
   - Creates mimetype, container.xml, content.opf, and toc.ncx
   - Converts article HTML to XHTML 1.1 with embedded CSS
   - Includes cover page and all articles in proper spine order
   - Uses lxml for XML generation and zipfile for EPUB packaging

6. **utils.py**: Utility functions
   - `extract_handle_from_url()`: Parses BlueSky profile URLs
   - `extract_links()`: Regex-based URL extraction from text
   - `sanitize_filename()`: Makes filenames safe for filesystem

### Data Flow

```
BlueSky API → Posts (with links) → ContentExtractor → Articles (with content + thumbnails)
                                                            ↓
                                                      CoverGenerator
                                                            ↓
                                                   mosaic cover image
                                                            ↓
                                           EPUBGenerator → EPUB file
```

### Key Design Decisions

- **Context managers**: All HTTP-based classes (BlueSkyClient, ContentExtractor, CoverGenerator) implement context manager protocol for proper resource cleanup
- **Type hints**: Full type annotations throughout for better maintainability
- **Error handling**: Individual article extraction failures don't stop the pipeline; only articles that successfully extract are included
- **EPUB 2 compliance**: Uses XHTML 1.1 strict DTD, proper OPF package structure, and NCX navigation as required by EPUB 2 spec
- **Image handling**: Cover generation uses center-crop strategy to ensure mosaic fills completely without whitespace, optimal for landscape article thumbnails in portrait book layout

## Testing Considerations

When testing changes:
- Test with `https://bsky.app/profile/republik.ch` (the canonical test feed)
- Verify EPUB validity using tools like `epubcheck` if available
- Check that failed article extractions don't crash the entire pipeline
- Ensure cover generation handles missing/invalid images gracefully
