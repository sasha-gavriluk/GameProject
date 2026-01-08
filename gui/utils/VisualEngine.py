import asyncio
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.animation import Animation
from kivy.uix.popup import Popup
from kivy.uix.label import Label

from gui.utils.Component import HandWidget, DeckWidget, CardWidget, GameButton
from gui.utils.AnimationManager import AnimationManager
from utils.engine import GameEngine, Player
from utils.cards import Deck
from utils.rule.rules_war import WarRules

ASPEED = 0.11  # Швидкість анімації роздачі карт

class PlayerVisual:
    def __init__(self, root_layout, logic_player, pos_hint, is_me=False):
        self.logic = logic_player
        self.is_me = is_me
        self.widget = HandWidget(pos_hint=pos_hint)
        self.widget.is_me = is_me 
        self.widget.max_selected = 1 
        root_layout.add_widget(self.widget)

    def add_card_widget(self, card_widget):
        self.widget.add_card(card_widget)
        if not self.is_me:
            card_widget.is_face_up = False
        else:
            card_widget.is_face_up = True
            
    def get_selected_card(self):
        for child in self.widget.children:
            if getattr(child, 'selected', False):
                return child
        return None


class VisualEngine:
    def __init__(self, root_layout):
        self.root = root_layout
        self.game_engine = None
        self.players = [] 
        self.zones = {} 
        self.bg_rect = None
        self.deck_widget = None
        self.action_buttons = [] # Список кнопок

    def create_table(self):
        # Цей метод можна викликати один раз при старті, 
        # бо фон не треба перестворювати
        if self.bg_rect: return 
        
        with self.root.canvas.before:
            Color(*get_color_from_hex('#27ae60'))
            self.bg_rect = Rectangle(size=self.root.size, pos=self.root.pos)
        self.root.bind(size=self._update_bg, pos=self._update_bg)

    def _update_bg(self, instance, value):
        if self.bg_rect:
            self.bg_rect.size = instance.size
            self.bg_rect.pos = instance.pos

    def reset_game(self):
        """Очищає стіл від попередньої гри"""
        # 1. Видаляємо візуальних гравців (руки)
        for p in self.players:
            if p.widget.parent:
                p.widget.parent.remove_widget(p.widget)
        self.players.clear()

        # 2. Видаляємо зони столу
        for zone in self.zones.values():
            if zone.parent:
                zone.parent.remove_widget(zone)
        self.zones.clear()

        # 3. Видаляємо колоду
        if self.deck_widget and self.deck_widget.parent:
            self.deck_widget.parent.remove_widget(self.deck_widget)
        self.deck_widget = None

        # 4. Видаляємо кнопки
        for btn in self.action_buttons:
            if btn.parent:
                btn.parent.remove_widget(btn)
        self.action_buttons.clear()

        # 5. Очищаємо будь-які карти, що могли зависнути на root
        cards_on_root = [w for w in self.root.children if isinstance(w, CardWidget)]
        for c in cards_on_root:
            self.root.remove_widget(c)

    def setup_game(self, game_type, player_names, exit_callback=None, **rule_params):
        # 1. Очищення
        self.reset_game()
        
        # --- ЗБЕРІГАЄМО CALLBACK ---
        self.exit_callback = exit_callback 
        
        print(f"--- Setting up game: {game_type} ---")
        
        rules = None
        layout_func = None

        if game_type == "WAR":
            rules = WarRules(**rule_params)
            layout_func = self._layout_war
        else:
            print(f"Unknown game type: {game_type}")
            return

        self.game_engine = GameEngine(rules)
        self._setup_players(player_names)
        
        self._create_common_ui(exit_callback)

        if layout_func:
            layout_func()

    def _show_game_over_popup(self, title_text, message_text, color_hex):
        """Показує вікно результату гри"""
        
        # Контейнер для вмісту попапу
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(20))
        
        # Повідомлення
        lbl_msg = Label(
            text=message_text, 
            font_size=dp(20), 
            color=get_color_from_hex(color_hex),
            halign='center',
            valign='middle'
        )
        content.add_widget(lbl_msg)
        
        # Кнопка виходу
        btn_exit = GameButton(text="В меню", size_hint=(1, None), height=dp(50))
        content.add_widget(btn_exit)
        
        # Створюємо попап
        popup = Popup(
            title=title_text,
            content=content,
            size_hint=(None, None),
            size=(dp(300), dp(250)),
            auto_dismiss=False # Забороняємо закривати кліком повз
        )
        
        # Прив'язуємо кнопку до виходу
        def on_exit_click(instance):
            popup.dismiss()
            if self.exit_callback:
                self.exit_callback()
                
        btn_exit.bind(on_release=on_exit_click)
        
        popup.open()
    
    def _create_common_ui(self, exit_callback):
        """Створює елементи інтерфейсу, спільні для всіх ігор"""
        # Кнопка "Меню" / "Вихід" зліва зверху
        btn_exit = GameButton(
            text="<",
            size_hint=(None, None),
            size=(dp(30), dp(50)),
            pos_hint={'x': 0.02, 'top': 0.98}
        )
        
        # Якщо передали функцію виходу - прив'язуємо її
        if exit_callback:
            btn_exit.bind(on_release=lambda x: exit_callback())
            
        self.root.add_widget(btn_exit)
        self.action_buttons.append(btn_exit) # Додаємо в список, щоб видалити при reset_game

    def _setup_players(self, names):
        self.game_engine.players = []
        positions = [
            {'center_x': 0.5, 'y': 0.02},    
            {'center_x': 0.5, 'top': 0.98}   
        ]
        
        for i, name in enumerate(names):
            p_logic = Player(name)
            self.game_engine.players.append(p_logic)
            pos = positions[i] if i < len(positions) else {'center_x': 0.5, 'center_y': 0.5}
            p_visual = PlayerVisual(self.root, p_logic, pos, is_me=(i == 0))
            self.players.append(p_visual)

    def _layout_war(self):
        self.deck_widget = DeckWidget(pos_hint={'center_x': 0.5, 'center_y': 0.5})
        self.root.add_widget(self.deck_widget)

        table_p = FloatLayout(size_hint=(None, None), size=(dp(100), dp(140)), 
                              pos_hint={'center_x': 0.4, 'center_y': 0.5})
        self.root.add_widget(table_p)
        self.zones['table_player'] = table_p

        table_b = FloatLayout(size_hint=(None, None), size=(dp(100), dp(140)), 
                              pos_hint={'center_x': 0.6, 'center_y': 0.5})
        self.root.add_widget(table_b)
        self.zones['table_bot'] = table_b

        btn_battle = GameButton(
            text="Бій!",
            size_hint=(None, None),
            size=(dp(120), dp(60)),
            pos_hint={'right': 0.95, 'center_y': 0.5}
        )
        btn_battle.bind(on_release=lambda x: self.on_war_battle_click())
        self.root.add_widget(btn_battle)
        self.action_buttons.append(btn_battle)

    # --- ЛОГІКА ХОДУ (WAR) ---
    def on_war_battle_click(self):
        if not self.players[0].logic.hand:
            print("Гра закінчена!")
            return

        player_vis = self.players[0]
        selected_card_widget = player_vis.get_selected_card()

        if not selected_card_widget:
            self._show_warning_popup("Виберіть карту для ходу!")
            return

        asyncio.create_task(self._play_war_round(selected_card_widget))

    def _show_warning_popup(self, message):
        content = Label(text=message, font_size=dp(18))
        popup = Popup(title='Увага', content=content, size_hint=(None, None), size=(dp(300), dp(200)))
        popup.open()

    async def _play_war_round(self, player_card_widget):
        p_me = self.players[0]
        p_bot = self.players[1]

        # Знаходимо логічну карту
        card_me_logic = None
        for c in p_me.logic.hand:
            if c.suit == player_card_widget.suit and c.rank == player_card_widget.rank:
                card_me_logic = c
                break
        
        if not card_me_logic: return
        p_me.logic.hand.remove(card_me_logic)

        if not p_bot.logic.hand: return
        card_bot_logic = p_bot.logic.hand.pop(0)

        await asyncio.gather(
            self._animate_play_specific_card(p_me, player_card_widget, self.zones['table_player']),
            self._animate_play_bot_card(p_bot, card_bot_logic, self.zones['table_bot'])
        )

        await asyncio.sleep(1.0)

        rank_values = self.game_engine.rules.ranks_values
        val_me = rank_values.get(card_me_logic.rank, 0)
        val_bot = rank_values.get(card_bot_logic.rank, 0)
        
        winner = None
        if val_me > val_bot:
            winner = p_me
        elif val_bot > val_me:
            winner = p_bot
        else:
            winner = p_me 

        winner.logic.hand.extend([card_me_logic, card_bot_logic])

        await asyncio.gather(
            self._animate_collect_card(card_me_logic, winner),
            self._animate_collect_card(card_bot_logic, winner)
        )

        me_lost = (len(p_me.logic.hand) == 0)
        bot_lost = (len(p_bot.logic.hand) == 0)

        if me_lost:
            self._show_game_over_popup(
                title_text="ПОРАЗКА",
                message_text="У вас закінчились карти!\nБот переміг.",
                color_hex="#e74c3c" # Червоний
            )
        elif bot_lost:
            self._show_game_over_popup(
                title_text="ПЕРЕМОГА!",
                message_text="Ви забрали всі карти!\nВітаємо!",
                color_hex="#f1c40f" # Золотий/Жовтий
            )

    # --- Допоміжні методи анімації ---
    async def _animate_play_specific_card(self, player_visual, card_widget, target_zone):
        player_visual.widget.remove_card(card_widget)
        window_pos = card_widget.to_window(*card_widget.pos)
        self.root.add_widget(card_widget)
        card_widget.pos = self.root.to_widget(*window_pos)
        
        target_pos = (
            target_zone.center_x - card_widget.width / 2,
            target_zone.center_y - card_widget.height / 2
        )
        
        anim_done = asyncio.Event()
        card_widget.selected = False
        card_widget.is_face_up = True
        
        AnimationManager.animate_card_to_table(
            card_widget, target_pos, duration=0.4, on_complete=lambda *args: anim_done.set()
        )
        await anim_done.wait()
        
        self.root.remove_widget(card_widget)
        target_zone.add_widget(card_widget)
        card_widget.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

    async def _animate_play_bot_card(self, bot_visual, card_logic, target_zone):
        card_widget = None
        for w in bot_visual.widget.children:
            if w.suit == card_logic.suit and w.rank == card_logic.rank:
                card_widget = w
                break
        
        if not card_widget and bot_visual.widget.children:
            card_widget = bot_visual.widget.children[-1]

        if card_widget:
            await self._animate_play_specific_card(bot_visual, card_widget, target_zone)

    async def _animate_collect_card(self, card_logic, winner_visual):
        card_widget = None
        for zone in self.zones.values():
            for child in zone.children:
                if isinstance(child, CardWidget) and child.suit == card_logic.suit and child.rank == card_logic.rank:
                    card_widget = child
                    break
            if card_widget: break
            
        if not card_widget: return

        if card_widget.parent:
            win_pos = card_widget.to_window(*card_widget.pos)
            card_widget.parent.remove_widget(card_widget)
            self.root.add_widget(card_widget)
            card_widget.pos = self.root.to_widget(*win_pos)
            card_widget.pos_hint = {}

        hand_w = winner_visual.widget
        target_pos = (
            hand_w.x + hand_w.width, 
            hand_w.center_y - card_widget.height / 2
        )

        anim_done = asyncio.Event()
        AnimationManager.animate_card_to_table(
            card_widget, target_pos, duration=0.5, on_complete=lambda *args: anim_done.set()
        )
        await anim_done.wait()

        self.root.remove_widget(card_widget)
        winner_visual.add_card_widget(card_widget)

    async def start_dealing_phase(self):
        if not self.deck_widget: return
        logic_deck = Deck()
        logic_deck.shuffle()
        self.deck_widget.cards = logic_deck.cards[:] 
        self.deck_widget.update_count()

        cards_to_deal = self.game_engine.rules.initial_cards_count or 6
        for _ in range(cards_to_deal):
            for player_visual in self.players:
                card_data = logic_deck.deal()
                if not card_data: break 
                player_visual.logic.receive_card(card_data)
                self.deck_widget.cards = logic_deck.cards[:]
                self.deck_widget.update_count()
                await self._animate_deal_flight(card_data, player_visual)

        self.deck_widget.cards = logic_deck.cards
        self.deck_widget.update_count()
        await self._move_deck_to_side()

    async def _move_deck_to_side(self):
        self.deck_widget.pos_hint = {}
        target_x = self.root.width * 0.15 - self.deck_widget.width / 2
        target_y = self.root.height * 0.5 - self.deck_widget.height / 2
        anim = Animation(pos=(target_x, target_y), duration=0.8, t='in_out_cubic')
        anim.start(self.deck_widget)
        await asyncio.sleep(0.8)

    async def _animate_deal_flight(self, card_data, target_player):
        card_widget = CardWidget(suit=card_data.suit, rank=card_data.rank)
        self.root.add_widget(card_widget)
        deck_pos = self.deck_widget.to_window(self.deck_widget.x, self.deck_widget.y)
        card_widget.pos = self.root.to_widget(*deck_pos)
        
        hand_widget = target_player.widget
        target_pos = (
            hand_widget.center_x - card_widget.width / 2,
            hand_widget.center_y - card_widget.height / 2
        )
        card_widget.is_face_up = False 
        card_widget.opacity = 1
        
        anim_done = asyncio.Event()
        AnimationManager.animate_card_to_table(
            card_widget, target_pos, duration=ASPEED, on_complete=lambda *args: anim_done.set()
        )
        await anim_done.wait()
        
        card_widget.pos_hint = {}
        self.root.remove_widget(card_widget)
        target_player.add_card_widget(card_widget)