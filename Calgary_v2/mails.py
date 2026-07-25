from creds import gmail_password, gmail_sender, gmail_receiver
from config import *

import smtplib, ssl
from email.message import EmailMessage

def alerte(objet, message):
    """
    Envoie un email avec l'objet et le message passé en parametres
    
    :param objet: str, Objet du mail
    :param message: str, corps du mail
    """
    try:

        msg = EmailMessage()
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL
        msg["Subject"] = objet

        msg.set_content(
            message,
            charset="utf-8"
        )

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP, SMTP_PORT, context=context) as server:
            server.login(SENDER_EMAIL, gmail_password)
            server.send_message(msg)
    except Exception as e:
        print(f"ERREUR: Envoi de mail : {e}")