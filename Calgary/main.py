import pandas as pd
import matplotlib.pyplot as plt 
from Backtester import Backtester
from maths import bollinger_bands, rsi
import numpy as np

DATA_FILE = "./data/XAUUSD.csv"

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

    df['prev_MoyMob'] = df["MoyMob"].shift(5)
    
    # Ajout de colonnes en décalé pour que pour chaque candle on garde certaines infos de la candle précédente
    df['prev_close'] = df['Close'].shift(1)
    df['prev_BB_lower'] = df['BB_lower'].shift(1)
    df['prev_BB_upper'] = df['BB_upper'].shift(1)

    # Moyennes mobiles
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()

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

    # balance = np.array(bt.balance_history, dtype=float)
    # price = df["Close"].values.astype(float)
    # min_len = min(len(balance), len(price))
    # balance = balance[-min_len:]
    # price = price[-min_len:]
    # assert balance[0] > 0, "Balance initiale invalide"
    # assert price[0] > 0, "Prix initial invalide"

    # balance_norm = balance / balance[0] * 100
    # price_norm = price / price[0] * 100

    # plt.figure(figsize=(12, 5))

    # plt.plot(balance_norm, label="Stratégie (base 100)", linewidth=1.5)
    # plt.plot(price_norm, label="Or (base 100)", linewidth=1, alpha=0.7)

    # plt.title("Performance relative : stratégie vs or")
    # plt.xlabel("Nombre de candles")
    # plt.ylabel("Base 100")
    # plt.grid(True)
    # plt.legend()
    # plt.tight_layout()
    # plt.show()






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