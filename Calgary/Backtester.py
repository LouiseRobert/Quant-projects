
BALANCE = 50 # Balance totale du compte
LEVERAGE = 20 # Levier

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
        bbupper = candle["BB_upper"]
        prev_bbupper = candle["prev_BB_upper"]
        bblower = candle["BB_lower"]
        prev_bblower = candle["prev_BB_lower"]
        
        if self.balance < self.balance * self.margin_ratio:
            print("Fonds insuffisant.")
            return

        #### Conditions de long
        # Si le RSI passe de inférieur à 30 à supérieur à 30
        rsi_long_ok = (prev_rsi < 30) and (rsi > 30)
        # Et que le prix croise la BB lower par le bas
        price_long_ok = (prev_close < prev_bblower) and (close > bblower)
        # Alors on considère qu'on est en position longue
        shouldibuy = rsi_long_ok and price_long_ok 

        # Conditions de vente de la position longue
        # take profit en variable car ajustable
        tp_long = moymob 

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
        shouldisell = rsi_short_ok and price_short_ok 

        # conditions d'achat de la position short 
        # Take profit en variable car ajustable
        tp_short = moymob 

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
                self.open_position(close, "short")

            # === OUVERTURE DE POSITION LONG ===
            elif shouldibuy == True:
                self.open_position(close, "long")
        # Si oui, on va gérer notre position en cours
        else:
            if self.position == "short":
                # === STOP LOSS SHORT ===
                if close >= self.stoploss:
                    self.stop_loss("short", close, candle.name)

                # === TAKE PROFIT SHORT ===
                elif take_profit_short == True:
                    self.take_profit("short", close, candle.name)
            elif self.position == "long":
                # === STOP LOSS LONG ===
                if close <= self.stoploss:
                    self.stop_loss("long", close, candle.name)

                # === TAKE PROFIT LONG ===
                elif take_profit_long == True:
                    self.take_profit("long", close, candle.name)

    def open_position(self, entry_price: float, direction: str = "long"):
        """
        Ouvre une position <direction> au prix <entry_price>
        
        :param entry_price: Prix d'entrée sur la position
        :type entry_price: float
        :param direction: Sens du trade: "long" ou "short"
        :type direction: str
        """
        if direction in ("short", "Short"):
            # On définit un stop loss dès l'entrée en position
            self.stoploss = entry_price * (1 + 0.002) # Stop 0.2% au dessus du prix de cloture (prix d'entrée)
            # self.stoploss = bblower * (1 + 0.0005)  # Stop 0.05% au dessus de BB_upper
        elif direction in ("long", "Long"):
            # On définit un stop loss dès l'entrée en position
            self.stoploss = entry_price * (1 - 0.002) # Stop 0.2% sous du prix de cloture (prix d'entrée)
            # self.stoploss = bblower * (1 - 0.0005)  # Stop 0.05% sous BB_upper
        else:
            raise ValueError("stop_loss : direction must be 'long' or 'short'")
        
        self.position = direction
        self.entry_price = entry_price

        self.margin_used = self.balance * self.margin_ratio
        self.position_size = self.margin_used * self.leverage
        self.units = self.position_size / entry_price
        self.balance -= self.margin_used

    def stop_loss(self, direction, price, datetime = ""):
        """
        Déclenche un stop loss à close price et calcul de PNL correspondant au sens de la position en cours
        
        :param direction: Sens du trade à stopper
        :param datetime: Date et temps pour le log
        """
        # Calcul des gains/pertes
        if direction in ("short", "Short"):
            pnl = (self.entry_price - price) * self.units
        elif direction in ("long", "Long"):
            pnl = (price - self.entry_price) * self.units
        else:
            raise ValueError("stop_loss : direction must be 'long' or 'short'")

        self.close_position(pnl)

        print(f"{datetime} --- {direction} stop loss --- prix d'entrée : {self.entry_price} --- {self.balance} ---")

        # Reset
        self.reset()

    def take_profit(self, direction, price, datetime = ""):
        """
        déclenche un take profit au prix price dans la direction du trade.
        
        :param direction: Sens du trade
        :param price: Prix auquel cloturer le trade
        :param datetime: Date et temps pour le log
        """
        # Calcul des gains/pertes
        if direction in ("short", "Short"):
            pnl = (self.entry_price - price) * self.units
        elif direction in ("long", "Long"):
            pnl = (price - self.entry_price) * self.units
        else:
            raise ValueError("stop_loss : direction must be 'long' or 'short'")

        self.close_position(pnl)

        print(f"{datetime} --- {direction} take profit --- prix d'entrée : {self.entry_price} --- {self.balance} ---")

        # Reset
        self.reset()
    
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