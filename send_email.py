import json
import os
import re
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml"])
    import yaml

try:
    import markdown
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"])
    import markdown


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)


def load_template():
    with open("email_template.html", "r", encoding="utf-8") as f:
        return f.read()


def parse_markdown_file(filepath):
    """Parse a markdown file with YAML frontmatter.
    Returns (frontmatter_dict, markdown_body)."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse YAML frontmatter between --- markers
    frontmatter = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()

    return frontmatter, body


def get_pregnancy_day(config):
    """Calculate current pregnancy week and day based on config start date."""
    israel_tz = timezone(timedelta(hours=2))
    now = datetime.now(israel_tz).date()
    start_date = datetime.strptime(config["pregnancy_start_date"], "%Y-%m-%d").date()
    start_week = config["pregnancy_start_week"]

    days_elapsed = (now - start_date).days

    if days_elapsed < 0:
        return None, None, None  # Not started yet

    week = start_week + days_elapsed // 7
    day = days_elapsed % 7 + 1

    if week > 42 or (week == 42 and day > 1):
        return None, None, None  # Past week 42 day 1

    return week, day, now


def build_email(config, sender, week, day, today):
    """Build the email message for the given pregnancy week and day."""
    content_path = Path(f"content/week-{week}/day-{day}.md")

    if not content_path.exists():
        print(f"No content file found: {content_path}")
        return None

    frontmatter, md_body = parse_markdown_file(content_path)

    # Convert markdown to HTML
    html_body = markdown.markdown(
        md_body,
        extensions=["extra", "sane_lists"]
    )

    # Load and fill the HTML template
    template = load_template()
    week_badge = f"Week {week} · Day {day}"
    html_email = template.replace("{{WEEK_BADGE}}", week_badge)
    html_email = html_email.replace("{{CONTENT}}", html_body)
    html_email = html_email.replace("{{WEEK}}", str(week))
    html_email = html_email.replace("{{DAY}}", str(day))

    # Get subject from frontmatter or generate default
    subject = frontmatter.get("subject", f"Daily Baby — Week {week}, Day {day}")

    # Build email message
    msg = MIMEMultipart("alternative")
    msg["From"] = f"Daily Baby <{sender}>"
    msg["To"] = ", ".join(config["recipients"])
    msg["Subject"] = subject

    # Plain text fallback
    msg.attach(MIMEText(md_body, "plain", "utf-8"))
    # HTML version
    msg.attach(MIMEText(html_email, "html", "utf-8"))

    return msg


def send_email(msg, sender, password, recipients):
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())


def main():
    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]

    config = load_config()

    # Allow overriding the date for testing (YYYY-MM-DD format)
    test_date = os.environ.get("TEST_DATE")
    if test_date:
        # Override the start date calculation with a specific date
        override_date = datetime.strptime(test_date, "%Y-%m-%d").date()
        start_date = datetime.strptime(config["pregnancy_start_date"], "%Y-%m-%d").date()
        start_week = config["pregnancy_start_week"]
        days_elapsed = (override_date - start_date).days
        if days_elapsed < 0:
            print("Test date is before pregnancy start date.")
            return
        week = start_week + days_elapsed // 7
        day = days_elapsed % 7 + 1
        today = override_date
    else:
        week, day, today = get_pregnancy_day(config)

    if week is None:
        print("No email to send today (outside pregnancy date range).")
        return

    print(f"Pregnancy Week {week}, Day {day} ({today})")

    msg = build_email(config, gmail_address, week, day, today)
    if msg is None:
        print("No content available for today. Skipping.")
        return

    send_email(msg, gmail_address, gmail_password, config["recipients"])
    print(f"Email sent to {config['recipients']} — Week {week}, Day {day}")


if __name__ == "__main__":
    main()
