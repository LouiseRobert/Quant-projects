#!/usr/bin/env python3
"""
Calcul de volatilité entre deux actifs?
Auteur : Louise Robert
Description :
"""

import yfinance as yf
import pandas as pd
from math import sqrt

def download_data(ticker: str, start: str = "2015-01-01", end: str = None) -> pd.Series:
    """
    Télécharge les prix de clôture dun actif.
    
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

def compute_volatility(rendements: pd.Series) -> float:
    """
    Calcule la volatilité d'une série de rendements journaliers.

    :@param rendements: Série de rendements journaliers
    :return: La volatilité annuelle d'un actif
    """
    # Calcul de la volatilité quotidienne
    daily_vol = rendements.std() # standard deviation = écart type

    # on annualise la volatilité 
    annualized_vol = daily_vol * sqrt(252)  # 252 jours de trading par an
    
    return annualized_vol

def volatility_ratio(ticker1: str, ticker2: str, start="2015-01-01", end=None):
    """
    Compare la volatilité de deux actifs.

    :@param ticker1: Actif à utiliser dans la comparaison de volatilité annuelle
    :@param ticker2: Second actif à comparer avec ticker1
    :@param start: Date de début de récolte des données de prix
    :@param end: Date de fin de récolte des données de prix
    """

    # On télécharge les données de prix des deux actifs
    data1 = download_data(ticker1, start, end)
    data2 = download_data(ticker2, start, end)
    
    # On calcule les taux de variations journaliers.
    rendement1 = data1.pct_change().dropna()
    rendement2 = data2.pct_change().dropna()
    
    # Calcul de la volatilité annualisée
    volatilite1 = compute_volatility(rendement1)
    volatilite2 = compute_volatility(rendement2)
    
    # Calcul du ratio entre volatilités des deux actifs
    ratio = volatilite1[ticker1] / volatilite2[ticker2]
    
    print(f"Volatilité annualisée de {ticker1} : {volatilite1[ticker1]:.2%}")
    print(f"Volatilité annualisée de {ticker2} : {volatilite2[ticker2]:.2%}")
    print(f"Volatility ratio ({ticker1}/{ticker2}) : {ratio:.2f}")

if __name__ == "__main__":
    volatility_ratio("MSFT", "GOOGL")