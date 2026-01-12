from kivy.uix.screenmanager import ScreenManager, FadeTransition
from gui.utils.UIManager import UIManager

# Імпорти екранів
from gui.screen.MainMenuScreen import MainMenuScreen
from gui.screen.LobbyScreen import LobbyScreen
from gui.screen.AuthScreen import AuthScreen
from gui.screen.LocalGameSelectScreen import LocalGameSelectScreen
from gui.screen.PlayGameScreen import PlayGameScreen  # <--- Новий імпорт
class ScreenController(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(transition=FadeTransition(), **kwargs)
        self.ui_manager = UIManager()
        
        # Реєстрація екранів
        self.add_widget(MainMenuScreen(ui_manager=UIManager(), controller=self, name='main_menu'))
        self.add_widget(LobbyScreen(ui_manager=UIManager(), controller=self, name='lobby'))
        self.add_widget(AuthScreen(ui_manager=UIManager(), controller=self, name='auth'))
        self.add_widget(LocalGameSelectScreen(ui_manager=UIManager(), controller=self, name='local_select'))
        
        # Єдиний екран для гри
        self.add_widget(PlayGameScreen(ui_manager=UIManager(), controller=self, name='play_game'))

        self.current = 'main_menu'

    def switch_screen(self, screen_name, **kwargs):
        """Перемикає екран і передає аргументи (kwargs) в цільовий екран"""
        if self.has_screen(screen_name):
            screen = self.get_screen(screen_name)
            
            # Якщо екран має метод update_context, передаємо туди дані
            if hasattr(screen, 'update_context'):
                screen.update_context(**kwargs)
            
            self.current = screen_name
        else:
            print(f"Screen {screen_name} not found!")
