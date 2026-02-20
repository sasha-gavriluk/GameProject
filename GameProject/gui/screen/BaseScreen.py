# --- БАЗОВИЙ ЕКРАН ---
from kivy.uix.screenmanager import Screen
from kivy.graphics import Color, Rectangle

from gui.config.Configs import VisualConfig

class BaseScreen(Screen):
    use_screen_background = True

    def __init__(self, ui_manager, controller, **kwargs):
        super().__init__(**kwargs)
        self.ui = ui_manager
        self.controller = controller
        self.style = ui_manager.style_manager
        self._bg_rect = None

        if self.use_screen_background:
            with self.canvas.before:
                Color(*VisualConfig.BACKGROUND_COLOR)
                self._bg_rect = Rectangle(pos=self.pos, size=self.size)
            self.bind(pos=self._update_bg_rect, size=self._update_bg_rect)

        self.build_ui()

    def _update_bg_rect(self, *_):
        if self._bg_rect:
            self._bg_rect.pos = self.pos
            self._bg_rect.size = self.size

    def build_ui(self): pass
