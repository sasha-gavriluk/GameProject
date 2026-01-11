import asyncio
from gui.config.Configs import sdp, responsive_metrics
from gui.NetworkBridge import net
from gui.sreen.BaseScreen import BaseScreen
from gui.utils.GameSettings import game_settings

class MainMenuScreen(BaseScreen):
    def __init__(self, ui_manager, controller, **kwargs):
        super().__init__(ui_manager, controller, **kwargs)
        self.controller = controller
        self.ui = ui_manager
        self.setup_ui()
        self.add_widget(self.ui.root)

    def setup_ui(self):
        self.ui.add("anchor", "AnchorLayout", anchor_x='center', anchor_y='center')
        
        self.ui.add("box", "BoxLayout", 
                    parent="anchor", 
                    orientation="vertical", 
                    spacing=sdp(20), 
                    size_hint=(None, None), 
                    width=sdp(300))
        
        self.ui.add("title", "TitleLabel", parent="box", text="CARD GAME")
        
        # === КНОПКУ "ВВІЙТИ" ВИДАЛЕНО ===
        
        self.ui.add("btn_play", "MenuButton", parent="box", text="Грати")
        self.ui.set_action("btn_play", "on_release", lambda x: self.controller.switch_screen('local_select'))
        
        # Кнопка тепер називається "Мережева гра", але логіка змінилась
        self.ui.add("btn_online", "MenuButton", parent="box", text="Мережева гра")
        self.ui.add("btn_settings", "MenuButton", parent="box", text="Налаштування")
        
        # Призначаємо нову дію
        self.ui.set_action("btn_online", "on_release", self.check_online_access)
        
        self.ui.build()
        
        box = self.ui.registry["box"]
        box.bind(minimum_height=box.setter('height'))
        self._bind_box_width(box)

    def _bind_box_width(self, box):
        def _update_box_width(*_):
            box.width = min(sdp(360), self.width * 0.9)
        self.bind(size=_update_box_width)
        responsive_metrics.bind(scale=lambda *_: _update_box_width())
        _update_box_width()

    def check_online_access(self, instance):
        
        # Якщо логін пустий - зразу на форму
        if not game_settings.login:
            print("Логін відсутній. Перехід на авторизацію.")
            if self.controller: self.controller.switch_screen('auth')
            return

        # Якщо є логін - пробуємо АВТОМАТИЧНО ПІДКЛЮЧИТИСЬ
        # Оскільки connect_and_login це async метод, нам треба запустити його правильно.
        # У Kivy це робиться через asyncio.create_task, якщо App запущено через async_run
        
        # Змінюємо текст кнопки на "Підключення...", щоб користувач бачив процес
        btn = self.ui.registry["btn_online"]
        original_text = btn.text
        btn.text = "Підключення..."
        btn.disabled = True # Блокуємо кнопку

        # Запускаємо асинхронну задачу
        asyncio.create_task(self._process_login(btn, original_text))

    async def _process_login(self, btn, original_text):
        """Асинхронна функція входу"""
        success, message = await net.connect_and_login()
        
        # Повертаємо кнопку назад
        btn.text = original_text
        btn.disabled = False

        if success:
            print(f"Авто-вхід успішний: {message}")
            if self.controller:
                self.controller.switch_screen('lobby')
        else:
            print(f"Помилка авто-входу: {message}")
            # Якщо помилка (невірний пароль або сервер лежить) -> йдемо на AuthScreen
            # Там користувач зможе ввести дані заново або побачити помилку
            if self.controller:
                self.controller.switch_screen('auth')
