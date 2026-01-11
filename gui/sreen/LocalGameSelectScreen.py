from gui.config.Configs import sdp, responsive_metrics
from gui.sreen.BaseScreen import BaseScreen

class LocalGameSelectScreen(BaseScreen):
    def __init__(self, ui_manager, controller, **kwargs):
        super().__init__(ui_manager, controller, **kwargs)
        self.ui = ui_manager
        self.controller = controller
        self.setup_ui()
        self.add_widget(self.ui.root)

    def setup_ui(self):
        self.ui.add("anchor_local", "AnchorLayout", anchor_x='center', anchor_y='center')
        
        self.ui.add("box_local", "BoxLayout", 
                    parent="anchor_local", 
                    orientation="vertical", 
                    spacing=sdp(20), 
                    size_hint=(None, None), 
                    width=sdp(300))
        
        self.ui.add("title_local", "TitleLabel", parent="box_local", text="Оберіть гру")
        
        # Кнопки ігор
        self.ui.add("btn_war", "MenuButton", parent="box_local", text="Війна")
        self.ui.add("btn_durak", "MenuButton", parent="box_local", text="Дурак")
        self.ui.add("btn_bridge", "MenuButton", parent="box_local", text="Брідж")

        # Налаштування дій кнопок з передачею типу гри
        self.ui.set_action("btn_war", "on_release", 
                           lambda x: self.start_game("WAR"))
        
        self.ui.set_action("btn_durak", "on_release", 
                           lambda x: self.start_game("DURAK"))
        
        self.ui.set_action("btn_bridge", "on_release", 
                           lambda x: self.start_game("BRIDGE"))

        # Кнопка Назад
        self.ui.add("btn_back", "MenuButton", parent="box_local", text="Назад")
        self.ui.set_action("btn_back", "on_release", 
                           lambda x: self.controller.switch_screen('main_menu'))
        
        self.ui.build()
        
        box = self.ui.registry["box_local"]
        box.bind(minimum_height=box.setter('height'))
        self._bind_box_width(box)

    def _bind_box_width(self, box):
        def _update_box_width(*_):
            box.width = min(sdp(360), self.width * 0.9)
        self.bind(size=_update_box_width)
        responsive_metrics.bind(scale=lambda *_: _update_box_width())
        _update_box_width()

    def start_game(self, game_type):
        # Викликаємо оновлений switch_screen з параметром game_type
        self.controller.switch_screen('play_game', game_type=game_type)
