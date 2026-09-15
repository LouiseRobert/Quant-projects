import time
import datetime

from maths import *
from api_calls import *
from config import *
from mails import *

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
            alerte(objet = f"RSI crossed ABOVE {RSI_HIGH}", message= "Préparation SELL.")

        if previous_rsi > RSI_HIGH and current_rsi <= RSI_HIGH:
            alerte(objet = f"RSI crossed BELOW {RSI_HIGH}", message= "Il faut effectuer un SELL.")

        # Si le RSI vient de franchir la limite basse
        if previous_rsi > RSI_LOW and current_rsi <= RSI_LOW:
            alerte(objet = f"RSI crossed BELOW {RSI_LOW}", message= "Préparation BUY.")

        if previous_rsi < RSI_LOW and current_rsi >= RSI_LOW:
            alerte(objet = f"RSI crossed ABOVE {RSI_LOW}", message= "Il faut effectuer un BUY.")

        # Initialisation pour la prochaine candle
        previous_timestamp = candle['snapshotTime']
        previous_rsi = current_rsi
        previous_close = close

