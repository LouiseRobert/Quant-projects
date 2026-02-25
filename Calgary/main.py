import http.client
import json
import time, datetime
from creds import login, password, apikey

from maths import compute_initial_avg_gain_loss, calcul_order_size, compute_rsi_from_avg, extract_close_prices

from mailing import alerte

API_FQDN = "demo-api-capital.backend-capital.com"
TICKER = "GOLD"
CALGARY_ACCOUNT_NAME = "Calgary"

### PARAMETRES RSI
RSI_PERIOD = 13
RSI_HIGH = 72
RSI_LOW = 28

QTE_LOSS = 0.045 # 5% de perte
QTE_TP = 0.0038 # 0.85% de gain si TP
    
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

def alternative_main():
    auth = get_connection_token()
    cst = auth['CST']
    token = auth["Token"]

    # Historique des trades
    trade_history = []

    # infos sur le compte Calgary:
    acc_info = get_account_info(cst, token)
    acc_id = acc_info["id"]

    current_acc = switch_active_account(cst, token, acc_id)

    leverage = get_account_leverage(cst, token)

    ### Initialisation
    # On récupère les dernières candles pour pouvoir calculer le RSI
    candles = get_last_candles(cst, token, candle_number=RSI_PERIOD + 2) # +2 car on va calculer 2 RSI, donc enlever une candle au tableau. normalement c'est +1.

    while candles is None:
        print("Erreur dans la récupération des candles, attente de 5 secondes...")
        time.sleep(5)
        candles = get_last_candles(cst, token, candle_number=RSI_PERIOD + 2)

    # On extrait les prix de cloture des candles récupérées
    closes = extract_close_prices(candles)
    previous_closes = list(closes) # RSI - 1

    # Calcul du dernier RSI
    previous_closes.pop(0) # On supprime le 1er élément pour ne garder que RSI_PERIOD + 1 (14) candles
    avg_gain, avg_loss = compute_initial_avg_gain_loss(previous_closes, RSI_PERIOD)

    # Initialisation avant le while True
    previous_timestamp = candles[-1]['snapshotTime']
    previous_close = closes[-1]

    rsi_cross_low = False
    rsi_cross_high = False
    new_candle_available = False

    print(f"Début du process : {datetime.datetime.now()}")
    while True:

        # Sommes nous en position ?
        positions = fetch_current_positions(cst, token)

        # Quand on passe à une nouvelle candle
        candle = get_last_candles(cst, token, 2)

        if candle is None or len(candle) < 2:
            time.sleep(10)
            continue

        current_candle = candle[-2]
        print(current_candle)

        # si on est sur une nouvelle candle
        if current_candle['snapshotTime'] != previous_timestamp :
            new_candle_available = True
        else:
            new_candle_available = False

        if new_candle_available:
            # On récupère son prix moyen de cloture et on le compare au précédent
            close = (current_candle['closePrice']['bid'] + current_candle['closePrice']['ask']) /2
            delta = close - previous_close

            gain = max(delta, 0)
            loss = max(-delta, 0)

            # Calcul du RSI courant
            avg_gain = (avg_gain * (RSI_PERIOD - 1) + gain) / RSI_PERIOD
            avg_loss = (avg_loss * (RSI_PERIOD - 1) + loss) / RSI_PERIOD

            current_rsi = compute_rsi_from_avg(avg_gain, avg_loss)
            print(f"{datetime.datetime.now()} : RSI courant: {current_rsi}")

            # Récupération du datetime
            candletime = datetime.datetime.fromisoformat(current_candle["snapshotTimeUTC"])

            # Informations sur le compte
            acc_info = get_account_info(cst, token)
            acc_id = acc_info["id"]
            balance_dispo = acc_info["balancedispo"]

            # Si on a pas de position en cours ET qu'il est avant 22h30
            if not positions and candletime.time() <= datetime.time(22, 30):
                # Pas de position courante, on regarde si on a un signal pour acheter ou vendre

                # déclencheurs RSI
                if current_rsi < RSI_LOW:
                    rsi_cross_low = True

                if current_rsi > RSI_HIGH:
                    rsi_cross_high = True

                # reinitialisation si fausse alerte
                if current_rsi > 50:
                    rsi_cross_low = False
                else:
                    rsi_cross_high = False

                # RSI vient de croiser sa borne supérieure ?
                if rsi_cross_high and (current_rsi < 65):
                    print("SELL")
                    deal_id = create_position(cst, token, "SELL", balance_dispo, leverage)

                    if deal_id != None:
                        trade_history.append({"deal_id": deal_id,
                                            "risk_amount": acc_info['balancetotale'] * QTE_LOSS
                                            })  
                        rsi_cross_high = False                    
                        alerte(f"SELL {TICKER}", f"SELL effectué à {datetime.datetime.now()}")
                    else: 
                        print("Erreur d'ouverture de trade.")
                        alerte("EXCEPTION", "Erreur d'ouverture de trade.")
                # RSI vient de croiser sa borne inférieure ?
                elif rsi_cross_low and (current_rsi > 35):
                    print("BUY")
                    deal_id = create_position(cst, token, "BUY", balance_dispo, leverage)      

                    if deal_id != None:
                        trade_history.append({"deal_id": deal_id,
                                            "risk_amount": acc_info['balancetotale'] * QTE_LOSS
                                            })
                        rsi_cross_low = False
                        alerte(f"BUY {TICKER}", f"BUY effectué à {datetime.datetime.now()}")
                    else: 
                        print("Erreur d'ouverture de trade.")
                        alerte("EXCEPTION", "Erreur d'ouverture de trade.")
                else:
                    print(f"Pas de trade en cours.")
            else:
                pass

            # Initialisation pour la prochaine candle
            previous_timestamp = current_candle['snapshotTime']
            # previous_previous_rsi = previous_rsi
            # previous_rsi = current_rsi
            previous_close = close
        
        if positions:
            position = positions[0] # 1 trade à la fois

            try:
                # stop loss : 3% de la balance totale au moment ou j'ai ouvert le trade
                stoploss = trade_history[-1]['risk_amount'] # Cette mécanique m'empeche donc de trader à la main sur ce compte
            except IndexError as e:
                # Il y a eu un problème, on va utiliser une solution pas top mais on continue
                print("IndexError Stop loss.")
                stoploss = acc_info['balancetotale'] * QTE_LOSS

            try:
                # takeprofit  : 0.65% de la balance totale au moment ou j'ai ouvert le trade
                takeprofit = acc_info['balancetotale'] * QTE_TP
            except IndexError as e:
                # Il y a eu un problème, on va utiliser une solution pas top mais on continue
                print("IndexError Take profit.")
                takeprofit = 0.5
                
            # Si la condition de stop loss est atteinte
            if position['position']['upl'] <= -stoploss: # en EUR
                # On ferme la position
                print(f"STOP LOSS. Perte : {position['position']['upl']}")
                deal_ref = close_position(cst, token, position['position']['dealId'])
                
                # réinitialisation des déclencheurs
                rsi_cross_high = False
                rsi_cross_low = False

                acc_info = get_account_info(cst, token)

                if deal_ref == None:
                    print("Erreur de fermeture de trade stop loss.")
                    alerte("EXCEPTION", "Erreur de fermeture de trade stop loss.")
                else:
                    alerte(f"STOP LOSS {TICKER}", f"STOP LOSS effectué à {datetime.datetime.now()} \n Perte : {position['position']['upl']} \n Balance : {acc_info['balancetotale']}")
            
            # Si la condition de takeprofit est atteinte
            elif position['position']['upl'] >= takeprofit: # en EUR
                # On ferme la position
                print(f"TAKE PROFIT. Gain : {position['position']['upl']}")
                deal_ref = close_position(cst, token, position['position']['dealId'])
                
                # réinitialisation des déclencheurs
                rsi_cross_high = False
                rsi_cross_low = False

                acc_info = get_account_info(cst, token)

                if deal_ref == None:
                    print("Erreur de fermeture de trade take profit.")
                    alerte("EXCEPTION", "Erreur de fermeture de trade take profit.")
                else:
                    alerte(f"TAKE PROFIT {TICKER}", f"TAKE PROFIT effectué à {datetime.datetime.now()} \n Gain : {position['position']['upl']} \n Balance : {acc_info['balancetotale']}")
            else:
                # Sinon rien 
                print(f"Etat du trade: {position['position']['upl']} EUR")

        time.sleep(10)

def main():
    auth = get_connection_token()
    cst = auth['CST']
    token = auth["Token"]

    # Historique des trades
    trade_history = []

    # infos sur le compte Calgary:
    acc_info = get_account_info(cst, token)
    acc_id = acc_info["id"]

    current_acc = switch_active_account(cst, token, acc_id)

    leverage = get_account_leverage(cst, token)

    ### Initialisation
    # On récupère les dernières candles pour pouvoir calculer le RSI
    candles = get_last_candles(cst, token, candle_number=RSI_PERIOD + 2) # +2 car on va calculer 2 RSI, donc enlever une candle au tableau. normalement c'est +1.

    while candles is None:
        print("Erreur dans la récupération des candles, attente de 5 secondes...")
        time.sleep(5)
        candles = get_last_candles(cst, token, candle_number=RSI_PERIOD + 2)

    # On extrait les prix de cloture des candles récupérées
    closes = extract_close_prices(candles)
    previous_closes = list(closes) # RSI - 1
    # previous_previous_closes = list(closes) # RSI - 2

    # Calcul du dernier RSI
    previous_closes.pop(0) # On supprime le 1er élément pour ne garder que RSI_PERIOD + 1 (14) candles
    avg_gain, avg_loss = compute_initial_avg_gain_loss(previous_closes, RSI_PERIOD)

    # Initialisation avant le while True
    previous_timestamp = candles[-1]['snapshotTime']
    previous_close = closes[-1]

    rsi_cross_low = False
    rsi_cross_high = False

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

        # Informations sur le compte
        acc_info = get_account_info(cst, token)
        acc_id = acc_info["id"]
        balance_dispo = acc_info["balancedispo"]

        # Sommes nous en position ?
        positions = fetch_current_positions(cst, token)

        if positions == []:
            # Pas de position courante, on regarde si on a un signal pour acheter ou vendre

            # déclencheurs RSI
            if current_rsi < RSI_LOW:
                rsi_cross_low = True

            if current_rsi > RSI_HIGH:
                rsi_cross_high = True

            # reinitialisation si fausse alerte
            if current_rsi > 50:
                rsi_cross_low = False
            else:
                rsi_cross_high = False

            # RSI vient de croiser sa borne supérieure ?
            if rsi_cross_high and (current_rsi < 65):
                print("SELL")
                deal_id = create_position(cst, token, "SELL", balance_dispo, leverage)

                if deal_id != None:
                    trade_history.append({"deal_id": deal_id,
                                          "risk_amount": acc_info['balancetotale'] * QTE_LOSS
                                          })  
                    rsi_cross_high = False                    
                    alerte(f"SELL {TICKER}", f"SELL effectué à {datetime.datetime.now()}")
                else: 
                    print("Erreur d'ouverture de trade.")
                    alerte("EXCEPTION", "Erreur d'ouverture de trade.")
            # RSI vient de croiser sa borne inférieure ?
            elif rsi_cross_low and (current_rsi > 35):
                print("BUY")
                deal_id = create_position(cst, token, "BUY", balance_dispo, leverage)      

                if deal_id != None:
                    trade_history.append({"deal_id": deal_id,
                                          "risk_amount": acc_info['balancetotale'] * QTE_LOSS
                                          })
                    rsi_cross_low = False
                    alerte(f"BUY {TICKER}", f"BUY effectué à {datetime.datetime.now()}")
                else: 
                    print("Erreur d'ouverture de trade.")
                    alerte("EXCEPTION", "Erreur d'ouverture de trade.")
            else:
                print(f"Pas de trade en cours. RSI : {current_rsi}")
        else:
            position = positions[0] # 1 trade à la fois

            try:
                # stop loss : 3% de la balance totale au moment ou j'ai ouvert le trade
                stoploss = trade_history[-1]['risk_amount'] # Cette mécanique m'empeche donc de trader à la main sur ce compte
            except IndexError as e:
                # Il y a eu un problème, on va utiliser une solution pas top mais on continue
                print("IndexError.")
                stoploss = acc_info['balancetotale'] * QTE_LOSS
                
            # Si la condition de stop loss est atteinte
            if position['position']['upl'] <= -stoploss: # en EUR
                # On ferme la position
                print(f"STOP LOSS. Perte : {position['position']['upl']}")
                deal_ref = close_position(cst, token, position['position']['dealId'])
                
                # réinitialisation des déclencheurs
                rsi_cross_high = False
                rsi_cross_low = False

                if deal_ref == None:
                    print("Erreur de fermeture de trade.")
                    alerte("EXCEPTION", "Erreur de fermeture de trade.")
                else:
                    alerte(f"STOP LOSS {TICKER}", f"STOP LOSS effectué à {datetime.datetime.now()} \n Perte : {position['position']['upl']}")
            else:
                # Sinon rien 
                print(f"Etat du trade: {position['position']['upl']} EUR")

        # Initialisation pour la prochaine candle
        previous_timestamp = candle['snapshotTime']
        # previous_previous_rsi = previous_rsi
        # previous_rsi = current_rsi
        previous_close = close

if __name__ == "__main__":
    # main()

    alternative_main()
