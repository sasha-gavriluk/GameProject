import asyncio
from collections import deque

from kivy.clock import Clock
from gui.screen.BaseScreen import BaseScreen
from gui.utils.VisualEngine import VisualEngine
from gui.utils.GameAdapter import GameAdapter 
from gui.NetworkBridge import net

class PlayGameScreen(BaseScreen):
    use_screen_background = False

    def __init__(self, ui_manager, controller, **kwargs):
        super().__init__(ui_manager, controller, **kwargs)
        self.game_type = "DURAK"
        self.online_mode = False
        self.room_id = None
        self.adapter = None
        self.visual_engine = None
        self.game_loop_event = None
        self.online_queue = deque()
        self.online_busy = False

    def on_enter(self):
        """Запускається автоматично при вході на екран"""
        self.clear_widgets()
        
        # 1. Створюємо Візуальний Двигун
        self.visual_engine = VisualEngine()
        self.visual_engine.set_callback(self.on_ui_action)
        self.visual_engine.go_back_callback = self.go_back
        self.add_widget(self.visual_engine)

        # ONLINE: клієнт лише рендерить серверні інструкції.
        if self.online_mode:
            self.adapter = None
            # Важливо: не чистимо online_queue тут, бо частина інструкцій
            # може прилетіти ще до on_enter (під час переходу з Lobby).
            self.online_busy = False
            net.start_listener(self.on_network_message)
            # Якщо щось уже в черзі — відпрацюємо одразу.
            self._drain_online_queue()
            # Страховка від втрати пакетів при переході екранів.
            asyncio.create_task(net.request_game_snapshot())
            return

        # LOCAL: повна логіка в клієнті (як і було раніше).
        self.adapter = GameAdapter(self.game_type)
        self.adapter.set_visual_engine(self.visual_engine)
        self.adapter.start()
        self.game_loop_event = Clock.schedule_interval(self.game_tick, 0.5)

    def on_leave(self):
        if self.game_loop_event:
            self.game_loop_event.cancel()
            self.game_loop_event = None
        self.adapter = None 

    def game_tick(self, dt):
        if self.adapter:
            # Тільки передаємо tick, команди обробляються автоматично в черзі адаптера
            self.adapter.process_input({'type': 'tick'})

    def on_ui_action(self, action_data):
        if self.online_mode:
            # Сервер-авторитет: надсилаємо лише намір дії.
            net_payload = {
                "action": action_data.get("action"),
                "cards": action_data.get("cards", []),
                "suit": action_data.get("suit"),
                "choice": action_data.get("choice"),
            }
            # Прибираємо порожні поля.
            net_payload = {k: v for k, v in net_payload.items() if v is not None and v != []}
            net_payload["type"] = "ui_action"
            Clock.schedule_once(lambda *_: asyncio.create_task(net.send_game_action(net_payload)), 0)
            return
        if self.adapter:
            self.adapter.process_input(action_data)

    def process_commands(self, commands):
        # Цей метод більше не потрібен, але залишаємо для сумісності (порожнім)
        pass

    def update_context(self, **kwargs):
        if 'game_type' in kwargs:
            self.game_type = kwargs['game_type']
        if 'online' in kwargs:
            self.online_mode = bool(kwargs['online'])
        if 'room_id' in kwargs:
            self.room_id = kwargs['room_id']

    def on_network_message(self, data):
        msg_type = data.get("type")
        if msg_type == "GAME_INSTRUCTION":
            instruction = data.get("instruction")
            if instruction:
                self.online_queue.append(instruction)
                self._drain_online_queue()
        elif msg_type == "GAME_BATCH":
            for instruction in data.get("instructions", []):
                self.online_queue.append(instruction)
            self._drain_online_queue()
        elif msg_type == "GAME_ERROR":
            print(f"[OnlineGame] {data.get('message', 'Невідома помилка')}")
        elif msg_type == "SEND_MESSAGE":
            # Ігровий чат/системні повідомлення можна показати окремо (за потреби).
            pass

    def _drain_online_queue(self):
        if self.online_busy or not self.online_queue or not self.visual_engine:
            return
        instruction = self.online_queue.popleft()
        self.online_busy = True
        self.visual_engine.execute_instruction(instruction, on_complete=self._on_online_instruction_done)

    def _on_online_instruction_done(self):
        self.online_busy = False
        self._drain_online_queue()

    def go_back(self):
        if self.online_mode:
            net.stop_listener()
            self.controller.switch_screen('room_entry')
            return
        self.controller.switch_screen('local_select')
