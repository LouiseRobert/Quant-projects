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

def bollinger_bands(close_series, period=30, num_std=2):
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