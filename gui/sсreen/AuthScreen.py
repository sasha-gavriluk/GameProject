import asyncio

from kivy.metrics import dp

from gui.utils.GameSettings import game_settings
from gui.sсreen.BaseScreen import BaseScreen
from gui.NetworkBridge import net

class AuthScreen(BaseScreen):
    def __init__(self, ui_manager, controller, **kwargs):
        super().__init__(ui_manager, controller, **kwargs)
        # BaseScreen вже викликає build_ui, але ми перевизначимо логіку ініціалізації тут,
        # якщо треба щось специфічне, або просто використаємо setup_ui як в інших.
        # Для однотипності краще використовувати структуру як в LobbyScreen:
        self.controller = controller
        self.ui = ui_manager
        self.setup_ui()
        self.add_widget(self.ui.root)

    def setup_ui(self):
        # 1. Якір по центру
        self.ui.add("auth_anchor", "AnchorLayout", anchor_x='center', anchor_y='center')

        # 2. Контейнер (вертикальний стовпчик)
        self.ui.add("auth_box", "BoxLayout", 
                    parent="auth_anchor",
                    orientation="vertical",
                    spacing=dp(15),       # Відступ між елементами
                    size_hint=(None, None),
                    width=dp(300))

        # 3. Заголовок
        self.ui.add("lbl_title", "TitleLabel", parent="auth_box", text="ВХІД")

        # 4. Поля вводу
        # Логін (підтягуємо збережений з налаштувань)
        saved_login = game_settings.login
        self.ui.add("inp_login", "GameTextInput", 
                    parent="auth_box", 
                    hint_text="Логін", 
                    text=saved_login,
                    write_tab=False) # Щоб Tab перемикав фокус (потрібна додаткова логіка, але поки так)

        # Пароль (password=True ховає символи)
        self.ui.add("inp_pass", "GameTextInput", 
                    parent="auth_box", 
                    hint_text="Пароль", 
                    password=True,
                    write_tab=False)

        # 5. Кнопки
        self.ui.add("btn_enter", "MenuButton", parent="auth_box", text="Вхід")
        self.ui.add("btn_reg", "MenuButton", parent="auth_box", text="Реєстрація")
        
        # Додаткова кнопка "Назад", щоб не застрягти
        self.ui.add("btn_back", "MenuButton", parent="auth_box", text="Назад")

        # 6. Дії
        self.ui.set_action("btn_enter", "on_release", self.do_login)
        self.ui.set_action("btn_reg", "on_release", self.do_register)
        self.ui.set_action("btn_back", "on_release", self.go_back)

        self.ui.build()
        
        # Авто-висота контейнера
        box = self.ui.registry["auth_box"]
        box.bind(minimum_height=box.setter('height'))

    def do_login(self, instance):
        login_val = self.ui.registry["inp_login"].text
        pass_val = self.ui.registry["inp_pass"].text

        if not login_val: return

        # 1. Спочатку зберігаємо введені дані в Settings (вони там зашифруються)
        game_settings.login = login_val
        game_settings.password = pass_val 

        # 2. Блокуємо кнопку, показуємо статус
        btn = self.ui.registry["btn_enter"]
        btn.text = "..."
        btn.disabled = True

        # 3. Пробуємо підключитись
        asyncio.create_task(self._process_auth(btn))

    async def _process_auth(self, btn):
        success, message = await net.connect_and_login()
        
        btn.text = "Вхід"
        btn.disabled = False

        if success:
            if self.controller: self.controller.switch_screen('lobby')
        else:
            # Тут можна показати Popup з помилкою (пізніше зробимо)
            print(f"LOGIN FAILED: {message}")
            # Тимчасово змінимо текст заголовка на помилку
            self.ui.registry["lbl_title"].text = "ПОМИЛКА ВХОДУ"
            self.ui.registry["lbl_title"].color = (1, 0, 0, 1) # Червоний

    def do_register(self, instance):
        # 1. Беремо дані прямо з полів (не з налаштувань!)
        login_val = self.ui.registry["inp_login"].text
        pass_val = self.ui.registry["inp_pass"].text

        if not login_val or not pass_val:
            self.ui.registry["lbl_title"].text = "Введіть логін і пароль!"
            self.ui.registry["lbl_title"].color = (1, 0, 0, 1)
            return

        print(f"Кнопка натиснута. Реєструємо: {login_val}")

        # 2. Блокуємо інтерфейс
        btn = self.ui.registry["btn_reg"]
        btn.text = "..."
        btn.disabled = True

        # 3. Запускаємо процес
        asyncio.create_task(self._process_register(btn, login_val, pass_val))

    async def _process_register(self, btn, login, password):
        # Викликаємо оновлений метод
        success, message = await net.register(login, password)
        
        btn.text = "Реєстрація"
        btn.disabled = False

        if success:
            print(f"Реєстрація ОК: {message}")
            self.ui.registry["lbl_title"].text = "Успішно! Тепер увійдіть"
            self.ui.registry["lbl_title"].color = (0, 1, 0, 1) # Зелений
            
            # Можна автоматично зберегти логін в налаштування для зручності
            from utils.GameSettings import game_settings
            game_settings.login = login
            # Пароль краще не зберігати при реєстрації, нехай введе для входу, 
            # або зберегти, якщо хочеш авто-вхід відразу.
        else:
            print(f"Реєстрація Fail: {message}")
            self.ui.registry["lbl_title"].text = str(message)
            self.ui.registry["lbl_title"].color = (1, 0, 0, 1) # Червоний

    def go_back(self, instance):
        if self.controller:
            self.controller.switch_screen('main_menu')