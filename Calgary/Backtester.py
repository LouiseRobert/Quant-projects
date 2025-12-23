
BALANCE = 50 # Balance totale du compte
LEVERAGE = 20 # Levier
SPREAD = 0.4 # dollars

class Backtester: 
    def __init__(self, df, balance=BALANCE, leverage=LEVERAGE): 
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
        # self.margin_per_trade = self.balance / 2 # Calcul de la valeur notionnelle totale contrôlée 
        self.margin_ratio = 0.5
        self.margin_used = None
        self.position_size = None

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
        prev_moymob = candle['prev_MoyMob']
        bbupper = candle["BB_upper"]
        prev_bbupper = candle["prev_BB_upper"]
        bblower = candle["BB_lower"]
        prev_bblower = candle["prev_BB_lower"]

        # Notion de trend
        sma50 = candle['SMA50']
        sma200 = candle['SMA200']

        trend_haussier = sma50 >= sma200

        # Notion de pente de la moyenne mobile, pour les conditions de sortie
        slope = moymob - prev_moymob 

        #### Conditions de long
        # Si le RSI passe de inférieur à 30 à supérieur à 30
        rsi_long_ok = (prev_rsi < 30) and (rsi > 30)
        # Et que le prix croise la BB lower par le bas
        price_long_ok = (prev_close < prev_bblower) and (close > bblower)
        # Alors on considère qu'on est en position longue
        shouldibuy = rsi_long_ok and price_long_ok and trend_haussier

        # Conditions de vente de la position longue
        # take profit en variable car ajustable
        tp_long = moymob #- (moymob*0.001)

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
        shouldisell = rsi_short_ok and price_short_ok and not trend_haussier

        # conditions d'achat de la position short 
        # Take profit en variable car ajustable
        tp_short = moymob #+ (moymob*0.001)

        # Si le RSI croise la barre des 30 par le dessous 
        rsi_buy_ok = (prev_rsi < 30) and (rsi > 30)
        # Et que le prix a atteint le take profit 
        price_buy_ok = close <= tp_short
        # Alors on cloture la position short
        take_profit_short = rsi_buy_ok or price_buy_ok

        # Position en cours ?
        if self.position is None:
            # === OUVERTURE DE POSITION SHORT ===
            if shouldisell == True:
                direction = "short"

                exec_price = self.get_execution_price(close, direction, "entry")
                self.open_position(exec_price, bbupper, direction)

            # === OUVERTURE DE POSITION LONG ===
            elif shouldibuy == True:
                direction = "long"

                exec_price = self.get_execution_price(close, direction, "entry")
                self.open_position(exec_price, bblower, "long")
        # Si oui, on va gérer notre position en cours
        else:
            if self.position == "short":
                exec_price = self.get_execution_price(close, "long", "exit") # prix d'execution de sortie du short au prix ASK
                # === STOP LOSS SHORT ===
                if exec_price >= self.stoploss:
                    self.exit_trade("stop loss", "short", exec_price, candle.name)

                # === TRAILING STOP ===
                # Si la moymob est supérieure au prix d'entrée du short ou que la moyenne mobile est en train de monter
                # elif moymob > self.entry_price and slope > 0:
                #     self.exit_trade("trailing stop", "short", close, candle.name)

                # === TAKE PROFIT SHORT ===
                elif take_profit_short == True:
                    self.exit_trade("take profit", "short", exec_price, candle.name)

            elif self.position == "long":
                exec_price = self.get_execution_price(close, "short", "exit") # prix d'execution de sortie du long au prix BID
                # === STOP LOSS LONG ===
                if exec_price <= self.stoploss:
                    self.exit_trade("stop loss", "long", exec_price, candle.name)
                
                # === TRAILING STOP ===
                # Si la moymob est inférieure au prix d'entrée du long ou que la moyenne mobile est en train de chuter
                # elif moymob < self.entry_price and slope < 0:
                #     self.exit_trade("trailing stop", "long", close, candle.name)

                # === TAKE PROFIT LONG ===
                elif take_profit_long == True:
                    self.exit_trade("take profit", "long", exec_price, candle.name)

    def open_position(self, entry_price: float, bb, direction: str = "long"):
        """
        Ouvre une position <direction> au prix <entry_price>
        
        :param entry_price: Prix d'entrée sur la position
        :type entry_price: float
        :param direction: Sens du trade: "long" ou "short"
        :type direction: str
        """
        self.position = direction
        self.entry_price = entry_price

        self.margin_used = self.balance * self.margin_ratio
        self.position_size = self.margin_used * self.leverage
        self.units = self.position_size / entry_price
        self.balance -= self.margin_used

        # intégration du spread pour le calcul des stops
        half_spread = SPREAD / 2

        if direction in ("short", "Short"):
            # On définit un stop loss dès l'entrée en position
            # self.stoploss = entry_price * (1 + 0.003) # Stop 0.3% au dessus du prix de cloture (prix d'entrée)
            self.stoploss = bb * (1 + 0.01)  # Stop 0.05% au dessus de BB_upper
            self.stoploss += half_spread
            
            # self.stoploss = self.entry_price - ((self.balance*0.005)/self.units) # Stop quand on a perdu 0.5% de la balance totale 
        elif direction in ("long", "Long"):
            # On définit un stop loss dès l'entrée en position
            # self.stoploss = entry_price * (1 - 0.0036) # Stop 0.36% sous le prix de cloture (prix d'entrée)
            self.stoploss = bb * (1 - 0.01)  # Stop 0.05% sous BB_lower
            self.stoploss -= half_spread

            # self.stoploss = self.entry_price + ((self.balance*0.005)/self.units)# Stop quand on a perdu 0.5% de la balance totale 
        else:
            raise ValueError("stop_loss : direction must be 'long' or 'short'")
        
    def exit_trade(self, label, direction, price, datetime = ""):
        """
        Docstring for exit_trade
        
        :param label: Description de la sortie du trade
        :param direction: Sens du trade à stopper
        :param price: Prix d'excution de la sortie du trade
        :param datetime: Date et temps pour le log
        """
        # Calcul des gains/pertes
        if direction in ("short", "Short"):
            pnl = (self.entry_price - price) * self.units
        elif direction in ("long", "Long"):
            pnl = (price - self.entry_price) * self.units
        else:
            raise ValueError(f"{label} : direction must be 'long' or 'short'")

        self.close_position(pnl)

        print(f"{datetime} --- {direction} {label} --- prix d'entrée : {self.entry_price} --- {self.balance} ---")

        # Reset
        self.reset()

    def get_execution_price(self, price, direction, side):
        """
        Renvoie le prix d'éxécution simulé selon le spread choisi
        side: 'entry' ou 'exit'
        direction: 'long' ou 'short'
        """
        half_spread = SPREAD / 2

        if direction in ("long", "Long"):
            if side == "entry":
                return price + half_spread  # achat au ask
            else:
                return price - half_spread  # vente au bid

        elif direction in ("short", "Short"):
            if side == "entry":
                return price - half_spread  # vente au bid
            else:
                return price + half_spread  # rachat au ask

    def close_position(self, pnl):
        """
        Fermeture d'un trade, mise à jour des variables du backtest
        
        :param pnl: Résultat du trade en train d'être fermé
        """

        # on débloque l'agrent de la balance
        self.balance += self.margin_used # marge restituée
        self.balance += pnl # pnl du trade
        self.trades.append(pnl)
        
    def reset(self):
        """
        Remet à None les parametres propres à une position courante.
        Met à jour l'historique de balance avec la balance courante.        
        """
        self.position = None
        self.margin_used = None
        self.entry_price = None
        self.units = None 
        self.stoploss = None
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