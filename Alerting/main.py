import http.client
import json
import time
import datetime
import smtplib, ssl
from email.message import EmailMessage

from creds import login, password, apikey, gmail_password, gmail_sender, gmail_receiver

### Mailing
SMTP = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = gmail_sender
RECEIVER_EMAIL = gmail_receiver


### API CAPITAL.COM
API_FQDN = "api-capital.backend-capital.com"
TICKER = "GOLD"

### PARAMETRES RSI
RSI_PERIOD = 13
RSI_HIGH = 72
RSI_LOW = 28

def get_API_time():
    """
    Pour vérifier qu'on contacte bien l'API
    """
    conn = http.client.HTTPSConnection(API_FQDN)
    payload = ''
    headers = {}
    conn.request("GET", "/api/v1/time", payload, headers)
    res = conn.getresponse()
    data = res.read()

    return data.decode("utf-8")["serverTime"]

def get_connection_token():
    """
    Connecte à l'API de Capital.com
    Renvoie un dictionnaire avec les infos d'autentifications pour les futures requetes API.

    :return: dict contenant "CST" et "Token" 
    """
    conn = http.client.HTTPSConnection(API_FQDN)
    payload = json.dumps({
    "identifier": login,
    "password": password
    })
    headers = {
    'X-CAP-API-KEY': apikey,
    'Content-Type': 'application/json'
    }
    conn.request("POST", "/api/v1/session", payload, headers)
    res = conn.getresponse()
    data = res.read()

    auth = {"CST": res.getheader("CST"),
            "Token": res.getheader("X-SECURITY-TOKEN")}

    return auth
    # print(f"Security token : {res.getheader("X-SECURITY-TOKEN")}")
    # print(data.decode("utf-8"))

def get_last_candles(cst, token, candle_number = 1):
    """
    Renvoie un dictionnaire contenant les <candle_number> dernières candles.

    :return: list de dict, None si la requete n'a pas abouti
    """
    try:
        conn = http.client.HTTPSConnection(API_FQDN)
        payload = ''
        headers = {
        'X-SECURITY-TOKEN': token,
        'CST': cst
        }
        conn.request("GET", f"/api/v1/prices/{TICKER}?resolution=MINUTE&max={candle_number}", payload, headers)
        res = conn.getresponse()
        data = res.read()

        json_str = data.decode("utf-8")

        data_dict = json.loads(json_str)

        if data_dict['prices'] is not None:
            candles = data_dict["prices"]
        else:
            candles = None

    except Exception as e:
        print(f"ERREUR: Récupération de la dernière candle : {e}")

    return candles

def compute_initial_avg_gain_loss(closes, period=13):
    """
    Calcule l'average gain et loss initial pour le RSI (méthode de Wilder)

    :param closes: liste ou array de prix de clôture
                   longueur = period + 1
    :param period: période RSI (ex: 13)
    :return: (avg_gain, avg_loss)
    """

    if len(closes) != period + 1:
        raise ValueError(
            f"Il faut exactement {period + 1} closes, reçu {len(closes)}"
        )

    total_gain = 0.0
    total_loss = 0.0

    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]

        if delta > 0:
            total_gain += delta
        else:
            total_loss += abs(delta)

    avg_gain = total_gain / period
    avg_loss = total_loss / period

    return avg_gain, avg_loss

def extract_close_prices(candles):
    """
    Extrait le prix moyen de cloture des candles passées en paramètre.
    
    :param candles: list de dict de candles
    :return: liste des prix moyen de cloture des candles, la dernière est la plus récente
    """
    # {'snapshotTime': '2026-02-04T19:12:00', 'snapshotTimeUTC': '2026-02-04T18:12:00', 'openPrice': {'bid': 4909.08, 'ask': 4910.08}, 'closePrice': {'bid': 4907.28, 'ask': 4909.18}, 'highPrice': {'bid': 4912.22, 'ask': 4913.22}, 'lowPrice': {'bid': 4905.71, 'ask': 4907.33}, 'lastTradedVolume': 273}
    closes = []
    for candle in candles:
        avg_close = ( candle['closePrice']['bid'] + candle['closePrice']['bid'] )/ 2
        closes.append(avg_close)
    
    # On inverse la liste pour faire passer la candle la plus récente à la fin
    return closes[::-1]

def compute_rsi_from_avg(avg_gain, avg_loss):
    """
    Calcule le RSI à partir des moyennes de gains/pertes (Wilder)

    :param avg_gain: moyenne des gains
    :param avg_loss: moyenne des pertes
    :return: RSI (float entre 0 et 100)
    """

    if avg_loss == 0:
        return 100.0

    if avg_gain == 0:
        return 0.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi

def wait_for_next_closed_candle(cst, token, last_candle_time):
    """
    Attend une candle différente de la dernière candle (définie par son timestamp last_candle_time).
    Renvoie cette nouvelle candle quand la condition est validée (plus ou moins 5 secondes)
    
    :param cst: CST pour se connecter à l'API
    :param token: Token pour se connecter à l'API
    :param last_candle_time: str, timestamp de la dernière candle
    :return: dict de la nouvelle candle
    """
    while True:
        candle = get_last_candles(cst, token, 2)[-2]

        if candle is not None and candle['snapshotTime'] != last_candle_time :
            return candle

        time.sleep(5)

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

if __name__ == "__main__":
    auth = get_connection_token()
    cst = auth['CST']
    token = auth["Token"]
    ### Initialisation
    # On récupère les dernières candles pour pouvoir calculer le RSI
    candles = get_last_candles(cst, token, candle_number=RSI_PERIOD + 1)

    while candles is None:
        print("Erreur dans la récupération des candles, attente de 5 secondes...")
        time.sleep(5)
        candles = get_last_candles(cst, token, candle_number=RSI_PERIOD + 1)

    # On extrait les prix de cloture des candles récupérées
    closes = extract_close_prices(candles)

    # Calcul du dernier RSI
    avg_gain, avg_loss = compute_initial_avg_gain_loss(closes, RSI_PERIOD)
    previous_rsi = compute_rsi_from_avg(avg_gain, avg_loss)

    # Initialisation avant le while True
    previous_timestamp = candles[-1]['snapshotTime']
    previous_close = closes[-1]


    print(f"Début du process : {datetime.datetime.now()}")
    while True:
        # Quand on passe à une nouvelle candle
        candle = wait_for_next_closed_candle(cst, token, previous_timestamp)
        print(candle)
        # On récupère son prix moyen de cloture et on le compare au précédent
        close = (candle['closePrice']['bid'] + candle['closePrice']['ask']) /2
        delta = close - previous_close

        gain = max(delta, 0)
        loss = max(-delta, 0)

        # Calcul du RSI courant
        avg_gain = (avg_gain * (RSI_PERIOD - 1) + gain) / RSI_PERIOD
        avg_loss = (avg_loss * (RSI_PERIOD - 1) + loss) / RSI_PERIOD

        current_rsi = compute_rsi_from_avg(avg_gain, avg_loss)
        print(f"{datetime.datetime.now()} : RSI courant: {current_rsi}")

        # Détection de franchissement
        # Si le RSI vient de franchir la limite haute
        if previous_rsi < RSI_HIGH and current_rsi >= RSI_HIGH:
            alerte(objet = f"RSI crossed ABOVE {RSI_HIGH}", message= "Il faut effctuer un SELL.")

        # Si le RSI vient de franchir la limite basse
        if previous_rsi > RSI_LOW and current_rsi <= RSI_LOW:
            alerte(objet = f"RSI crossed BELOW {RSI_LOW}", message= "Il faut effctuer un BUY.")

        # Initialisation pour la prochaine candle
        previous_timestamp = candle['snapshotTime']
        previous_rsi = current_rsi
        previous_close = close

    # print(wait_for_next_closed_candle(cst, token, "2026-02-04T19:30:00"))

