import random
import math
import pygame
from constants import TILEWALL


class Monster:

    _idCounter = 0   #counter so every instance gets a unique ID

    def __init__(self, monsterType, startTileX, startTileY, tileSize,
                 hp=3, damage=1):
        Monster._idCounter += 1
        self.enemyID    = Monster._idCounter
        self.type       = monsterType   # e.g. "spider"
        self.tileSize   = tileSize

        # Pixel position - centred inside the starting tile
        self.posX  = startTileX * tileSize + tileSize // 2
        self.posY  = startTileY * tileSize + tileSize // 2

        self.hp     = hp
        self._maxHp = hp
        self.damage = damage
        self.alive  = True



    def move(self, mazeGetTileType, dt):
        pass

    def attack(self, player):

        print(f"[Monster {self.enemyID}] Attacks for {self.damage} damage!")
        return self.damage

    def takeDamage(self, amount, immunityDuration=0.0):
        if hasattr(self, "immunityTimer") and self.immunityTimer > 0.0:
            return 0

        actual = min(amount, self.hp)
        self.hp -= actual
        if self.hp <= 0:
            self.alive = False
            print(f"[Monster {self.enemyID}] Defeated.")

        if hasattr(self, "immunityTimer"):
            self._immunityDuration = immunityDuration
            self.immunityTimer     = immunityDuration

        return actual

    def renderHealthBar(self, surface, drawX, drawY, spriteW, spriteH):

        barW = max(4, spriteW - 4)
        barH = max(3, spriteH // 8)

        barX = drawX + (spriteW - barW) // 2
        barY = drawY + spriteH + 2

        fraction = max(0.0, self.hp / max(1, self._maxHp))
        fillW    = max(0, int(barW * fraction))

        # Black outline drawn 1px outside the bar so it does not overlap the fill
        outlineRect = pygame.Rect(barX - 1, barY - 1, barW + 2, barH + 2)
        pygame.draw.rect(surface, (0, 0, 0), outlineRect)

        bgRect = pygame.Rect(barX, barY, barW, barH)
        pygame.draw.rect(surface, (80, 0, 0), bgRect)

        if fillW > 0:
            fgRect = pygame.Rect(barX, barY, fillW, barH)
            pygame.draw.rect(surface, (210, 30, 30), fgRect)



_START_ANGLES_DEG = [45, 135, 225, 315]


class Spider(Monster):

    SPEED_TILES_PER_SEC = 2.0

    def __init__(self, startTileX, startTileY, tileSize):
        super().__init__("spider", startTileX, startTileY, tileSize,
                         hp=50, damage=25)

        spriteSize     = tileSize // 4
        self._halfSize = spriteSize // 2

        speed = tileSize * self.SPEED_TILES_PER_SEC

        # Pick one of the four diagonal starting angles at random
        angleDeg = random.choice(_START_ANGLES_DEG)
        angleRad = math.radians(angleDeg)

        # vx positive = right, vy positive = down (pygame screen coords)
        self._vx = speed * math.cos(angleRad)
        self._vy = -speed * math.sin(angleRad)   # negate: screen y is inverted

        # Render angle derived from velocity; updated every frame in move()
        self._renderAngle = 0.0

        self._rotatedCache = {}

        # Immunity after being hit: set to the weapon swing duration so the
        # same swing cannot deal damage multiple times per arc.
        self.immunityTimer    = 0.0
        self._immunityDuration = 0.0   # set from outside when a hit lands


    def move(self, mazeGetTileType, dt):
        if not self.alive:
            return

        # Tick immunity timer down each frame
        if self.immunityTimer > 0.0:
            self.immunityTimer = max(0.0, self.immunityTimer - dt)

        ts   = self.tileSize
        half = self._halfSize

        newX = self.posX + self._vx * dt

        # Leading edge depends on direction
        if self._vx > 0:
            edgeX = newX + half
        else:
            edgeX = newX - half

        edgeTileX = int(edgeX // ts)
        edgeTileY = int(self.posY // ts)

        if mazeGetTileType(edgeTileX, edgeTileY) == TILEWALL:
            # Reflect horizontal component
            self._vx = -self._vx
            if self._vx < 0:
                # was moving right, wall is on the right
                newX = edgeTileX * ts - half
            else:
                # was moving left, wall is on the left
                newX = (edgeTileX + 1) * ts + half
            self._mutateVelocity()

        self.posX = newX



        newY = self.posY + self._vy * dt

        if self._vy > 0:
            edgeY = newY + half
        else:
            edgeY = newY - half

        edgeTileX2 = int(self.posX // ts)
        edgeTileY2 = int(edgeY // ts)

        if mazeGetTileType(edgeTileX2, edgeTileY2) == TILEWALL:
            # Reflect vertical component
            self._vy = -self._vy
            # Same logic as horizontal: test the NEW vy sign after the flip.
            if self._vy < 0:
                # was moving down, wall is below
                newY = edgeTileY2 * ts - half
            else:
                # was moving up, wall is above
                newY = (edgeTileY2 + 1) * ts + half
            self._mutateVelocity()

        self.posY = newY


        self._renderAngle = math.degrees(math.atan2(-self._vy, self._vx)) - 90



    def _mutateVelocity(self):
        mutateDeg = random.uniform(-20, 20)
        mutateRad = math.radians(mutateDeg)

        cosA = math.cos(mutateRad)
        sinA = math.sin(mutateRad)

        newVx = self._vx * cosA - self._vy * sinA
        newVy = self._vx * sinA + self._vy * cosA

        self._vx = newVx
        self._vy = newVy

    def render(self, surface, baseImage, offsetX, offsetY):

        if not self.alive:
            return

        cacheKey = round(self._renderAngle) % 360

        if cacheKey not in self._rotatedCache:
            self._rotatedCache[cacheKey] = pygame.transform.rotate(
                baseImage, self._renderAngle
            )

        img = self._rotatedCache[cacheKey]
        w   = img.get_width()
        h   = img.get_height()

        drawX = int(self.posX - offsetX) - w // 2
        drawY = int(self.posY - offsetY) - h // 2
        surface.blit(img, (drawX, drawY))

        # Draw health bar beneath the sprite
        self.renderHealthBar(surface, drawX, drawY, w, h)




class Zombie(Monster):

    SPEED_TILES_PER_SEC  = 0.8
    WANDER_SPEED_FACTOR  = 0.5   # wander speed as a fraction
    AGGRO_SPEED_FACTOR   = 0.7   # aggro-radius chase speed as a fraction
    AGGRO_TILES          = 5     # tile-distance at which the zombie notices the player

    def __init__(self, startTileX, startTileY, tileSize):
        super().__init__("zombie", startTileX, startTileY, tileSize,
                         hp=100, damage=40)

        self.tileSize  = tileSize
        self._speed    = tileSize * self.SPEED_TILES_PER_SEC


        spriteSize          = tileSize // 4
        self._padX          = spriteSize * (4   / 16)
        self._padY          = spriteSize * (7.5 / 16)
        self._vertOffset    = spriteSize * (0.5 / 16)


        self._facingRight = True


        wanderSpeed     = self._speed * self.WANDER_SPEED_FACTOR
        startDir        = random.choice([(1, 1), (1, -1), (-1, 1), (-1, -1)])
        self._wanderVx  = wanderSpeed * startDir[0]
        self._wanderVy  = wanderSpeed * startDir[1]
        self.immunityTimer     = 0.0
        self._immunityDuration = 0.0
        self._stuckTimer = 0.0


    def _tileOf(self, pixelPos):

        return int(round(pixelPos / self.tileSize - 0.5))

    def _hasLineSight(self, mazeGetTileType, myTileX, myTileY,
                      playerTileX, playerTileY):

        if myTileY == playerTileY:
            lo = min(myTileX, playerTileX) + 1
            hi = max(myTileX, playerTileX)
            for tx in range(lo, hi):
                if mazeGetTileType(tx, myTileY) == TILEWALL:
                    return False
            return True

        if myTileX == playerTileX:
            lo = min(myTileY, playerTileY) + 1
            hi = max(myTileY, playerTileY)
            for ty in range(lo, hi):
                if mazeGetTileType(myTileX, ty) == TILEWALL:
                    return False
            return True

        return False

    def _applyMove(self, mazeGetTileType, cx, cy, vx, vy, dt):
        ts   = self.tileSize
        padX = self._padX
        padY = self._padY

        newCx    = cx + vx * dt
        blockedH = False
        if vx != 0.0:
            if vx > 0:
                probeX = newCx + padX
            else:
                probeX = newCx - padX
            pTileX = int(probeX // ts)
            hitTop = mazeGetTileType(pTileX, int((cy - padY) // ts)) == TILEWALL
            hitBot = mazeGetTileType(pTileX, int((cy + padY) // ts)) == TILEWALL
            if hitTop or hitBot:
                blockedH = True
                if vx > 0:
                    newCx = pTileX * ts - padX
                else:
                    newCx = (pTileX + 1) * ts + padX


        newCy    = cy + vy * dt
        blockedV = False
        if vy != 0.0:
            if vy > 0:
                probeY = newCy + padY
            else:
                probeY = newCy - padY
            pTileY = int(probeY // ts)
            hitL = mazeGetTileType(int((newCx - padX) // ts), pTileY) == TILEWALL
            hitR = mazeGetTileType(int((newCx + padX) // ts), pTileY) == TILEWALL
            if hitL or hitR:
                blockedV = True
                if vy > 0:
                    newCy = pTileY * ts - padY
                else:
                    newCy = (pTileY + 1) * ts + padY

        return newCx, newCy, blockedH, blockedV



    def move(self, mazeGetTileType, dt, playerTileX=None, playerTileY=None):

        if not self.alive:
            return

        if self.immunityTimer > 0.0:
            self.immunityTimer = max(0.0, self.immunityTimer - dt)

        vOff = self._vertOffset
        ts   = self.tileSize

        # Hitbox centre this frame
        cx = self.posX
        cy = self.posY + vOff

        myTileX = self._tileOf(cx)
        myTileY = self._tileOf(cy)

        vx      = 0.0
        vy      = 0.0
        chasing = False

        if playerTileX is not None and playerTileY is not None:
            # Pixel-space direction toward the player tile centre
            targetX = playerTileX * ts + ts // 2
            targetY = playerTileY * ts + ts // 2
            dx      = targetX - cx
            dy      = targetY - cy
            pixDist = (dx * dx + dy * dy) ** 0.5

            tileDist = (abs(playerTileX - myTileX) + abs(playerTileY - myTileY))

            if self._hasLineSight(mazeGetTileType, myTileX, myTileY,
                                  playerTileX, playerTileY):
                # Full-speed direct chase along the clear corridor
                chasing = True
                spd = self._speed
                if pixDist > 0:
                    vx = (dx / pixDist) * spd
                    vy = (dy / pixDist) * spd

            elif tileDist <= self.AGGRO_TILES:
                chasing = True
                spd = self._speed * self.AGGRO_SPEED_FACTOR
                if pixDist > 0:
                    vx = (dx / pixDist) * spd
                    vy = (dy / pixDist) * spd

        if not chasing:
            vx = self._wanderVx
            vy = self._wanderVy


        newCx, newCy, blockedH, blockedV = self._applyMove(mazeGetTileType, cx, cy, vx, vy, dt)

        if blockedH:
            self._wanderVx = -self._wanderVx
        if blockedV:
            self._wanderVy = -self._wanderVy

        self.posX = newCx
        self.posY = newCy - vOff


        if vx > 0:
            self._facingRight = True
        elif vx < 0:
            self._facingRight = False


        if not chasing:
            moved = abs(newCx - cx) + abs(newCy - cy)
            if moved < 0.5:
                self._stuckTimer += dt
            else:
                self._stuckTimer = 0.0

            if self._stuckTimer > 0.4:
                wanderSpeed      = self._speed * self.WANDER_SPEED_FACTOR

                tileCx = myTileX * ts + ts // 2
                tileCy = myTileY * ts + ts // 2
                if cx < tileCx:
                    bx = 1
                else:
                    bx = -1

                if cy < tileCy:
                    by = 1
                else:
                    by = -1
                self._wanderVx   = wanderSpeed * bx
                self._wanderVy   = wanderSpeed * by
                self._stuckTimer = 0.0


    def render(self, surface, imgLeft, imgRight, offsetX, offsetY):

        if not self.alive:
            return

        if self._facingRight:
            img = imgRight
        else:
            img = imgLeft
        w   = img.get_width()
        h   = img.get_height()

        drawX = int(self.posX - offsetX) - w // 2
        drawY = int(self.posY - offsetY) - h // 2
        surface.blit(img, (drawX, drawY))

        # Draw health bar beneath the sprite
        self.renderHealthBar(surface, drawX, drawY, w, h)