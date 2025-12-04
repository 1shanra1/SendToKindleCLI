import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from .config import Config


def send_email(subject: str, file_content: bytes, filename: str):
    """
    Sends an email with the file content as an attachment to the Kindle email address.
    """
    msg = MIMEMultipart()
    msg['From'] = Config.SMTP_USER
    msg['To'] = Config.KINDLE_EMAIL
    msg['Subject'] = subject

    # Kindle needs an attachment to convert.
    # We attach the EPUB file.
    attachment = MIMEApplication(file_content, _subtype="epub+zip")
    attachment.add_header('Content-Disposition', 'attachment', filename=filename)
    msg.attach(attachment)

    try:
        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        raise RuntimeError(f"Failed to send email: {e}")
