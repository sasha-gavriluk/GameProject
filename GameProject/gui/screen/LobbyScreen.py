import asyncio
from kivy.clock import Clock

from gui.screen.BaseScreen import BaseScreen
from gui.NetworkBridge import net
from gui.utils.GameSettings import game_settings
from gui.config.Configs import VisualConfig

# ==========================================
# 1. ПОПАП: НАЛАШТУВАННЯ КІМНАТИ (Таймер)
# ==========================================
class RoomSettingsDialog:
    def __init__(self, lobby_screen):
        self.lobby = lobby_screen
        self.ui = lobby_screen.ui
        
        # Створюємо контент
        self.layout = self.ui.dynamic.create("BoxLayout", orientation='vertical', padding=20, spacing=15)
        self.layout.add_widget(self.ui.dynamic.create("Label", text="Зворотній відлік (сек):", font_size=VisualConfig.ssp(20), size_hint_y=None, height=VisualConfig.sdp(30)))
        
        self.time_row = self.ui.dynamic.create("BoxLayout", orientation='horizontal', spacing=10, size_hint_y=None, height=VisualConfig.sdp(50))
        self.time_btns = {
            3: self.ui.dynamic.create("GameToggleButton", text="3", group="timer"),
            5: self.ui.dynamic.create("GameToggleButton", text="5", group="timer", state="down"),
            10: self.ui.dynamic.create("GameToggleButton", text="10", group="timer")
        }
        for val, btn in self.time_btns.items():
            btn.bind(on_release=lambda instance, v=val: self._on_change(v))
            self.time_row.add_widget(btn)
        
        self.layout.add_widget(self.time_row)
        
        # Використовуємо MenuButton для фіксованого оригінального розміру
        btn_close = self.ui.dynamic.create("MenuButton", text="Закрити")
        self.layout.add_widget(btn_close)
        
        # Використовуємо Popup замість ModalView
        self.view = self.ui.dynamic.create("GamePopup", title="Налаштування кімнати", content=self.layout, size_hint=(0.6, 0.4), auto_dismiss=True)
        btn_close.bind(on_release=self.view.dismiss)

    def _on_change(self, val):
        if not self.lobby.is_host: return
        self.lobby.settings["countdown"] = val
        self.lobby.send_settings_update()

    def update_ui(self, countdown):
        if countdown in self.time_btns:
            self.time_btns[countdown].state = "down"
        disabled = not self.lobby.is_host
        for btn in self.time_btns.values():
            btn.disabled = disabled

    def open(self):
        self.view.open()

# ==========================================
# 2. ПОПАП: НАЛАШТУВАННЯ САМОЇ ГРИ
# ==========================================
class GameSettingsDialog:
    def __init__(self, lobby_screen):
        self.lobby = lobby_screen
        self.ui = lobby_screen.ui
        
        self.layout = self.ui.dynamic.create("BoxLayout", orientation='vertical', padding=20, spacing=10)
        
        self.lbl_title = self.ui.dynamic.create("Label", font_size=VisualConfig.ssp(22), size_hint_y=None, height=VisualConfig.sdp(40))
        self.layout.add_widget(self.lbl_title)
        
        # Контейнер для динамічних налаштувань
        self.settings_container = self.ui.dynamic.create("BoxLayout", orientation='vertical', spacing=10)
        self.layout.add_widget(self.settings_container)
        
        btn_close = self.ui.dynamic.create("MenuButton", text="Закрити")
        self.layout.add_widget(btn_close)
        
        self.view = self.ui.dynamic.create("GamePopup", title="Налаштування гри", content=self.layout, size_hint=(0.8, 0.65), auto_dismiss=True)
        btn_close.bind(on_release=self.view.dismiss)

        # ПОПЕРЕДНЄ СТВОРЕННЯ КНОПОК
        self.durak_mode_btns = {
            "podkidnoy": self.ui.dynamic.create("GameToggleButton", text="Підкидний", group="durak_mode"),
            "perevodnoy": self.ui.dynamic.create("GameToggleButton", text="Перевідний", group="durak_mode"),
            "mixed": self.ui.dynamic.create("GameToggleButton", text="Змішаний", group="durak_mode")
        }
        for k, btn in self.durak_mode_btns.items():
            btn.bind(on_release=lambda instance, val=k: self._on_mode_change(val))

        self.deck_size_btns = {
            36: self.ui.dynamic.create("GameToggleButton", text="36 карт", group="deck_size"),
            52: self.ui.dynamic.create("GameToggleButton", text="52 карти", group="deck_size")
        }
        for k, btn in self.deck_size_btns.items():
            btn.bind(on_release=lambda instance, val=k: self._on_deck_change(val))

        self.bridge_lbl = self.ui.dynamic.create("Label", text="Використовується стандартна колода 52 карти.", font_size=VisualConfig.ssp(18))

    def _on_mode_change(self, val):
        if not self.lobby.is_host: return
        self.lobby.settings["durak_mode"] = val
        self.lobby.send_settings_update()

    def _on_deck_change(self, val):
        if not self.lobby.is_host: return
        self.lobby.settings["deck_size"] = val
        self.lobby.send_settings_update()

    @staticmethod
    def _move_btn_to_row(btn, row):
        # При clear_widgets() у батька кнопки можуть лишитись "прив'язаними" до старого row.
        if btn.parent and btn.parent is not row:
            btn.parent.remove_widget(btn)
        if btn.parent is not row:
            row.add_widget(btn)

    def update_ui(self):
        self.settings_container.clear_widgets()
        game_type = self.lobby.settings.get("game_type", "DURAK")
        
        self.lbl_title.text = f"Налаштування: {game_type}"
        self.view.title = f"Налаштування: {game_type}"

        disabled = not self.lobby.is_host

        if game_type == "DURAK":
            self.settings_container.add_widget(self.ui.dynamic.create("Label", text="Режим гри:", size_hint_y=None, height=VisualConfig.sdp(30), font_size=VisualConfig.ssp(18)))
            row_mode = self.ui.dynamic.create("BoxLayout", orientation='horizontal', spacing=10, size_hint_y=None, height=VisualConfig.sdp(50))
            current_mode = self.lobby.settings.get("durak_mode", "mixed")
            for k, btn in self.durak_mode_btns.items():
                btn.disabled = disabled
                btn.state = "down" if k == current_mode else "normal"
                self._move_btn_to_row(btn, row_mode)
            self.settings_container.add_widget(row_mode)

        if game_type in ["DURAK", "WAR"]:
            self.settings_container.add_widget(self.ui.dynamic.create("Label", text="Колода:", size_hint_y=None, height=VisualConfig.sdp(30), font_size=VisualConfig.ssp(18)))
            row_deck = self.ui.dynamic.create("BoxLayout", orientation='horizontal', spacing=10, size_hint_y=None, height=VisualConfig.sdp(50))
            current_deck = self.lobby.settings.get("deck_size", 36)
            for k, btn in self.deck_size_btns.items():
                btn.disabled = disabled
                btn.state = "down" if k == current_deck else "normal"
                self._move_btn_to_row(btn, row_deck)
            self.settings_container.add_widget(row_deck)

        if game_type == "BRIDGE":
            self.settings_container.add_widget(self.bridge_lbl)

    def open(self):
        self.update_ui()
        self.view.open()

# ==========================================
# 3. ГОЛОВНИЙ ЕКРАН ЛОББІ
# ==========================================
class LobbyScreen(BaseScreen):
    def __init__(self, ui_manager, controller, **kwargs):
        self.is_host = False
        self.room_id = None
        self.settings = {"game_type": "DURAK", "countdown": 5, "durak_mode": "mixed", "deck_size": 36}
        super().__init__(ui_manager, controller, **kwargs)

    def build_ui(self):
        self.room_settings_dialog = RoomSettingsDialog(self)
        self.game_settings_dialog = GameSettingsDialog(self)
        self._build_in_room_ui()

    # --- СТАН 2: В СЕРЕДИНІ КІМНАТИ (ВЕРТИКАЛЬНИЙ ДИЗАЙН) ---
    def _build_in_room_ui(self):
        self.in_room_layout = self.ui.dynamic.create("FloatLayout")
        
        # Топ: Ім'я та Ключ кімнати
        self.lbl_name = self.ui.dynamic.create("Label", text="", font_size=VisualConfig.ssp(18), pos_hint={'x': 0.02, 'top': 0.98}, size_hint=(0.4, 0.1), halign='left')
        self.lbl_name.bind(size=lambda s, w: setattr(s, 'text_size', w))
        
        self.lbl_room_id = self.ui.dynamic.create("Label", text="", font_size=VisualConfig.ssp(22), color=(0, 1, 0, 1), bold=True, pos_hint={'center_x': 0.5, 'top': 0.98}, size_hint=(0.4, 0.1))
        
        self.in_room_layout.add_widget(self.lbl_name)
        self.in_room_layout.add_widget(self.lbl_room_id)

        # ЦЕНТР: Вертикальне розділення
        main_box = self.ui.dynamic.create("BoxLayout", orientation='vertical', size_hint=(0.96, 0.74), pos_hint={'center_x': 0.5, 'top': 0.87}, spacing=15)
        
        # --- ВЕРХНЯ ПОЛОВИНА: Дії та гравці ---
        top_panel = self.ui.dynamic.create("BoxLayout", orientation='vertical', size_hint_y=0.48, spacing=10)
        
        # 3 кнопки ігор
        self.game_toggles_box = self.ui.dynamic.create("GridLayout", cols=3, size_hint_y=None, height=VisualConfig.sdp(50), spacing=10)
        self.game_btns = {
            "DURAK": self.ui.dynamic.create("GameToggleButton", text="Дурак", group="main_game", state="down"),
            "BRIDGE": self.ui.dynamic.create("GameToggleButton", text="Брідж", group="main_game"),
            "WAR": self.ui.dynamic.create("GameToggleButton", text="Війна", group="main_game")
        }
        for k, btn in self.game_btns.items():
            btn.bind(on_release=lambda instance, val=k: self._on_game_change(val))
            self.game_toggles_box.add_widget(btn)
        top_panel.add_widget(self.game_toggles_box)
        
        # Кнопка Налаштування гри
        btn_game_settings = self.ui.dynamic.create("GameButton", text="Налаштування гри", size_hint_y=None, height=VisualConfig.sdp(50))
        btn_game_settings.bind(on_release=lambda x: self.game_settings_dialog.open())
        top_panel.add_widget(btn_game_settings)
        
        # Список гравців: в один ряд з переносом на новий, якщо не влазять
        self.players_box = self.ui.dynamic.create("BoxLayout", orientation='vertical', size_hint_y=0.5, spacing=VisualConfig.sdp(6))
        self.players_title = self.ui.dynamic.create("Label", text="Гравці:", font_size=VisualConfig.ssp(20), size_hint_y=None, height=VisualConfig.sdp(30), bold=True)
        self.players_wrap = self.ui.dynamic.create(
            "StackLayout",
            orientation='lr-tb',
            size_hint=(1, 1),
            spacing=(VisualConfig.sdp(8), VisualConfig.sdp(8)),
            padding=(0, 0, 0, 0)
        )
        self.players_box.add_widget(self.players_title)
        self.players_box.add_widget(self.players_wrap)
        top_panel.add_widget(self.players_box)
        
        main_box.add_widget(top_panel)
        
        # --- НИЖНЯ ПОЛОВИНА: Чат (Ваші компоненти) ---
        bottom_panel = self.ui.dynamic.create("ChatSurface", orientation='vertical', size_hint_y=0.7, spacing=VisualConfig.sdp(8))
        
        self.chat_history = self.ui.dynamic.create("ChatHistoryLabel")
        
        self.chat_scroll = self.ui.dynamic.create("ChatScrollView", size_hint_y=1)
        self.chat_scroll.add_widget(self.chat_history)
        bottom_panel.add_widget(self.chat_scroll)
        
        # Контейнер вводу чату тепер має фіксовану висоту (щоб не розтягувати TextInput)
        chat_input_box = self.ui.dynamic.create("ChatSurface", size_hint_y=0.2, padding=(VisualConfig.sdp(6), VisualConfig.sdp(6), VisualConfig.sdp(6), VisualConfig.sdp(6)))
        self.chat_input = self.ui.dynamic.create("ChatTextInput", hint_text="Повідомлення...") # size_hint_y=0.2 прибрано
        self.chat_input.bind(on_text_validate=self.send_msg)
        btn_send = self.ui.dynamic.create("GameButton", text="Надіслати", size_hint_x=0.3)
        btn_send.bind(on_release=self.send_msg)
        chat_input_box.add_widget(self.chat_input)
        chat_input_box.add_widget(btn_send)
        bottom_panel.add_widget(chat_input_box)
        
        main_box.add_widget(bottom_panel)
        self.in_room_layout.add_widget(main_box)
        
        # --- НИЗ: 3 Кнопки ---
        bottom_bar = self.ui.dynamic.create("BoxLayout", orientation='horizontal', size_hint=(0.96, None), height=VisualConfig.sdp(60), pos_hint={'center_x': 0.5, 'y': 0.02}, spacing=10)
        
        btn_room_settings = self.ui.dynamic.create("MenuButton", text="Налаш. кімнати")
        btn_room_settings.bind(on_release=lambda x: self.room_settings_dialog.open())
        
        self.btn_action = self.ui.dynamic.create("MenuButton", text="Готовий")
        self.btn_action.bind(on_release=self._on_action_click)
        
        btn_leave = self.ui.dynamic.create("MenuButton", text="Вийти", background_color=(0.8, 0.2, 0.2, 1))
        btn_leave.bind(on_release=self.leave_room)
        
        bottom_bar.add_widget(btn_room_settings)
        bottom_bar.add_widget(self.btn_action)
        bottom_bar.add_widget(btn_leave)
        
        self.in_room_layout.add_widget(bottom_bar)

    # --- ЛОГІКА ---
    def on_enter(self, *args):
        if not self.children:
            self.add_widget(self.in_room_layout)

    def update_context(self, room_id=None, **kwargs):
        if room_id:
            self.switch_to_room(room_id)

    def switch_to_room(self, room_id):
        self.room_id = room_id
        self.lbl_room_id.text = f"Ключ: {room_id}"
        self.lbl_name.text = f"Ім'я: {game_settings.login}"
        self.clear_widgets()
        self.add_widget(self.in_room_layout)
        self.chat_history.text = ""
        net.start_listener(self.on_network_message)
        asyncio.create_task(net._send_only("GET_ROOM_STATE", {}))

    def _on_game_change(self, val):
        if not self.is_host: return
        self.settings["game_type"] = val
        self.send_settings_update()

    def _set_action_button_palette(self, base_rgba):
        # Міняємо палітру кастомної кнопки, а не background_color Kivy Button.
        r, g, b, a = base_rgba
        self.btn_action._idle_bg = (r, g, b, a)
        self.btn_action._hover_bg = (min(1, r + 0.08), min(1, g + 0.08), min(1, b + 0.08), a)
        self.btn_action._down_bg = (max(0, r - 0.08), max(0, g - 0.08), max(0, b - 0.08), a)
        self.btn_action._redraw()

    def send_settings_update(self):
        asyncio.create_task(net._send_only("UPDATE_SETTINGS", {"settings": self.settings}))

    def on_network_message(self, data):
        msg_type = data.get("type")
        if msg_type == "ROOM_STATE":
            self.update_room_ui(data)
        elif msg_type == "SEND_MESSAGE":
            user = data.get("username", "Unknown")
            msg = data.get("message", "")
            self.chat_history.append_message(user, msg)
            Clock.schedule_once(lambda *_: setattr(self.chat_scroll, "scroll_y", 0), 0)
        elif msg_type == "GAME_STARTED":
            pass # Перехід до гри буде тут

    def update_room_ui(self, data):
        host = data.get("host")
        players = data.get("players", {})
        self.settings = data.get("settings", {})
        my_name = game_settings.login

        self.is_host = (my_name == host)
        
        # Синхронізація кнопок вибору гри
        game_type = self.settings.get("game_type", "DURAK")
        if game_type in self.game_btns:
            self.game_btns[game_type].state = "down"
            
        # Блокуємо кнопки, якщо це не Голова
        is_disabled = not self.is_host
        for btn in self.game_btns.values():
            btn.disabled = is_disabled

        # Оновлення списку гравців
        self.players_wrap.clear_widgets()
        
        all_ready = True
        for name, state in players.items():
            status = "Готовий" if state.get("ready") else "Не готовий"
            if not state.get("ready") and name != host: all_ready = False
            role = "(Головний)" if name == host else ""
            player_lbl = self.ui.dynamic.create(
                "Label",
                text=f"{name} {role} - {status}",
                font_size=VisualConfig.ssp(16),
                size_hint=(None, None),
                width=VisualConfig.sdp(260),
                height=VisualConfig.sdp(34),
                halign='left',
                valign='middle'
            )
            player_lbl.bind(size=lambda s, w: setattr(s, 'text_size', w))
            self.players_wrap.add_widget(player_lbl)

        # Логіка Центральної Кнопки ("Почати" або "Готовий")
        if self.is_host:
            self.btn_action.text = "Почати гру"
            self.btn_action.disabled = not all_ready
            self._set_action_button_palette((0.2, 0.8, 0.2, 1) if all_ready else (0.5, 0.5, 0.5, 1))
        else:
            am_i_ready = players.get(my_name, {}).get("ready", False)
            self.btn_action.text = "Не готовий" if am_i_ready else "Готовий"
            self._set_action_button_palette((0.8, 0.8, 0.2, 1) if am_i_ready else (0.2, 0.8, 0.2, 1))
            self.btn_action.disabled = False

        self.room_settings_dialog.update_ui(self.settings.get("countdown", 5))

    def _on_action_click(self, instance):
        if self.is_host:
            asyncio.create_task(net._send_only("START_GAME", {}))
        else:
            asyncio.create_task(net._send_only("READY_TOGGLE", {}))

    def send_msg(self, instance):
        msg = self.chat_input.text.strip()
        if msg:
            asyncio.create_task(net.send_chat(msg))
            self.chat_input.text = ""

    def leave_room(self, instance):
        net.stop_listener()
        net.close()
        self.controller.switch_screen('room_entry')
