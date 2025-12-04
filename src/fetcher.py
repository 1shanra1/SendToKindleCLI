import requests
from ebooklib import epub
from io import BytesIO
import uuid
import re
import html


def extract_title_from_url(url: str) -> str:
    """
    Extracts the article title from a Wikipedia URL.
    e.g., 'https://en.wikipedia.org/wiki/HAL_Tejas' -> 'HAL_Tejas'
    """
    # Handle both /wiki/Title and /w/index.php?title=Title formats
    if '/wiki/' in url:
        return url.split('/wiki/')[-1].split('#')[0].split('?')[0]
    elif 'title=' in url:
        match = re.search(r'title=([^&]+)', url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract article title from URL: {url}")


def fetch_article(url: str) -> dict:
    """
    Fetches Wikipedia article content using the Action API.
    Returns a dict with 'title' and 'content' (plain text with wiki markup for sections).
    """
    title = extract_title_from_url(url)

    # Use Wikipedia's Action API to get clean extract
    api_url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'prop': 'extracts',
        'titles': title,
        'format': 'json',
        'explaintext': '1',  # Plain text, no HTML
        'exsectionformat': 'wiki',  # Keep section markers
    }

    headers = {
        'User-Agent': 'KindleWikipediaCLI/0.1.0 (https://github.com/kindle-wikipedia-cli)'
    }

    try:
        response = requests.get(api_url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        pages = data.get('query', {}).get('pages', {})
        if not pages:
            raise RuntimeError("No pages returned from API")

        # Get the first (and only) page
        page = next(iter(pages.values()))

        if 'missing' in page:
            raise RuntimeError(f"Article not found: {title}")

        return {
            'title': page.get('title', title.replace('_', ' ')),
            'content': page.get('extract', '')
        }

    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch article: {e}")


def get_title(article_data: dict) -> str:
    """
    Returns the article title from the fetched data.
    """
    if isinstance(article_data, dict):
        return article_data.get('title', 'Wikipedia Article')
    # Fallback for backwards compatibility
    return "Wikipedia Article"


def clean_content(article_data: dict) -> str:
    """
    Converts Wikipedia plain text extract to EPUB-compatible HTML.
    Handles section headers (== Title ==) and paragraphs.
    """
    if isinstance(article_data, dict):
        content = article_data.get('content', '')
    else:
        content = str(article_data)

    if not content:
        return "<p>No content found.</p>"

    lines = content.split('\n')
    html_parts = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for section headers (== Title ==, === Title ===, etc.)
        header_match = re.match(r'^(={2,6})\s*(.+?)\s*\1$', line)
        if header_match:
            level = len(header_match.group(1))
            title = header_match.group(2)
            # Map == to h2, === to h3, etc.
            h_level = min(level, 6)
            escaped_title = html.escape(title)
            html_parts.append(f'<h{h_level}>{escaped_title}</h{h_level}>')
        else:
            # Regular paragraph
            escaped_text = html.escape(line)
            html_parts.append(f'<p>{escaped_text}</p>')

    if not html_parts:
        return "<p>No content found.</p>"

    return '\n'.join(html_parts)


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
    # Note: Don't include 'nav' in spine - causes crashes on some Kindle devices
    book.toc = (chapter,)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = [chapter]

    # Write to BytesIO and return bytes
    output = BytesIO()
    epub.write_epub(output, book)
    return output.getvalue()
