class Trendline:
    def __init__(self, direction, candles, tolerance=0.001):
        """
        Classe permettant de gérer la trendline d'un trade.
        Une instance de cette classe correspond à UN trade
        Elle est créée à l'ouverture du trade
        et supprimée à la fermeture.*

        direction :
            "long"  -> trendline sous le prix
            "short" -> trendline au-dessus du prix

        tolerance :
            tolérance avant de considérer qu'il y a
            une véritable cassure.

            0.001 = 0,1 %
        """

        self.direction = direction.lower()
        self.tolerance = tolerance

        # Liste des points utilisés par la trendline.
        # Chaque point est :
        # (x, prix)
        # Exemple :
        # [(0, 4900), (12, 4950)]
        self.points = []

        # Recherche du premier swing
        self.points.append(self.find_first_swing(candles))

        self.slope = None # Pente de la droite
        self.intercept = None # Ordonnée à l'origine
        self.active = False # Indique si nous avons actuellement une trendline exploitable.

    def find_first_swing(self, prices):
        """
        Trouve le premier point P0 de la trendline.
        prices :
            Liste des Low pour un LONG
            Liste des High pour un SHORT
        direction :
            "long"  -> cherche le prix le plus bas
            "short" -> cherche le prix le plus haut
        Retourne :
            (index, prix)
        """

        if self.direction == "long":
            index = prices.index(min(prices))

        elif self.direction == "short":
            index = prices.index(max(prices))

        else:
            raise ValueError("direction doit être 'long' ou 'short'")

        return (index, prices[index])

    def add_point(self, x, price):
        """
        Ajoute un nouveau point à la trendline.

        x     = numéro de la bougie depuis l'entrée
        price = prix du swing

        Exemple :
            add_point(12, 4950)
        """
        self.points.append((x, price))

        # Impossible de tracer une droite
        # avec un seul point.
        if len(self.points) < 2:
            self.active = False
            return

        # Avec au moins deux points,
        # on peut calculer la trendline.
        self.calculate()

    def calculate(self):
        """
        Calcule la droite passant par les deux derniers
        points de la trendline.

        y = slope * x + intercept
        """
        # On prend les deux derniers points.
        x0, y0 = self.points[-2]
        x1, y1 = self.points[-1]

        # Sécurité : impossible d'avoir deux points
        # avec exactement le même x.
        if x1 == x0:
            return

        # Calcul de la pente.
        self.slope = (y1 - y0) / (x1 - x0)

        # Calcul de l'intercept.
        self.intercept = y0 - self.slope * x0

        self.active = True

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
        