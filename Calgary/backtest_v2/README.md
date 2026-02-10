# Version 2 du backtest de ma stratégie.

Cette stratégie part du principe que l'on sait que le prix va aller dans notre direction et qu'au moins il va toucher notre TP. L'idée est de ne carrément pas mettre de stop loss. 
On va quand même mettre un stop loss assez loin pour se prévenir des fausses alertes mais suffisamment loin pour permettre au prix de faire sa vie jusqu'à toucher notre TP.

### La stratégie évoquée dans cette version 2:
Dans cette version la stratégie se décompose comme suit:

Pour chaque candle de 1min sont calculés RSI et les bandes de bollinger, ainsi que la MA: "milieu" des deux bandes de bollinger.

Voici les conditions pour passer un ordre à l'achat ou à la vente:
- le RSI doit être sorti des bornes 70 et 30 à la candle -2
- Le RSI -1 ne doit pas dépasser le RSI -2 
- L'achat ou la vente ne se fait qu'après la cloture de cette seconde candle.

Dans ce cas on passe un ordre dans la direction appropriée.

La condition de sortie de trade est simple:
- Soit le stop loss a été atteint.
- Soit on atteint le take profit.

Le take profit est définit comme 0.64% de mon capital total.
Le stop loss est définit comme 5% du capital total.

# Reflexions
