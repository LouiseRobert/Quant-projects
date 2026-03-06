import numpy as np
import random

def rsi(close_series, window = 13):
    """
    Fonction de calcul du RSI.

    :@param close_series: pandas.Series, colone des prix de cloture
    :@param window: Int, Fenetre temporelle du calcul
    :@return: pandas.Series, Relative Strength Index
    """
    # calcule la différence d'un jour à l'autre
    delta = close_series.diff()

    # On isole les jours positifs et les jours négatifs
    gain = (delta.where(delta > 0, 0)).rolling(window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window).mean()

    # ratio
    rs = gain / loss

    rsi = 100 - (100 / (1 + rs))

    return rsi

def bollinger_bands(close_series, period=25, num_std=2):
    """
    Calcule les bandes de Bollinger.
    
    close_series : DataFrame contenant une colonne 'Close'
    period : période de la moyenne mobile (ex : 20)
    num_std : nombre d'écarts-types (ex : 2)
    """
    
    # Moyenne mobile
    ma = close_series.rolling(window=period).mean()
    
    # Écart-type
    std = close_series.rolling(window=period).std()
    
    # Bandes
    upper = ma + num_std * std
    lower = ma - num_std * std
    
    return ma, upper, lower

def monte_carlo_simulation(all_trades, start_balance=100, simulations=1000):

    final_balances = []
    max_drawdowns = []

    for _ in range(simulations):

        trades = all_trades.copy()
        random.shuffle(trades)

        balance = start_balance
        peak = start_balance
        max_dd = 0

        for trade in trades:

            balance *= (1 + trade)

            if balance > peak:
                peak = balance

            drawdown = (peak - balance) / peak * 100

            if drawdown > max_dd:
                max_dd = drawdown

        final_balances.append(balance)
        max_drawdowns.append(max_dd)

    print("===== MONTE CARLO =====")
    print("Simulations :", simulations)
    print()
    print("Balance finale moyenne :", round(np.mean(final_balances),2))
    print("Balance finale médiane :", round(np.median(final_balances),2))
    print("Pire balance finale :", round(min(final_balances),2))
    print("Meilleure balance finale :", round(max(final_balances),2))
    print()
    print("Drawdown moyen :", round(np.mean(max_drawdowns),2), "%")
    print("Pire drawdown :", round(max(max_drawdowns),2), "%")

    return final_balances, max_drawdowns