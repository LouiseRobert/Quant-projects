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
        self.dataframe = df 
        self.balance = balance 
        self.balance_history = []
        self.leverage = leverage 
        self.margin_per_trade = margin_per_trade # Calcul de la valeur notionnelle totale contrôlée 
        self.position_size = margin_per_trade * leverage 

        self.position = None # si je suis actuellement dans un trade 
        self.entry_price = None # si oui, à combien suis-je entrée 
        self.stoploss = None # le stop loss est fixe et calculé à la prise de position 
        self.units = None # quantité d'or contrôlée 
        self.trades = [] # log des trades cloturés
        self.limit = None

    def on_candle(self, candle):
        open_ = candle["Open"]
        close = candle["Close"]
        prev_close = candle["prev_close"]
        high = candle["High"]
        low = candle["Low"]
        rsi = candle["RSI"]
        prev_rsi = candle["prev_RSI"]
        moymob = candle["MoyMob"]
        bbupper = candle["BB_upper"]
        bblower = candle["BB_lower"]
        prev_bblower = candle["prev_BB_lower"]

        # Conditions d'achat
        rsi_buy_ok = (prev_rsi < 30) and (rsi > 30)
        price_buy_ok = (prev_close < prev_bblower) and (close > bblower)
        shouldibuy = rsi_buy_ok and price_buy_ok

        # Conditions de vente
        # tp_price = (bbupper + moymob)/2 # TP au milieu entre la moyenne mobile et BB Upper
        tp_price = bbupper + 0.05

        rsi_sell_ok = (prev_rsi > 70) and (rsi < 70)
        price_sell_ok = close >= tp_price
        take_profit = rsi_sell_ok or price_sell_ok

        # === OUVERTURE DE POSITION ===
        if self.position is None:
            if self.limit != None:
                if low < self.limit:
                    self.position = "long"
                    self.entry_price = self.limit
                    self.limit = None

                    self.stoploss = self.entry_price * (1 - 0.002) # Stop 0.2% sous le prix de cloture (prix d'entrée)
                    # self.stoploss = bblower * (1 - 0.0005)  # Stop 0.05% sous BB_lower
                    self.units = self.position_size / self.entry_price

                    # On immobilise 25€
                    self.balance -= self.margin_per_trade
                else:
                    if close >= moymob:
                        self.limit = None
            else:
                if shouldibuy == True:
                    self.limit = bblower
            

        # === STOP LOSS ===
        elif self.position == "long" and low <= self.stoploss:
            pnl = (self.stoploss - self.entry_price) * self.units

            self.balance += self.margin_per_trade  # marge restituée
            self.balance += pnl                    # PnL du trade
            self.trades.append(pnl)

            print(f"{candle.name} --- stop loss --- prix d'entrée : {self.entry_price} --- {self.balance} ---")

            # Reset
            self.position = None
            self.entry_price = None
            self.units = None
            

        # === TAKE PROFIT ===
        elif self.position == "long" and take_profit == True:
            pnl = (close - self.entry_price) * self.units

            self.balance += self.margin_per_trade  # marge restituée
            self.balance += pnl                    # PnL du trade
            self.trades.append(pnl)

            print(f"{candle.name} --- take profit --- prix d'entrée : {self.entry_price} --- {self.balance} ---")

            # Reset
            self.position = None
            self.entry_price = None
            self.units = None
        
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