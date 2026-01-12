# --- БАЗОВИЙ ЕКРАН ---
from kivy.uix.screenmanager import Screen

class BaseScreen(Screen):
    def __init__(self, ui_manager, controller, **kwargs):
        super().__init__(**kwargs)
        self.ui = ui_manager
        self.controller = controller
        self.style = ui_manager.style_manager
        self.build_ui()

    def build_ui(self): pass