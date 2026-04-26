import mysql.connector
from player_stats import PlayerStats

DB_CONFIG = {
    "host":           "database-1.cjo00eeyu8az.eu-north-1.rds.amazonaws.com",
    "port":           3306,
    "user":           "NEA",
    "password":       "NEANEANEA",
    "database":       "neadb",
    "ssl_disabled":   False,
    "ssl_ca":         "./global-bundle.pem",
    "autocommit":     True,
    "connect_timeout": 5
}


class DatabaseManager:

    def __init__(self):
        self.connection  = None
        self.tables      = ["Users", "PlayerStats"]
        self.dbAvailable = True
        self._initDB()

    def _connect(self):
        try:
            return mysql.connector.connect(**DB_CONFIG)
        except mysql.connector.errors.DatabaseError as e:
            raise ConnectionError("No internet connection. Please check your network and try again.") from e

    def _initDB(self):
        try:
            conn = self._connect()
            cur  = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS Users (
                    userID       INT         PRIMARY KEY AUTO_INCREMENT,
                    username     VARCHAR(50) UNIQUE NOT NULL,
                    passwordHash TEXT        NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS PlayerStats (
                    userID         INT   PRIMARY KEY,
                    level          INT   NOT NULL,
                    coins          INT   NOT NULL,
                    mazesCompleted INT   NOT NULL,
                    fastestTime    FLOAT
                );
            """)

            conn.commit()
            conn.close()

        except:
            print("Could not connect to databas")

    def createUser(self, username, passwordHash):
        if not self.dbAvailable:
            return None
        conn = self._connect()
        cur  = conn.cursor()

        cur.execute(
            "INSERT INTO Users (username, passwordHash) VALUES (%s, %s)",
            (username, passwordHash)
        )
        cur.fetchall()
        userID = cur.lastrowid

        cur.execute(
            "INSERT INTO PlayerStats (userID, level, coins, mazesCompleted, fastestTime) "
            "VALUES (%s, 1, 0, 0, NULL)",
            (userID,)
        )
        cur.fetchall()

        conn.commit()
        conn.close()
        return userID

    def checkLogin(self, username, passwordHash):
        if not self.dbAvailable:
            return False
        conn = self._connect()
        cur  = conn.cursor()
        cur.execute(
            "SELECT userID FROM Users WHERE username=%s AND passwordHash=%s",
            (username, passwordHash)
        )
        row = cur.fetchone()
        conn.close()
        return row is not None

    def getUserID(self, username):
        if not self.dbAvailable:
            return None
        conn = self._connect()
        cur  = conn.cursor()
        cur.execute("SELECT userID FROM Users WHERE username=%s", (username,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    def saveStats(self, userID, stats):
        if not self.dbAvailable:
            return
        level, coins, mazesCompleted, fastestTime = stats.toTuple()
        conn = self._connect()
        cur  = conn.cursor()
        cur.execute("""
            UPDATE PlayerStats
            SET level=%s, coins=%s, mazesCompleted=%s, fastestTime=%s
            WHERE userID=%s
        """, (level, coins, mazesCompleted, fastestTime, userID))
        conn.commit()
        conn.close()

    def loadStats(self, userID):
        if not self.dbAvailable:
            return PlayerStats()
        conn = self._connect()
        cur  = conn.cursor()
        cur.execute(
            "SELECT level, coins, mazesCompleted, fastestTime FROM PlayerStats WHERE userID=%s",
            (userID,)
        )
        row = cur.fetchone()
        conn.close()

        if row:
            stats = PlayerStats()
            stats.loadFromTuple(row)
            return stats
        return PlayerStats()

    def getShopItems(self):
        # Returns all items excluding Stone Sword, ordered by itemID ascending
        if not self.dbAvailable:
            return []
        conn = self._connect()
        cur  = conn.cursor()
        cur.execute("""
            SELECT itemID, itemName, itemType, damage, price
            FROM Items
            WHERE itemName != 'Stone Sword'
            ORDER BY itemID ASC
            LIMIT 6
        """)
        rows = cur.fetchall()
        conn.close()
        return rows

    def getUserItems(self, userID):
        # Returns (itemID, itemName, quantity) for all items the user owns
        if not self.dbAvailable:
            return []
        conn = self._connect()
        cur  = conn.cursor()
        cur.execute("""
            SELECT i.itemID, i.itemName, ui.quantity
            FROM UserItems ui
            JOIN Items i ON ui.itemID = i.itemID
            WHERE ui.userID = %s AND ui.quantity > 0
        """, (userID,))
        rows = cur.fetchall()
        conn.close()
        return rows

    def purchaseItem(self, userID, itemName, price):
        if not self.dbAvailable:
            return False
        conn = self._connect()
        cur  = conn.cursor()


        cur.execute("SELECT coins FROM PlayerStats WHERE userID = %s", (userID,))
        row = cur.fetchone()
        cur.fetchall()
        if row is None:
            conn.close()
            return False
        currentCoins = row[0]
        if currentCoins < price:
            conn.close()
            return False

        # Look up the item
        cur.execute("SELECT itemID FROM Items WHERE itemName = %s", (itemName,))
        row = cur.fetchone()
        cur.fetchall()
        if row is None:
            conn.close()
            return False
        itemID = row[0]

        # Deduct coins
        cur.execute(
            "UPDATE PlayerStats SET coins = coins - %s WHERE userID = %s",
            (price, userID)
        )

        # Add item to user's inventory
        cur.execute("""
            INSERT INTO UserItems (userID, itemID, quantity)
            VALUES (%s, %s, 1)
            ON DUPLICATE KEY UPDATE quantity = quantity + 1
        """, (userID, itemID))

        conn.commit()
        conn.close()
        return True

    def giveItem(self, userID, itemName, quantity=1):
        if not self.dbAvailable:
            return
        conn = self._connect()
        cur  = conn.cursor()
        cur.execute("SELECT itemID FROM Items WHERE itemName = %s", (itemName,))
        row = cur.fetchone()
        cur.fetchall()
        if row is None:
            conn.close()
            return
        itemID = row[0]
        cur.execute("""
            INSERT INTO UserItems (userID, itemID, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + %s
        """, (userID, itemID, quantity, quantity))
        cur.fetchall()
        conn.commit()
        conn.close()

    def getPasswordHash(self, username):
        if not self.dbAvailable:
            return None
        conn = self._connect()
        cur  = conn.cursor()
        cur.execute(
            "SELECT passwordHash FROM Users WHERE username=%s",
            (username,)
        )
        row = cur.fetchone()
        conn.close()
        if row is not None:
            return row[0]
        else:
            return None