# Kindle Wikipedia CLI

Send Wikipedia articles to your Kindle with a single command.

## Features

- **EPUB format** with images throughout the article
- **Clean content** via Wikipedia's API
- **Works via terminal** after setup

## Prerequisites

- Python 3.8+ and `pipx`
- Email with SMTP access (e.g., Gmail with [App Password](https://support.google.com/accounts/answer/185833))
- Sender email added to your [Amazon Approved Senders List](https://www.amazon.com/gp/help/customer/display.html?nodeId=GX9XLEVV8G4DB28H)

## Installation

```bash
git clone https://github.com/yourusername/kindle-wikipedia-cli.git
cd kindle-wikipedia-cli
pipx install .
```

## Configuration

```bash
cp .env.example ~/.kindle-wikipedia-cli.env
```

Edit `~/.kindle-wikipedia-cli.env`:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-app-password
KINDLE_EMAIL=you@kindle.com
```

## Usage

```bash
send-to-kindle https://en.wikipedia.org/wiki/HAL_Tejas

# Multiple articles
send-to-kindle url1,url2,url3
```

## Development

```bash
python3 -m venv venv && source venv/bin/activate && pip install -e .
```
