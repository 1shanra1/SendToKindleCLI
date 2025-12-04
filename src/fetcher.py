import requests
from bs4 import BeautifulSoup
from typing import Optional

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

def clean_content(html_content: str, title: str) -> str:
    """
    Cleans the Wikipedia HTML content for Kindle reading.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Try to find the main content area
    content = soup.find('div', {'id': 'mw-content-text'})
    if not content:
        content = soup.find('body')
    
    if not content:
        raise RuntimeError("Could not find content in the page.")

    # Remove unwanted elements
    for selector in [
        '.mw-editsection', 
        '.reference', 
        '.noprint', 
        '#mw-navigation', 
        '#footer', 
        '.mw-jump-link',
        '.infobox', # Optional: infoboxes can be messy on Kindle
        '.reflist',
        'script',
        'style'
    ]:
        for element in content.select(selector):
            element.decompose()

    # Create a simple HTML wrapper
    clean_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            body {{ font-family: sans-serif; }}
            img {{ max-width: 100%; height: auto; }}
        </style>
    </head>
    <body>
        <h1>{title}</h1>
        {content.prettify()}
    </body>
    </html>
    """
    return clean_html

def get_title(html_content: str) -> str:
    soup = BeautifulSoup(html_content, 'html.parser')
    title_tag = soup.find('title')
    if title_tag:
        return title_tag.get_text().replace(' - Wikipedia', '')
    return "Wikipedia Article"
