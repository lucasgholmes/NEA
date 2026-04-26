import math
import pygame
from constants import TILEWALL, TILEFINISH, baseSpeed, accel, drag, player as PLAYER_KEY


class Player:

    def __init__(self, startTileX, startTileY, tileSize):
        # Pixel position - centred inside the starting tile
        self.posX  = startTileX * tileSize + tileSize // 2
        self.posY  = startTileY * tileSize + tileSize // 2

        # Current tile (computed each frame from pixel position)
        self.tileX = startTileX
        self.tileY = startTileY

        self._tileSize = tileSize

        # Velocity in pixels per second
        self._velX = 0.0
        self._velY = 0.0

        # Health
        self.maxHp = 100
        self.hp    = 100

        # Immunity frames after being hit (seconds remaining)
        self.immunityTimer = 0.0
        self.IMMUNITY_DURATION = 1.0   # seconds of invincibility after a hit


        self.hitImmunityTimer    = 0.0
        self.HIT_IMMUNITY_DURATION = 0.5   # seconds

        self._swingDir   = None
        self._swingTimer = 0.0
        self._SWING_DUR  = 0.25


        self._prevMoveKeys = {
            pygame.K_w: False,
            pygame.K_a: False,
            pygame.K_s: False,
            pygame.K_d: False,
        }


    def move(self, mazeGetTileType, dt):
        keys   = pygame.key.get_pressed()
        ts     = self._tileSize
        maxSpd = ts * baseSpeed   # max speed in pixels/s
        acc    = ts * accel       # acceleration in pixels/s^2
        drg    = ts * drag        # drag in pixels/s^2

        swingMap = [
            (pygame.K_w, "up"),
            (pygame.K_s, "down"),
            (pygame.K_a, "left"),
            (pygame.K_d, "right"),
        ]
        for key, direction in swingMap:
            nowPressed  = bool(keys[key])
            wasPressed  = self._prevMoveKeys[key]
            justPressed = nowPressed and not wasPressed
            if justPressed and self._swingDir is None:
                self._swingDir   = direction
                self._swingTimer = 0.0
                break

        if self._swingDir is not None:
            self._swingTimer += dt
            if self._swingTimer >= self._SWING_DUR:
                self._swingDir   = None
                self._swingTimer = 0.0

        # Store key states for next frame's edge-detection
        for key in self._prevMoveKeys:
            self._prevMoveKeys[key] = bool(keys[key])

        inputX = 0
        inputY = 0
        if keys[pygame.K_LEFT]:
            inputX = -1
        if keys[pygame.K_RIGHT]:
            inputX =  1
        if keys[pygame.K_UP]:
            inputY = -1
        if keys[pygame.K_DOWN]:
            inputY =  1

        if inputX != 0:
            self._velX += inputX * acc * dt
        else:
            if self._velX > 0:
                self._velX = max(0.0, self._velX - drg * dt)
            elif self._velX < 0:
                self._velX = min(0.0, self._velX + drg * dt)

        if inputY != 0:
            self._velY += inputY * acc * dt
        else:
            # No vertical input: apply drag toward zero
            if self._velY > 0:
                self._velY = max(0.0, self._velY - drg * dt)
            elif self._velY < 0:
                self._velY = min(0.0, self._velY + drg * dt)


        if self._velX >  maxSpd:
            self._velX =  maxSpd
        if self._velX < -maxSpd:
            self._velX = -maxSpd
        if self._velY >  maxSpd:
            self._velY =  maxSpd
        if self._velY < -maxSpd:
            self._velY = -maxSpd


        spriteSize = ts // 4
        padX = spriteSize * (6 / 16)
        padY = spriteSize * (8 / 16)

        px = self.posX
        py = self.posY


        newPx = px + self._velX * dt
        if self._velX > 0:
            checkTx = int((newPx + padX) // ts)
        else:
            checkTx = int((newPx - padX) // ts)
        checkTy = int(py // ts)
        if mazeGetTileType(checkTx, checkTy) == TILEWALL:
            # Hit a wall - kill horizontal velocity
            self._velX = 0.0
        else:
            px = newPx

        # Vertical movement - probe the leading vertical edge
        newPy = py + self._velY * dt
        checkTx = int(px // ts)
        if self._velY > 0:
            checkTy = int((newPy + padY) // ts)
        else:
            checkTy = int((newPy - padY) // ts)
        if mazeGetTileType(checkTx, checkTy) == TILEWALL:
            # Hit a wall - kill vertical velocity
            self._velY = 0.0
        else:
            py = newPy

        self.posX  = px
        self.posY  = py
        self.tileX = int(px // ts)
        self.tileY = int(py // ts)



    def collide(self, mazeGetTileType):
        return mazeGetTileType(self.tileX, self.tileY)


    def collectItem(self, item):
        print(f"[Player] Collected item: {item}")



    def takeDamage(self, amount):

        if self.immunityTimer > 0.0:
            return 0
        if self.hitImmunityTimer > 0.0:
            return 0

        actual = min(amount, self.hp)
        self.hp -= actual
        self.immunityTimer = self.IMMUNITY_DURATION
        return actual

    def grantHitImmunity(self):

        self.hitImmunityTimer = self.HIT_IMMUNITY_DURATION


    def render(self, surface, images, viewWidth, viewHeight):

        img = images[PLAYER_KEY]
        w, h = img.get_width(), img.get_height()
        playerX = viewWidth  // 2 - w // 2
        playerY = viewHeight // 2 - h // 2

        if self.hitImmunityTimer > 0.0:
            tinted = img.copy()
            whiteOverlay = pygame.Surface((w, h), pygame.SRCALPHA)
            whiteOverlay.fill((180, 180, 180, 0))
            tinted.blit(whiteOverlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(tinted, (playerX, playerY))
        elif self.immunityTimer > 0.0:
            tinted = img.copy()
            redOverlay = pygame.Surface((w, h), pygame.SRCALPHA)
            redOverlay.fill((255, 80, 80, 200))
            tinted.blit(redOverlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(tinted, (playerX, playerY))
        else:
            surface.blit(img, (playerX, playerY))


        weaponImg = images.get("weapon")
        if weaponImg is not None:
            ww = weaponImg.get_width()
            wh = weaponImg.get_height()

            # Centre of the player sprite in view coordinates
            cx = playerX + w // 2
            cy = playerY + h // 2

            # Radius from player centre to weapon centre during a swing.
            # Uses the sprite size so it scales with tile size.
            swingRadius = w * 1.1

            if self._swingDir is not None:
                progress = self._swingTimer / self._SWING_DUR

                dirBaseAngle = {
                    "right":   0,
                    "up":     90,
                    "left":  180,
                    "down":  270,
                }
                baseAngle = dirBaseAngle[self._swingDir]


                sweepRange = 60
                currentAngle = baseAngle - sweepRange + progress * sweepRange * 2

                rad    = math.radians(currentAngle)
                offsetX = int( math.cos(rad) * swingRadius)
                offsetY = int(-math.sin(rad) * swingRadius)

                weaponX = cx + offsetX - ww // 2
                weaponY = cy + offsetY - wh // 2

                rotated    = pygame.transform.rotate(weaponImg, currentAngle - 45)
                rotatedW   = rotated.get_width()
                rotatedH   = rotated.get_height()
                surface.blit(rotated, (cx + offsetX - rotatedW // 2,
                                       cy + offsetY - rotatedH // 2))
            else:

                handX   = playerX + int(w * 16 / 16)
                handY   = playerY + int(h *  7 / 16)
                weaponX = handX - ww // 2
                weaponY = handY - wh // 2
                surface.blit(weaponImg, (weaponX, weaponY))



    def renderHealthBar(self, screen, x, y, barW, barH):

        fraction = max(0.0, self.hp / self.maxHp)
        fillW    = max(0, int(barW * fraction))


        outlineRect = pygame.Rect(x - 1, y - 1, barW + 2, barH + 2)
        pygame.draw.rect(screen, (0, 0, 0), outlineRect)

        # Background (empty bar)
        bgRect = pygame.Rect(x, y, barW, barH)
        pygame.draw.rect(screen, (80, 0, 0), bgRect)

        # Foreground (current health)
        if fillW > 0:
            fgRect = pygame.Rect(x, y, fillW, barH)
            pygame.draw.rect(screen, (210, 30, 30), fgRect)