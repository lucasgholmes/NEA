# 🌀 Warped Ways

> A top-down maze exploration game built in Python with Pygame, featuring procedurally generated mazes, enemy AI, a weapon shop, player progression, and local multiplayer support.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation & Running](#installation--running)
- [Gameplay](#gameplay)
- [Architecture](#architecture)
- [Database](#database)
- [Multiplayer](#multiplayer)
- [Assets](#assets)

---

## Overview

Warped Ways is an A-Level Computer Science NEA project. The player navigates randomly generated mazes, collects coins, fights enemies, and races against the clock to reach the finish tile. Progress is saved to a remote MySQL database, and a shop system lets players spend earned coins on weapons that boost combat damage.

---

## Features

- **Procedural maze generation** using a randomised depth-first search (DFS) algorithm on a logical cell grid
- **Enemy AI** — Spiders that roam randomly and Zombies that patrol and charge when the player enters their line of sight
- **Combat system** — Player attacks enemies; enemies deal damage on contact; floating damage numbers provide visual feedback
- **Coin system** — Coins are randomly scattered across path tiles and animate with a sine-wave pulse; collecting them increments a round total
- **Weapon shop** — Purchase weapons with coins to increase attack damage; equip a weapon before entering a maze
- **Player progression** — Level, total coins, mazes completed, and fastest time are all tracked and persisted
- **Timed runs** — A HUD timer counts down per-session; a fastest-time record is maintained per user
- **Pause menu** — In-game pause overlay (P key) with Resume and Main Menu options
- **Death screen** — Dedicated YOU DIED overlay displayed when the player's health reaches zero
- **User accounts** — Register and log in with hashed passwords; all stats are stored per account
- **Local multiplayer** — A TCP socket-based Server/Client system for two-player sessions on a LAN
- **Difficulty scaling** — Easy / Medium / Hard modes scale enemy counts and other parameters

---

## Project Structure

```
warped-ways/
│
├── main.py                  # Entry point — launches the Tkinter GUI app
├── GUI.py                   # All Tkinter screens (login, menu, shop, multiplayer lobby, etc.)
├── game_manager.py          # Core Pygame game loop, rendering, HUD, pause/death menus
├── maze.py                  # Maze generation (DFS), tile map, coin placement, coin pickup logic
├── player.py                # Player movement, collision, health, attack
├── enemy.py                 # Monster base class; Spider and Zombie subclasses with AI
├── tile.py                  # Tile data class (type, coin state, shrink animation)
├── item.py                  # Item data class used by the shop
├── user.py                  # User data class (username, userID)
├── player_stats.py          # PlayerStats data class (level, coins, mazesCompleted, fastestTime)
├── database_manager.py      # MySQL interface — users, stats, shop items, inventory
├── multiplayerConnection.py # TCP socket Server and Client classes for LAN multiplayer
├── constants.py             # Shared constants (tile types, speeds, image paths, FPS)
│
└── ASSETS/
    ├── Path.png / Wall.png / Start.png / Finish.png
    ├── Player.png
    ├── spider.png / zombie-left.png / zombie-right.png
    ├── coin.png / heart.png
    ├── StoneSword.png / IronSword.png / WoodenClub.png
    ├── DoomDagger.png / GreatHammer.png / MeatClub.png / WarpedBlade.png
    ├── warpedwayslogo.png
    └── Minecraft.otf
```

---

## Requirements

- Python 3.10+
- [Pygame](https://www.pygame.org/) — game loop and rendering
- [mysql-connector-python](https://pypi.org/project/mysql-connector-python/) — database connectivity
- A valid SSL certificate file (`global-bundle.pem`) in the project root for the AWS RDS connection

Install dependencies with:

```bash
pip install pygame mysql-connector-python
```

---

## Installation & Running

1. Clone or download the repository.
2. Place all image/font assets inside an `ASSETS/` folder in the project root (paths are defined in `constants.py`).
3. Ensure `global-bundle.pem` is present in the project root for the database SSL connection.
4. Run the game:

```bash
python main.py
```

The Tkinter window will open, presenting the login/register screen.

---

## Gameplay

| Key | Action |
|-----|--------|
| `W A S D` | Move player |
| `Space` | Attack (swings equipped weapon) |
| `P` | Pause / unpause |
| `Escape` | Quit to menu |

**Objective:** Navigate from the **Start** tile to the **Finish** tile as fast as possible, collecting coins and defeating enemies along the way.

**Enemies:**
- **Spider** — Randomly wanders the maze; damages the player on contact.
- **Zombie** — Patrols its row/column; charges at the player when line-of-sight is established.

**Coins** are scattered on path tiles. Collect them by walking over them — they play a shrink animation when picked up. Coins carry over to the shop between runs.

---

## Architecture

### Maze Generation

`Maze.generate()` builds a perfect maze (no loops, every cell reachable) using iterative DFS on an 8×8 logical cell grid, then expands it to a `17×17` tile map (wall/path grid). A random start column-1 tile and a random finish right-edge tile are placed afterwards.

### Game Loop

`GameManager.startGame()` drives the Pygame loop at 240 FPS. Each frame:
1. Handles events (quit, escape, pause).
2. Advances the session timer.
3. Updates player position and collision.
4. Updates each Spider and Zombie.
5. Checks coin pickups and enemy contact.
6. Renders the maze, drops, enemies, player, HUD, and floating damage numbers.

### Enemy AI

- **Spider** (`enemy.Spider`) — picks a random adjacent open tile each time it reaches its target; smooth pixel interpolation between tiles.
- **Zombie** (`enemy.Zombie`) — checks whether the player shares its row or column with no walls in between; if so, it charges; otherwise it patrols back and forth along its current axis.

### Camera

The camera is always centred on the player. The maze renders a 3×3 tile window (`tileCount = 3`) that scrolls smoothly with the player's sub-pixel position.

---

## Database

The game connects to an **AWS RDS MySQL** instance. The schema comprises four tables:

| Table | Purpose |
|-------|---------|
| `Users` | Stores `userID`, `username`, and `passwordHash` |
| `PlayerStats` | Stores `level`, `coins`, `mazesCompleted`, and `fastestTime` per user |
| `Items` | Catalogue of shop weapons (name, type, damage, price) |
| `UserItems` | Junction table recording which items each user owns and in what quantity |

`DatabaseManager` handles all queries. If the database is unreachable, `dbAvailable` is set to `False` and the game falls back to in-memory defaults so it can still be played offline.

Passwords are hashed before being sent to the database — the plain-text password is never stored.

---

## Multiplayer

`multiplayerConnection.py` provides a simple TCP socket layer for local area network (LAN) two-player sessions.

- **Server** — Binds to `0.0.0.0:5555`, listens for one incoming client, and fires an `on_client_connected` callback when the client joins. Incoming messages are handled on a background daemon thread.
- **Client** — Connects to a given IP and port, then listens on a background daemon thread.

The host's local IP is detected automatically via `getLocalIP()` and displayed in the multiplayer lobby screen so the joining player knows what address to enter.

---

## Assets

All game assets (sprites, tiles, fonts) are loaded from the `ASSETS/` directory. Paths are centralised in `constants.py` so they can be updated in one place. The game uses `pygame.transform.smoothscale` for tile and UI images and `pygame.transform.scale` (nearest-neighbour) for pixel-art sprites to preserve their crisp look.

---

*This project was developed as an AQA A-Level Computer Science Non-Examined Assessment (NEA).*
