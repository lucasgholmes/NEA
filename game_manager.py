import time
import random
import pygame
from constants import (TILEFINISH, TILEWALL, TILESTART,
                       tileCount, fps,
                       PATH_IMG, WALL_IMG, START_IMG, FINISH_IMG, PLAYER_IMG,
                       COIN_IMG, HEART_IMG, SPIDER_IMG,
                       ZOMBIE_LEFT_IMG, ZOMBIE_RIGHT_IMG,
                       zombieLeft as ZOMBIE_LEFT_KEY, zombieRight as ZOMBIE_RIGHT_KEY,
                       FONT_TTF,
                       player as PLAYER_KEY)
from maze   import Maze
from player import Player
from enemy  import Spider, Zombie
import math

class GameManager:
    def __init__(self, currentUser, difficulty = 1):
        self.currentUser      = currentUser
        self.difficulty       = difficulty

        # Set during startGame / loadMaze
        self._maze    = None
        self._player  = None
        self._images  = {}
        self._hudFont      = None   # loaded in startGame for the timer HUD
        self._coinHudImg   = None   # scaled coin image for the in-game HUD
        self._heartHudImg  = None   # scaled heart image for the health bar HUD
        self._roundCoinCount = 0    # coins collected this round
        self._running = False
        self._spiders      = []     # list of Spider instances for this maze run
        self._zombies      = []     # list of Zombie instances for this maze run
        self._damageNumbers = []    # list of active floating damage number dicts
        self._equippedWeaponPath = None
        self._drops = []
        self._dropCoinSurface  = None
        self._dropHeartSurface = None


    def loadMaze(self, tileSize, spiderCount = 5):
        """Instantiate a fresh Maze and position the player at the start."""
        self._maze   = Maze(spiderCount=spiderCount)
        self._player = Player(1, self._maze.startY // tileSize if tileSize else 1,
                              tileSize)
        # Place player at the correct start tile (column 1, startY row)
        startTileX = 1
        startTileY = self._maze.startY // tileSize if tileSize else self._maze.startY
        # startY is already an odd tile-row index from Maze, not pixels
        startTileY = self._maze.startY
        self._player = Player(startTileX, startTileY, tileSize)


    def _loadImages(self, tileSize):
        def safLoad(path, size, smooth=True):
            try:
                img = pygame.image.load(path).convert_alpha()
                if smooth:
                    return pygame.transform.smoothscale(img, size)
                return pygame.transform.scale(img, size)
            except Exception:
                s = pygame.Surface(size, pygame.SRCALPHA)
                s.fill((255, 0, 255, 255))
                return s

        ts = tileSize
        self._images = {
            0:           safLoad(PATH_IMG,   (ts, ts)),
            1:           safLoad(WALL_IMG,   (ts, ts)),
            2:           safLoad(START_IMG,  (ts, ts)),
            3:           safLoad(FINISH_IMG, (ts, ts)),
            PLAYER_KEY:       safLoad(PLAYER_IMG,       (ts // 4, ts // 4), smooth=False),
            "spider":         safLoad(SPIDER_IMG,        (ts // 4, ts // 4), smooth=False),
            ZOMBIE_LEFT_KEY:  safLoad(ZOMBIE_LEFT_IMG,   (ts // 4, ts // 4), smooth=False),
            ZOMBIE_RIGHT_KEY: safLoad(ZOMBIE_RIGHT_IMG,  (ts // 4, ts // 4), smooth=False),
        }

    
        weaponSize = (ts // 6, ts // 6)
        if self._equippedWeaponPath is not None:
            self._images["weapon"] = safLoad(self._equippedWeaponPath, weaponSize, smooth=False)
        else:
            self._images["weapon"] = None

        coinIconSize = max(16, ts // 8)
        self._coinHudImg  = safLoad(COIN_IMG,  (coinIconSize, coinIconSize))

        self._heartHudImg = safLoad(HEART_IMG, (coinIconSize, coinIconSize), smooth=False)

        dropCoinW  = ts // 6
        dropCoinH  = dropCoinW * 360 // 315
        dropHeartW = ts // 6
        dropHeartH = dropHeartW   # heart PNG is square
        self._dropCoinSurface  = safLoad(COIN_IMG,  (dropCoinW,  dropCoinH))
        self._dropHeartSurface = safLoad(HEART_IMG, (dropHeartW, dropHeartH), smooth=False)

    def startGame(self, tkApp, sessionTimeLimit = None, equippedWeaponPath = None,
                  difficultyMultiplier = 1, equippedWeaponDamage = 0):

        self._equippedWeaponPath   = equippedWeaponPath
        self._equippedWeaponDamage = equippedWeaponDamage
        tkApp.withdraw()
        result     = None
        playerDied = False
        timeLeft   = sessionTimeLimit   #
        try:
            pygame.init()

            displayInfo       = pygame.display.Info()
            screenW           = displayInfo.current_w
            screenH           = displayInfo.current_h
            margin            = 96
            fitTileSize       = min((screenW - margin) // tileCount,
                                    (screenH - margin) // tileCount)

            viewW  = fitTileSize * tileCount
            viewH  = fitTileSize * tileCount
            screen = pygame.display.set_mode((viewW, viewH), pygame.DOUBLEBUF)
            pygame.display.set_caption("Warped Ways")
            view   = pygame.Surface((viewW, viewH)).convert()
            clock  = pygame.time.Clock()

            # Spider count scales with difficulty: Easy = 5, Medium = 10, Hard = 15.
            # Each spider gets its own unique tile so none start on top of each other.
            baseSpiderCount = 5
            spiderCount = baseSpiderCount * difficultyMultiplier

            self.loadMaze(fitTileSize, spiderCount)
            self._loadImages(fitTileSize)

            # One spider per spawn tile — all start on separate tiles
            self._spiders = []
            for (tx, ty) in self._maze.spiderTiles:
                self._spiders.append(Spider(tx, ty, fitTileSize))

            # Zombies spawn at half the spider count — each on its own tile
            self._zombies = []
            for (tx, ty) in self._maze.zombieTiles:
                self._zombies.append(Zombie(tx, ty, fitTileSize))

            # Reset round coin counter for this maze run
            self._roundCoinCount = 0

            # Load HUD font for the timer display
            def loadFont(size):
                try:
                    return pygame.font.Font(FONT_TTF, size)
                except Exception:
                    return pygame.font.SysFont("Arial", size, bold=True)

            self._hudFont = loadFont(viewH // 18)

            startTime    = time.time()
            self._running = True

            while self._running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._running = False
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self._running = False
                        if event.key == pygame.K_p:
                            # open pause overlay; block until player chooses
                            pauseResult = self.pauseGame(screen, view)
                            if pauseResult == "menu":
                                self._running = False   # drop back to tkinter menu
                            elif pauseResult == "quit":
                                self._running = False
                                result = None           # discard any partial score

                dt = clock.tick(fps) / 1000

                if timeLeft is not None:
                    timeLeft -= dt
                    if timeLeft < 0:
                        timeLeft = 0


                self._player.move(self._maze.getTileType, dt)

                # Update all spiders
                for spider in self._spiders:
                    spider.move(self._maze.getTileType, dt)

                # Update all zombies — pass player tile coords so they can
                # check line-of-sight along shared rows/columns
                for zombie in self._zombies:
                    zombie.move(self._maze.getTileType, dt,
                                playerTileX=self._player.tileX,
                                playerTileY=self._player.tileY)

                # Compute the same hitbox half-extents used in Player.move so
                # the coin pickup boundary matches the wall collision boundary.
                spriteSize   = fitTileSize // 4
                playerPadX   = spriteSize * (6 / 16)
                playerPadY   = spriteSize * (8 / 16)
                if self._maze.checkCoinPickup(self._player.posX, self._player.posY,
                                              fitTileSize, playerPadX, playerPadY):
                    self._roundCoinCount += 1

                if self._player.immunityTimer > 0.0:
                    self._player.immunityTimer = max(
                        0.0, self._player.immunityTimer - dt
                    )
                if self._player.hitImmunityTimer > 0.0:
                    self._player.hitImmunityTimer = max(
                        0.0, self._player.hitImmunityTimer - dt
                    )


                # Both sprites are rendered at tileSize // 4 pixels.
                # A circular distance check between the two centres is used:
                # if the distance is less than the sum of their radii (each
                # being half the sprite size) they are considered to be touching.
                spritePx = fitTileSize // 4
                hitRadius = spritePx   # sum of both half-sizes (0.5 + 0.5 = 1 sprite)
                for spider in self._spiders:
                    if not spider.alive:
                        continue
                    dx = self._player.posX - spider.posX
                    dy = self._player.posY - spider.posY
                    dist = (dx * dx + dy * dy) ** 0.5
                    if dist < hitRadius:
                        # Randomise damage: base ± 30%
                        rawDmg   = spider.damage * random.uniform(0.7, 1.3)
                        dmgDealt = self._player.takeDamage(round(rawDmg))
                        if dmgDealt > 0:
                            # Spawn a floating damage number at the player's
                            # screen-centre position.  It drifts upward and fades.
                            self._damageNumbers.append({
                                "text":    str(dmgDealt),
                                "x":       float(viewW // 2),
                                "y":       float(viewH // 2 - spritePx),
                                "velY":    -60.0,   # pixels per second upward
                                "life":    0.7,     # seconds until fully gone
                                "maxLife": 0.7,
                            })

                for zombie in self._zombies:
                    if not zombie.alive:
                        continue
                    dx = self._player.posX - zombie.posX
                    dy = self._player.posY - zombie.posY
                    dist = (dx * dx + dy * dy) ** 0.5
                    if dist < hitRadius:
                        rawDmg   = zombie.damage * random.uniform(0.7, 1.3)
                        dmgDealt = self._player.takeDamage(round(rawDmg))
                        if dmgDealt > 0:
                            self._damageNumbers.append({
                                "text":    str(dmgDealt),
                                "x":       float(viewW // 2),
                                "y":       float(viewH // 2 - spritePx),
                                "velY":    -60.0,
                                "life":    0.7,
                                "maxLife": 0.7,
                            })

            
                if (self._equippedWeaponDamage > 0
                        and self._player._swingDir is not None):
                    import math as math
                    swingRadius = (fitTileSize // 4) * 1.1
                    dirBaseAngle = {
                        "right":   0,
                        "up":     90,
                        "left":  180,
                        "down":  270,
                    }
                    baseAngle    = dirBaseAngle[self._player._swingDir]
                    progress     = self._player._swingTimer / self._player._SWING_DUR
                    sweepRange   = 60
                    currentAngle = baseAngle - sweepRange + progress * sweepRange * 2
                    rad          = math.radians(currentAngle)

                    # Weapon centre in world-space coordinates
                    weaponWorldX = self._player.posX + math.cos(rad) * swingRadius
                    weaponWorldY = self._player.posY - math.sin(rad) * swingRadius

                    # Hit zone: half a sprite width radius around the weapon centre
                    hitZone = fitTileSize // 8

                    for spider in self._spiders:
                        if not spider.alive:
                            continue
                        dx   = weaponWorldX - spider.posX
                        dy   = weaponWorldY - spider.posY
                        dist = (dx * dx + dy * dy) ** 0.5
                        if dist < hitZone:
                            # Damage: base randomised in [-10%, +30%] range
                            rawDmg   = self._equippedWeaponDamage * random.uniform(0.9, 1.3)
                            dmgDealt = spider.takeDamage(
                                round(rawDmg),
                                immunityDuration=self._player._SWING_DUR
                            )
                            if dmgDealt > 0:
                                self._player.grantHitImmunity()
                                screenX = spider.posX - (self._player.posX - viewW // 2)
                                screenY = spider.posY - (self._player.posY - viewH // 2)
                                self._damageNumbers.append({
                                    "text":    str(dmgDealt),
                                    "x":       float(screenX),
                                    "y":       float(screenY - spritePx),
                                    "velY":    -60.0,
                                    "life":    0.7,
                                    "maxLife": 0.7,
                                    "colour":  (50, 220, 80),   # green
                                })

                        
                            if not spider.alive:
                                if self._player.hp < 50:
                                    dropKind = "heart"
                                else:
                                    dropKind = random.choice(("coin", "heart"))
                                self._drops.append({
                                    "kind":        dropKind,
                                    "x":           spider.posX,
                                    "y":           spider.posY,
                                    "shrinking":   False,
                                    "shrinkScale": 1.0,
                                })

                
                    for zombie in self._zombies:
                        if not zombie.alive:
                            continue
                        dx   = weaponWorldX - zombie.posX
                        dy   = weaponWorldY - zombie.posY
                        dist = (dx * dx + dy * dy) ** 0.5
                        if dist < hitZone:
                            rawDmg   = self._equippedWeaponDamage * random.uniform(0.9, 1.3)
                            dmgDealt = zombie.takeDamage(
                                round(rawDmg),
                                immunityDuration=self._player._SWING_DUR
                            )
                            if dmgDealt > 0:
                                self._player.grantHitImmunity()
                                screenX = zombie.posX - (self._player.posX - viewW // 2)
                                screenY = zombie.posY - (self._player.posY - viewH // 2)
                                self._damageNumbers.append({
                                    "text":    str(dmgDealt),
                                    "x":       float(screenX),
                                    "y":       float(screenY - spritePx),
                                    "velY":    -60.0,
                                    "life":    0.7,
                                    "maxLife": 0.7,
                                    "colour":  (50, 220, 80),
                                })

                           
                            if not zombie.alive:
                                if self._player.hp < 50:
                                    dropKind = "heart"
                                else:
                                    dropKind = random.choice(("coin", "heart"))
                                self._drops.append({
                                    "kind":        dropKind,
                                    "x":           zombie.posX,
                                    "y":           zombie.posY,
                                    "shrinking":   False,
                                    "shrinkScale": 1.0,
                                })

           
                tileUnder = self._player.collide(self._maze.getTileType)
                if tileUnder == TILEFINISH:
                    result = round(time.time() - startTime, 2)
                    self._running = False
                    break

                
                if self._player.hp <= 0:
                    result     = round(time.time() - startTime, 2)
                    playerDied = True
                    self._running = False
                    break

        
                p = self._player
                offsetX = p.posX - viewW // 2
                offsetY = p.posY - viewH // 2

                self._maze.render(view, self._images, fitTileSize,
                                  offsetX, offsetY, dt)
                self._player.render(view, self._images, viewW, viewH)

        
                spiderImg = self._images.get("spider")
                if spiderImg is not None:
                    for spider in self._spiders:
                        spider.render(view, spiderImg, offsetX, offsetY)

                zombieImgLeft  = self._images.get(ZOMBIE_LEFT_KEY)
                zombieImgRight = self._images.get(ZOMBIE_RIGHT_KEY)
                if zombieImgLeft is not None and zombieImgRight is not None:
                    for zombie in self._zombies:
                        zombie.render(view, zombieImgLeft, zombieImgRight,
                                      offsetX, offsetY)

         
                self._updateDrops(dt, fitTileSize)
                self._checkDropPickup(fitTileSize)

       
                self._drawDrops(view, offsetX, offsetY, dt)

                screen.blit(view, (0, 0))

                if timeLeft is not None:
                    self._drawTimerHud(screen, timeLeft)

       
                self._drawCoinHud(screen)

    
                self._drawPlayerHealthBar(screen)

  
                self._updateDamageNumbers(dt)
                self._drawDamageNumbers(screen)

                pygame.display.flip()


            if playerDied:
                self._deathMenu(screen, view)

        finally:
            pygame.quit()
            tkApp.deiconify()

        return result, timeLeft, self._roundCoinCount, playerDied



    def _drawTimerHud(self, screen, timeLeft):
     
        mins   = int(timeLeft) // 60
        secs   = int(timeLeft) % 60
        text   = f"{mins:02d}:{secs:02d}"
        colour = (255, 60, 60) if timeLeft < 60 else (255, 255, 255)

        surf = self._hudFont.render(text, True, colour)

        pad     = 8
        bgRect  = pygame.Rect(
            screen.get_width() - surf.get_width() - pad * 2 - 4,
            4,
            surf.get_width() + pad * 2,
            surf.get_height() + pad
        )
        backing = pygame.Surface((bgRect.width, bgRect.height), pygame.SRCALPHA)
        backing.fill((0, 0, 0, 140))
        screen.blit(backing, (bgRect.x, bgRect.y))

        # Text sits inside the backing rectangle with padding
        screen.blit(surf, (bgRect.x + pad, bgRect.y + pad // 2))


    def _drawCoinHud(self, screen):
        pad      = 8
        textSurf = self._hudFont.render(str(self._roundCoinCount), True, (255, 255, 255))

        # Total width: icon + small gap + text
        iconGap  = 6
        if self._coinHudImg is not None:
            iconW = self._coinHudImg.get_width()
            iconH = self._coinHudImg.get_height()
        else:
            iconW = 0
            iconH = 0

        totalW = iconW + iconGap + textSurf.get_width()
        totalH = max(iconH, textSurf.get_height())

        bgRect = pygame.Rect(
            4,
            4,
            totalW + pad * 2,
            totalH + pad
        )

        backing = pygame.Surface((bgRect.width, bgRect.height), pygame.SRCALPHA)
        backing.fill((0, 0, 0, 140))
        screen.blit(backing, (bgRect.x, bgRect.y))

        # Draw icon vertically centred inside the backing box
        drawY = bgRect.y + pad // 2
        if self._coinHudImg is not None:
            iconY = drawY + (totalH - iconH) // 2
            screen.blit(self._coinHudImg, (bgRect.x + pad, iconY))

        # Draw text vertically centred next to the icon
        textY = drawY + (totalH - textSurf.get_height()) // 2
        screen.blit(textSurf, (bgRect.x + pad + iconW + iconGap, textY))



    def _drawPlayerHealthBar(self, screen):
        
        pad     = 8
        iconGap = 6
        barH    = max(8, screen.get_height() // 50)
        barW    = screen.get_width() // 6

        if self._heartHudImg is not None:
            iconW = self._heartHudImg.get_width()
            iconH = self._heartHudImg.get_height()
        else:
            iconW = 0
            iconH = 0

        totalH = max(iconH, barH)
        totalW = iconW + iconGap + barW

        # Position directly below the coin HUD backing box
        coinHudH = self._coinHudImg.get_height() if self._coinHudImg else 16
        topY = 4 + coinHudH + pad + 6

        bgRect  = pygame.Rect(4, topY, totalW + pad * 2, totalH + pad)
        backing = pygame.Surface((bgRect.width, bgRect.height), pygame.SRCALPHA)
        backing.fill((0, 0, 0, 140))
        screen.blit(backing, (bgRect.x, bgRect.y))

        drawY = bgRect.y + pad // 2

        # Heart icon vertically centred inside the backing box
        if self._heartHudImg is not None:
            iconY = drawY + (totalH - iconH) // 2
            screen.blit(self._heartHudImg, (bgRect.x + pad, iconY))

        # Health bar vertically centred next to the icon
        barX = bgRect.x + pad + iconW + iconGap
        barY = drawY + (totalH - barH) // 2
        self._player.renderHealthBar(screen, barX, barY, barW, barH)



    def _updateDrops(self, dt, tileSize):
        SHRINK_SPEED = 3.0   # scale units per second (drop gone in ~0.33 s)

        alive = []
        for drop in self._drops:
            if drop["shrinking"]:
                drop["shrinkScale"] -= SHRINK_SPEED * dt
                if drop["shrinkScale"] > 0.0:
                    alive.append(drop)
                # drops at or below 0 are simply not re-appended (removed)
            else:
                alive.append(drop)
        self._drops = alive

    def _checkDropPickup(self, tileSize):
    
        if not self._drops:
            return

        spriteSize = tileSize // 4
        padX       = spriteSize * (6 / 16)
        padY       = spriteSize * (8 / 16)

        px = self._player.posX
        py = self._player.posY

        playerLeft   = px - padX
        playerRight  = px + padX
        playerTop    = py - padY
        playerBottom = py + padY

        for drop in self._drops:
            if drop["shrinking"]:
                continue

            if drop["kind"] == "coin":
                surf = self._dropCoinSurface
            else:
                surf = self._dropHeartSurface

            if surf is None:
                continue

            halfW = surf.get_width()  // 2
            halfH = surf.get_height() // 2

            dropLeft   = drop["x"] - halfW
            dropRight  = drop["x"] + halfW
            dropTop    = drop["y"] - halfH
            dropBottom = drop["y"] + halfH

            if (playerRight  >= dropLeft
                    and playerLeft   <= dropRight
                    and playerBottom >= dropTop
                    and playerTop    <= dropBottom):
                drop["shrinking"] = True

                if drop["kind"] == "coin":
                    self._roundCoinCount += 1
                else:
                    # Heal 50 hp, capped at the player's maximum
                    healed = min(50, self._player.maxHp - self._player.hp)
                    self._player.hp += healed

    def _drawDrops(self, surface, offsetX, offsetY, dt):
        PULSE_AMPLITUDE = 0.12
        PULSE_SPEED     = 1.5
        ticks           = pygame.time.get_ticks()
        pulseFactor     = 1.0 + PULSE_AMPLITUDE * math.sin(
            2 * math.pi * PULSE_SPEED * ticks / 1000.0
        )

        for drop in self._drops:
            if drop["kind"] == "coin":
                baseSurf = self._dropCoinSurface
            else:
                baseSurf = self._dropHeartSurface

            if baseSurf is None:
                continue

            if drop["shrinking"]:
                scaleFactor = drop["shrinkScale"]
            else:
                scaleFactor = pulseFactor

            baseW = baseSurf.get_width()
            baseH = baseSurf.get_height()
            drawW = max(1, int(baseW * scaleFactor))
            drawH = max(1, int(baseH * scaleFactor))
            scaled = pygame.transform.smoothscale(baseSurf, (drawW, drawH))

            # Centre on the drop's world position, offset by camera
            screenX = int(drop["x"] - offsetX) - drawW // 2
            screenY = int(drop["y"] - offsetY) - drawH // 2
            surface.blit(scaled, (screenX, screenY))


    def _updateDamageNumbers(self, dt):

        for num in self._damageNumbers:
            num["y"]    += num["velY"] * dt
            num["life"] -= dt

        newDamageNumbers = []

        for n in self._damageNumbers:
            if n["life"] > 0:
                newDamageNumbers.append(n)

        self._damageNumbers = newDamageNumbers

    def _drawDamageNumbers(self, screen):

        if not self._damageNumbers:
            return

        fontSize = max(14, screen.get_height() // 22)
        try:
            font = pygame.font.Font(FONT_TTF, fontSize)
        except:
            font = pygame.font.SysFont("Arial", fontSize, bold=True)

        for num in self._damageNumbers:

            alpha   = int(255 * (num["life"] / num["maxLife"]))
            alpha   = max(0, min(255, alpha))

            x = int(num["x"])
            y = int(num["y"])

            # Shadow (black, offset by 2px) drawn first
            shadowSurf = font.render(num["text"], True, (0, 0, 0))
            shadowSurf.set_alpha(alpha)
            screen.blit(shadowSurf,
                        (x - shadowSurf.get_width() // 2 + 2,
                         y - shadowSurf.get_height() // 2 + 2))

            textColour = num.get("colour", (220, 30, 30))
            textSurf = font.render(num["text"], True, textColour)
            textSurf.set_alpha(alpha)
            screen.blit(textSurf,
                        (x - textSurf.get_width()  // 2,
                         y - textSurf.get_height() // 2))


    def endGame(self):
        self._running = False


    def pauseGame(self, screen: pygame.Surface, gameView: pygame.Surface):

        viewW, viewH = screen.get_size()

        def loadFont(size):
            try:
                return pygame.font.Font(FONT_TTF, size)
            except Exception:
                return pygame.font.SysFont("Arial", size, bold=True)

        titleFont  = loadFont(viewH // 12)
        buttonFont = loadFont(viewH // 22)

        btnW      = int(viewW * 0.45)   # button width  = 45% of view
        btnH      = int(viewH * 0.10)   # button height = 10% of view
        btnGap    = int(viewH * 0.03)   # vertical gap between buttons
        panelPad  = int(viewH * 0.06)   # padding inside the panel

        buttons = [
            ("RESUME",    "resume", (39, 174, 96),  (46, 204, 113)),   # green
            ("MAIN MENU", "menu",   (52, 152, 219),  (41, 128, 185)),  # blue
        ]

        totalBtnH = len(buttons) * btnH + (len(buttons) - 1) * btnGap
        titleH    = titleFont.size("PAUSED")[1]

        panelW = btnW + panelPad * 2
        panelH = panelPad + titleH + panelPad + totalBtnH + panelPad

        panelX = viewW // 2 - panelW // 2
        panelY = viewH // 2 - panelH // 2

        btnRects = []
        for i in range(len(buttons)):
            bx = viewW // 2 - btnW // 2
            by = panelY + panelPad + titleH + panelPad + i * (btnH + btnGap)
            btnRects.append(pygame.Rect(bx, by, btnW, btnH))


        overlay = pygame.Surface((viewW, viewH), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))

        panel = pygame.Surface((panelW, panelH), pygame.SRCALPHA)
        panel.fill((30, 30, 30, 220))

        clock = pygame.time.Clock()

        while True:
            mousePos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:         # P toggles back to resume
                        return "resume"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, (_, signal, _, _) in zip(btnRects, buttons):
                        if rect.collidepoint(mousePos):
                            return signal               # clicked — return signal


            screen.blit(gameView, (0, 0))
            screen.blit(overlay,  (0, 0))
            screen.blit(panel,    (panelX, panelY))


            titleSurf = titleFont.render("PAUSED", True, (255, 255, 255))
            screen.blit(titleSurf, (viewW // 2 - titleSurf.get_width() // 2,
                                    panelY + panelPad))


            for rect, (label, _, colNormal, colHover) in zip(btnRects, buttons):
                if rect.collidepoint(mousePos):
                    colour = colHover
                else:
                    colour = colNormal
                pygame.draw.rect(screen, colour, rect, border_radius=10)

                pygame.draw.rect(screen, (0, 0, 0, 80), rect,
                                 width=2, border_radius=10)

                labelSurf = buttonFont.render(label, True, (255, 255, 255))
                screen.blit(labelSurf,
                            (rect.centerx - labelSurf.get_width()  // 2,
                             rect.centery - labelSurf.get_height() // 2))

            pygame.display.flip()
            clock.tick(30)      # low tick rate is fine while paused


    def _deathMenu(self, screen, gameView):

        viewW, viewH = screen.get_size()

        def loadFont(size):
            try:
                return pygame.font.Font(FONT_TTF, size)
            except Exception:
                return pygame.font.SysFont("Arial", size, bold=True)

        titleFont  = loadFont(viewH // 12)
        buttonFont = loadFont(viewH // 22)


        btnW     = int(viewW * 0.45)
        btnH     = int(viewH * 0.10)
        btnGap   = int(viewH * 0.03)
        panelPad = int(viewH * 0.06)

        # button configs:
        buttons = [
            ("RESUME",    "resume", (80, 80, 80),    (80, 80, 80),    True),
            ("MAIN MENU", "menu",   (52, 152, 219),  (41, 128, 185),  False),
        ]

        totalBtnH = len(buttons) * btnH + (len(buttons) - 1) * btnGap
        titleH    = titleFont.size("YOU DIED")[1]

        panelW = btnW + panelPad * 2
        panelH = panelPad + titleH + panelPad + totalBtnH + panelPad

        panelX = viewW // 2 - panelW // 2
        panelY = viewH // 2 - panelH // 2

        btnRects = []
        for i in range(len(buttons)):
            bx = viewW // 2 - btnW // 2
            by = panelY + panelPad + titleH + panelPad + i * (btnH + btnGap)
            btnRects.append(pygame.Rect(bx, by, btnW, btnH))

        overlay = pygame.Surface((viewW, viewH), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))

        panel = pygame.Surface((panelW, panelH), pygame.SRCALPHA)
        panel.fill((30, 30, 30, 220))

        clock = pygame.time.Clock()

        while True:
            mousePos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, (_, signal, _, _, greyed) in zip(btnRects, buttons):
                        if greyed:
                            continue
                        if rect.collidepoint(mousePos):
                            return signal


            screen.blit(gameView, (0, 0))
            screen.blit(overlay,  (0, 0))
            screen.blit(panel,    (panelX, panelY))


            titleSurf = titleFont.render("YOU DIED", True, (200, 30, 30))
            screen.blit(titleSurf, (viewW // 2 - titleSurf.get_width() // 2,
                                    panelY + panelPad))

            for rect, (label, _, colNormal, colHover, greyed) in zip(btnRects, buttons):
                if greyed:
                    colour = colNormal
                else:
                    if rect.collidepoint(mousePos):
                        colour = colHover
                    else:
                        colour = colNormal

                pygame.draw.rect(screen, colour, rect, border_radius=10)
                pygame.draw.rect(screen, (0, 0, 0, 80), rect,
                                 width=2, border_radius=10)

                if greyed:
                    labelColour = (160, 160, 160)
                else:
                    labelColour = (255, 255, 255)

                labelSurf = buttonFont.render(label, True, labelColour)
                screen.blit(labelSurf,
                            (rect.centerx - labelSurf.get_width()  // 2,
                             rect.centery - labelSurf.get_height() // 2))

            pygame.display.flip()
            clock.tick(30)