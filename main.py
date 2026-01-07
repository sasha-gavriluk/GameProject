import asyncio
from kivy.app import App

from gui.ScreenController import ScreenController


from gui.utils.GameSettings import game_settings
print(f"Завантажено налаштування для гравця: {game_settings.login}")
if not game_settings.login:
    print("Увага: Логін не встановлено. Буде використано гостьовий режим.")

class CardGameApp(App):
    def build(self):
        self.screen_controller = ScreenController()
        return self.screen_controller

    async def app_func(self):
        # Запускаємо Kivy в асинхронному циклі
        await self.async_run(async_lib='asyncio')
        # Тут можна додати очищення ресурсів після закриття вікна
        print("Додаток закрито")

if __name__ == '__main__':
    app = CardGameApp()
    asyncio.run(app.app_func())