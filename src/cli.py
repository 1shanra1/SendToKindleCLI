import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from .config import Config
from .fetcher import fetch_article, clean_content, get_title, create_epub
from .sender import send_email

app = typer.Typer()
console = Console()


@app.command()
def main(urls: str = typer.Argument(..., help="Comma-separated list of Wikipedia URLs")):
    """
    Send Wikipedia articles to your Kindle.
    """
    try:
        Config.validate()
    except ValueError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        raise typer.Exit(code=1)

    url_list = [url.strip() for url in urls.split(',')]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        for url in url_list:
            task_id = progress.add_task(description=f"Processing {url}...", total=None)
            try:
                # Fetch from Wikipedia API
                progress.update(task_id, description=f"Fetching {url}...")
                article_data = fetch_article(url)

                # Get title
                title = get_title(article_data)
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
                filename = f"{safe_title}.epub"

                # Convert to HTML
                progress.update(task_id, description=f"Processing '{title}'...")
                body_content = clean_content(article_data)
                
                # Create EPUB
                progress.update(task_id, description=f"Creating EPUB for '{title}'...")
                epub_bytes = create_epub(title, body_content, source_url=url)

                # Send
                progress.update(task_id, description=f"Sending '{title}' to Kindle...")
                send_email(f"Convert: {title}", epub_bytes, filename)

                console.print(f"[green]✓[/green] Successfully sent '[bold]{title}[/bold]' to Kindle.")

            except Exception as e:
                console.print(f"[red]✗[/red] Failed to process {url}: {e}")
            finally:
                progress.remove_task(task_id)


if __name__ == "__main__":
    app()
