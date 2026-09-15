import pandas as pd
import matplotlib.pyplot as plt 
from Backtester import Backtester
from maths import bollinger_bands, rsi, monte_carlo_simulation
import numpy as np

DATA_FILE = "../data/XAU_1m_2023.csv"

LOSS_RATE = 0.05
PROFIT_RATE = 0.0029

def main(tp_rate = PROFIT_RATE, sl_rate = LOSS_RATE):
    df = pd.read_csv(DATA_FILE, sep=";")

    # Conversion de la colonne Date en datetime
    df["datetime"] = pd.to_datetime(
        df["Date"],
        format="%Y.%m.%d %H:%M"
    )

    # Conversion en timestamp Unix (secondes)
    df["timestamp"] = df["datetime"].astype("int64") # 10**9

    df["horodatage"] = df["datetime"]

    # Mettre le datetime en index
    df = df.set_index("datetime")

    # Nettoyage des colonnes inutiles
    df = df.drop(columns=["Date"])

    # Ajout de la colonne RSI pour chaque candle
    df["RSI"] = rsi(df["Close"])

    # Ajout de la colonne contenant le RSI précédent
    df['RSI-1'] = df['RSI'].shift(1)
    df['RSI-2'] = df['RSI'].shift(2)

    df["MoyMob"], df["BB_upper"], df['BB_lower'] = bollinger_bands(df["Close"], 21)
    
    df['prev_BB_lower'] = df['BB_lower'].shift(1)
    df['prev_BB_upper'] = df['BB_upper'].shift(1)

    df = df.dropna()

    bt = Backtester(df, profit_rate=tp_rate, loss_rate=sl_rate)

    results = bt.run()

    positifs = 0
    negatifs = 0
    for trade in results["all_trades"]:
        if trade["PNL"] >= 0:
            positifs += 1
        else:
            negatifs += 1

    wins = [t["PNL"] for t in results["all_trades"] if t["PNL"] > 0]
    avg_win = sum(wins) / len(wins)

    losses = [t["PNL"] for t in results["all_trades"] if t["PNL"] < 0]
    avg_loss = sum(losses) / len(losses)  # sera négatif

    total_gain = sum(wins)
    total_loss = abs(sum(losses))

    profit_factor = total_gain / total_loss

    equity = 100
    equity_curve = []

    for t in results["all_trades"]:
        equity += t["PNL"]
        equity_curve.append(equity)

    peak = 100
    max_dd = 0

    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak
        if dd > max_dd:
            max_dd = dd

    max_dd_percent = max_dd * 100

    # ================================
    #     AFFICHAGE DES RESULTATS
    # ================================

    # print("===== BACKTEST TERMINE =====")
    # print(f"Balance finale        : {results['final_balance']:.2f} €")
    # print(f"PNL total             : {results['total_pnl']:.2f} €")
    # print(f"Nombre de trades      : {results['number_of_trades']}")
    # print(f"Nombre de trades gagnants   : {positifs}")
    # print(f"Nombre de trades perdants   : {negatifs}")
    # print(f"Winrate                     : {((positifs/results['number_of_trades'])*100):.2f}%")
    # print(f"Average win                 : {avg_win:.2f}")
    # print(f"Average loss                : {avg_loss:.2f}")
    # print(f"Profit factor               : {profit_factor:.2f}")
    # print(f"Max drawdown                : {max_dd_percent:.2f} %")
    # print(f"Espérance                   : {(((positifs/results['number_of_trades'])) * avg_win) + ((1-((positifs/results['number_of_trades']))) * avg_loss):.2f}")
    # print(f"Moyenne du nombre de trades : {results['number_of_trades']/260:.2f} trades/jour")
    # print("-----------------------------------")

    print(f"{tp_rate:.5f};{sl_rate:.5f};{results['final_balance']:.2f};{(((positifs/results['number_of_trades'])) * avg_win) + ((1-((positifs/results['number_of_trades']))) * avg_loss):.2f};{profit_factor:.2f};{results['total_pnl']:.2f};{results['number_of_trades']};{positifs};{negatifs};{((positifs/results['number_of_trades'])*100):.2f};{avg_win:.2f};{avg_loss:.2f};{max_dd_percent:.2f};{results['number_of_trades']/260:.2f}")

    # final_balances, drawdowns = monte_carlo_simulation(results["all_trades"])

            
if __name__ == "__main__":

    print("Take profit;Stop loss;Balance finale;Esperance;Profit factor;PNL Total;Nombre de trades;Nombre de positifs;Nombre de negatifs;Winrate;Montant moyen gagne;Montant moyen perdu;Drawdown max;Nombre de trades journalier")

    for tp_i in range(10, 250, 5):      # 0.001 → 0.025
        tp = tp_i / 10000

        for sl_i in range(50, 1500, 50):  # 0.005 → 0.15
            sl = sl_i / 10000

            main(tp_rate=tp, sl_rate=sl)
