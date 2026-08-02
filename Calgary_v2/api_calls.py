import http.client
import json
import time as time_module
from config import *
from maths import *

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
        conn.request("GET", f"/api/v1/prices/{TICKER}?resolution={CANDLE_SIZE}&max={candle_number}", payload, headers)
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
        time_module.sleep(5)

def get_account_leverage(cst, token):
    """
    Renvoie le levier utilisé pour le compte courant
    
    :param cst: Description
    :param token: Description

    :return: le levier utilisé sur le compte
    """
    result = None

    conn = http.client.HTTPSConnection(API_FQDN)
    payload = ''
    headers = {
    'X-SECURITY-TOKEN': token,
    'CST': cst
    }
    conn.request("GET", "/api/v1/accounts/preferences", payload, headers)
    res = conn.getresponse()
    data = res.read()
    json_str = data.decode("utf-8")

    data_dict = json.loads(json_str)

    if data_dict['leverages']:
        result = data_dict['leverages']["COMMODITIES"]["current"]

    return result

def get_account_info(cst, token):
    """
    Récupère les informations du compte CALGARY_ACCOUNT_NAME
    
    :param cst: Description
    :param token: Description

    :return: dict {"id", "status", "balancetotale", "balancedispo"}
    """
    result = None

    accounts = get_all_accounts(cst, token)
    if accounts is not None:
        for acc in accounts:
            if acc['accountName'] == CALGARY_ACCOUNT_NAME:
                result = {
                    "id": acc["accountId"],
                    "status": acc["status"],
                    "balancetotale": acc["balance"]["balance"],
                    "balancedispo": acc["balance"]["available"]
                }                  
    else:
        print("No account found")

    return result

def get_all_accounts(cst, token):
    """
    Récupère tous les comptes disponibles
    
    :param cst: Description
    :param token: Description

    :return: dict de tous les comptes disponibles
    """
    result = None

    conn = http.client.HTTPSConnection(API_FQDN)
    payload = ''
    headers = {
    'X-SECURITY-TOKEN': token,
    'CST': cst
    }
    conn.request("GET", "/api/v1/accounts", payload, headers)
    res = conn.getresponse()
    data = res.read()

    json_str = data.decode("utf-8")

    data_dict = json.loads(json_str)

    if data_dict['accounts']:
        result = data_dict['accounts']
    
    return result

def switch_active_account(cst, token, acc_id):
    """
    Switcher le compte actuf vers acc_id
    
    :param cst: Description
    :param token: Description
    :param acc_id: ID du compte vers lequel switcher

    :return: dict {"trailingStopsEnabled", "dealingEnabled", "hasActiveDemoAccounts", "hasActiveLiveAccounts"}
    """
    result = None
    conn = http.client.HTTPSConnection(API_FQDN)
    payload = json.dumps({
    "accountId": acc_id
    })
    headers = {
    'X-SECURITY-TOKEN': token,
    'CST': cst,
    'Content-Type': 'application/json'
    }
    conn.request("PUT", "/api/v1/session", payload, headers)
    res = conn.getresponse()
    data = res.read()
    json_str = data.decode("utf-8")

    data_dict = json.loads(json_str)
    
    try:
        if data_dict['dealingEnabled']:
            result = data_dict
    except KeyError as e:
        if data_dict['errorCode'] == 'error.not-different.accountId':
            result = acc_id
        else:
            print("ERREUR", e)
    
    return result

def get_price(cst, token, direction):
    """
    Renvoie le prix actuel (pas de la candle précédente !!) et de la direction de TICKER
    
    :param cst: Description
    :param token: Description
    :param direction: Description
    """
    try:
        price = None

        conn = http.client.HTTPSConnection(API_FQDN)
        payload = ''
        headers = {
        'X-SECURITY-TOKEN': token,
        'CST': cst
        }
        conn.request("GET", f"/api/v1/prices/{TICKER}?resolution={CANDLE_SIZE}&max=1", payload, headers)
        res = conn.getresponse()
        data = res.read()

        json_str = data.decode("utf-8")

        data_dict = json.loads(json_str)

        if data_dict['prices'] is not None:
            prices = data_dict["prices"][0]["closePrice"]

            if direction.lower() == "buy":
                # On achete le prix ASK
                price = prices['ask']

            elif direction.lower() == "sell":
                # On vend le prix BID
                price = prices['bid']
            else:
                print("Error: mauvaise direction. doit être BUY ou SELL.")
        else:
            print("Error: impossible de récupérer les cours.")

    except Exception as e:
        print(f"ERREUR: Récupération de la dernière candle : {e}")

    return price

def create_position(cst, token, direction, available_balance, leverage):
    """
    Ouvre une position dans la direction choisie.
    
    :param cst: Description
    :param token: Description
    :param direction: Description
    :param available_balance: Description
    :param leverage: Description
    """
    position_ref = None

    execution_price = get_price(cst, token, direction)

    size = calcul_order_size(available_balance, leverage, execution_price)

    conn = http.client.HTTPSConnection(API_FQDN)
    payload = json.dumps({
    "epic": TICKER, # TICKER
    "direction": direction, # BUY ou SELL
    "size": size, # genre 0.3 
    "guaranteedStop": True, # True pour moi car pas le choix
    "stopAmount": round(available_balance*0.47), # Quantité à perdre si SL 
    "profitAmount": round(available_balance*QTE_TP)
    })
    headers = {
    'X-SECURITY-TOKEN': token,
    'CST': cst,
    'Content-Type': 'application/json'
    }
    conn.request("POST", "/api/v1/positions", payload, headers)
    res = conn.getresponse()
    data = res.read()
    json_str = data.decode("utf-8")

    data_dict = json.loads(json_str)

    if data_dict.get('errorCode'):
        print(data_dict['errorCode'])

    if data_dict.get('dealReference'):
        position_ref = data_dict['dealReference']

    return position_ref

def close_position(cst, token, deal_id):
    """
    Ferme la position deal_id
    
    :param cst: Description
    :param token: Description
    :param deal_id: Description

    :return: la reference de la position fermée
    """
    conn = http.client.HTTPSConnection(API_FQDN)
    payload = ''
    headers = {
    'X-SECURITY-TOKEN': token,
    'CST': cst
    }
    conn.request("DELETE", f"/api/v1/positions/{deal_id}", payload, headers)
    res = conn.getresponse()
    data = res.read()
    json_str = data.decode("utf-8")

    data_dict = json.loads(json_str)

    if data_dict.get('errorCode'):
        print(data_dict['errorCode'])

    if data_dict.get('dealReference'):
        position_ref = data_dict['dealReference']

    return position_ref

def fetch_current_positions(cst, token):
    """
    Récupère toutes les positions en cours
    
    :param cst: Description
    :param token: Description
    
    :return: tableau de dict {position, market}
    """
    conn = http.client.HTTPSConnection(API_FQDN)
    payload = ''
    headers = {
    'X-SECURITY-TOKEN': token,
    'CST': cst
    }
    conn.request("GET", "/api/v1/positions", payload, headers)
    res = conn.getresponse()
    data = res.read()
    json_str = data.decode("utf-8")

    data_dict = json.loads(json_str)

    positions = data_dict.get('positions', [])

    return positions