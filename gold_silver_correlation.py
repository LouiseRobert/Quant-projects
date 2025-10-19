#!/usr/bin/env python3
"""
Analyse de corrélation entre l'or et l'argent.
Auteur : Louise Robert
Description :
    Télécharge les données historiques de l'or (XAUUSD) et de l'argent (XAGUSD),
    calcule leur corrélation et produit une visualisation claire.
"""

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

def download_data(ticker: str, start: str = "2015-01-01", end: str = None) -> pd.Series:
    """
    Télécharge les prix de clôture d’un actif.
    
    :@param ticker: Ticker de l'actif à télécharger (ex: AAPL)
    :@param start: Date de début de la série à télécharger (format: YYYY-MM-DD)
    :@param end: Date de fin de la série à télécharger (format: YYYY-MM-DD)
    :return: Une série de prix de fermeture de l'actif courant sur la période donnée
    """
    # On télécharge le dataframe des données de prix de l'actif 
    dataframe = yf.download(ticker, start=start, end=end, progress=False)

    # On récupère uniquement le prix de cloture de l'actif en une série
    serie_closeprice = dataframe['Close']

    # on renomme cette série avec le nom ticker de l'actif courant
    # serie_closeprice.rename(ticker)

    return serie_closeprice

def compute_correlation(series1: pd.Series, series2: pd.Series, window: int = 60) -> pd.Series:
    """
    Calcule la corrélation glissante entre deux séries de prix.
    
    :@param series1: Première série dont on va calculer la corrélation
    :@param series2: Seconde série à comparer avec la première
    :@param window: fenetre de glissement, nombre fixe d'observation utilisé par fenetre si integer
    :return: Le coefficient de corrélation de Pearson des deux séries données.
    """

    # on applique une fenetre glissante sur la première série
    serieglissante = series1.rolling(window)

    # on calcule le coefficient de correlation sur cette première série par rapport à la seconde
    # la corrélation de Pearson est utilisée par défaut
    coef_correlation = serieglissante.corr(series2)

    return coef_correlation

def plot_correlation(prices: pd.DataFrame, rolling_corr: pd.Series):
    """
    Affiche les courbes de prix et leur corrélation glissante.

    :@param prices: dataframe à afficher
    :@param rolling_corr: corrélation glissante
    """
    fig, ax1 = plt.subplots(figsize=(10, 6))

    ax1.set_title("Corrélation entre l'Or et l'Argent", fontsize=14)
    ax1.plot(prices.index, prices["GC=F"]/prices["GC=F"].iloc[0], label="Or (normalisé)", color="gold")
    ax1.plot(prices.index, prices["SI=F"]/prices["SI=F"].iloc[0], label="Argent (normalisé)", color="silver")
    ax1.set_ylabel("Prix normalisé")
    ax1.legend(loc="upper left")

    ax2 = ax1.twinx()
    ax2.plot(rolling_corr.index, rolling_corr, color="black", linestyle="solid", label="Corrélation 60j")
    ax2.set_ylabel("Corrélation")
    ax2.legend(loc="lower right")

    plt.tight_layout()
    plt.show()

def main():
    # On télécharge les données de l'or et de l'argent
    # "=F" car on parle des contrats à terme sur l'or et l'argent, Yahoo ne fournissant pas de prix spot sur ces actifs
    gold = download_data("GC=F", start = "2015-01-01")
    silver = download_data("SI=F", start = "2015-01-01")

    # On concatène les séries gold et silver et on supprime les valeurs nulles
    prices = pd.concat([gold, silver], axis=1).dropna()

    # On calcule la corrélation glissante des deux actifs 
    rolling_corr = compute_correlation(prices["GC=F"], prices["SI=F"])

    # On affiche un graphique de visualisation de la corrélation de l'or et de l'argent
    # plot_correlation(prices, rolling_corr)

    # On calcule simplement le coeffcient de corrélation entre l'or et l'argent et on l'affiche (2 chiffres après la virgule)
    print(f"Corrélation moyenne Pearson : {prices['GC=F'].corr(prices['SI=F'], method = "pearson"):.2f}")
    print(f"Corrélation moyenne Kendall's Tau : {prices['GC=F'].corr(prices['SI=F'], method = "kendall"):.2f}")
    print(f"Corrélation moyenne Spearman: {prices['GC=F'].corr(prices['SI=F'], method = "spearman"):.2f}")

if __name__ == "__main__":
    main()
