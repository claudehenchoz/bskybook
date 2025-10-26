"""EPUB 2 generation."""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from lxml import etree

from bskybook.content import Article
from bskybook.utils import sanitize_filename

logger = logging.getLogger(__name__)


class EPUBGenerator:
    """Generates EPUB 2 ebooks."""

    def __init__(self):
        """Initialize the EPUB generator."""
        self.articles: list[Article] = []
        self.title = "BlueSky Book"
        self.author = "BlueSky Collection"
        self.cover_data: Optional[bytes] = None

    def create_epub(
        self,
        articles: list[Article],
        title: str,
        author: str,
        cover_data: Optional[bytes],
        output_path: Path
    ) -> None:
        """Create an EPUB 2 file.

        Args:
            articles: List of articles to include
            title: Book title
            author: Book author
            cover_data: Cover image data (JPEG bytes)
            output_path: Path to save the EPUB file
        """
        self.articles = articles
        self.title = title
        self.author = author
        self.cover_data = cover_data

        logger.info(f"Creating EPUB with {len(articles)} articles")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create EPUB zip file
        with ZipFile(output_path, 'w') as epub:
            # Add mimetype (must be first, uncompressed)
            epub.writestr('mimetype', 'application/epub+zip', compress_type=ZIP_STORED)

            # Add container.xml
            self._add_container(epub)

            # Add content.opf
            self._add_content_opf(epub)

            # Add toc.ncx
            self._add_toc_ncx(epub)

            # Add cover page
            if cover_data:
                self._add_cover(epub)

            # Add article content
            self._add_articles(epub)

        logger.info(f"EPUB created successfully: {output_path}")

    def _add_container(self, epub: ZipFile) -> None:
        """Add META-INF/container.xml to the EPUB.

        Args:
            epub: ZipFile object
        """
        container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
        epub.writestr('META-INF/container.xml', container_xml, compress_type=ZIP_DEFLATED)

    def _add_content_opf(self, epub: ZipFile) -> None:
        """Add OEBPS/content.opf metadata file.

        Args:
            epub: ZipFile object
        """
        # Create unique identifier
        book_id = str(uuid.uuid4())
        date = datetime.now().strftime('%Y-%m-%d')

        # Namespaces
        ns_dc = "http://purl.org/dc/elements/1.1/"
        ns_opf = "http://www.idpf.org/2007/opf"

        # Create root element
        package = etree.Element(
            'package',
            version="2.0",
            nsmap={'dc': ns_dc, None: ns_opf},
            attrib={
                'unique-identifier': 'bookid'
            }
        )

        # Metadata
        metadata = etree.SubElement(package, 'metadata')

        title_elem = etree.SubElement(metadata, f'{{{ns_dc}}}title')
        title_elem.text = self.title

        author_elem = etree.SubElement(metadata, f'{{{ns_dc}}}creator')
        author_elem.set(f'{{{ns_opf}}}role', 'aut')
        author_elem.text = self.author

        lang_elem = etree.SubElement(metadata, f'{{{ns_dc}}}language')
        lang_elem.text = 'en'

        date_elem = etree.SubElement(metadata, f'{{{ns_dc}}}date')
        date_elem.text = date

        identifier_elem = etree.SubElement(metadata, f'{{{ns_dc}}}identifier')
        identifier_elem.set('id', 'bookid')
        identifier_elem.text = f'urn:uuid:{book_id}'

        # Cover metadata
        if self.cover_data:
            cover_meta = etree.SubElement(metadata, 'meta')
            cover_meta.set('name', 'cover')
            cover_meta.set('content', 'cover-image')

        # Manifest
        manifest = etree.SubElement(package, 'manifest')

        # Add TOC
        toc_item = etree.SubElement(manifest, 'item')
        toc_item.set('id', 'ncx')
        toc_item.set('href', 'toc.ncx')
        toc_item.set('media-type', 'application/x-dtbncx+xml')

        # Add cover image
        if self.cover_data:
            cover_img_item = etree.SubElement(manifest, 'item')
            cover_img_item.set('id', 'cover-image')
            cover_img_item.set('href', 'cover.jpg')
            cover_img_item.set('media-type', 'image/jpeg')

            # Cover page
            cover_page_item = etree.SubElement(manifest, 'item')
            cover_page_item.set('id', 'cover')
            cover_page_item.set('href', 'cover.html')
            cover_page_item.set('media-type', 'application/xhtml+xml')

        # Add articles
        for idx, article in enumerate(self.articles):
            item = etree.SubElement(manifest, 'item')
            item.set('id', f'article{idx}')
            item.set('href', f'article{idx}.html')
            item.set('media-type', 'application/xhtml+xml')

        # Spine
        spine = etree.SubElement(package, 'spine')
        spine.set('toc', 'ncx')

        # Add cover to spine
        if self.cover_data:
            cover_itemref = etree.SubElement(spine, 'itemref')
            cover_itemref.set('idref', 'cover')

        # Add articles to spine
        for idx in range(len(self.articles)):
            itemref = etree.SubElement(spine, 'itemref')
            itemref.set('idref', f'article{idx}')

        # Write to EPUB
        content = etree.tostring(
            package,
            pretty_print=True,
            xml_declaration=True,
            encoding='UTF-8'
        )
        epub.writestr('OEBPS/content.opf', content, compress_type=ZIP_DEFLATED)

    def _add_toc_ncx(self, epub: ZipFile) -> None:
        """Add OEBPS/toc.ncx navigation file.

        Args:
            epub: ZipFile object
        """
        ns = "http://www.daisy.org/z3986/2005/ncx/"

        ncx = etree.Element(
            'ncx',
            version="2005-1",
            nsmap={None: ns}
        )
        ncx.set('{http://www.w3.org/XML/1998/namespace}lang', 'en')

        # Head
        head = etree.SubElement(ncx, 'head')

        uid_meta = etree.SubElement(head, 'meta')
        uid_meta.set('name', 'dtb:uid')
        uid_meta.set('content', 'urn:uuid:' + str(uuid.uuid4()))

        depth_meta = etree.SubElement(head, 'meta')
        depth_meta.set('name', 'dtb:depth')
        depth_meta.set('content', '1')

        # Doc title
        doc_title = etree.SubElement(ncx, 'docTitle')
        text = etree.SubElement(doc_title, 'text')
        text.text = self.title

        # Nav map
        nav_map = etree.SubElement(ncx, 'navMap')

        # Add cover
        if self.cover_data:
            nav_point = etree.SubElement(nav_map, 'navPoint')
            nav_point.set('id', 'cover')
            nav_point.set('playOrder', '1')

            nav_label = etree.SubElement(nav_point, 'navLabel')
            nav_text = etree.SubElement(nav_label, 'text')
            nav_text.text = 'Cover'

            content = etree.SubElement(nav_point, 'content')
            content.set('src', 'cover.html')

        # Add articles
        for idx, article in enumerate(self.articles):
            play_order = idx + 2 if self.cover_data else idx + 1

            nav_point = etree.SubElement(nav_map, 'navPoint')
            nav_point.set('id', f'article{idx}')
            nav_point.set('playOrder', str(play_order))

            nav_label = etree.SubElement(nav_point, 'navLabel')
            nav_text = etree.SubElement(nav_label, 'text')
            nav_text.text = article.title

            content = etree.SubElement(nav_point, 'content')
            content.set('src', f'article{idx}.html')

        # Write to EPUB
        content = etree.tostring(
            ncx,
            pretty_print=True,
            xml_declaration=True,
            encoding='UTF-8',
            doctype='<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">'
        )
        epub.writestr('OEBPS/toc.ncx', content, compress_type=ZIP_DEFLATED)

    def _add_cover(self, epub: ZipFile) -> None:
        """Add cover image and cover page.

        Args:
            epub: ZipFile object
        """
        if not self.cover_data:
            return

        # Add cover image
        epub.writestr('OEBPS/cover.jpg', self.cover_data, compress_type=ZIP_DEFLATED)

        # Add cover HTML page
        cover_html = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Cover</title>
    <style type="text/css">
        body { margin: 0; padding: 0; text-align: center; }
        img { max-width: 100%; max-height: 100%; }
    </style>
</head>
<body>
    <div>
        <img src="cover.jpg" alt="Cover" />
    </div>
</body>
</html>'''
        epub.writestr('OEBPS/cover.html', cover_html, compress_type=ZIP_DEFLATED)

    def _add_articles(self, epub: ZipFile) -> None:
        """Add article content pages.

        Args:
            epub: ZipFile object
        """
        for idx, article in enumerate(self.articles):
            html_content = self._create_article_html(article)
            epub.writestr(f'OEBPS/article{idx}.html', html_content, compress_type=ZIP_DEFLATED)

    def _create_article_html(self, article: Article) -> str:
        """Create XHTML content for an article.

        Args:
            article: Article object

        Returns:
            XHTML string
        """
        # Clean and prepare HTML content
        content = article.content_html

        # Wrap in proper XHTML structure
        html = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{self._escape_xml(article.title)}</title>
    <style type="text/css">
        body {{
            font-family: Georgia, serif;
            line-height: 1.6;
            margin: 1em;
        }}
        h1 {{
            font-size: 1.8em;
            margin-bottom: 0.5em;
        }}
        h2 {{
            font-size: 1.4em;
            margin-top: 1em;
        }}
        p {{
            margin: 1em 0;
            text-align: justify;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
        }}
        .meta {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 1em;
        }}
    </style>
</head>
<body>
    <h1>{self._escape_xml(article.title)}</h1>
    <div class="meta">
        {f'<p>By {self._escape_xml(article.author)}</p>' if article.author else ''}
        {f'<p>{article.date}</p>' if article.date else ''}
        <p><a href="{self._escape_xml(article.url)}">Source</a></p>
    </div>
    <div class="content">
        {content}
    </div>
</body>
</html>'''
        return html

    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        if not text:
            return ''
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;'))
