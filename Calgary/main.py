import http.client
import json
from creds import login, password, apikey

API_FQDN = "demo-api-capital.backend-capital.com"
TICKER = "GOLD"
CALGARY_ACCOUNT_NAME = "Calgary"
    
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
                    "balancetotale": ["balance"]["balance"],
                    "balancedispo": acc["balance"]["available"]
                }                  
    else:
        print("No account found")

    return result

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

    if data_dict['dealingEnabled']:
        result = data_dict
    
    return result

def calcul_order_size(balance_totale, leverage, price):
    """
    Calcule la taille de l'ordre qui doit être passé selon la balance totale, le levier et le prix
    
    :param balance_totale: Description
    :param leverage: Description
    :param price: Description

    :return: float, taille de l'ordre qui va être passé
    """
    margin_ratio = 0.5

    margin_used = balance_totale * margin_ratio

    notional = margin_used * leverage

    size = notional / price

    return round(size, 2)

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
        conn.request("GET", f"/api/v1/prices/{TICKER}?resolution=MINUTE&max=1", payload, headers)
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
    position_id = None

    execution_price = get_price(cst, token, direction)

    size = calcul_order_size(available_balance, leverage, execution_price)

    conn = http.client.HTTPSConnection(API_FQDN)
    payload = json.dumps({
    "epic": TICKER, # TICKER
    "direction": direction, # BUY ou SELL
    "size": size, # genre 0.3 
    "guaranteedStop": True, # True pour moi car pas le choix
    "stopAmount": round(available_balance*0.45), # Quantité à perdre si SL 
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

    if data_dict.get('positions'):
        positions = data_dict['positions']
    else:
        print("Erreur de récupération des positions")
        positions = []

    return positions

if __name__ == "__main__":
    # connexion
    auth = get_connection_token()

    cst = auth['CST']
    token = auth['Token']

    # infos sur le compte Calgary:
    acc_info = get_account_info(cst, token)
    acc_id = acc_info["id"]
    leverage = get_account_leverage(cst, token)
    balance_dispo = acc_info["balancedispo"]

    current_acc = switch_active_account(cst, token, acc_id)

    positions = fetch_current_positions(cst, token)

    if positions == []:

        if signal == "SHORT":
            deal_id = create_position(cst, token, "SELL", balance_dispo, leverage)
        elif signal == "LONG":
            deal_id = create_position(cst, token, "BUY", balance_dispo, leverage)        
        else:
            pass
    else:
        position = positions[0] # 1 trade à la fois
        if position.upl <= stoploss: # en EUR
            deal_ref = close_position(cst, token, position.deal_id)
        else:
            pass

