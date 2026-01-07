
from kivy.uix.screenmanager import ScreenManager, FadeTransition

from gui.utils.UIManager import UIManager

from gui.sreen.MainMenuScreen import MainMenuScreen
from gui.sreen.LobbyScreen import LobbyScreen
from gui.sreen.AuthScreen import AuthScreen
from gui.sreen.GameScreen import GameScreen
from gui.sreen.LocalGameSelectScreen import LocalGameSelectScreen

from gui.sreen.WarGameScreen import WarGameScreen

class ScreenController(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(transition=FadeTransition(), **kwargs)
        self.ui_manager = UIManager()
        
        self.add_widget(MainMenuScreen(ui_manager=UIManager(), controller=self, name='main_menu'))
        self.add_widget(LobbyScreen(ui_manager=UIManager(), controller=self, name='lobby'))
        self.add_widget(AuthScreen(ui_manager=UIManager(), controller=self, name='auth'))
        self.add_widget(GameScreen(ui_manager=UIManager(), controller=self, name='game'))
        self.add_widget(LocalGameSelectScreen(ui_manager=UIManager(), controller=self, name='local_select'))

        # Game 

        self.add_widget(WarGameScreen(ui_manager=UIManager(), controller=self, name='war_game'))

        self.current = 'main_menu'

    def switch_screen(self, screen_name): self.current = screen_name