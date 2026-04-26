import random
import pygame
import math
from constants import TILEPATH, TILEWALL, TILESTART, TILEFINISH, player, COIN_IMG, COIN_CHANCE
from tile import Tile


class _Node:
    def __init__(self, x, y):
        self.x           = x
        self.y           = y
        self.connections = []   # adjacency list

    def connect(self, other):
        if other not in self.connections:
            self.connections.append(other)

    def disconnect(self, other):
        if other in self.connections:
            self.connections.remove(other)



class Maze:

    def __init__(self, spiderCount = 5):
        self.width   = 8    # logical cell grid width
        self.height  = 8   # logical cell grid height

        self.mapWidth  = self.width  * 2 + 1   # pixel-tile grid dimensions
        self.mapHeight = self.height * 2 + 1
        self.tileMap   = []               # 2-D list of Tile objects
        self.startY    = 0                # pixel-tile row of the start cell

        self._coinImgPath    = COIN_IMG
        self._coinSurface    = None
        self._coinLastTsSize = None

        self.spiderTiles = []
        self.zombieTiles = []

        self.generate(spiderCount)


    def generate(self, spiderCount = 5):
        nodes = {}
        for y in range(self.height):
            for x in range(self.width):
                nodes[(x, y)] = _Node(x, y)

        # Random starting cell
        sx = random.randint(0, self.width  - 1)
        sy = random.randint(0, self.height - 1)
        self._dfsGen(nodes[(sx, sy)], nodes, [])

        rawMap = []
        for i in range(self.mapHeight):
            rawMap.append([TILEWALL] * self.mapWidth)

        # Carve paths from DFS connections
        for y in range(self.height):
            for x in range(self.width):
                mx = 2 * x + 1      # interior odd column
                my = 2 * y + 1      # interior odd row
                rawMap[my][mx] = TILEPATH
                node = nodes[(x, y)]
                for nbr in node.connections:
                    rawMap[my + (nbr.y - y)][mx + (nbr.x - x)] = TILEPATH

        # Place start and finish
        self.startY = random.randint(0, self.height - 1) * 2 + 1
        rawMap[self.startY][1] = TILESTART
        rawMap[random.randint(0, self.height - 1) * 2 + 1][self.width * 2 - 1] = TILEFINISH

        self.tileMap = []
        for y in range(self.mapHeight):
            row = []
            for x in range(self.mapWidth):
                row.append(Tile(x, y, rawMap[y][x]))
            self.tileMap.append(row)

        COIN_W_RATIO = 1 / 6          # coin width  as fraction of tileSize
        COIN_H_RATIO = (360 / 315) / 6 # coin height as fraction of tileSize

        for row in self.tileMap:
            for tile in row:
                if tile.type == TILEPATH:
                    if random.random() < COIN_CHANCE:
                        tile.hasCoin = True
                        tile.coinOffsetX = random.uniform(0.0, 1.0 - COIN_W_RATIO)
                        tile.coinOffsetY = random.uniform(0.0, 1.0 - COIN_H_RATIO)


        def allNeighboursOpen(tx, ty):
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx = tx + dx
                ny = ty + dy
                if not (0 <= nx < self.mapWidth and 0 <= ny < self.mapHeight):
                    return False
                if self.tileMap[ny][nx].type == TILEWALL:
                    return False
            return True

        pathTiles = []
        for row in self.tileMap:
            for tile in row:
                if tile.type == TILEPATH and allNeighboursOpen(tile.x, tile.y):
                    pathTiles.append((tile.x, tile.y))

        if len(pathTiles) >= spiderCount:
            self.spiderTiles = random.sample(pathTiles, spiderCount)
        elif len(pathTiles) > 0:
            self.spiderTiles = pathTiles[:]
        else:
            fallback = []
            for row in self.tileMap:
                for tile in row:
                    if tile.type == TILEPATH:
                        fallback.append((tile.x, tile.y))
            self.spiderTiles = random.sample(fallback, min(spiderCount, len(fallback)))

        zombieCount  = max(1, spiderCount // 2)
        remaining = []
        for t in pathTiles:
            if t not in self.spiderTiles:
                remaining.append(t)
        if len(remaining) >= zombieCount:
            self.zombieTiles = random.sample(remaining, zombieCount)
        elif len(remaining) > 0:
            self.zombieTiles = remaining[:]
        else:
            fallbackZ = [
                (tile.x, tile.y)
                for row in self.tileMap
                for tile in row
                if tile.type == TILEPATH
                and allNeighboursOpen(tile.x, tile.y)
                and (tile.x, tile.y) not in self.spiderTiles
            ]
            if not fallbackZ:
                fallbackZ = []
                for row in self.tileMap:
                    for tile in row:
                        if tile.type == TILEPATH and (tile.x, tile.y) not in self.spiderTiles:
                            fallbackZ.append((tile.x, tile.y))
            self.zombieTiles = random.sample(fallbackZ, min(zombieCount, len(fallbackZ)))

    def _dfsGen(self, cell, nodes, visited):
        visited.append(cell)
        offsets = [(0, -1), (0, 1), (1, 0), (-1, 0)]
        while True:
            unvisited = []
            for dx, dy in offsets:
                nx, ny = cell.x + dx, cell.y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    nbr = nodes[(nx, ny)]
                    if nbr not in visited:
                        unvisited.append(nbr)
            if not unvisited:
                break
            nxt = random.choice(unvisited)
            cell.connect(nxt)
            nxt.connect(cell)
            self._dfsGen(nxt, nodes, visited)


    def getTileType(self, tileX: int, tileY: int) -> int:

        if 0 <= tileX < self.mapWidth and 0 <= tileY < self.mapHeight:
            return self.tileMap[tileY][tileX].type
        return TILEWALL

    def checkCoinPickup(self, playerPixelX, playerPixelY, tileSize, playerPadX, playerPadY):
        coinW = tileSize // 6
        coinH = coinW * 360 // 315

        centerTileX = int(playerPixelX // tileSize)
        centerTileY = int(playerPixelY // tileSize)

        # Player hitbox edges
        playerLeft   = playerPixelX - playerPadX
        playerRight  = playerPixelX + playerPadX
        playerTop    = playerPixelY - playerPadY
        playerBottom = playerPixelY + playerPadY

        for dy in range(-1, 2):
            for dx in range(-1, 2):
                tx = centerTileX + dx
                ty = centerTileY + dy
                if not (0 <= tx < self.mapWidth and 0 <= ty < self.mapHeight):
                    continue
                tile = self.tileMap[ty][tx]
                if not tile.hasCoin or tile.coinShrinking:
                    continue

                # Pixel position of the coin's top-left corner
                coinPixelX = tx * tileSize + int(tile.coinOffsetX * tileSize)
                coinPixelY = ty * tileSize + int(tile.coinOffsetY * tileSize)

                # AABB overlap: player hitbox rectangle vs coin rectangle
                if (playerRight  >= coinPixelX
                        and playerLeft   <= coinPixelX + coinW
                        and playerBottom >= coinPixelY
                        and playerTop    <= coinPixelY + coinH):
                    tile.coinShrinking = True
                    return True

        return False

    def render(self, surface, images, tileSize, offsetX, offsetY, dt=0.0):

        surface.fill((0, 0, 0))    # clear last frame

        viewW = surface.get_width()
        viewH = surface.get_height()

        firstTileX = int(offsetX) // tileSize
        lastTileX  = int(offsetX + viewW - 1) // tileSize
        firstTileY = int(offsetY) // tileSize
        lastTileY  = int(offsetY + viewH - 1) // tileSize

        if self._coinLastTsSize != tileSize:
            coinW = tileSize // 6
            coinH = coinW * 360 // 315
            try:
                raw = pygame.image.load(self._coinImgPath).convert_alpha()
                self._coinSurface = pygame.transform.smoothscale(raw, (coinW, coinH))
            except Exception:
                self._coinSurface = None
            self._coinLastTsSize = tileSize


        PULSE_AMPLITUDE = 0.12
        PULSE_SPEED     = 1.5
        SHRINK_SPEED    = 3.0

        if self._coinSurface is not None:
            ticks       = pygame.time.get_ticks()
            pulseFactor = 1.0 + PULSE_AMPLITUDE * math.sin(
                2 * math.pi * PULSE_SPEED * ticks / 1000.0
            )
        else:
            pulseFactor = 1.0

        for ty in range(firstTileY, lastTileY + 1):
            for tx in range(firstTileX, lastTileX + 1):
                tileType  = self.getTileType(tx, ty)
                tileImage = images.get(tileType, images[TILEWALL])
                drawX = tx * tileSize - round(offsetX)
                drawY = ty * tileSize - round(offsetY)
                surface.blit(tileImage, (drawX, drawY))

                # Draw coin if this tile has one.
                # Collected coins play a shrink animation before being removed.
                if (self._coinSurface is not None
                        and 0 <= ty < self.mapHeight
                        and 0 <= tx < self.mapWidth
                        and self.tileMap[ty][tx].hasCoin):
                    tile = self.tileMap[ty][tx]

                    # Advance shrink animation for collected coins
                    if tile.coinShrinking:
                        tile.coinShrinkScale -= SHRINK_SPEED * dt
                        if tile.coinShrinkScale <= 0.0:
                            tile.hasCoin         = False
                            tile.coinShrinking   = False
                            tile.coinShrinkScale = 1.0
                            continue

                    # Shrinking coins use their own per-tile scale;
                    # normal coins use the shared sine-wave pulse factor
                    if tile.coinShrinking:
                        scaleFactor = tile.coinShrinkScale
                    else:
                        scaleFactor = pulseFactor

                    baseW  = self._coinSurface.get_width()
                    baseH  = self._coinSurface.get_height()
                    drawW  = max(1, int(baseW * scaleFactor))
                    drawH  = max(1, int(baseH * scaleFactor))
                    scaled = pygame.transform.smoothscale(self._coinSurface, (drawW, drawH))

                    # Centre the scaled coin on the same anchor point as the base size,
                    # so both the pulse and shrink animate from the coin's centre
                    anchorX = drawX + int(tile.coinOffsetX * tileSize) + baseW // 2
                    anchorY = drawY + int(tile.coinOffsetY * tileSize) + baseH // 2
                    coinX   = anchorX - drawW // 2
                    coinY   = anchorY - drawH // 2
                    surface.blit(scaled, (coinX, coinY))