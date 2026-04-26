class PlayerStats:

    def __init__(self, level=1, coins=0, mazesCompleted=0, fastestTime=None):
        self.level          = level
        self.coins          = coins
        self.mazesCompleted = mazesCompleted
        self.fastestTime    = fastestTime   # None until the player finishes their first maze


    def updateStats(self, timeTaken, coinsCollected=0):
        self.mazesCompleted += 1
        self.coins          += coinsCollected
        self.level          += 1

        if self.fastestTime is None or timeTaken < self.fastestTime:
            self.fastestTime = timeTaken


    def loadFromTuple(self, row):
        self.level, self.coins, self.mazesCompleted, self.fastestTime = row

    def toTuple(self):
        return self.level, self.coins, self.mazesCompleted, self.fastestTime