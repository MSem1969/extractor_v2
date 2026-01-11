from gmail_client import GmailClient
import pyzmail
import logging

logging.basicConfig(level=logging.INFO)

gmail = GmailClient()
if gmail.connetti():
    gmail.seleziona_cartella()

    uids = gmail.client.search(['UNSEEN'])
    print(f"\nTotale email non lette: {len(uids)}")
    print(f"Analizzerò le prime 10...\n")

    for uid in list(uids)[:10]:
        messages = gmail.client.fetch([uid], ['RFC822'])
        msg = pyzmail.PyzMessage.factory(messages[uid][b'RFC822'])

        subject = msg.get_decoded_header('subject', 'N/A')
        print(f"\n{'='*60}")
        print(f"UID {uid}: {subject[:50]}")
        print(f"{'='*60}")

        has_attachments = False

        for i, part in enumerate(msg.mailparts):
            if part.is_body == 'attachment' and part.filename:
                has_attachments = True
                filename = part.filename
                print(f"  Allegato {i}: {filename}")

                if filename.lower().endswith('.eml'):
                    print(f"     E' un .eml! Analizzo...")
                    try:
                        content = part.get_payload()
                        inner_msg = pyzmail.PyzMessage.factory(content)
                        inner_subject = inner_msg.get_decoded_header(
                            'subject', 'N/A')
                        print(f"     Oggetto interno: {inner_subject[:40]}")

                        for j, inner_part in enumerate(inner_msg.mailparts):
                            if inner_part.is_body == 'attachment' and inner_part.filename:
                                print(
                                    f"       Allegato interno: {inner_part.filename}")
                                if inner_part.filename.lower().endswith('.pdf'):
                                    print(f"          PDF TROVATO!")
                    except Exception as e:
                        print(f"     Errore: {e}")

                elif filename.lower().endswith('.pdf'):
                    print(f"     PDF DIRETTO!")

        if not has_attachments:
            print(f"  Nessun allegato")

    gmail.disconnetti()
