import asyncio
from gui.sreen.BaseScreen import BaseScreen
from gui.utils.VisualEngine import VisualEngine

class WarGameScreen(BaseScreen):
    
    def build_ui(self):
        self.visual_engine = VisualEngine(self.ui.root)
        self.visual_engine.create_table()
        self.add_widget(self.ui.root)

    def on_enter(self, *args):
        print("Entering War Game Screen...")
        
        game_settings = {
            "game_type": "WAR",
            "player_names": ["Hero", "Bot"],
            # "initial_cards_count": 6 
        }

        g_type = game_settings.pop("game_type")
        p_names = game_settings.pop("player_names")
        
        # --- ПЕРЕДАЄМО CALLBACK ВИХОДУ ---
        self.visual_engine.setup_game(
            g_type, 
            p_names, 
            exit_callback=self.return_to_menu, # <--- Ось наша функція
            **game_settings
        )

        self.game_task = asyncio.create_task(self.start_game_sequence())

    async def start_game_sequence(self):
        await asyncio.sleep(0.5)
        await self.visual_engine.start_dealing_phase()

    def return_to_menu(self):
        """Логіка натискання кнопки 'Меню'"""
        print("Returning to menu...")
        
        # 1. Зупиняємо асинхронні процеси (роздачу, бій)
        if hasattr(self, 'game_task') and self.game_task:
            self.game_task.cancel()
            
        # 2. Очищаємо стіл (опційно, бо reset_game спрацює при наступному вході, 
        # але краще почистити пам'ять одразу)
        self.visual_engine.reset_game()
        
        # 3. Переходимо на екран вибору (або головне меню)
        # Припускаю, що ім'я попереднього екрану 'local_game_select' або 'main_menu'
        # Перевір у ScreenController.py, як називається екран списку ігор.
        self.controller.current = 'local_select' 

    def on_leave(self, *args):
        """Додаткова підстраховка при виході"""
        if hasattr(self, 'game_task') and self.game_task:
            self.game_task.cancel()