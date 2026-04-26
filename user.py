import bcrypt
import mysql.connector


class User:

    def __init__(self, db):
        self._db           = db
        self.username      = None
        self._passwordHash = None
        self.userID        = None
        self.stats         = None

    def _hashPassword(self, plainText):
        return bcrypt.hashpw(plainText.encode("utf-8"), bcrypt.gensalt())

    def _checkPassword(self, plainText, hashed):
        hashed = hashed.encode()
        return bcrypt.checkpw(plainText.encode("utf-8"), hashed)

    def login(self, username, plainPassword):
        storedHash = self._db.getPasswordHash(username)
        if storedHash is not None and self._checkPassword(plainPassword, storedHash):
            self.username      = username
            self._passwordHash = storedHash
            self.userID        = self._db.getUserID(username)
            self.stats         = self._db.loadStats(self.userID)
            return True
        return False

    def register(self, username, plainPassword):
        hashed = self._hashPassword(plainPassword)
        try:
            self.userID        = self._db.createUser(username, hashed)
            self.username      = username
            self._passwordHash = hashed
            self.stats         = self._db.loadStats(self.userID)
            # Every new player starts with one Stone Sword
            self._db.giveItem(self.userID, "Stone Sword", 1)
            return True
        except mysql.connector.IntegrityError:
            raise ValueError(f"Username '{username}' is already taken.")

    def logout(self):
        self.username      = None
        self._passwordHash = None
        self.userID        = None
        self.stats         = None

    def getIsLoggedIn(self):
        return self.username is not None

    def saveStats(self):
        if self.getIsLoggedIn() and self.userID is not None:
            self._db.saveStats(self.userID, self.stats)

    def returnPassword(self):
        return self._passwordHash