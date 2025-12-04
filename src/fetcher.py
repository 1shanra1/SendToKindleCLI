import requests
from ebooklib import epub
from io import BytesIO
import uuid
import re
import html
from urllib.parse import unquote


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


def fetch_section_images(title: str, headers: dict) -> dict:
    """
    Fetches HTML and maps section headings to their image URLs.
    Returns a dict like {'Section Name': ['url1', 'url2'], ...}
    The special key '_lead' contains images before the first heading.
    """
    api_url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'parse',
        'page': title,
        'prop': 'text',
        'format': 'json',
    }

    try:
        response = requests.get(api_url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        if 'error' in data:
            return {}

        html_content = data.get('parse', {}).get('text', {}).get('*', '')
        if not html_content:
            return {}

        # Collect all headings and images with their positions
        items = []

        # Find h2 and h3 headings
        for m in re.finditer(r'<h([23])[^>]*id="([^"]+)"[^>]*>([^<]+)</h\1>', html_content):
            heading_text = m.group(3).strip()
            items.append((m.start(), 'heading', heading_text))

        # Find figures with images (skip infobox by checking position)
        # Infobox is typically in the first ~20k chars
        for m in re.finditer(r'<figure[^>]*>(.*?)</figure>', html_content, re.DOTALL):
            figure_html = m.group(1)
            img_match = re.search(r'<img[^>]*src="([^"]+)"', figure_html)
            if img_match:
                src = img_match.group(1)
                # Only include wikimedia images, skip icons/logos
                if 'upload.wikimedia' in src and not any(skip in src.lower() for skip in [
                    'icon', 'logo', 'flag_of', 'commons-logo', 'edit-ltr', 'ambox',
                    'question_book', 'wiki_letter', 'disambig', 'folder_hexagonal'
                ]):
                    # Convert protocol-relative URL to https
                    if src.startswith('//'):
                        src = 'https:' + src
                    items.append((m.start(), 'image', src))

        # Sort by position
        items.sort(key=lambda x: x[0])

        # Map images to sections
        section_images = {'_lead': []}
        current_section = '_lead'

        for pos, item_type, value in items:
            if item_type == 'heading':
                current_section = value
                if current_section not in section_images:
                    section_images[current_section] = []
            else:  # image
                section_images[current_section].append(value)

        # Remove empty sections
        return {k: v for k, v in section_images.items() if v}

    except requests.RequestException:
        return {}


def fetch_article(url: str) -> dict:
    """
    Fetches Wikipedia article content using the Action API.
    Returns a dict with 'title', 'content' (plain text with wiki markup for sections),
    and optionally 'image' (bytes) and 'image_filename'.
    """
    title = extract_title_from_url(url)

    # Use Wikipedia's Action API to get clean extract + main image
    api_url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'prop': 'extracts|pageimages',
        'titles': title,
        'format': 'json',
        'explaintext': '1',  # Plain text, no HTML
        'exsectionformat': 'wiki',  # Keep section markers
        'pithumbsize': '800',  # Get thumbnail at 800px width
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

        result = {
            'title': page.get('title', title.replace('_', ' ')),
            'content': page.get('extract', '')
        }

        # Fetch the main image if available
        thumbnail = page.get('thumbnail', {})
        image_url = thumbnail.get('source')
        if image_url:
            try:
                img_response = requests.get(image_url, headers=headers)
                img_response.raise_for_status()
                result['image'] = img_response.content
                # Extract filename from URL
                result['image_filename'] = image_url.split('/')[-1]
            except requests.RequestException:
                pass  # Image fetch failed, continue without it

        # Fetch section images from HTML
        section_images = fetch_section_images(title, headers)
        if section_images:
            result['section_images'] = section_images

        return result

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


def clean_content(article_data: dict, section_images: dict = None) -> tuple:
    """
    Converts Wikipedia plain text extract to EPUB-compatible HTML.
    Handles section headers (== Title ==) and paragraphs.
    Inserts image references at section boundaries.

    Returns a tuple of (html_content, image_refs) where image_refs is a list of
    (filename, url) tuples for images that need to be downloaded.
    """
    if isinstance(article_data, dict):
        content = article_data.get('content', '')
    else:
        content = str(article_data)

    if not content:
        return "<p>No content found.</p>", []

    section_images = section_images or {}
    lines = content.split('\n')
    html_parts = []
    image_refs = []  # (filename, url) pairs
    image_counter = 0

    # Helper to generate image HTML for a section
    def get_section_image_html(section_name):
        nonlocal image_counter
        urls = section_images.get(section_name, [])
        img_html_parts = []
        for url in urls:
            # Generate a unique filename
            ext = url.split('.')[-1].split('?')[0].lower()
            if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                ext = 'jpg'
            filename = f"img_{image_counter}.{ext}"
            image_counter += 1
            image_refs.append((filename, url))
            img_html_parts.append(
                f'<p style="text-align:center;"><img src="images/{filename}" alt="" style="max-width:100%;"/></p>'
            )
        return '\n'.join(img_html_parts)

    # Add lead images (before first heading)
    lead_img_html = get_section_image_html('_lead')
    if lead_img_html:
        html_parts.append(lead_img_html)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for section headers (== Title ==, === Title ===, etc.)
        header_match = re.match(r'^(={2,6})\s*(.+?)\s*\1$', line)
        if header_match:
            level = len(header_match.group(1))
            section_title = header_match.group(2)
            # Map == to h2, === to h3, etc.
            h_level = min(level, 6)
            escaped_title = html.escape(section_title)
            html_parts.append(f'<h{h_level}>{escaped_title}</h{h_level}>')

            # Add images for this section right after the heading
            section_img_html = get_section_image_html(section_title)
            if section_img_html:
                html_parts.append(section_img_html)
        else:
            # Regular paragraph
            escaped_text = html.escape(line)
            html_parts.append(f'<p>{escaped_text}</p>')

    if not html_parts:
        return "<p>No content found.</p>", []

    return '\n'.join(html_parts), image_refs


def create_epub(title: str, body_content: str, source_url: str = "",
                image_data: bytes = None, image_filename: str = None,
                image_refs: list = None) -> bytes:
    """
    Creates an EPUB file from the given title and body content.
    Optionally includes a lead image and section images.

    Args:
        title: Article title
        body_content: HTML content for the article body
        source_url: Original Wikipedia URL
        image_data: Lead image bytes (optional)
        image_filename: Lead image filename (optional)
        image_refs: List of (filename, url) tuples for section images (optional)

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

    # Media type helper
    def get_media_type(filename):
        ext = filename.lower().split('.')[-1]
        media_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'svg': 'image/svg+xml',
            'webp': 'image/webp',
        }
        return media_types.get(ext, 'image/jpeg')

    # Handle lead image if provided
    lead_image_html = ""
    if image_data and image_filename:
        img_item = epub.EpubImage()
        img_item.file_name = f"images/{image_filename}"
        img_item.media_type = get_media_type(image_filename)
        img_item.content = image_data
        book.add_item(img_item)
        lead_image_html = f'<p style="text-align:center;"><img src="images/{html.escape(image_filename)}" alt="{safe_title}" style="max-width:100%;"/></p>'

    # Download and add section images
    headers = {
        'User-Agent': 'KindleWikipediaCLI/0.1.0 (https://github.com/kindle-wikipedia-cli)'
    }
    if image_refs:
        for filename, url in image_refs:
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                img_item = epub.EpubImage()
                img_item.file_name = f"images/{filename}"
                img_item.media_type = get_media_type(filename)
                img_item.content = response.content
                book.add_item(img_item)
            except requests.RequestException:
                # Skip failed images - the HTML will show a broken image
                # which is better than failing the whole EPUB
                pass

    # Create the chapter with the article content
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
{lead_image_html}
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
