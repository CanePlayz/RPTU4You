import email
import imaplib
import os
import re
from datetime import datetime
from email import policy
from email.message import EmailMessage
from email.utils import mktime_tz, parseaddr, parsedate_tz
from zoneinfo import ZoneInfo

import scraper.util.frontend_interaction as frontend_interaction
from scraper.util.create_news_entry import create_news_entry
from scraper.util.save_as_json import save_as_json


def clean_html(html: str) -> str:
    # Ersetze Zeilenumbrüche durch <br>-Tags
    html.replace("\r\n", "<br>")

    # Entferne einzelne <br>
    html = re.sub(r"(?<!<br>)<br>(?!<br>)", "", html)
    # Reduziere mehrere <br> zu einem einzigen <br>
    html = re.sub(r"(<br>\s*){2,}", "<br>", html)

    # Anführungszeichen werden manchmal falsch kodiert
    html = html.replace("", "'")

    return html.strip()


def connect_mailbox() -> imaplib.IMAP4_SSL:
    server = os.getenv("IMAP_SERVER", "")
    port = int(os.getenv("IMAP_PORT", "993"))
    username = os.getenv("IMAP_USERNAME", "")
    password = os.getenv("IMAP_PASSWORD", "")

    mailbox = imaplib.IMAP4_SSL(server, port)
    mailbox.login(username, password)
    mailbox.select("INBOX")
    return mailbox


def fetch_all_messages(mailbox: imaplib.IMAP4_SSL) -> list[EmailMessage]:
    status, data = mailbox.search(None, "ALL")
    if status != "OK":
        print("[WARN] Keine Nachrichten gefunden oder Fehler bei der Suche")
        return []

    messages: list[EmailMessage] = []
    msg_nums = data[0].split()

    for num in msg_nums:
        status, msg_data = mailbox.fetch(num, "(RFC822)")
        if status != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
            continue

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email, policy=policy.default)
        messages.append(msg)

    return messages


def parse_message(msg: EmailMessage) -> dict:
    email_list_dict = {}

    # Extrahiere die relevanten Informationen aus der E-Mail
    subject = msg.get("Subject", "")
    subject_prefix_match = re.match(r"^\[(.*?)\]\s*", subject)
    subject_prefix = subject_prefix_match.group(1) if subject_prefix_match else ""
    subject_clean = re.sub(r"^\[.*?\]\s*", "", subject)
    sender_raw = msg.get("From", "")
    sender_name, sender_email = parseaddr(sender_raw)

    date_tuple = parsedate_tz(msg.get("Date"))
    if date_tuple is not None:
        timestamp = mktime_tz(date_tuple)
        date = datetime.fromtimestamp(timestamp, ZoneInfo("Europe/Berlin"))
    # Fallback auf aktuelle Zeit, falls Datum nicht verfügbar ist
    else:
        date = datetime.now(ZoneInfo("Europe/Berlin"))

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()
            if content_type == "text/plain" and disposition != "attachment":
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")

    body = clean_html(body)

    if subject_prefix:
        source_name = "Mailverteiler " + subject_prefix
    else:
        try:
            source_name = email_list_dict[sender_email]
        except KeyError:
            source_name = "Unknown"

    return create_news_entry(
        "",
        subject_clean,
        date,
        body,
        [],
        "Email-Verteiler",
        source_name,
    )


def main() -> None:
    mailbox = connect_mailbox()
    messages = fetch_all_messages(mailbox)

    news = [parse_message(m) for m in messages]

    mailbox.close()
    mailbox.logout()

    # Einträge in JSON-Datei speichern (zum Testen)
    # save_as_json(news, "mail_scraper")

    # Einträge an Frontend senden
    frontend_interaction.send_data(news, "Mail-Scraper")


if __name__ == "__main__":
    main()
