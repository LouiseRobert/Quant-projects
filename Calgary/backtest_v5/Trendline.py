class Trendline:
    def __init__(self, direction, prices, tolerance=0.006):

        self.direction = direction.lower()
        self.tolerance = tolerance

        self.points = []

        self.slope = None
        self.intercept = None
        self.active = False

        self.min_slope = 0.1
        self.min_slope_factor = 0.02

        # Le dernier élément correspond à la candle courante
        self.current = len(prices) - 1

        # P0 : toujours présent
        self.points.append(self.find_first_swing(prices))

        # P1 : soit un vrai swing, soit une ligne provisoire
        self.find_second_swing(prices)

    def find_first_swing(self, prices):

        if self.direction == "long":
            index = prices.index(min(prices))

        elif self.direction == "short":
            index = prices.index(max(prices))

        else:
            raise ValueError("direction doit être 'long' ou 'short'")

        return (index, prices[index])

    def find_second_swing(self, prices):

        x0, y0 = self.points[0]

        candidates = []

        # Cherche uniquement les candles APRÈS P0
        for x in range(x0 + 1, len(prices)):

            price = prices[x]

            slope = (price - y0) / (x - x0)

            if abs(slope) < self.min_slope:
                continue

            candidates.append((x, price, slope))

        # Aucun candidat réel
        if not candidates:

            # Ligne provisoire
            if self.direction == "long":
                p1 = (
                    self.current,
                    y0 + self.min_slope * (self.current - x0)
                )
            else:
                p1 = (
                    self.current,
                    y0 - self.min_slope * (self.current - x0)
                )

        else:

            # P1 donnant la pente la plus plate
            p1 = min(candidates, key=lambda c: abs(c[2]))[:2]

        self.points.append(p1)

        # Construction immédiate de la trendline
        self.calculate()

    def add_swing(self, x, price):

        x0, y0 = self.points[0]

        if x == x0:
            return False

        new_slope = (price - y0) / (x - x0)

        # Pente trop plate
        if abs(new_slope) < self.min_slope:
            return False

        # On ne remplace la ligne que par une pente plus plate
        if self.slope is not None and abs(new_slope) >= abs(self.slope):
            return False

        # Nouveau P1 accepté
        self.points[1] = (x, price)

        self.calculate()

        return True

    def calculate(self):

        x0, y0 = self.points[0]
        x1, y1 = self.points[1]

        if x1 == x0:
            self.active = False
            self.slope = None
            self.intercept = None
            return False

        self.slope = (y1 - y0) / (x1 - x0)
        self.intercept = y0 - self.slope * x0

        self.active = True

        return True
        
    def price_at(self, x):
        """
        Retourne le prix de la trendline à la bougie x.

        Exemple :
            trendline.price_at(20)
        """

        if not self.active:
            return None

        return self.slope * x + self.intercept

    def is_breakout(self, x, price):
        """
        Détermine si le prix a réellement cassé la trendline.

        Pour un LONG :
            cassure si le prix est suffisamment SOUS la ligne
        Pour un SHORT :
            cassure si le prix est suffisamment AU-DESSUS.
        """

        if not self.active:
            return False

        trendline_price = self.price_at(x)

        # =========================
        # LONG
        # =========================

        if self.direction == "long":

            # Exemple :
            #
            # trendline = 5000
            # tolerance = 0.1 %
            # seuil = 4995
            # Entre 4995 et 5000 :
            #     pas de cassure          
            # Sous 4995 :
            #     cassure

            breakout_level = (
                trendline_price
                * (1 - self.tolerance)
            )

            return price < breakout_level


        # =========================
        # SHORT
        # =========================

        else:

            # Même logique mais inversée.
            breakout_level = (
                trendline_price
                * (1 + self.tolerance)
            )

            return price > breakout_level

    def update(self, prices):

        # Candle actuelle = dernière valeur de la liste
        current_price = prices[-1]

        # 1. Vérifier une cassure sur la candle actuelle
        if self.is_breakout(self.current, current_price):
            return "breakout"

        # 2. Vérifier si candle -1 est un nouveau swing
        swing = self.is_new_swing(prices)

        if swing is not None:
            if self.add_swing(*swing):
                return "new_swing"

        return "nothing"

    def is_new_swing(self, prices):

        previous = prices[0]
        current = prices[1]
        next_price = prices[2]

        if self.direction == "long":
            if current < previous and current < next_price:
                return (self.current - 1, current)

        elif self.direction == "short":
            if current > previous and current > next_price:
                return (self.current - 1, current)

        return None