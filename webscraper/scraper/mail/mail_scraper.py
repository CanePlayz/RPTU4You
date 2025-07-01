import email
import imaplib
import os
from datetime import datetime
from email import policy
from email.message import EmailMessage
from email.utils import mktime_tz, parseaddr, parsedate_tz
from zoneinfo import ZoneInfo

import scraper.util.frontend_interaction as frontend_interaction
from scraper.util.create_news_entry import create_news_entry
from scraper.util.save_as_json import save_as_json


def connect_mailbox() -> imaplib.IMAP4_SSL:
    server = os.getenv("IMAP_SERVER", "")
    port = int(os.getenv("IMAP_PORT", "993"))
    username = os.getenv("IMAP_USERNAME", "")
    password = os.getenv("IMAP_PASSWORD", "")

    print(f"[INFO] Verbinde mit Mailserver {server}:{port} als {username}")
    mailbox = imaplib.IMAP4_SSL(server, port)
    mailbox.login(username, password)
    mailbox.select("INBOX")
    print("[INFO] Verbindung erfolgreich hergestellt und INBOX ausgewählt")
    return mailbox


def fetch_all_messages(mailbox: imaplib.IMAP4_SSL) -> list[EmailMessage]:
    print("[INFO] Suche nach allen Nachrichten...")
    status, data = mailbox.search(None, "ALL")
    if status != "OK":
        print("[WARN] Keine Nachrichten gefunden oder Fehler bei der Suche")
        return []

    messages: list[EmailMessage] = []
    msg_nums = data[0].split()
    print(f"[INFO] {len(msg_nums)} Nachrichten gefunden")

    for num in msg_nums:
        print(f"[DEBUG] Hole Nachricht Nr. {num.decode()}")
        status, msg_data = mailbox.fetch(num, "(RFC822)")
        if status != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
            print(f"[WARN] Nachricht Nr. {num.decode()} konnte nicht abgerufen werden")
            continue

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email, policy=policy.default)
        messages.append(msg)

    print(f"[INFO] Insgesamt {len(messages)} Nachrichten erfolgreich geladen")
    return messages


def parse_message(msg: EmailMessage) -> dict:
    email_list_dict = {
        "ulrike.hahn@rhrk.uni-kl.de": "inf-kolloquium",
        "garth@rptu.de": "inf-stud",
    }

    subject = msg.get("Subject", "")
    sender_raw = msg.get("From", "")
    sender_name, sender_email = parseaddr(sender_raw)
    print(f"[DEBUG] Verarbeite Nachricht von {sender_email} mit Betreff '{subject}'")

    date_tuple = parsedate_tz(msg.get("Date"))
    if date_tuple is not None:
        timestamp = mktime_tz(date_tuple)
        date = datetime.fromtimestamp(timestamp, ZoneInfo("Europe/Berlin"))
    else:
        print("[WARN] Kein gültiges Datum gefunden, verwende aktuellen Zeitpunkt")
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

    body = body.strip().replace("\r\n", "<br>")

    try:
        source_name = email_list_dict[sender_email]
    except KeyError:
        source_name = "Unknown"
        print(
            f"[INFO] Absender {sender_email} nicht in Mapping gefunden → Quelle = Unknown"
        )

    return create_news_entry(
        "",
        subject,
        date,
        body,
        [],
        "Email",
        source_name,
    )


def main() -> None:
    print("[INFO] Starte Mail-Scraper...")
    mailbox = connect_mailbox()
    messages = fetch_all_messages(mailbox)
    print("[INFO] Beginne mit der Verarbeitung der Nachrichten...")

    news = [parse_message(m) for m in messages]

    mailbox.close()
    mailbox.logout()
    print("[INFO] Mailbox geschlossen")

    save_as_json(news, "pressemitteilungen")
    print(f"[INFO] {len(news)} Einträge als JSON gespeichert")

    # frontend_interaction.send_data(news, "Mail-Scraper")
    print("[INFO] Verarbeitung abgeschlossen")


if __name__ == "__main__":
    main()
