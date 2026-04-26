import threading
import customtkinter as ctk
from PIL import Image

from constants          import (LOGO_IMG, COIN_IMG,
                                WOODENCLUB_IMG, IRONSWORD_IMG, DOOMDAGGER_IMG,
                                GREATHAMMER_IMG, MEATCLUB_IMG, STONESWORD_IMG,
                                WARPEDBLADE_IMG)
from database_manager   import DatabaseManager
from user               import User
from game_manager       import GameManager
from multiplayerConnection import Server, Client, getLocalIP


class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.db          = DatabaseManager()
        self.currentUser = User(self.db)    # not loged in
        self.lastScore   = None
        self.sessionTime = 0.0

        # The weapon name currently selected in the shop equip dropdown.
        # None means no weapon chosen.
        self._equippedWeaponName = None

        # Difficulty: 1 = Easy, 2 = Medium, 3 = Hard
        # Controls spider count multiplier (1x, 2x, 3x)
        self._difficulty = 1

        self._timerMinutes    = 20
        self._timerRemaining  = None
        self._menuTimerActive = False

        self.title("Warped Ways")
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")

        self._font      = ctk.CTkFont(family="Minecraft", size=32)
        self._font64    = ctk.CTkFont(family="Minecraft", size=64)
        self._fontSmall = ctk.CTkFont(family="Minecraft", size=20)
        self._logoscale = 2

        self._coinImg = ctk.CTkImage(
            light_image=Image.open(COIN_IMG),
            size=(32, 32))


        self._buttonHeight = 80
        self._buttonWidth = 500

        self._buildMainMenu()
        self._buildLoginFrame()
        self._buildSinglePlayerFrame()
        self._buildShopFrame()
        self._buildMultiplayerFrames()

        self._showFrame(self.mainMenuFrame)


    def _buildMainMenu(self):
        self.mainMenuFrame = ctk.CTkFrame(self, fg_color="transparent")

        try:
            logoImg = ctk.CTkImage(
                light_image=Image.open(LOGO_IMG),
                size=((453)*self._logoscale, (88)*self._logoscale)
            )
            ctk.CTkLabel(self.mainMenuFrame, image=logoImg, text="").pack(pady=(60, 20))
        except:
            ctk.CTkLabel(self.mainMenuFrame, text="WARPED WAYS",
                         font=self._font64).pack(pady=(60, 20))


        if self.db.dbAvailable == True:
            dbState = "normal"
        else:
            dbState = "disabled"


        if not self.db.dbAvailable:
            ctk.CTkLabel(self.mainMenuFrame,
                         text="Cannot connect to server.\nLogin and Register are unavailable.",
                         text_color="red", font=self._font).pack(pady=(0, 10))

        ctk.CTkButton(self.mainMenuFrame, text="LOG IN",
                      command=self._showLogin,
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      state=dbState).pack(pady=(0, 20))
        ctk.CTkButton(self.mainMenuFrame, text="REGISTER",
                      command=self._showRegister,
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      state=dbState).pack(pady=(0, 20))
        ctk.CTkButton(self.mainMenuFrame, text="QUIT",
                      command=self.destroy,
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      fg_color="red").pack(pady=(0, 20))

    def _buildLoginFrame(self):
        self.loginFrame = ctk.CTkFrame(self, fg_color="transparent")
        self._isRegisterMode = False

        self.loginLabel = ctk.CTkLabel(self.loginFrame, text="LOG IN",
                                       font=self._font64)
        self.loginLabel.pack(pady=(60, 20))

        self.usernameEntry = ctk.CTkEntry(self.loginFrame,
                                          placeholder_text="Username",
                                          width=self._buttonWidth, font=self._font)
        self.usernameEntry.pack(pady=(0, 10))

        self.passwordEntry = ctk.CTkEntry(self.loginFrame,
                                          placeholder_text="Password",
                                          show="*", width=self._buttonWidth, font=self._font)
        self.passwordEntry.pack(pady=(0, 10))

        self._errorVar   = ctk.StringVar()
        self.errorLabel  = ctk.CTkLabel(self.loginFrame, textvariable=self._errorVar,
                                        text_color="red", font=self._font)

        self.submitBtn = ctk.CTkButton(self.loginFrame, text="SUBMIT",
                                       command=self._submitLogin,
                                       width=self._buttonWidth, height=self._buttonHeight, font=self._font)
        self.submitBtn.pack(pady=(10, 10))

        ctk.CTkButton(self.loginFrame, text="BACK",
                      command=self._backFromLogin,
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      fg_color="red").pack(pady=(0, 20))

    def _buildSinglePlayerFrame(self):
        self.singlePlayerFrame = ctk.CTkFrame(self, fg_color="transparent")

        self.spUserLabel    = ctk.CTkLabel(self.singlePlayerFrame,
                                           text="USER: #", font=self._font64)
        self.spUserLabel.pack(pady=(40, 20))

        self.scoreLabel     = ctk.CTkLabel(self.singlePlayerFrame,
                                           text="Previous Score: -", font=self._font)
        self.scoreLabel.pack(pady=(0, 10))

        self.fastestLabel   = ctk.CTkLabel(self.singlePlayerFrame,
                                           text="Fastest Time: -", font=self._font)
        self.fastestLabel.pack(pady=(0, 10))

        self.levelLabel     = ctk.CTkLabel(self.singlePlayerFrame,
                                           text="Level: 1", font=self._font)
        self.levelLabel.pack(pady=(0, 10))

        spCoinsRow = ctk.CTkFrame(self.singlePlayerFrame, fg_color="transparent")
        spCoinsRow.pack(pady=(0, 10))

        self.coinsLabel = ctk.CTkLabel(spCoinsRow, text="Coins: 0", font=self._font)
        self.coinsLabel.pack(side="left", padx=(0, 8))

        if self._coinImg is not None:
            ctk.CTkLabel(spCoinsRow, image=self._coinImg, text="").pack(side="left")

        self.mazesLabel     = ctk.CTkLabel(self.singlePlayerFrame,
                                           text="Mazes Completed: 0", font=self._font)
        self.mazesLabel.pack(pady=(0, 10))

        self.sessionLabel   = ctk.CTkLabel(self.singlePlayerFrame,
                                           text="Session Time: 0 s", font=self._font)
        self.sessionLabel.pack(pady=(0, 20))

        # Only shown before the session has started
        self.timerSliderLabel = ctk.CTkLabel(self.singlePlayerFrame,
                                             text=f"Session Timer: {self._timerMinutes} min",
                                             font=self._font)
        self.timerSliderLabel.pack(pady=(0, 6))

        self.timerSlider = ctk.CTkSlider(self.singlePlayerFrame,
                                         from_=1, to=40,
                                         number_of_steps=39,
                                         width=self._buttonWidth,
                                         command=self._onTimerSliderChange)
        self.timerSlider.set(self._timerMinutes)
        self.timerSlider.pack(pady=(0, 20))


        # 3 steps: 1 = Easy, 2 = Medium, 3 = Hard
        # Controls number of spiders.
        diffLabels = {1: "Easy", 2: "Medium", 3: "Hard"}
        self.difficultySliderLabel = ctk.CTkLabel(
            self.singlePlayerFrame,
            text=f"Difficulty: {diffLabels[self._difficulty]}",
            font=self._font
        )
        self.difficultySliderLabel.pack(pady=(0, 6))

        self.difficultySlider = ctk.CTkSlider(
            self.singlePlayerFrame,
            from_=1, to=3,
            number_of_steps=2,
            width=self._buttonWidth,
            command=self._onDifficultySliderChange
        )
        self.difficultySlider.set(self._difficulty)
        self.difficultySlider.pack(pady=(0, 20))

        # Shown once the session timer has expired
        self.timeUpLabel = ctk.CTkLabel(self.singlePlayerFrame,
                                        text="Time's up! Session over.",
                                        text_color="red", font=self._font)


        self.playBtn = ctk.CTkButton(self.singlePlayerFrame, text="PLAY",
                                     command=self._runGame,
                                     width=self._buttonWidth, height=self._buttonHeight,
                                     font=self._font, fg_color="green")
        self.playBtn.pack(pady=(0, 20))

        ctk.CTkButton(self.singlePlayerFrame, text="SHOP & EQUIP",
                      command=self._showShop,
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      fg_color="#8B5CF6").pack(pady=(0, 10))

        ctk.CTkButton(self.singlePlayerFrame, text="BACK",
                      command=self._logout,
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      fg_color="red").pack(pady=(0, 10))

        ctk.CTkButton(self.singlePlayerFrame, text="SAVE & EXIT",
                      command=self._saveExit,
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      fg_color="orange").pack(pady=(0, 20))

    def _onTimerSliderChange(self, value):
        # Round to nearest integer and store
        self._timerMinutes = int(round(value))
        self.timerSliderLabel.configure(text=f"Session Timer: {self._timerMinutes} min")

    def _onDifficultySliderChange(self, value):
        # Snap to 1, 2 or 3
        self._difficulty = int(round(value))
        diffLabels = {1: "Easy", 2: "Medium", 3: "Hard"}
        self.difficultySliderLabel.configure(
            text=f"Difficulty: {diffLabels[self._difficulty]}"
        )


    _WEAPON_IMG_MAP = {
        "Wooden Club":  WOODENCLUB_IMG,
        "Iron Sword":   IRONSWORD_IMG,
        "Doom Dagger":  DOOMDAGGER_IMG,
        "Great Hammer": GREATHAMMER_IMG,
        "Meat Club":    MEATCLUB_IMG,
        "Stone Sword":  STONESWORD_IMG,
        "Warped Blade": WARPEDBLADE_IMG,
    }

    _WEAPON_DAMAGE_MAP = {
        "Wooden Club":  10,
        "Iron Sword":   25,
        "Doom Dagger":  40,
        "Great Hammer": 50,
        "Meat Club":    15,
        "Stone Sword":  20,
        "Warped Blade": 60,
    }

    def _buildShopFrame(self):
        self.shopFrame = ctk.CTkFrame(self, fg_color="transparent")

        ctk.CTkLabel(self.shopFrame, text="SHOP & EQUIP",
                     font=self._font64).pack(pady=(40, 10))

        shopCoinsRow = ctk.CTkFrame(self.shopFrame, fg_color="transparent")
        shopCoinsRow.pack(pady=(0, 20))

        self.shopCoinsLabel = ctk.CTkLabel(shopCoinsRow, text="Coins: 0", font=self._font)
        self.shopCoinsLabel.pack(side="left", padx=(0, 8))

        if self._coinImg is not None:
            ctk.CTkLabel(shopCoinsRow, image=self._coinImg, text="").pack(side="left")

        self.weaponGrid = ctk.CTkFrame(self.shopFrame, fg_color="transparent")
        self.weaponGrid.pack(pady=(0, 20))

        ctk.CTkLabel(self.shopFrame, text="Equip Weapon:",
                     font=self._font).pack(pady=(0, 6))

        self.equipVar = ctk.StringVar(value="")
        self.equipDropdown = ctk.CTkOptionMenu(self.shopFrame,
                                               values=[""],
                                               variable=self.equipVar,
                                               command=self._onEquipChange,
                                               width=self._buttonWidth,
                                               font=self._font)
        self.equipDropdown.pack(pady=(0, 20))

        # Red error label shown when a purchase fails
        self.shopErrorLabel = ctk.CTkLabel(self.shopFrame, text="",
                                           text_color="red", font=self._fontSmall)

        ctk.CTkButton(self.shopFrame, text="BACK",
                      command=lambda: self._showFrame(self.singlePlayerFrame),
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      fg_color="red").pack(pady=(0, 20))

    def _showShop(self):
        # Refresh coin count
        self.shopCoinsLabel.configure(
            text=f"Coins: {self.currentUser.stats.coins}")

        # Hide any previous purchase error
        if self.shopErrorLabel.winfo_ismapped():
            self.shopErrorLabel.pack_forget()

        # Clear previous cards from the grid
        for widget in self.weaponGrid.winfo_children():
            widget.destroy()

        # Load shop items from DB
        shopItems = self.db.getShopItems()

        for i, (itemID, name, itemType, damage, price) in enumerate(shopItems):
            row = i // 2
            col = i % 2

            card = ctk.CTkFrame(self.weaponGrid, width=320, height=170,
                                corner_radius=10, border_width=2,
                                border_color="#8B5CF6")
            card.grid(row=row, column=col, padx=16, pady=8)
            card.pack_propagate(False)

            imgPath = self._WEAPON_IMG_MAP.get(name)
            if imgPath is not None:
                try:
                    rawImg = Image.open(imgPath).convert("RGBA")
                    sharpImg = rawImg.resize((64, 64), Image.NEAREST)
                    weaponImg = ctk.CTkImage(
                        light_image=sharpImg,
                        dark_image=sharpImg,
                        size=(64, 64)
                    )
                    ctk.CTkLabel(card, image=weaponImg, text="").pack(side="left", padx=(8, 4), pady=8)
                except Exception:
                    pass


            infoFrame = ctk.CTkFrame(card, fg_color="transparent")
            infoFrame.pack(side="left", expand=True, fill="both", padx=(0, 8))

            ctk.CTkLabel(infoFrame, text=name,
                         font=self._fontSmall).pack(anchor="w", pady=(8, 0))
            ctk.CTkLabel(infoFrame, text=f"DMG: {damage}",
                         font=self._fontSmall).pack(anchor="w")
            ctk.CTkLabel(infoFrame, text=f"Price: {price}",
                         font=self._fontSmall).pack(anchor="w")

            ctk.CTkButton(infoFrame, text="BUY",
                          command=lambda n=name, p=price: self._buyItem(n, p),
                          font=self._fontSmall,
                          height=36,
                          fg_color="#8B5CF6").pack(anchor="w", pady=(4, 0))

        # Load user's owned items for the equip dropdown
        userItems = self.db.getUserItems(self.currentUser.userID)

        if userItems:
            ownedNames = [row[1] for row in userItems]
            self.equipDropdown.configure(values=ownedNames)

            # Restore the previously chosen weapon if it is still in the list,
            # otherwise default to the first owned weapon
            if self._equippedWeaponName in ownedNames:
                self.equipVar.set(self._equippedWeaponName)
            else:
                self.equipVar.set(ownedNames[0])
                self._equippedWeaponName = ownedNames[0]
        else:
            self.equipDropdown.configure(values=["No weapons owned"])
            self.equipVar.set("No weapons owned")
            self._equippedWeaponName = None

        self._showFrame(self.shopFrame)

    def _onEquipChange(self, choice):
        self._equippedWeaponName = choice

    def _buyItem(self, itemName, price):
        if self.currentUser.stats.coins < price:
            self.shopErrorLabel.configure(text="Not enough coins!")
            if not self.shopErrorLabel.winfo_ismapped():
                self.shopErrorLabel.pack(pady=(0, 8))
            self.after(2500, self._hideShopError)
            return
        success = self.db.purchaseItem(self.currentUser.userID, itemName, price)

        if success:
            self.currentUser.stats.coins -= price
            self.currentUser.saveStats()
            self._showShop()
        else:
            self.shopErrorLabel.configure(text="Purchase failed. Try again.")
            if not self.shopErrorLabel.winfo_ismapped():
                self.shopErrorLabel.pack(pady=(0, 8))
            self.after(2500, self._hideShopError)

    def _hideShopError(self):
        if self.shopErrorLabel.winfo_ismapped():
            self.shopErrorLabel.pack_forget()

    def _buildMultiplayerFrames(self):

        self.mpChoiceFrame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self.mpChoiceFrame, text="Server or Client",
                     font=self._font).pack(pady=(0, 20))
        ctk.CTkButton(self.mpChoiceFrame, text="Server",
                      command=self._showMPServer,
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      fg_color="#1E90FF").pack(pady=(0, 20))
        ctk.CTkButton(self.mpChoiceFrame, text="Client",
                      command=self._showMPClient,
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      fg_color="#1E90FF").pack(pady=(0, 20))
        ctk.CTkButton(self.mpChoiceFrame, text="Back",
                      command=lambda: self._showFrame(self.loggedInFrame),
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      fg_color="red").pack(pady=(0, 20))

        self.mpServerFrame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self.mpServerFrame, text="Host a Server",
                     font=self._font).pack(pady=(40, 20))
        ctk.CTkLabel(self.mpServerFrame, text=f"Your IP: {getLocalIP()}",
                     font=self._font).pack(pady=(0, 10))
        self.serverStatusLabel = ctk.CTkLabel(self.mpServerFrame,
                                              text="Waiting to start...",
                                              font=self._font)
        self.serverStatusLabel.pack(pady=(0, 20))
        ctk.CTkButton(self.mpServerFrame, text="Start Server",
                      command=self._startServer,
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      fg_color="green").pack(pady=(0, 20))
        ctk.CTkButton(self.mpServerFrame, text="Back",
                      command=lambda: self._showFrame(self.mpChoiceFrame),
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      fg_color="red").pack(pady=(0, 20))


        self.mpClientFrame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self.mpClientFrame, text="Join a Server",
                     font=self._font).pack(pady=(40, 20))
        self.ipEntry = ctk.CTkEntry(self.mpClientFrame,
                                    placeholder_text="Enter Server IP",
                                    width=self._buttonWidth, font=self._font)
        self.ipEntry.pack(pady=(0, 20))
        ctk.CTkButton(self.mpClientFrame, text="Connect",
                      command=lambda: self._connectToServer(self.ipEntry.get()),
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      fg_color="green").pack(pady=(0, 20))
        ctk.CTkButton(self.mpClientFrame, text="Back",
                      command=lambda: self._showFrame(self.mpChoiceFrame),
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      fg_color="red").pack(pady=(0, 20))


        self.mpLobbyFrame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self.mpLobbyFrame, text="Lobby (Coming Soon...)",
                     font=self._font).pack(pady=(40, 20))
        ctk.CTkButton(self.mpLobbyFrame, text="Back to Menu",
                      command=lambda: self._showFrame(self.mpChoiceFrame),
                      width=self._buttonWidth, height=self._buttonHeight, font=self._font,
                      fg_color="red").pack(pady=(0, 20))


    def _showFrame(self, frame: ctk.CTkFrame):
        for f in (self.mainMenuFrame, self.loginFrame,
                  self.singlePlayerFrame, self.shopFrame,
                  self.mpChoiceFrame, self.mpServerFrame,
                  self.mpClientFrame, self.mpLobbyFrame):
            f.pack_forget()
        frame.pack(expand=True)



    def _backFromLogin(self):
        self._clearLoginEntries()
        self._showFrame(self.mainMenuFrame)

    def _clearLoginEntries(self):
        self.usernameEntry.delete(0, "end")
        self.passwordEntry.delete(0, "end")
        self._hideError()

    def _showLogin(self):
        if not self.db.dbAvailable:
            return
        self._isRegisterMode = False
        self.loginLabel.configure(text="LOG IN")
        self.submitBtn.configure(text="SUBMIT")
        self._showFrame(self.loginFrame)

    def _showRegister(self):
        if not self.db.dbAvailable:
            return
        self._isRegisterMode = True
        self.loginLabel.configure(text="REGISTER")
        self.submitBtn.configure(text="CREATE ACCOUNT")
        self._showFrame(self.loginFrame)

    def _showError(self, message: str):
        self._errorVar.set(message)
        if not self.errorLabel.winfo_ismapped():
            self.errorLabel.pack(pady=(4, 0))
        self.after(2500, self._hideError)

    def _hideError(self):
        self._errorVar.set("")
        if self.errorLabel.winfo_ismapped():
            self.errorLabel.pack_forget()

    def _submitLogin(self):
        if not self.db.dbAvailable:
            return
        self.submitBtn.configure(state="disabled")
        try:
            username = self.usernameEntry.get().strip()
            password = self.passwordEntry.get()

            if not username or not password:
                self._showError("Please enter a username and password.")
                return

            if self._isRegisterMode:
                try:
                    self.currentUser.register(username, password)
                    self._afterLoginSuccess()
                except ConnectionError as e:
                    self._showError(str(e))
                except ValueError as e:
                    self._showError(str(e))
            else:
                try:
                    if self.currentUser.login(username, password):
                        self._afterLoginSuccess()
                    else:
                        self._showError("Invalid username or password.")
                        self.passwordEntry.delete(0, "end")
                except ConnectionError as e:
                    self._showError(str(e))
        finally:
            self.submitBtn.configure(state="normal")

    def _afterLoginSuccess(self):
        self._clearLoginEntries()
        self.sessionTime      = 0.0
        self.lastScore        = None
        # Reset timer so the new session gets a fresh slider
        self._timerMinutes    = 20
        self._timerRemaining  = None
        self._menuTimerActive = False
        self.timerSlider.set(self._timerMinutes)
        self._showSinglePlayer()

    def _logout(self):
        self.currentUser.saveStats()
        self.currentUser.logout()
        # Reset timer state ready for next login
        self._timerMinutes    = 20
        self._timerRemaining  = None
        self._menuTimerActive = False
        self._showFrame(self.mainMenuFrame)


    def _showSinglePlayer(self):
        u  = self.currentUser
        st = u.stats

        self.spUserLabel.configure(text=f"USER: {u.username}")
        self.scoreLabel.configure(
            text=f"Previous Score: {self.lastScore} s" if self.lastScore else "Previous Score: -")
        self.fastestLabel.configure(
            text=f"Fastest Time: {st.fastestTime} s" if st.fastestTime else "Fastest Time: -")
        self.levelLabel.configure(text=f"Level: {st.level}")
        self.coinsLabel.configure(text=f"Coins: {st.coins}")
        self.mazesLabel.configure(text=f"Mazes Completed: {st.mazesCompleted}")
        sessionMins = int(self.sessionTime) // 60
        sessionSecs = int(self.sessionTime) % 60
        self.sessionLabel.configure(text=f"Session Time: {sessionMins:02d}:{sessionSecs:02d}")


        if self._timerRemaining is None:
            # Session not yet started - show editable slider
            self.timerSlider.configure(state="normal")
            self.timerSliderLabel.configure(
                text=f"Session Timer: {self._timerMinutes} min")
            self.timerSlider.pack(pady=(0, 20))
            self.timerSliderLabel.pack(pady=(0, 6))
        else:
            # Session already running - lock the slider and show remaining time
            self.timerSlider.configure(state="disabled")
            mins = int(self._timerRemaining) // 60
            secs = int(self._timerRemaining) % 60
            self.timerSliderLabel.configure(
                text=f"Time Remaining: {mins:02d}:{secs:02d}")

        if self._timerRemaining is not None and self._timerRemaining <= 0:
            if not self.timeUpLabel.winfo_ismapped():
                self.timeUpLabel.pack(pady=(0, 10))
            self.playBtn.configure(state="disabled")
        else:
            self.timeUpLabel.pack_forget()
            self.playBtn.configure(state="normal")

        self._showFrame(self.singlePlayerFrame)

    def _runGame(self):
        if self._timerRemaining is None:
            self._timerRemaining = self._timerMinutes * 60.0

        self._menuTimerActive = False

        equippedImgPath    = self._WEAPON_IMG_MAP.get(self._equippedWeaponName)
        equippedWeaponDmg  = self._WEAPON_DAMAGE_MAP.get(self._equippedWeaponName, 0)

        gm                                           = GameManager(self.currentUser, self.currentUser.stats.level)
        elapsed, self._timerRemaining, roundCoins, playerDied = gm.startGame(
            self, self._timerRemaining, equippedImgPath, self._difficulty,
            equippedWeaponDamage=equippedWeaponDmg
        )

        if playerDied:
            # Player died: session time still consumed but no score/coin/maze reward
            self.sessionTime += elapsed if elapsed is not None else 0.0
            self.currentUser.saveStats()
        elif elapsed is not None:
            self.lastScore    = elapsed
            self.sessionTime += elapsed
            self.currentUser.stats.updateStats(elapsed, roundCoins)
            self.currentUser.saveStats()

        # Restore window geometry
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.deiconify()
        self.geometry(f"{sw}x{sh}+0+0")

        # Resume menu-side countdown now that we are back in CTk
        self._startMenuTimer()
        self._showSinglePlayer()

    def _startMenuTimer(self):
        if self._timerRemaining is None:
            return
        if self._timerRemaining <= 0:
            return
        self._menuTimerActive = True
        self._menuTimerTick()

    def _menuTimerTick(self):
        if not self._menuTimerActive:
            return
        if self._timerRemaining is None:
            return

        self._timerRemaining -= 1
        if self._timerRemaining <= 0:
            self._timerRemaining  = 0
            self._menuTimerActive = False

        # If the singleplayer frame is currently visible, refresh its labels
        if self.singlePlayerFrame.winfo_ismapped():
            self._showSinglePlayer()

        if self._menuTimerActive:
            self.after(1000, self._menuTimerTick)

    def _saveExit(self):
        self.currentUser.saveStats()
        self.destroy()

    # Unfinished Multiplayer

    def _showMultiplayer(self):
        self._showFrame(self.mpChoiceFrame)

    def _showMPServer(self):
        self._showFrame(self.mpServerFrame)

    def _showMPClient(self):
        self._showFrame(self.mpClientFrame)

    def _startServer(self):
        self.serverStatusLabel.configure(text="Server started. Waiting for client...")
        server = Server(ip="0.0.0.0", port=5555,
                        on_client_connected=self._onClientConnected)
        server.startAsyncServer()

    def _onClientConnected(self):
        self.serverStatusLabel.configure(text="Client connected!")
        self._showFrame(self.mpLobbyFrame)

    def _connectToServer(self, ip: str):
        if not ip.strip():
            return
        client = Client(ip=ip, port=5555)
        threading.Thread(target=self._tryConnect, args=(client,), daemon=True).start()

    def _tryConnect(self, client: Client):
        _, online = client.setupClientConnection()
        if online:
            self.after(0, lambda: self._showFrame(self.mpLobbyFrame))


if __name__ == "__main__":
    app = App()
    app.mainloop()