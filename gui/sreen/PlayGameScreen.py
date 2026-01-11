from kivy.clock import Clock
from gui.sreen.BaseScreen import BaseScreen
from gui.utils.VisualEngine import VisualEngine

# Імпортуємо наш новий адаптер (який ми створили раніше)
from gui.utils.GameAdapter import GameAdapter 

class PlayGameScreen(BaseScreen):
    def __init__(self, ui_manager, controller, **kwargs):
        super().__init__(ui_manager, controller, **kwargs)
        self.game_type = "DURAK"  # Дефолтний тип
        self.adapter = None       # Логіка (API)
        self.visual_engine = None # Картинка
        self.game_loop_event = None

    def on_enter(self):
        """Запускається автоматично при вході на екран"""
        self.clear_widgets()
        
        # 1. Створюємо Візуальний Двигун (пустий)
        self.visual_engine = VisualEngine()
        # Кажемо йому: "Коли гравець щось тицяє, гукай мене (метод on_ui_action)"
        self.visual_engine.set_callback(self.on_ui_action)
        self.visual_engine.add_common_ui(self.go_back)
        self.add_widget(self.visual_engine)

        # 2. Створюємо Адаптер (Логіку)
        # Він підготує правила, створить гравців і колоду
        self.adapter = GameAdapter(self.game_type)
        
        # 3. ЗАПУСК!
        # Адаптер повертає список перших команд (наприклад: SETUP_TABLE, SYNC_HANDS)
        start_commands = self.adapter.start()
        self.process_commands(start_commands)

        # 4. Запускаємо таймер гри (60 разів на секунду або рідше)
        # Це потрібно, щоб боти могли "думати" в реальному часі
        self.game_loop_event = Clock.schedule_interval(self.game_tick, 0.5)

    def on_leave(self):
        """При виході з екрану зупиняємо все"""
        if self.game_loop_event:
            self.game_loop_event.cancel()
        self.adapter = None # Очищаємо пам'ять

    def game_tick(self, dt):
        """Періодичне оновлення (хід ботів)"""
        if self.adapter:
            # Питаємо адаптер: "Є щось нове? Може бот походив?"
            # Передаємо подію 'tick', щоб адаптер знав, що пройшов час
            commands = self.adapter.process_input({'type': 'tick'})
            self.process_commands(commands)

    def on_ui_action(self, action_data):
        """
        Цей метод викликає VisualEngine, коли гравець клікає карту.
        action_data приклад: {'type': 'card_click', 'card_id': '10_hearts'}
        """
        if self.adapter:
            # Відправляємо дію в логіку
            commands = self.adapter.process_input(action_data)
            # Виконуємо те, що відповіла логіка (напр. 'PLAY_CARD' або 'SHOW_ERROR')
            self.process_commands(commands)

    def process_commands(self, commands):
        """Виконує список команд у візуальному двигуні"""
        if not commands: return
        
        for cmd in commands:
            self.visual_engine.execute_instruction(cmd)

    def update_context(self, **kwargs):
        """Отримує параметри при переключенні екранів (напр. тип гри)"""
        if 'game_type' in kwargs:
            self.game_type = kwargs['game_type']

    def go_back(self):
        self.controller.switch_screen('local_select')