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

def get_last_candles(cst, token, candle_number = 1):
    """
    Renvoie un dictionnaire contenant les <candle_number> dernières candles.

    :return: list de dict, None si la requete n'a pas abouti
    """
    try:
        candles = None

        conn = http.client.HTTPSConnection(API_FQDN)
        payload = ''
        headers = {
        'X-SECURITY-TOKEN': token,
        'CST': cst
        }
        conn.request("GET", f"/api/v1/prices/{TICKER}?resolution=MINUTE_5&max={candle_number}", payload, headers)
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
        candle = get_last_candles(cst, token, 2)

        # si les candles ont pu être récupérées, on renvoie la première (la dernière candle cloturée)
        if candle is not None and candle[-2]['snapshotTime'] != last_candle_time :
            return candle[-2]

        time.sleep(5)