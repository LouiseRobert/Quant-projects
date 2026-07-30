import time as time_module
from datetime import datetime, time
 
from config import *
from maths import *
from mails import *
from api_calls import *


def calgary():
    """ Travail du robot lancé la nuit """
    # ------------ Initialisation Compte ------------ #
    auth = get_connection_token()
    cst = auth['CST']
    token = auth["Token"]

    # Historique des trades
    trade_history = []

    # infos sur le compte Calgary:
    acc_info = get_account_info(cst, token)
    acc_id = acc_info["id"]

    #current_acc = switch_active_account(cst, token, acc_id)

    leverage = get_account_leverage(cst, token)

    # ------------ Initialisation Candles ------------ #
    # On récupère les dernières candles pour pouvoir calculer le RSI
    candles = get_last_candles(cst, token, candle_number=RSI_PERIOD + 1) 

    while candles is None:
        print("Erreur dans la récupération des candles, attente de 5 secondes...")
        time_module.sleep(5)
        candles = get_last_candles(cst, token, candle_number=RSI_PERIOD + 1)

    # On extrait les prix de cloture des candles récupérées
    closes = extract_close_prices(candles)
    previous_closes = list(closes) # RSI - 1

    # Calcul du dernier RSI
    avg_gain, avg_loss = compute_initial_avg_gain_loss(previous_closes, RSI_PERIOD)

    # ------------  Initialisation avant le while True ------------ #
    previous_timestamp = candles[-1]['snapshotTime']
    previous_close = closes[-1]

    should_sell = False
    should_buy = False

    previous_rsi = None

    while True:
        # ------------  process de la candle courante  ------------ #
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

        now = datetime.now()
        print(f"{now} : RSI courant: {current_rsi}")

        # Si on est à la première itération de boucle
        if previous_rsi is None:
            previous_rsi = current_rsi

        # Informations sur le compte
        acc_info = get_account_info(cst, token)
        balance_dispo = acc_info["balancedispo"]

        #  ------------ Somme nous la nuit ? ------------ #
        ### l'heure est bonne si on est entre minuit et 9h
        nighttime = time(0, 0) <= now.time() < time(9, 0)

        #  ------------ Sommes nous en position ? ------------ #
        positions = fetch_current_positions(cst, token)
        if positions == []:
            # Pas de position courante, on regarde si on a un signal pour acheter ou vendre

            # Détection de franchissement
            # Si le RSI vient de franchir la limite haute
            if previous_rsi < RSI_HIGH and current_rsi >= RSI_HIGH:
                alerte(objet = f"RSI crossed ABOVE {RSI_HIGH}", message= "Préparation SELL.")

            if previous_rsi > RSI_HIGH and current_rsi <= RSI_HIGH:
                alerte(objet = f"RSI crossed BELOW {RSI_HIGH}", message= "Il faut effectuer un SELL.")
                should_sell = True and nighttime

            # Si le RSI vient de franchir la limite basse
            if previous_rsi > RSI_LOW and current_rsi <= RSI_LOW:
                alerte(objet = f"RSI crossed BELOW {RSI_LOW}", message= "Préparation BUY.")

            if previous_rsi < RSI_LOW and current_rsi >= RSI_LOW:
                alerte(objet = f"RSI crossed ABOVE {RSI_LOW}", message= "Il faut effectuer un BUY.")
                should_buy = True and nighttime

            # RSI vient de croiser sa borne supérieure et rerentrer dans la norme RSI ?
            if should_sell:
                print("SELL")
                deal_id = create_position(cst, token, "SELL", balance_dispo, leverage)

                if deal_id is not None:
                    trade_history.append({"deal_id": deal_id,
                                        "risk_amount": acc_info['balancetotale'] * QTE_LOSS,
                                        "profit_goal": acc_info['balancetotale'] * QTE_TP
                                        })  
                    alerte(f"SELL {TICKER}", f"SELL effectué à {datetime.now()}")
                else: 
                    print("Erreur d'ouverture de trade.")
                    alerte("EXCEPTION", "Erreur d'ouverture de trade.")

                should_sell = False 

            # RSI vient de croiser sa borne inférieure et rerentrer dans la norme RSI ?
            elif should_buy:
                print("BUY")
                deal_id = create_position(cst, token, "BUY", balance_dispo, leverage)      

                if deal_id is not None:
                    trade_history.append({"deal_id": deal_id,
                                        "risk_amount": acc_info['balancetotale'] * QTE_LOSS,
                                        "profit_goal": acc_info['balancetotale'] * QTE_TP
                                        })
                    alerte(f"BUY {TICKER}", f"BUY effectué à {datetime.now()}")
                else: 
                    print("Erreur d'ouverture de trade.")
                    alerte("EXCEPTION", "Erreur d'ouverture de trade.")
                
                should_buy = False

            else:
                print(f"Pas de trade en cours. RSI : {current_rsi}")
        else:
            # On ne manage les position que la nuit
            if nighttime:
                position = positions[0] # 1 trade à la fois
                try:
                    # stop loss : 5% de la balance totale au moment ou j'ai ouvert le trade
                    stoploss = trade_history[-1]['risk_amount'] # Cette mécanique m'empeche donc de trader à la main sur ce compte
                except IndexError as e:
                    # Il y a eu un problème, on va utiliser une solution pas top mais on continue
                    print("IndexError.")
                    stoploss = acc_info['balancetotale'] * QTE_LOSS
                    
                try:
                    # take profit: 0.5% de la balance totale au moment ou j'ai ouvert le trade
                    takeprofit = trade_history[-1]['profit_goal']
                except IndexError as e:
                    # Il y a eu un problème, on va utiliser une solution pas top mais on continue
                    print("IndexError.")
                    takeprofit = acc_info['balancetotale'] * QTE_TP

                # Si la condition de stop loss est atteinte
                if position['position']['upl'] <= -stoploss: # en EUR
                    # On ferme la position
                    print(f"STOP LOSS. Perte : {position['position']['upl']}")
                    deal_ref = close_position(cst, token, position['position']['dealId'])
                    
                    # réinitialisation des déclencheurs
                    should_buy = False
                    should_sell = False

                    if deal_ref is None:
                        print("Erreur de fermeture de trade.")
                        alerte("EXCEPTION", "Erreur de fermeture de trade.")
                    else:
                        alerte(f"STOP LOSS {TICKER}", f"STOP LOSS effectué à {datetime.now()} \n Perte : {position['position']['upl']}")

                # Si on atteint le TP ou qu'on passe la barre des RSI 50 on ferme en TP
                elif (position['position']['upl'] > takeprofit) or ((previous_rsi < 50 <= current_rsi) or (previous_rsi > 50 >= current_rsi)): # en EUR
                    # On ferme la position
                    print(f"TAKE PROFIT. Gain : {position['position']['upl']}")
                    deal_ref = close_position(cst, token, position['position']['dealId'])
                    
                    # réinitialisation des déclencheurs
                    should_buy = False
                    should_sell = False

                    if deal_ref is None:
                        print("Erreur de fermeture de trade.")
                        alerte("EXCEPTION", "Erreur de fermeture de trade.")
                    else:
                        alerte(f"TAKE PROFIT {TICKER}", f"TAKE PROFIT effectué à {datetime.now()} \n Gain : {position['position']['upl']}")
                else:
                    # Sinon rien 
                    print(f"Etat du trade: {position['position']['upl']} EUR")
            else:
                # Rien, on est en journée donc on gère la position manuellement
                pass

        # ------------  Initialisation pour la prochaine candle ------------ #
        previous_timestamp = candle['snapshotTime']
        previous_close = close
        previous_rsi = current_rsi

def main():
    """
    """
    print(f"Début du process : {datetime.now()}")

    calgary()
        
if __name__ == "__main__":
    main()
