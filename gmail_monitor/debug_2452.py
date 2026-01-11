from gmail_client import GmailClient
import pyzmail
import logging

logging.basicConfig(level=logging.DEBUG)

gmail = GmailClient()
if gmail.connetti():
    gmail.seleziona_cartella()

    print("\n" + "="*60)
    print("ANALISI DETTAGLIATA UID 2542")
    print("="*60)

    messages = gmail.client.fetch([2542], ['RFC822'])
    msg = pyzmail.PyzMessage.factory(messages[2542][b'RFC822'])

    subject = msg.get_decoded_header('subject', 'N/A')
    print(f"\nOggetto: {subject}")
    print(f"Parti totali: {len(msg.mailparts)}")

    for i, part in enumerate(msg.mailparts):
        print(f"\n--- Parte {i} ---")
        print(f"  Filename: {part.filename}")
        print(f"  Type: {part.type}")
        print(f"  Is attachment: {part.is_body == 'attachment'}")
        print(f"  Charset: {part.charset}")

        if part.filename:
            filename_lower = part.filename.lower()
            print(f"  Filename lowercase: {filename_lower}")
            print(f"  Ends with .eml: {filename_lower.endswith('.eml')}")
            print(f"  Ends with .pdf: {filename_lower.endswith('.pdf')}")

            # Se e' .eml, analizza
            if filename_lower.endswith('.eml'):
                print(f"\n  *** ANALISI .EML ***")
                content = part.get_payload()
                print(f"  Dimensione: {len(content)} bytes")

                try:
                    inner_msg = pyzmail.PyzMessage.factory(content)
                    print(f"  Parsing OK!")
                    print(f"  Parti interne: {len(inner_msg.mailparts)}")

                    for j, inner_part in enumerate(inner_msg.mailparts):
                        print(f"\n    --- Parte interna {j} ---")
                        print(f"      Filename: {inner_part.filename}")
                        print(f"      Type: {inner_part.type}")
                        print(
                            f"      Is attachment: {inner_part.is_body == 'attachment'}")

                        if inner_part.filename:
                            inner_lower = inner_part.filename.lower()
                            print(
                                f"      Ends with .pdf: {inner_lower.endswith('.pdf')}")

                            if inner_lower.endswith('.pdf'):
                                inner_content = inner_part.get_payload()
                                if inner_content:
                                    print(f"      *** PDF TROVATO! ***")
                                    print(
                                        f"      Dimensione: {len(inner_content)} bytes")
                                else:
                                    print(f"      ERRORE: Payload vuoto")
                except Exception as e:
                    print(f"  ERRORE parsing .eml: {e}")
                    import traceback
                    traceback.print_exc()

    gmail.disconnetti()

print("\n" + "="*60)
