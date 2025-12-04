import os
from dotenv import load_dotenv

from pathlib import Path

# Load from current directory OR home directory
# This allows the tool to work globally if the user puts the .env in their home folder
env_path = Path.home() / ".kindle-wikipedia-cli.env"
load_dotenv(dotenv_path=env_path)
load_dotenv() # Also try default (current directory) as fallback/override

class Config:
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    KINDLE_EMAIL = os.getenv("KINDLE_EMAIL")

    @classmethod
    def validate(cls):
        missing = []
        if not cls.SMTP_HOST: missing.append("SMTP_HOST")
        if not cls.SMTP_USER: missing.append("SMTP_USER")
        if not cls.SMTP_PASSWORD: missing.append("SMTP_PASSWORD")
        if not cls.KINDLE_EMAIL: missing.append("KINDLE_EMAIL")
        
        if missing:
            raise ValueError(f"Missing configuration variables: {', '.join(missing)}. Please check your .env file.")
