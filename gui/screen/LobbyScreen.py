import asyncio
from kivy.uix.popup import Popup

from gui.utils.Component import GameTextInput, MenuButton

from gui.NetworkBridge import net

from gui.screen.BaseScreen import BaseScreen
from gui.config.Configs import VisualConfig
from gui.utils.Responsive import bind_responsive_width, bind_scaled_property

# --- ЕКРАН ЛОБІ (Оновлений) ---
class LobbyScreen(BaseScreen):
    def __init__(self, ui_manager, controller, **kwargs):
        super().__init__(ui_manager, controller, **kwargs)
        self.controller = controller
        self.ui = ui_manager # Локальний менеджер
        self.setup_ui()
        self.add_widget(self.ui.root)

    def setup_ui(self):
        # 1. Головний контейнер (Якір)
        self.ui.add("main_anchor", "AnchorLayout", anchor_x='center', anchor_y='center')

        # 2. Меню (стовпчик)
        self.ui.add("menu_box", "BoxLayout", 
                    parent="main_anchor",
                    orientation="vertical",
                    spacing=VisualConfig.sdp(20),
                    size_hint=(None, None),
                    width=VisualConfig.sdp(320)) # Фіксована ширина меню
        
        # Автоматична висота меню залежно від вмісту
        self.ui.widgets = self.ui.registry # Хак для доступу, або краще через build
        # Але оскільки UIManager будує все в кінці, прив'язку робимо після build()
        
        # 3. Використовуємо наші нові компоненти!
        
        # ЗАГОЛОВОК (TitleLabel вже має налаштований шрифт і колір)
        self.ui.add("logo", "TitleLabel", 
                    parent="menu_box",
                    text="КАРТКОВА ГРА")

        # КНОПКИ (MenuButton вже має розмір і стиль)
        self.ui.add("btn_create", "MenuButton", 
                    parent="menu_box", 
                    text="Створити кімнату")

        self.ui.add("btn_join", "MenuButton", 
                    parent="menu_box", 
                    text="Приєднатись")

        self.ui.add("btn_back", "MenuButton", 
                    parent="menu_box", 
                    text="Назад")
        
        # ДОДАЄМО ПРИВ'ЯЗКУ ДІЇ
        self.ui.set_action("btn_create", "on_release", self.do_create_room)
        self.ui.set_action("btn_back", "on_release", self.go_back)
        self.ui.set_action("btn_join", "on_release", self.show_join_popup)

        # Будуємо
        self.ui.build()
        
        # Хак для авто-висоти (після build об'єкти вже існують)
        box = self.ui.registry["menu_box"]
        box.bind(minimum_height=box.setter('height'))
        bind_scaled_property(box, "spacing", 20)
        bind_responsive_width(box, max_width=360, ratio=0.85, min_width=260)

    def go_back(self, instance):
        if self.controller:
            self.controller.switch_screen('main_menu')

    # --- НОВИЙ МЕТОД ---
    def do_create_room(self, instance):
        # Блокуємо кнопку, щоб не нажати двічі
        btn = self.ui.registry["btn_create"]
        btn.text = "Створення..."
        btn.disabled = True
        
        # Запускаємо асинхронний запит
        asyncio.create_task(self._process_creation(btn))

    async def _process_creation(self, btn):
        # Викликаємо метод створення
        success, result = await net.create_room()
        
        # Повертаємо кнопку в нормальний стан
        btn.text = "Створити кімнату"
        btn.disabled = False

        if success:
            room_id = result
            print(f"Перехід в кімнату {room_id}")
            
            # Отримуємо доступ до екрану гри через контролер і оновлюємо ID
            if self.controller:
                game_screen = self.controller.get_screen('game')
                game_screen.update_room_info(room_id)
                
                # Перемикаємо екран
                self.controller.switch_screen('game')
        else:
            print(f"Помилка створення: {result}")
            # Можна вивести помилку в Label, якщо хочеш

    def show_join_popup(self, instance):
        """Створює і показує вікно для вводу ID"""
        
        # 1. Вміст вікна (вертикальний бокс)
        from kivy.uix.boxlayout import BoxLayout
        content = BoxLayout(
            orientation='vertical',
            spacing=VisualConfig.sdp(10),
            padding=VisualConfig.sdp(10),
        )
        
        self.join_input = GameTextInput(hint_text="Введіть ID кімнати (напр. 1234)", multiline=False)
        
        # 3. Кнопки
        btn_go = MenuButton(text="Увійти")
        btn_cancel = MenuButton(text="Скасувати")
        
        content.add_widget(self.join_input)
        content.add_widget(btn_go)
        content.add_widget(btn_cancel)

        # 4. Самі вікно
        self.popup = Popup(title='Приєднатися до гри',
                           content=content,
                           size_hint=(None, None),
                           size=(VisualConfig.sdp(300), VisualConfig.sdp(200)),
                           auto_dismiss=False)

        # 5. Дії
        btn_go.bind(on_release=self.do_join_room)
        btn_cancel.bind(on_release=self.popup.dismiss)
        
        self.popup.open()

    def do_join_room(self, instance):
        room_id = self.join_input.text.strip()
        if not room_id:
            return

        # Блокуємо кнопку, щоб не спамити
        instance.text = "..."
        instance.disabled = True

        # Запускаємо асинхронний процес
        asyncio.create_task(self._process_join(room_id, instance))

    async def _process_join(self, room_id, btn_instance):
        success, message = await net.join_room(room_id)
        print(success)
        print(message)
        
        if success:
            print(f"Приєднано до {room_id}")
            self.popup.dismiss() # Закриваємо вікно
            
            # Переходимо в гру
            if self.controller:
                game_screen = self.controller.get_screen('game')
                game_screen.update_room_info(room_id)
                self.controller.switch_screen('game')
        else:
            # Якщо помилка - повертаємо кнопку і показуємо помилку в полі
            btn_instance.text = "Увійти"
            btn_instance.disabled = False
            self.join_input.text = ""
            self.join_input.hint_text = f"Помилка: {message}"
