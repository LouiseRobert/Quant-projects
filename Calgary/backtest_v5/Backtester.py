BALANCE = 30 # Balance totale du compte
LEVERAGE = 20 # Levier
SPREAD = 0.4 # dollars

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
        self.trendline = None
        self.units = None # quantité d'or contrôlée 
        self.trades = [] # log des trades cloturés

        self.durations = {"open": None,
                          "close": None}

        self.rsi_cross_low = False
        self.rsi_cross_high = False

    def last_candles(self, index, label="close", k=1):
        """
        Renvoie les k dernières candles
        """
        return self.dataframe[label].loc[:index].iloc[-k:].tolist()
    
    def on_candle(self, candle, index):
        open = candle["Open"]
        close = candle["Close"]
        high = candle["High"]
        low = candle["Low"]
        rsi = candle["RSI"]
        datetime = candle["horodatage"]
        timestamp = candle["timestamp"]
        
        buy_signal = False
        sell_signal = False
        shouldibuy = False
        shouldisell = False

        daytime = datetime.hour >= 9 and not (datetime.weekday() == 4 and datetime.hour >= 22)
        print(f"{datetime} ----- RSI : {rsi}, close : {close}")
        # Position en cours ?
        if self.position is None:
            #### Conditions de long

            # couleur de la candle 
            if open < close:
                candle_color = "green"
            else:
                candle_color = "red"

            # Si le RSI passe de inférieur à 30 à supérieur à 30 et que le RSI actuel est < au précédent
            if rsi < 30 :
                self.rsi_cross_low = True
                self.rsi_cross_high = False # protection en cas de retournement

            #### Conditions de short
            # Si le RSI croise la barre des 73 par le dessus 
            if rsi > 70 :
                self.rsi_cross_high = True
                self.rsi_cross_low = False # protection en cas de retournement

            # Quand le RSI signale le retournement, on surveille le signal
            if self.rsi_cross_low and (rsi > 42):
                buy_signal = True
                sell_signal = False # protection en cas de retournement

            if self.rsi_cross_high and (rsi < 58) :
                sell_signal = True
                buy_signal = False # protection en cas de retournement

            # On entre en position après une candle inverse
            if buy_signal :#and candle_color == "red":
                shouldibuy = True and daytime

            if sell_signal :#and candle_color == "green":
                shouldisell = True and daytime
            
            # === OUVERTURE DE POSITION SHORT ===
            if shouldisell == True and daytime:
                direction = "short"
                print("SELL")

                exec_price = self.get_execution_price(close, direction, "entry")
                self.open_position(exec_price, direction)

                self.durations["open"] = timestamp

                shouldisell = False
                sell_signal = False

            # === OUVERTURE DE POSITION LONG ===
            elif shouldibuy == True and daytime:
                direction = "long"
                print("BUY")

                exec_price = self.get_execution_price(close, direction, "entry")
                self.open_position(exec_price, "long")

                self.durations["open"] = timestamp

                shouldibuy = False
                buy_signal = False

        # Si oui, on va gérer notre position en cours
        else:
            ### Conditions de vente de la position longue

            if self.position == "short":
                exec_price = self.get_execution_price(high, "long", "exit") # prix d'execution de sortie du short au prix ASK

                # === STOP LOSS SHORT ===
                if exec_price >= self.stoploss:
                    self.durations["close"] = timestamp
                    self.exit_trade("Stop loss short", "short", exec_price, candle.name)

                # === TAKE PROFIT SHORT ===
                elif low <= self.takeprofit:
                    exec_price = self.get_execution_price(low, "long", "exit") # prix d'execution de sortie du short au prix ASK
                    self.durations["close"] = timestamp

                    self.exit_trade("take profit", "short", exec_price, candle.name)

                elif (timestamp - self.durations["open"])/1000000000 > 5400:
                    exec_price = self.get_execution_price(close, "long", "exit") # prix d'execution de sortie du short au prix ASK
                    self.durations["close"] = timestamp

                    self.exit_trade("Time stop", "short", exec_price, candle.name)
                # === Rien ===
                else:
                    pass

            elif self.position == "long":
                exec_price = self.get_execution_price(low, "short", "exit") # prix d'execution de sortie du long au prix BID

                # === STOP LOSS LONG ===
                if exec_price <= self.stoploss:
                    self.durations["close"] = timestamp
                    self.exit_trade("Stop loss long", "long", exec_price, candle.name)

                # === TAKE PROFIT LONG ===
                elif high >= self.takeprofit:
                    self.durations["close"] = timestamp
                    exec_price = self.get_execution_price(high, "short", "exit") # prix d'execution de sortie du long au prix BID

                    self.exit_trade("take profit", "long", exec_price, candle.name)

                elif (timestamp - self.durations["open"])/1000000000 > 5400:
                    exec_price = self.get_execution_price(close, "short", "exit") # prix d'execution de sortie du short au prix ASK
                    self.durations["close"] = timestamp

                    self.exit_trade("Time stop", "long", exec_price, candle.name)

                else:
                    pass
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
            self.takeprofit = entry_price + (profit_amount / self.units)
        elif self.position == "short":
            self.stoploss = entry_price + (loss_amount / self.units)
            self.takeprofit = entry_price - (profit_amount / self.units)
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

        print(f"{datetime} --- {direction} {label} --- prix d'entree : {self.entry_price} --- {self.balance} ---")

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

        self.trendline = None

        self.durations = {
            "open": None,
            "close": None
        }

    def run(self):
        for index, candle in self.dataframe.iterrows():
            self.on_candle(candle, index)

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