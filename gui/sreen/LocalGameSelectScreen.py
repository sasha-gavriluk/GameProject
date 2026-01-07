from kivy.metrics import dp
from gui.sreen.BaseScreen import BaseScreen

class LocalGameSelectScreen(BaseScreen):
    def __init__(self, ui_manager, controller, **kwargs):
        super().__init__(ui_manager, controller, **kwargs)
        self.ui = ui_manager
        self.controller = controller
        self.setup_ui()
        self.add_widget(self.ui.root)

    def setup_ui(self):
        # Основний контейнер
        self.ui.add("anchor_local", "AnchorLayout", anchor_x='center', anchor_y='center')
        
        # Вертикальний список кнопок
        self.ui.add("box_local", "BoxLayout", 
                    parent="anchor_local", 
                    orientation="vertical", 
                    spacing=dp(20), 
                    size_hint=(None, None), 
                    width=dp(300))
        
        # Заголовок
        self.ui.add("title_local", "TitleLabel", parent="box_local", text="Ігри")
        
        # 3 кнопки ігор
        self.ui.add("btn_war", "MenuButton", parent="box_local", text="Війна")
        self.ui.add("btn_durak", "MenuButton", parent="box_local", text="Дурак")
        self.ui.add("btn_bridge", "MenuButton", parent="box_local", text="Брідж")

        self.ui.set_action("btn_war", "on_release", lambda x: self.controller.switch_screen('war_game'))
        
        # Кнопка Назад
        self.ui.add("btn_back", "MenuButton", parent="box_local", text="Назад")
        self.ui.set_action("btn_back", "on_release", lambda x: self.controller.switch_screen('main_menu'))
        
        # Тут можна додати обробники для кнопок ігор, коли вони будуть готові
        # self.ui.set_action("btn_war", "on_release", ...)

        self.ui.build()
        
        # Автоматична висота для боксу
        box = self.ui.registry["box_local"]
        box.bind(minimum_height=box.setter('height'))