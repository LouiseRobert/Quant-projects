from creds import login, password, apikey, gmail_password, gmail_sender, gmail_receiver

### Mailing
SMTP = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = gmail_sender
RECEIVER_EMAIL = gmail_receiver

### API CAPITAL.COM
API_FQDN = "api-capital.backend-capital.com"
TICKER = "GOLD"
CALGARY_ACCOUNT_NAME = "Calgary"

### PARAMETRES RSI
RSI_PERIOD = 14
RSI_HIGH = 70
RSI_LOW = 30

QTE_LOSS = 0.05 # 5% de perte
QTE_TP = 0.005 # 0.5% de gain si TP

CANDLE_SIZE = "MINUTE" #"MINUTE_5"

