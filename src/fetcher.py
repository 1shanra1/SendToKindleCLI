import requests
from bs4 import BeautifulSoup
from ebooklib import epub
from io import BytesIO
import uuid
import re
import html


def fetch_article(url: str) -> str:
    """
    Fetches the Wikipedia article content from the given URL.
    """
    try:
        headers = {
            'User-Agent': 'KindleWikipediaCLI/0.1.0 (https://github.com/yourusername/kindle-wikipedia-cli; ishanrai@example.com)'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch URL {url}: {e}")


def get_title(html_content: str) -> str:
    """
    Extracts the article title from HTML.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    title_tag = soup.find('title')
    if title_tag:
        return title_tag.get_text().replace(' - Wikipedia', '')
    return "Wikipedia Article"


def clean_content(html_content: str) -> str:
    """
    Cleans Wikipedia HTML and returns XHTML-compliant body content for EPUB.
    Returns only the inner content (no html/body wrapper).
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the main content area
    content = soup.find('div', {'id': 'mw-content-text'})
    if not content:
        content = soup.find('body')
    if not content:
        raise RuntimeError("Could not find content in the page.")

    # Aggressively remove unwanted elements
    selectors_to_remove = [
        # Wikipedia UI elements
        '.mw-editsection', '.reference', '.noprint', '#mw-navigation',
        '#footer', '.mw-jump-link', '.infobox', '.reflist', '.navbox',
        '.sidebar', '.sistersitebox', '.portalbox', '.metadata', '.hatnote',
        '.toc', '.catlinks', '.printfooter', '.mw-authority-control',
        '.ambox', '.mbox', '.mw-empty-elt', '.thumb', '.gallery',
        '.wikitable',
        # Media elements
        'script', 'style', 'link', 'meta', 'img', 'figure', 'figcaption',
        'video', 'audio', 'iframe', 'object', 'embed', 'canvas', 'svg',
        'map', 'area', 'noscript', 'picture', 'source',
        # Form elements
        'input', 'button', 'select', 'textarea', 'form',
    ]

    for selector in selectors_to_remove:
        for element in content.select(selector):
            element.decompose()

    # Convert links to plain text (unwrap keeps the text content)
    for a in content.find_all('a'):
        a.unwrap()

    # Allowed semantic tags for EPUB
    allowed_tags = {
        'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'br', 'hr',
        'ul', 'ol', 'li',
        'blockquote',
        'b', 'strong', 'i', 'em', 'u', 'sub', 'sup',
        'dl', 'dt', 'dd',
    }

    # Unwrap disallowed tags (keeps their text content)
    for tag in content.find_all(True):
        if tag.name not in allowed_tags:
            tag.unwrap()

    # Strip ALL attributes from remaining tags
    for tag in content.find_all(True):
        tag.attrs = {}

    # Extract text content and rebuild as clean paragraphs
    # This avoids XML parsing issues from malformed HTML
    paragraphs = []
    for element in content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote']):
        text = element.get_text(separator=' ', strip=True)
        if text:
            tag_name = element.name
            # Escape any special XML characters in the text
            escaped_text = html.escape(text)
            paragraphs.append(f'<{tag_name}>{escaped_text}</{tag_name}>')

    if not paragraphs:
        return "<p>No content found.</p>"

    return '\n'.join(paragraphs)


def create_epub(title: str, body_content: str, source_url: str = "") -> bytes:
    """
    Creates an EPUB file from the given title and body content.
    Returns the EPUB as bytes.
    """
    book = epub.EpubBook()

    # Metadata
    book.set_identifier(str(uuid.uuid4()))
    book.set_title(title)
    book.set_language('en')
    book.add_author('Wikipedia')

    if source_url:
        book.add_metadata('DC', 'source', source_url)

    # Escape title for safe XML usage
    safe_title = html.escape(title)

    # Create the chapter with the article content
    # Use simple HTML structure - ebooklib handles the rest
    chapter = epub.EpubHtml(
        title=title,
        file_name='article.xhtml',
        lang='en'
    )
    chapter.content = f'''<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>{safe_title}</title>
</head>
<body>
<h1>{safe_title}</h1>
{body_content}
</body>
</html>'''

    book.add_item(chapter)

    # Table of contents and spine
    book.toc = (chapter,)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav', chapter]

    # Write to BytesIO and return bytes
    output = BytesIO()
    epub.write_epub(output, book)
    return output.getvalue()
