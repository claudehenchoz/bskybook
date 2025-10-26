# bskybook

Create beautiful EPUB 2 ebooks from BlueSky feeds.

## Features

- Fetch recent posts from any BlueSky account
- Extract and scrape linked articles
- Convert content to well-formatted EPUB 2
- Generate beautiful mosaic covers from article thumbnails
- Clean, maintainable codebase with type hints

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

## Usage

Basic usage:
```bash
bskybook https://bsky.app/profile/republik.ch
```

Specify number of posts:
```bash
bskybook https://bsky.app/profile/republik.ch --count 30
```

Custom output file:
```bash
bskybook republik.ch --output my-ebook.epub
```

Verbose output:
```bash
bskybook republik.ch --verbose
```

## How it Works

1. **Fetch Posts**: Uses the anonymous BlueSky API to fetch recent posts
2. **Extract Links**: Finds all links in the posts
3. **Scrape Content**: Uses trafilatura to extract article content
4. **Generate Cover**: Creates a mosaic from article thumbnail images
5. **Create EPUB**: Generates a properly formatted EPUB 2 file

## Requirements

- Python 3.8+
- Internet connection for fetching posts and articles

## License

MIT
