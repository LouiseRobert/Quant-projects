import pandas as pd
import matplotlib.pyplot as plt 

DATA_FILE = "./data/XAUUSD.csv"

BALANCE = 50 # Balance totale du compte
LEVERAGE = 20 # Levier
MARGIN_TRADE = 25 # Argent engagé dans les trades (50% de la balance)

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

class Backtester: 
    def __init__(self, df, balance=BALANCE, leverage=LEVERAGE, margin_per_trade=MARGIN_TRADE): 
        """
        Docstring for __init__
        
        :param self: Description
        :param df: Dataframe pour le backtest
        :param balance: Quantité d'argent au départ dans le compte fictif
        :param leverage: Levier utilisé pour trader
        :param margin_per_trade: Marge en argent réservée de la balance
        """
        self.dataframe = df 
        self.balance = balance 
        self.balance_history = []
        self.leverage = leverage 
        self.margin_per_trade = margin_per_trade # Calcul de la valeur notionnelle totale contrôlée 
        self.position_size = margin_per_trade * leverage # Taille de ma positione en cours 

        self.position = None # si je suis actuellement dans un trade 
        self.entry_price = None # si oui, à combien suis-je entrée 
        self.stoploss = None # le stop loss est fixe et calculé à la prise de position 
        self.units = None # quantité d'or contrôlée 
        self.trades = [] # log des trades cloturés

    def on_candle(self, candle):
        open_ = candle["Open"]
        close = candle["Close"]
        prev_close = candle["prev_close"]
        high = candle["High"]
        low = candle["Low"]
        rsi = candle["RSI"]
        prev_rsi = candle["prev_RSI"]
        moymob = candle["MoyMob"] # Moyenne mobile, exact milieu entre BB lower et BB upper
        bbupper = candle["BB_upper"]
        prev_bbupper = candle["prev_BB_upper"]
        bblower = candle["BB_lower"]
        prev_bblower = candle["prev_BB_lower"]

        #### Conditions de long
        # Si le RSI passe de inférieur à 30 à supérieur à 30
        rsi_long_ok = (prev_rsi < 30) and (rsi > 30)
        # Et que le prix croise la BB lower par le bas
        price_long_ok = (prev_close < prev_bblower) and (close > bblower)
        # Alors on considère qu'on est en position longue
        shouldibuy = rsi_long_ok and price_long_ok

        # Conditions de vente de la position longue
        # take profit en variable car ajustable
        tp_long = moymob 

        # Si le RSI croise la barre des 70 par le dessus 
        rsi_sell_ok = (prev_rsi > 70) and (rsi < 70)
        # Et que le prix (close) a atteint le take profit définit plus haut
        price_sell_ok = close >= tp_long
        # Alors on cloture la position longue
        take_profit_long = rsi_sell_ok or price_sell_ok

        #### Conditions de short
        # Si le RSI croise la barre des 70 par le dessus 
        rsi_short_ok = (prev_rsi > 70) and (rsi < 70)
        # Et que le prix croise la BB upper par le dessus 
        price_short_ok = (prev_close > prev_bbupper) and (close < bbupper)
        # Alors on considère qu'on est en position short
        shouldisell = rsi_short_ok and price_short_ok

        # conditions d'achat de la position short 
        # Take profit en variable car ajustable
        tp_short = moymob 

        # Si le RSI croise la barre des 30 par le dessous 
        rsi_buy_ok = (prev_rsi < 30) and (rsi > 30)
        # Et que le prix a atteint le take profit 
        price_buy_ok = close <= tp_short
        # Alors on cloture la position short
        take_profit_short = rsi_buy_ok or price_buy_ok

        # === OUVERTURE DE POSITION SHORT ===
        if self.position is None and shouldisell == True:
            self.position = "short"
            self.entry_price = close

            # On définit un stop loss dès l'entrée en position
            self.stoploss = close * (1 + 0.002) # Stop 0.2% au dessus du prix de cloture (prix d'entrée)
            # self.stoploss = bblower * (1 + 0.0005)  # Stop 0.05% au dessus de BB_upper
            self.units = self.position_size / close

            # On immobilise 25€
            self.balance -= self.margin_per_trade

        # === STOP LOSS SHORT ===
        elif self.position == "short" and high >= self.stoploss:
            # Calcul des gains/pertes
            pnl = (self.entry_price - self.stoploss) * self.units

            # on débloque l'agrent de la balance
            self.balance += self.margin_per_trade  # marge restituée
            self.balance += pnl                    # PnL du trade
            self.trades.append(pnl)

            print(f"{candle.name} --- SHORT stop loss --- prix d'entrée : {self.entry_price} --- {self.balance} ---")

            # Reset
            self.position = None
            self.entry_price = None
            self.units = None
            self.stoploss = None
            
        # === TAKE PROFIT SHORT ===
        elif self.position == "short" and take_profit_short == True:
            # Calcul des gains/pertes
            pnl = (self.entry_price - close) * self.units

            # on débloque l'agrent de la balance
            self.balance += self.margin_per_trade  # marge restituée
            self.balance += pnl                    # PnL du trade
            self.trades.append(pnl)

            print(f"{candle.name} --- SHORT take profit --- prix d'entrée : {self.entry_price} --- {self.balance} ---")

            # Reset
            self.position = None
            self.entry_price = None
            self.units = None 
            self.stoploss = None

        # === OUVERTURE DE POSITION LONG ===
        if self.position is None and shouldibuy == True:
            self.position = "long"
            self.entry_price = close

            # On définit un stop loss dès l'entrée en position
            self.stoploss = close * (1 - 0.002) # Stop 0.2% sous le prix de cloture (prix d'entrée)
            # self.stoploss = bblower * (1 - 0.0005)  # Stop 0.05% sous BB_lower
            self.units = self.position_size / close

            # On immobilise 25€
            self.balance -= self.margin_per_trade

        # === STOP LOSS LONG ===
        elif self.position == "long" and low <= self.stoploss:
            # Calcul des gains/pertes
            pnl = (self.stoploss - self.entry_price) * self.units

            self.balance += self.margin_per_trade  # marge restituée
            self.balance += pnl                    # PnL du trade
            self.trades.append(pnl)

            print(f"{candle.name} --- LONG stop loss --- prix d'entrée : {self.entry_price} --- {self.balance} ---")

            # Reset
            self.position = None
            self.entry_price = None
            self.units = None
            self.stoploss = None
            
        # === TAKE PROFIT LONG ===
        elif self.position == "long" and take_profit_long == True:
            # Calcul des gains/pertes
            pnl = (close - self.entry_price) * self.units

            self.balance += self.margin_per_trade  # marge restituée
            self.balance += pnl                    # PnL du trade
            self.trades.append(pnl)

            print(f"{candle.name} --- LONG take profit --- prix d'entrée : {self.entry_price} --- {self.balance} ---")

            # Reset
            self.position = None
            self.entry_price = None
            self.units = None
            self.stoploss = None
        
        # Log de la balance actuelle pour le graphique
        self.balance_history.append(self.balance)


    def run(self):
        for _, candle in self.dataframe.iterrows():
            self.on_candle(candle)

        return {
            "final_balance": self.balance,
            "total_pnl": sum(self.trades),
            "number_of_trades": len(self.trades),
            "all_trades": self.trades
        }


def main():
    df = pd.read_csv(DATA_FILE, sep="\t")

    # Combiner 'Date' + 'Timestamp' en un seul datetime
    df["datetime"] = pd.to_datetime(df["Date"].astype(str) + " " + df["Timestamp"])

    # Mettre l’index
    df = df.set_index("datetime")

    # Optionnel retirer les anciennes colonnes
    df = df.drop(columns=["Date", "Timestamp"])

    # Ajout de la colonne RSI pour chaque candle
    df["RSI"] = rsi(df["Close"])

    # Ajout de la colonne contenant le RSI précédent
    df['prev_RSI'] = df['RSI'].shift(1)

    df["MoyMob"], df["BB_upper"], df['BB_lower'] = bollinger_bands(df["Close"])

    # Ajout de colonnes en décalé pour que pour chaque candle on garde certaines infos de la candle précédente
    df['prev_close'] = df['Close'].shift(1)
    df['prev_BB_lower'] = df['BB_lower'].shift(1)
    df['prev_BB_upper'] = df['BB_upper'].shift(1)

    df = df.dropna()

    bt = Backtester(df)

    results = bt.run()

    # ================================
    #     AFFICHAGE DES RESULTATS
    # ================================

    print("===== BACKTEST TERMINE =====")
    print(f"Balance finale        : {results['final_balance']:.2f} €")
    print(f"PNL total             : {results['total_pnl']:.2f} €")
    print(f"Nombre de trades      : {results['number_of_trades']}")
    print(f"Moyenne du nombre de trades : {results['number_of_trades']/3266} trades/jour")
    print("-----------------------------------")
    # print("Liste des trades (PNL unitaire) :")
    # for i, pnl in enumerate(results["all_trades"], start=1):
    #     print(f"Trade {i:02d} : {pnl:.2f} €")

    # ================================
    #      GRAPHIQUE DE BALANCE
    # ================================

    plt.figure(figsize=(12, 5))
    plt.plot(bt.balance_history, label="Balance", linewidth=1.5)
    plt.title("Évolution de la balance pendant le backtest")
    plt.xlabel("Nombre de candles")
    plt.ylabel("Balance (€)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()


# ===== BACKTEST TERMINE =====
# Balance finale        : 232.86 €
# PNL total             : 182.86 €
# Nombre de trades      : 16702

# ===== BACKTEST TERMINE =====
# Balance finale        : 254.33 €
# PNL total             : 204.33 €
# Nombre de trades      : 17372

# ===== BACKTEST TERMINE =====
# Balance finale        : 243.93 €
# PNL total             : 193.93 €
# Nombre de trades      : 18248

# stop 0.15%
# ===== BACKTEST TERMINE =====
# Balance finale        : 249.77 €
# PNL total             : 199.77 €
# Nombre de trades      : 16626

# Stop 0.13%
# TP BBupper
# ===== BACKTEST TERMINE =====
# Balance finale        : 246.61 €
# PNL total             : 196.61 €
# Nombre de trades      : 16585

# Stop 0.1% sous le prix de cloture
# TP bbuper + 0.05 centimes
# ===== BACKTEST TERMINE =====
# Balance finale        : 259.30 €
# PNL total             : 209.30 €
# Nombre de trades      : 17106

# Stop 0.2% sous le prix de cloture
# TP bbuper + 0.05 centimes
# ===== BACKTEST TERMINE =====
# Balance finale        : 249.95 €
# PNL total             : 199.95 €
# Nombre de trades      : 15755
# Moyenne du nombre de trades : 4.823943661971831 trades/jour

# Stop 0.2% sous le prix de cloture
# TP bbuper + 0.1 centimes
# ===== BACKTEST TERMINE =====
# Balance finale        : 248.21 €
# PNL total             : 198.21 €
# Nombre de trades      : 15720
# Moyenne du nombre de trades : 4.813227189222291 trades/jour

# tp moymob
# ===== BACKTEST TERMINE =====
# Balance finale        : 300.43 €
# PNL total             : 250.43 €
# Nombre de trades      : 32078
# Moyenne du nombre de trades : 9.821800367421924 trades/jour