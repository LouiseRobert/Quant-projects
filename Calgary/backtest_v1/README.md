# Version 1 du backtest de ma stratégie.

J'ai choisi de versionner mes backtests de cette façon car je veux être libre de la direction que prend l'évolution des backtests.

### La stratégie évoquée dans cette version 1:
Dans cette version la stratégie se décompose comme suit:

Pour chaque candle de 1min sont calculés RSI et les bandes de bollinger, ainsi que la MA: "milieu" des deux bandes de bollinger.

Deux conditions sont necessaires pour passer un ordre à l'achat ou à la vente.
Pour chaque bande de bollinger (BB), si le prix était hors bandes et revient entre les deux bandes => 1ère condition OK
Pour chaque candle, si le RSI calculé dépasse la borne 30 ou la borne 70 et revient vers un RSI moins extrème (<30 ou >70) => 2ème condition OK

Dans ce cas on passe un ordre dans la direction appropriée.

La condition de sortie de trade est simple:
- Soit le stop loss a été atteint.
- Soit on atteint la moyenne mobile centrale des BB
- Soit le RSI ressort des bornes 30 ou 70 dans le sens favorable au trade (70 pour un achat par exemple) (Ce scénario n'arrive jamais)

# Reflexions
Cette stratégie, bien que prometteuse, ne me satisfait pas.
Tout d'abord et principalement, le take profit à la moyenne mobile me positionne souvent en négatif sur le trade. Cependant, le trade est labellisé "take profit".
Ca me fait perdre souvent de l'argent, bien que le backtest montre une stratégie solide sur le long terme, je ne la trouve pas assez stable pour cette raison.
Ensuite, je pense que pour une stratégie suivante il serait interessant d'étudier un take profit fixe.
