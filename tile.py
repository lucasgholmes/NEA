from constants import TILEWALL, TILEPATH, TILESTART, TILEFINISH


class Tile:

    def __init__(self, x, y, tileType):
        self.x       = x
        self.y       = y
        self.type    = tileType
        self.hasCoin      = False
        self.coinOffsetX  = 0.0
        self.coinOffsetY  = 0.0
        self.coinShrinking  = False
        self.coinShrinkScale = 1.0

    def isWalkable(self):
        return self.type != TILEWALL
