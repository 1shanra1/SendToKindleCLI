# Kindle Wikipedia CLI

A simple CLI tool to send Wikipedia articles directly to your Kindle.

## Features

*   **Simple**: Send articles with a single command from anywhere.
*   **Clean**: Strips clutter (sidebars, footers) for a perfect reading experience.
*   **Secure**: Uses your own email credentials stored locally.

## Prerequisites

*   Python 3.8+
*   `pipx` (Recommended for installing CLI tools)
*   An email account with SMTP access (e.g., Gmail with App Password).
*   **Crucial**: Add your sender email to your [Approved Personal Document E-mail List](https://www.amazon.com/gp/help/customer/display.html?nodeId=GX9XLEVV8G4DB28H) on Amazon.

## Installation

We recommend using `pipx` to install the tool globally in an isolated environment.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/kindle-wikipedia-cli.git
    cd kindle-wikipedia-cli
    ```

2.  **Install:**
    ```bash
    pipx install .
    ```

## Configuration

To use the tool from anywhere, create a configuration file in your home directory.

1.  **Create the config file:**
    ```bash
    cp .env.example ~/.kindle-wikipedia-cli.env
    ```

2.  **Edit `~/.kindle-wikipedia-cli.env`** with your details:
    *   `SMTP_HOST`: e.g., `smtp.gmail.com`
    *   `SMTP_PORT`: `587`
    *   `SMTP_USER`: Your email address.
    *   `SMTP_PASSWORD`: Your email password (or App Password).
    *   `KINDLE_EMAIL`: Your Send-to-Kindle email address.

## Usage

Run the command from any terminal window:

```bash
send-to-kindle https://en.wikipedia.org/wiki/Python_(programming_language)
```

**Multiple URLs:**
```bash
send-to-kindle url1,url2,url3
```

## Development

To set up a local development environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```
