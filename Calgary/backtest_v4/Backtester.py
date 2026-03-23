
BALANCE = 100 # Balance totale du compte
LEVERAGE = 20 # Levier
SPREAD = 0.4 # dollars

# Coupe les trades après 166 minutes (+- 2h30)
TIME_STOP = 10000
BREAKEVEN_STOP = 300

class Backtester: 
    def __init__(self, df, profit_rate, loss_rate, balance=BALANCE, leverage=LEVERAGE): 
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
        self.balance_history = [self.balance]
        self.leverage = leverage 
        self.profit_rate = profit_rate
        self.loss_rate = loss_rate
        self.margin_ratio = 0.5
        self.margin_used = None
        self.position_size = None

        self.position = None # si je suis actuellement dans un trade 
        self.entry_price = None # si oui, à combien suis-je entrée 
        self.stoploss = None # le stop loss est fixe et calculé à la prise de position 
        self.takeprofit = None # Le Take profit est fixe et calculé à la prise de position 
        self.units = None # quantité d'or contrôlée 
        self.trades = [] # log des trades cloturés

        self.durations = {"open": None,
                          "close": None}

        self.rsi_cross_low = False
        self.rsi_cross_high = False

    def on_candle(self, candle):
        close = candle["Close"]
        high = candle["High"]
        low = candle["Low"]
        rsi = candle["RSI"]
        atr_pct = candle["ATR_pct"]
        datetime = candle["horodatage"]
        timestamp = candle["timestamp"]
    
        # Position en cours ?
        if self.position is None:
            #### Conditions de long

            # Si le RSI passe de inférieur à 30 à supérieur à 30 et que le RSI actuel est < au précédent
            if rsi < 24 :
                self.rsi_cross_low = True
            # Alors on considère qu'on est en position longue
            shouldibuy = self.rsi_cross_low and (rsi > 35)

            #### Conditions de short
            # Si le RSI croise la barre des 70 par le dessus 
            if rsi > 76 :
                self.rsi_cross_high = True
            # Alors on considère qu'on est en position short
            shouldisell = self.rsi_cross_high and (rsi < 65) 

            if rsi > 50:
                self.rsi_cross_low = False
            else:
                self.rsi_cross_high = False

            friday_after_21 = datetime.weekday() == 4 and datetime.hour > 21 
            
            # === OUVERTURE DE POSITION SHORT ===
            if shouldisell == True and (datetime.hour < 22 or (datetime.hour == 22 and datetime.minute <= 30)) and not friday_after_21:
                direction = "short"

                exec_price = self.get_execution_price(close, direction, "entry")
                self.open_position(exec_price, direction)

                self.durations["open"] = timestamp

            # === OUVERTURE DE POSITION LONG ===
            elif shouldibuy == True and (datetime.hour < 22 or (datetime.hour == 22 and datetime.minute <= 30)) and not friday_after_21:
                direction = "long"

                exec_price = self.get_execution_price(close, direction, "entry")
                self.open_position(exec_price, "long")

                self.durations["open"] = timestamp
        # Si oui, on va gérer notre position en cours
        else:
            ### Conditions de vente de la position longue

            price_sell_ok = high >= self.takeprofit
            # Alors on cloture la position longue
            take_profit_long = price_sell_ok

            ### conditions d'achat de la position short 

            price_buy_ok = low <= self.takeprofit
            # Alors on cloture la position short
            take_profit_short = price_buy_ok

            if self.position == "short":
                exec_price = self.get_execution_price(high, "long", "exit") # prix d'execution de sortie du short au prix ASK
                # === STOP LOSS SHORT ===
                if exec_price >= self.stoploss or (timestamp - self.durations["open"])/1000000000 > TIME_STOP:
                    self.durations["close"] = timestamp

                    self.exit_trade("stop loss", "short", exec_price, candle.name)

                # === TAKE PROFIT SHORT ===
                elif take_profit_short == True:
                    exec_price = self.get_execution_price(low, "long", "exit") # prix d'execution de sortie du short au prix ASK
                    self.durations["close"] = timestamp

                    self.exit_trade("take profit", "short", exec_price, candle.name)
                
                # === Modification du TP à Break even ===
                elif (timestamp - self.durations["open"])/1000000000 > BREAKEVEN_STOP:
                    self.takeprofit = self.entry_price - SPREAD/2

            elif self.position == "long":
                exec_price = self.get_execution_price(low, "short", "exit") # prix d'execution de sortie du long au prix BID
                # === STOP LOSS LONG ===
                if exec_price <= self.stoploss or (timestamp - self.durations["open"])/1000000000 > TIME_STOP:
                    self.durations["close"] = timestamp

                    self.exit_trade("stop loss", "long", exec_price, candle.name)

                # === TAKE PROFIT LONG ===
                elif take_profit_long == True:
                    self.durations["close"] = timestamp
                    exec_price = self.get_execution_price(high, "short", "exit") # prix d'execution de sortie du long au prix BID

                    self.exit_trade("take profit", "long", exec_price, candle.name)
                
                # === Modification du TP à Break even ===
                elif (timestamp - self.durations["open"])/1000000000 > BREAKEVEN_STOP:
                    self.takeprofit = self.entry_price + SPREAD/2
            else:
                pass

    def open_position(self, entry_price: float, direction: str = "long"):
        """
        Ouvre une position <direction> au prix <entry_price>
        
        :param entry_price: Prix d'entrée sur la position
        :type entry_price: float
        :param direction: Sens du trade: "long" ou "short"
        :type direction: str
        """
        self.position = direction.lower()
        self.entry_price = entry_price

        # balance totale avant trade
        balance_before_trade = self.balance

        # marge investie
        self.margin_used = self.balance * self.margin_ratio
        self.position_notional = self.margin_used * self.leverage
        self.units = (balance_before_trade * self.margin_ratio * self.leverage) / entry_price
            
        half_spread = SPREAD/2
        # SL / TP fixés en € sur la balance totale
        loss_amount = self.loss_rate * balance_before_trade
        profit_amount = self.profit_rate * balance_before_trade

        # prix de SL / TP correct
        if self.position == "long":
            self.stoploss = entry_price - (loss_amount / self.units)
            self.takeprofit = entry_price + (profit_amount / self.units) + half_spread
        elif self.position == "short":
            self.stoploss = entry_price + (loss_amount / self.units)
            self.takeprofit = entry_price - (profit_amount / self.units) - half_spread
        else:
            raise ValueError("direction must be 'long' or 'short'")
        
        # enfin on débite la marge
        self.balance -= self.margin_used
        
    def exit_trade(self, label, direction, price, datetime = ""):
        """
        Calcul du PNL du
        
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

        # print(f"{datetime} --- {direction} {label} --- prix d'entree : {self.entry_price} --- {self.balance} ---")

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
        pct_pnl = pnl/self.balance

        try:
            self.trades.append({"PNL": pnl,
                                "PNL_pct": pct_pnl,
                                "duration": (self.durations["close"] - self.durations["open"])})
        except TypeError as t:
            self.trades.append({"PNL": pnl,
                                "PNL_pct": pct_pnl,
                                "duration": 0})
        
        
    def reset(self):
        """
        Remet à None les parametres propres à une position courante.
        Met à jour l'historique de balance avec la balance courante.        
        """
        self.rsi_cross_high = False
        self.rsi_cross_low = False

        self.balance_history.append(self.balance)
        self.position = None
        self.margin_used = None
        self.entry_price = None
        self.units = None 
        self.stoploss = None
        self.takeprofit = None

        self.durations = {
            "open": None,
            "close": None
        }

    def run(self):
        for _, candle in self.dataframe.iterrows():
            self.on_candle(candle)

         # clôture forcée si position ouverte
        if self.position is not None:
            last_close = self.dataframe.iloc[-1]["Close"]

            if self.position == "long":
                exec_price = self.get_execution_price(last_close, "short", "exit")
                pnl = (exec_price - self.entry_price) * self.units
            else:
                exec_price = self.get_execution_price(last_close, "long", "exit")
                pnl = (self.entry_price - exec_price) * self.units

            self.close_position(pnl)
            self.reset()

        return {
            "final_balance": self.balance,
            "total_pnl": sum(trade["PNL"] for trade in self.trades),
            "number_of_trades": len(self.trades),
            "all_trades": self.trades,
        }