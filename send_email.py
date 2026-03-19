import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)


def build_email(config, sender):
    israel_tz = timezone(timedelta(hours=2))
    now = datetime.now(israel_tz)
    date_str = now.strftime("%A, %B %d, %Y")

    subject = f"{config['subject']} - {date_str}"

    # TODO: Replace this test body with actual content
    body = f"Hello!\n\nThis is your daily email for {date_str}.\n\nThis is a test message to verify the automation works.\n"

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(config["recipients"])
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    return msg


def send_email(msg, sender, password, recipients):
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())


def main():
    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]

    config = load_config()
    msg = build_email(config, gmail_address)
    send_email(msg, gmail_address, gmail_password, config["recipients"])

    print(f"Email sent to {config['recipients']}")


if __name__ == "__main__":
    main()
