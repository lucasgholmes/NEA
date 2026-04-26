class Item:

    def __init__(self, itemName, itemType, itemDamage):
        self.itemName   = itemName
        self.itemType   = itemType
        self.itemDamage = itemDamage

    def use(self, target=None):
        print(f"Using {self.itemName} (type={self.itemType})")
        if target is not None:
            target.takeDamage(self.itemDamage)
        return self.itemDamage

    def equip(self, player):
        print(f"{self.itemName} equipped by {player}")

