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

def extract_close_prices(candles):
    """
    Extrait le prix moyen de cloture des candles passées en paramètre.
    
    :param candles: list de dict de candles
    :return: liste des prix moyen de cloture des candles, la dernière est la plus récente
    """
    # {'snapshotTime': '2026-02-04T19:12:00', 'snapshotTimeUTC': '2026-02-04T18:12:00', 'openPrice': {'bid': 4909.08, 'ask': 4910.08}, 'closePrice': {'bid': 4907.28, 'ask': 4909.18}, 'highPrice': {'bid': 4912.22, 'ask': 4913.22}, 'lowPrice': {'bid': 4905.71, 'ask': 4907.33}, 'lastTradedVolume': 273}
    closes = []
    for candle in candles:
        avg_close = ( candle['closePrice']['bid'] + candle['closePrice']['ask'] )/ 2
        closes.append(avg_close)
    
    return closes