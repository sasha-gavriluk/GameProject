from gui.sreen.BaseScreen import BaseScreen
from gui.utils.VisualEngine import VisualEngine
from kivy.metrics import dp
from kivy.uix.label import Label

class PlayGameScreen(BaseScreen):
    def __init__(self, ui_manager, controller, **kwargs):
        super().__init__(ui_manager, controller, **kwargs)
        self.game_type = None  # Сюди прийде "WAR", "DURAK" або "BRIDGE"
        self.visual_engine = None

        # Мапінг для відповідності ідентифікаторів пресетам у VisualEngine
        self.GAME_MODES = {
            "WAR": "war",
            "DURAK": "durak",
            "BRIDGE": "bridge"
        }

    def on_enter(self):
        """Викликається автоматично при вході на екран"""
        self.clear_widgets()
        
        if not self.game_type:
            self.add_widget(Label(text="Помилка: Не обрано тип гри"))
            return

        # Визначаємо внутрішній ідентифікатор гри (наприклад, "WAR" -> "war")
        internal_type = self.GAME_MODES.get(self.game_type, "durak")
        print(f"PlayGameScreen: Запуск візуального двигуна для режиму: {internal_type}")
        
        # 1. Створюємо конфігураційний словник
        # Можна додати додаткові параметри: кількість гравців, складність тощо.
        config = {
            "game_type": internal_type,
            "difficulty": "easy" 
        }

        # 2. Ініціалізуємо VisualEngine
        # Передаємо game_type окремо, а решту в config, як ми налаштували у VisualEngine.__init__
        self.visual_engine = VisualEngine(game_type=internal_type, config=config)
        
        # 3. Додаємо інтерфейс (Кнопка Назад)
        self.visual_engine.add_common_ui(back_callback=self.go_back)
        
        # 4. Додаємо двигун на екран
        self.add_widget(self.visual_engine)

    def update_context(self, **kwargs):
        """
        Метод отримує дані від ScreenController при переході.
        Наприклад: controller.switch_screen('play_game', game_type='WAR')
        """
        if 'game_type' in kwargs:
            self.game_type = kwargs['game_type']
            print(f"PlayGameScreen: Отримано тип гри: {self.game_type}")

    def go_back(self):
        """Повернення до меню вибору"""
        # Якщо у вас в ScreenController екран називається 'local_game_select'
        # переконайтеся що назва вірна
        self.controller.switch_screen('local_select')