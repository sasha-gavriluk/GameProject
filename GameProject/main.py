import asyncio
from kivy.app import App
# --- ДОДАНО ---
from kivy.core.window import Window
from kivy.config import Config

# Вмикаємо повний екран (для ПК і Android)
# 'auto' приховує інтерфейс ОС і розтягує додаток
Window.fullscreen = 'auto' 

# Можна також дозволити зміну розмірів, якщо це десктоп
Config.set('graphics', 'resizable', True)
# ----------------

from gui.ScreenController import ScreenController
from gui.utils.GameSettings import game_settings

class CardGameApp(App):
    def build(self):
        # Тепер App вже існує, і тут безпечно звертатися до налаштувань
        print(f"Завантажено налаштування для гравця: {game_settings.login}")
        if not game_settings.login:
            print("Увага: Логін не встановлено. Буде використано гостьовий режим.")
            
        self.screen_controller = ScreenController()
        return self.screen_controller

    def on_start(self):
        game_settings.reload()
        game_settings.apply_orientation()

    async def app_func(self):
        await self.async_run(async_lib='asyncio')
        print("Додаток закрито")

if __name__ == '__main__':
    app = CardGameApp()
    asyncio.run(app.app_func())
