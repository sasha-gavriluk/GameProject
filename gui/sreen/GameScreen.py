import asyncio

from kivy.metrics import dp
from gui.NetworkBridge import net
from gui.sreen.BaseScreen import BaseScreen

class GameScreen(BaseScreen):
    def __init__(self, ui_manager, controller, **kwargs):
        super().__init__(ui_manager, controller, **kwargs)
        self.controller = controller
        self.ui = ui_manager
        self.room_id = None
        self.setup_ui()
        self.add_widget(self.ui.root)

    def setup_ui(self):
        # 1. Головний контейнер (Якір)
        self.ui.add("game_anchor", "AnchorLayout", anchor_x='center', anchor_y='center')

        # 2. Вертикальний бокс на весь екран (з відступами)
        self.ui.add("main_box", "BoxLayout", 
                    parent="game_anchor",
                    orientation="vertical",
                    spacing=dp(10),
                    padding=dp(20),
                    size_hint=(1, 1)) # На весь екран

        # === ВЕРХНЯ ЧАСТИНА: ІНФО ПРО КІМНАТУ ===
        self.ui.add("info_box", "BoxLayout", 
                    parent="main_box", 
                    orientation="vertical", 
                    size_hint_y=None, 
                    height=dp(100))
        
        self.ui.add("lbl_room_title", "TitleLabel", parent="info_box", text="КІМНАТА", font_size="20sp", height=dp(30))
        self.ui.add("lbl_room_id", "Label", parent="info_box", text="---", font_size="40sp", bold=True, color=(0, 1, 0, 1))

        # === СЕРЕДНЯ ЧАСТИНА: ЧАТ (SCROLLVIEW) ===
        # Створюємо фон для чату (можна через canvas, але поки просто контейнер)
        
        # ScrollView потребує size_hint
        self.ui.add("chat_scroll", "ScrollView", 
                    parent="main_box", 
                    size_hint=(1, 1), # Займає весь вільний простір
                    do_scroll_x=False)

        # Всередині ScrollView має бути один віджет, що розтягується по висоті
        # Ми використаємо Label, у якого text_size=(width, None) для переносу слів
        self.ui.add("chat_log", "Label",
                    # parent="chat_scroll", <-- UIManager поки не вміє додавати напряму в ScrollView через add()
                    # Тому ми додамо його вручну після build, або використаємо BoxLayout всередині
                    text="Чат розпочато...\n",
                    font_size="16sp",
                    halign="left",
                    valign="bottom",
                    markup=True,
                    size_hint_y=None) # Висота буде змінюватись динамічно
        
        # === НИЖНЯ ЧАСТИНА: ВВІД ПОВІДОМЛЕННЯ ===
        self.ui.add("input_box", "BoxLayout", 
                    parent="main_box", 
                    orientation="horizontal", 
                    spacing=dp(10), 
                    size_hint_y=None, 
                    height=dp(50))

        self.ui.add("inp_chat", "GameTextInput", 
                    parent="input_box", 
                    hint_text="Написати повідомлення...",
                    size_hint_x=0.8)

        self.ui.add("btn_send", "MenuButton", 
                    parent="input_box", 
                    text="->", 
                    size_hint_x=0.2) # Маленька кнопка

        # === ПІДВАЛ: КНОПКИ УПРАВЛІННЯ ===
        self.ui.add("controls_box", "BoxLayout", 
                    parent="main_box", 
                    orientation="horizontal", 
                    spacing=dp(20), 
                    size_hint_y=None, 
                    height=dp(60))

        self.ui.add("btn_start", "MenuButton", parent="controls_box", text="Почати гру", disabled=True)
        self.ui.add("btn_leave", "MenuButton", parent="controls_box", text="Вийти")

        # === ДІЇ ===
        self.ui.set_action("btn_send", "on_release", self.send_message)
        self.ui.set_action("inp_chat", "on_text_validate", self.send_message) # Enter теж відправляє
        self.ui.set_action("btn_leave", "on_release", self.leave_room)

        self.ui.build()

        # === РУЧНІ ПРИВ'ЯЗКИ (Те, що складніше через UIManager) ===
        
        # 1. Додаємо chat_log в chat_scroll
        scroll = self.ui.registry["chat_scroll"]
        chat_label = self.ui.registry["chat_log"]
        
        # ВАЖЛИВО: Спочатку видаляємо його зі старого місця (FloatLayout/root), 
        # куди його помилково додав UIManager
        if chat_label.parent:
            chat_label.parent.remove_widget(chat_label)
            
        # Тепер безпечно додаємо в скрол
        scroll.add_widget(chat_label)

        # 2. Налаштування розтягування тексту чату
        chat_label.bind(width=lambda *x: chat_label.setter('text_size')(chat_label, (chat_label.width, None)))
        chat_label.bind(texture_size=lambda *x: chat_label.setter('height')(chat_label, chat_label.texture_size[1]))

        # 3. Налаштування кнопки вводу
        self.ui.registry["inp_chat"].multiline = False

    def update_room_info(self, room_id):
        self.room_id = room_id
        self.ui.registry["lbl_room_id"].text = str(room_id)
        self.add_chat_message("System", f"Ви увійшли в кімнату {room_id}")

    def send_message(self, instance):
        inp = self.ui.registry["inp_chat"]
        text = inp.text
        if not text: return

        asyncio.create_task(net.send_chat(text))

        # 2. Очищаємо поле
        inp.text = ""
        # Повертаємо фокус (по бажанню)
        # inp.focus = True 

    def add_chat_message(self, author, text):
        """Додає повідомлення в лог"""
        chat_lbl = self.ui.registry["chat_log"]
        
        # Форматуємо: Жирний автор, звичайний текст
        color_hex = "00ff00" if author == "System" else "ffff00" # Зелений для системи, Жовтий для гравців
        new_line = f"[color={color_hex}][b]{author}:[/b][/color] {text}\n"
        
        chat_lbl.text += new_line
        
        # Автопрокрутка вниз
        scroll = self.ui.registry["chat_scroll"]
        scroll.scroll_y = 0 

    def leave_room(self, instance):
        if self.controller:
            self.controller.switch_screen('lobby')
            self.ui.registry["chat_log"].text = "" # Очистити чат при виході

    def on_enter(self, *args):
        # Запускаємо слухача і кажемо йому: "Всі нові повідомлення кидай в self.handle_server_message"
        net.start_listener(self.handle_server_message)

    # Цей метод викликається, коли ми йдемо з екрану
    def on_leave(self, *args):
        net.stop_listener()

    def handle_server_message(self, data):
        """Обробка вхідних повідомлень від сервера"""
        # print(f"[GameScreen] Отримано: {data}") # Розкоментуй для дебагу
        
        msg_type = data.get("type")
        
        # === ПРАВКА: Слухаємо SEND_MESSAGE ===
        if msg_type == "SEND_MESSAGE" or msg_type == "CHAT_MESSAGE": 
            # (Залишив CHAT_MESSAGE про всяк випадок, але сервер шле SEND_MESSAGE)
            
            payload = data.get("payload", data) # Іноді payload всередині, іноді дані плоскі
            
            # Сервер надсилає username і message на верхньому рівні (у data)
            author = data.get("username") or payload.get("username") or "Unknown"
            
            # Сервер надсилає 'message', але join_room може слати 'text'
            text = data.get("message") or data.get("text") or payload.get("message")
            
            if text:
                self.add_chat_message(author, text)

        # Обробка інших подій (наприклад, початок гри) може бути тут