from kivy.clock import Clock
from gui.screen.BaseScreen import BaseScreen
from gui.utils.VisualEngine import VisualEngine
from gui.utils.GameAdapter import GameAdapter 
from gui.utils.GameSettings import game_settings

class PlayGameScreen(BaseScreen):
    def __init__(self, ui_manager, controller, **kwargs):
        super().__init__(ui_manager, controller, **kwargs)
        self.game_type = "DURAK"
        self.adapter = None
        self.visual_engine = None
        self.game_loop_event = None

    def on_enter(self):
        """Запускається автоматично при вході на екран"""
        self.clear_widgets()
        
        # 1. Створюємо Візуальний Двигун
        self.visual_engine = VisualEngine()
        self.visual_engine.set_callback(self.on_ui_action)
        self.visual_engine.add_common_ui(self.go_back)
        self.add_widget(self.visual_engine)

        # 2. Створюємо Адаптер
        self.adapter = GameAdapter(self.game_type)
        
        # === !!! ВАЖЛИВО: ЗВ'ЯЗУЄМО ЇХ !!! ===
        self.adapter.set_visual_engine(self.visual_engine)
        
        # 3. ЗАПУСК
        # Тепер адаптер сам керує командами через чергу, тому просто start()
        self.adapter.start()

        # 4. Таймер гри
        self.game_loop_event = Clock.schedule_interval(self.game_tick, 0.5)

    def on_leave(self):
        if self.game_loop_event:
            self.game_loop_event.cancel()
        self.adapter = None 

    def game_tick(self, dt):
        if self.adapter:
            # Тільки передаємо tick, команди обробляються автоматично в черзі адаптера
            self.adapter.process_input({'type': 'tick'})

    def on_ui_action(self, action_data):
        if self.adapter:
            self.adapter.process_input(action_data)

    def process_commands(self, commands):
        # Цей метод більше не потрібен, але залишаємо для сумісності (порожнім)
        pass

    def update_context(self, **kwargs):
        if 'game_type' in kwargs:
            self.game_type = kwargs['game_type']

    def go_back(self):
        self.controller.switch_screen('local_select')