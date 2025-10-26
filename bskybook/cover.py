"""Cover generation using image mosaics."""

import io
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont

from bskybook.content import Article

logger = logging.getLogger(__name__)


class CoverGenerator:
    """Generates cover images from article thumbnails."""

    # E-reader resolution
    COVER_WIDTH = 1264
    COVER_HEIGHT = 1680

    def __init__(self, timeout: int = 30):
        """Initialize the cover generator.

        Args:
            timeout: Request timeout for downloading images
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    @staticmethod
    def _get_ordinal_suffix(day: int) -> str:
        """Get the ordinal suffix for a day number.

        Args:
            day: Day of month (1-31)

        Returns:
            Ordinal suffix ('st', 'nd', 'rd', or 'th')
        """
        if 10 <= day % 100 <= 20:
            return 'th'
        else:
            return {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')

    @staticmethod
    def _format_creation_date() -> str:
        """Format the current date for the cover subtitle.

        Returns:
            Formatted date string like "Sunday, 26th of October 2025"
        """
        now = datetime.now()
        day = now.day
        suffix = CoverGenerator._get_ordinal_suffix(day)
        return now.strftime(f"%A, {day}{suffix} of %B %Y")

    def generate_cover(
        self,
        articles: list[Article],
        title: str = "BlueSky Book",
        output_path: Optional[Path] = None
    ) -> bytes:
        """Generate a cover image from article thumbnails.

        Args:
            articles: List of articles with thumbnail URLs
            title: Title to display on the cover
            output_path: Optional path to save the cover image

        Returns:
            Cover image as bytes (JPEG format)
        """
        logger.info(f"Generating cover from {len(articles)} articles")

        # Download thumbnail images
        thumbnail_urls = [a.thumbnail_url for a in articles if a.thumbnail_url]
        images = self._download_images(thumbnail_urls)

        if not images:
            logger.warning("No thumbnail images available, creating simple cover")
            cover = self._create_simple_cover(title)
        else:
            # Create mosaic
            cover = self._create_mosaic(images, title)

        # Convert to bytes
        img_bytes = io.BytesIO()
        cover.save(img_bytes, format='JPEG', quality=95)
        img_data = img_bytes.getvalue()

        # Optionally save to file
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(img_data)
            logger.info(f"Saved cover to {output_path}")

        return img_data

    def _download_images(self, urls: list[str]) -> list[Image.Image]:
        """Download images from URLs.

        Args:
            urls: List of image URLs

        Returns:
            List of PIL Image objects
        """
        images = []

        for url in urls[:20]:  # Limit to 20 images
            try:
                logger.debug(f"Downloading image: {url}")
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()

                img = Image.open(io.BytesIO(response.content))
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                images.append(img)

            except Exception as e:
                logger.debug(f"Failed to download image {url}: {e}")
                continue

        logger.info(f"Successfully downloaded {len(images)} images")
        return images

    def _create_mosaic(self, images: list[Image.Image], title: str) -> Image.Image:
        """Create a mosaic layout from images.

        Uses a 2-column layout optimized for portrait covers with landscape images.
        Images are center-cropped to fill cells completely with no whitespace.

        Args:
            images: List of PIL images (assumed to be landscape)
            title: Title to overlay on the cover

        Returns:
            Cover image
        """
        # Use 2 columns for portrait orientation with landscape images
        cols = 2
        num_images = len(images)
        rows = math.ceil(num_images / cols)

        # Reserve space for title overlay at bottom
        title_height = 200
        available_height = self.COVER_HEIGHT - title_height

        # Calculate cell dimensions
        cell_width = self.COVER_WIDTH // cols
        cell_height = available_height // rows

        # Create canvas
        canvas = Image.new('RGB', (self.COVER_WIDTH, self.COVER_HEIGHT), color='#1a1a1a')

        # Place images in grid
        for idx, img in enumerate(images):
            row = idx // cols
            col = idx % cols

            # Crop image to fill cell completely (no whitespace)
            img_cropped = self._crop_to_fill(img, cell_width, cell_height)

            # Calculate position (images fill cells edge-to-edge)
            x = col * cell_width
            y = row * cell_height

            canvas.paste(img_cropped, (x, y))

        # Add title overlay
        canvas = self._add_title_overlay(canvas, title)

        return canvas

    def _crop_to_fill(self, img: Image.Image, target_width: int, target_height: int) -> Image.Image:
        """Crop image to fill target dimensions completely (center crop).

        Scales the image so it covers the target dimensions, then crops excess
        from the center. This ensures no whitespace in the mosaic.

        Args:
            img: PIL Image
            target_width: Target width
            target_height: Target height

        Returns:
            Cropped image that exactly fills target dimensions
        """
        img_ratio = img.width / img.height
        target_ratio = target_width / target_height

        # Scale so the image covers the target (one dimension will be larger)
        if img_ratio > target_ratio:
            # Image is wider - scale by height, crop width
            scale_height = target_height
            scale_width = int(target_height * img_ratio)
        else:
            # Image is taller - scale by width, crop height
            scale_width = target_width
            scale_height = int(target_width / img_ratio)

        # Resize image to cover target dimensions
        img_scaled = img.resize((scale_width, scale_height), Image.Resampling.LANCZOS)

        # Calculate crop box (center crop)
        left = (scale_width - target_width) // 2
        top = (scale_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height

        # Crop to exact target dimensions
        return img_scaled.crop((left, top, right, bottom))

    def _add_title_overlay(self, img: Image.Image, title: str) -> Image.Image:
        """Add a semi-transparent title overlay to the image.

        Args:
            img: PIL Image
            title: Title text

        Returns:
            Image with title overlay
        """
        # Create a copy
        overlay_img = img.copy()
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Draw semi-transparent rectangle at bottom
        rect_height = 200
        draw.rectangle(
            [(0, img.height - rect_height), (img.width, img.height)],
            fill=(0, 0, 0, 180)
        )

        # Try to use nice fonts, fall back to default
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            try:
                title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
                subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            except:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()

        # Get creation date subtitle
        creation_date = self._format_creation_date()
        subtitle = f"Created on {creation_date}, by bskybook"

        # Get text bounding boxes for centering
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_height = title_bbox[3] - title_bbox[1]

        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_height = subtitle_bbox[3] - subtitle_bbox[1]

        # Calculate vertical spacing
        spacing = 10
        total_height = title_height + spacing + subtitle_height
        start_y = img.height - rect_height // 2 - total_height // 2

        # Draw title text
        title_x = (img.width - title_width) // 2
        title_y = start_y
        draw.text((title_x, title_y), title, fill=(255, 255, 255, 255), font=title_font)

        # Draw subtitle text
        subtitle_x = (img.width - subtitle_width) // 2
        subtitle_y = start_y + title_height + spacing
        draw.text((subtitle_x, subtitle_y), subtitle, fill=(200, 200, 200, 255), font=subtitle_font)

        # Composite overlay onto image
        overlay_img.paste(Image.alpha_composite(overlay_img.convert('RGBA'), overlay).convert('RGB'))

        return overlay_img

    def _create_simple_cover(self, title: str) -> Image.Image:
        """Create a simple text-based cover when no images are available.

        Args:
            title: Cover title

        Returns:
            Cover image
        """
        img = Image.new('RGB', (self.COVER_WIDTH, self.COVER_HEIGHT), color='#2C3E50')
        draw = ImageDraw.Draw(img)

        # Try to use nice fonts
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        except:
            try:
                title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
                subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
            except:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()

        # Get creation date subtitle
        creation_date = self._format_creation_date()
        subtitle = f"Created on {creation_date}, by bskybook"

        # Get text bounding boxes
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_height = title_bbox[3] - title_bbox[1]

        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_height = subtitle_bbox[3] - subtitle_bbox[1]

        # Calculate vertical spacing
        spacing = 20
        total_height = title_height + spacing + subtitle_height
        start_y = (self.COVER_HEIGHT - total_height) // 2

        # Draw title
        title_x = (self.COVER_WIDTH - title_width) // 2
        title_y = start_y
        draw.text((title_x, title_y), title, fill='white', font=title_font)

        # Draw subtitle
        subtitle_x = (self.COVER_WIDTH - subtitle_width) // 2
        subtitle_y = start_y + title_height + spacing
        draw.text((subtitle_x, subtitle_y), subtitle, fill='#cccccc', font=subtitle_font)

        return img

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
