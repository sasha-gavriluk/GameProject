import math
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.metrics import dp

# Імпорт нашого нового конфігу
from gui.config.Configs import VisualConfig, WarPreset, DurakPreset

from gui.utils.Component import HandWidget, DeckWidget, CardWidget, GameButton, BattleAreaWidget
from gui.utils.AnimationManager import AnimationManager

# gui/utils/VisualEngine.py

class VisualEngine(FloatLayout):
    def __init__(self, **kwargs):
        self.game_config = kwargs.pop('config', {})
        self.game_type = kwargs.pop('game_type', 'durak')
        
        super().__init__(**kwargs)
        
        presets = {"durak": DurakPreset(), "war": WarPreset()}
        self.current_preset = presets.get(self.game_type, DurakPreset())

        self.bg_rect = None
        self.players = []
        self.deck = None
        self.trump_card = None
        self.cards_on_table = []

        self.battle_zone = BattleAreaWidget()
        self.add_widget(self.battle_zone)
        
        self.create_table()
        Clock.schedule_once(self.setup_table_by_preset, 0.1)
        self.bind(size=self.update_layout, pos=self.update_layout)

    def create_table(self):
        with self.canvas.before:
            Color(*VisualConfig.TABLE_COLOR)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)

    def setup_table_by_preset(self, dt):
        """
        Початкове налаштування столу: створення гравців, колоди та закритих карт.
        """
        print(f"VisualEngine: Налаштування столу для гри {self.current_preset.name}")
        self.players = []

        # 1. Додаємо гравців (Герой + Боти)
        self.add_player("Я", "hero", is_main=True)
        for i in range(1, self.current_preset.default_players):
            self.add_player(f"Бот {i}", f"bot_{i}", is_main=False)

        # 2. Розраховуємо ПОЧАТКОВУ позицію колоди (можна змінити офсети в Configs)
        target_deck_center = (
            self.center_x - VisualConfig.DECK_OFFSET_X,
            self.center_y + VisualConfig.DECK_OFFSET_Y
        )

        # 3. Створюємо колоду
        self.deck = DeckWidget()
        self.deck.shuffle()
        self.deck.center = target_deck_center

        # 4. Створюємо козир (спочатку закритий і точно під колодою)
        if self.current_preset.show_trump:
            real_trump = self.deck.cards.pop(0) # Беремо реальну карту
            self.deck.update_count()
            
            self.trump_card = CardWidget(
                suit=real_trump.suit, 
                rank=real_trump.rank, 
                is_face_up=False, # ЗАКРИТИЙ на старті
                center=target_deck_center
            )
            self.add_widget(self.trump_card)
            self.add_widget(self.deck)
        else:
            self.add_widget(self.deck)

        # 5. Додаємо кнопки та оновлюємо розмітку
        self.setup_game_buttons()
        self.update_layout()
        
        # 6. Запускаємо роздачу (пауза 0.5 сек)
        Clock.schedule_once(self.start_dealing_process, 0.5)

    def start_dealing_process(self, dt):
        """Формує чергу роздачі згідно з пресетом"""
        preset = self.current_preset
        if not self.deck: return

        # Визначаємо кількість карт для кожного
        if preset.deal_type == "equal":
            cards_per_p = len(self.deck.cards) // len(self.players)
        else:
            cards_per_p = preset.cards_per_player or 6

        deal_queue = []
        for _ in range(cards_per_p):
            for player in self.players:
                deal_queue.append(player)
        
        self._deal_next_card(deal_queue)

    def start_dealing_animation(self, dt):
        """Тут буде викликатися логіка роздачі карт"""
        print(f"Початок анімації роздачі: {self.current_preset.deal_type}")
        # Для тесту просто додамо по пару карт кожному
        for player in self.players:
            for _ in range(self.current_preset.cards_per_player or 3):
                card = CardWidget(suit='spades', rank='10')
                player.add_card(card)

    def add_player(self, name, p_id, is_main=False):
        hand = HandWidget(name=name, player_id=p_id, is_main_player=is_main)
        self.add_widget(hand)
        self.players.append(hand)
        return hand

    def update_layout(self, *args):
        """
        Повне оновлення інтерфейсу при зміні розміру вікна або стану гри:
        1. Супротивники в ряд зверху.
        2. Зона бою (Battle Area) по центру (згідно з BATTLE_AREA_Y_RATIO).
        3. Карти на столі прив'язані до центру зони бою.
        4. Колода зліва (в грі) або в центрі (на старті).
        """
        # Оновлення фону
        if self.bg_rect:
            self.bg_rect.pos = self.pos
            self.bg_rect.size = self.size
            
        if not self.players:
            return

        # --- 1. РОЗМІЩЕННЯ ГРАВЦІВ ---
        main_player = next((p for p in self.players if p.is_main_player), None)
        opponents = [p for p in self.players if not p.is_main_player]

        # Головний гравець (Герой)
        if main_player:
            main_player.width = min(self.width * VisualConfig.HERO_WIDTH_PERCENT, VisualConfig.HERO_MAX_WIDTH)
            main_player.center_x = self.center_x
            main_player.y = VisualConfig.HERO_BOTTOM_OFFSET

        # Супротивники (Боти) - в ряд при самому верху
        if opponents:
            n = len(opponents)
            top_margin = dp(10)
            opp_slot_width = dp(140) 
            total_row_width = n * opp_slot_width
            
            if total_row_width > self.width * 0.95:
                opp_slot_width = (self.width * 0.95) / n
                total_row_width = self.width * 0.95

            start_x = self.center_x - (total_row_width / 2) + (opp_slot_width / 2)
            for i, opp in enumerate(opponents):
                opp.center_x = start_x + (i * opp_slot_width)
                opp.top = self.height - top_margin

        # --- 2. РОЗМІЩЕННЯ ЗОНИ БОЮ ТА КАРТ НА СТОЛІ ---
        if hasattr(self, 'battle_zone'):
            # Встановлюємо розміри зони бою
            self.battle_zone.width = self.width * 0.6
            self.battle_zone.center_x = self.center_x
            # Центруємо по висоті згідно з конфігом (наприклад, 0.42)
            self.battle_zone.center_y = self.height * VisualConfig.BATTLE_AREA_Y_RATIO

            # Оновлюємо позиції всіх карт, які вже лежать на столі (cards_on_table)
            # Це важливо, щоб при зміні розміру вікна карти не "тікали" від зони
            card_spacing = dp(45)
            # Початкова точка X всередині зони
            start_table_x = self.battle_zone.x + dp(60) 
            
            for i, card in enumerate(self.cards_on_table):
                # Карта завжди по центру зони бою по вертикалі
                card.center_y = self.battle_zone.center_y
                # Зміщення по горизонталі (віяло на столі)
                card.center_x = start_table_x + (i * card_spacing)

        # --- 3. РОЗМІЩЕННЯ КОЛОДИ ТА КОЗИРЯ ---
        if self.deck:
            # Визначаємо, чи колода вже в ігровій позиції зліва
            is_in_battle_pos = self.deck.center_x < self.width * 0.3
            
            if is_in_battle_pos:
                target_y_ratio = VisualConfig.DECK_GAME_Y_RATIO
                
                # Корекція висоти колоди, якщо рука Героя занадто широка
                hero_left_edge = main_player.x if main_player else self.width
                if hero_left_edge < self.width * 0.25:
                    target_y_ratio = 0.55 
                
                self.deck.center_x = self.width * VisualConfig.DECK_GAME_X_RATIO
                self.deck.center_y = self.height * target_y_ratio
                
                if self.trump_card:
                    self.trump_card.center_y = self.deck.center_y
                    self.trump_card.center_x = self.deck.center_x + dp(40)
            else:
                # Початкова позиція в центрі (зміщена згідно з офсетами)
                self.deck.center_x = self.center_x - VisualConfig.DECK_OFFSET_X
                self.deck.center_y = self.center_y + VisualConfig.DECK_OFFSET_Y
                
                if self.trump_card:
                    if self.trump_card.angle == 90: # Якщо вже відкритий
                        self.trump_card.center_y = self.deck.center_y
                        self.trump_card.center_x = self.deck.center_x + dp(40)
                    else: # Якщо ще закритий під колодою
                        self.trump_card.center = self.deck.center

    def setup_game_ui(self):
        """Створює кнопки, описані в пресеті"""
        for i, btn_text in enumerate(self.current_preset.buttons):
            btn = GameButton(
                text=btn_text,
                size_hint=(None, None),
                size=(dp(100), dp(45)),
                # Розміщуємо кнопки в ряд над картами гравця
                pos=(self.width/2 + (i-1)*dp(110), dp(180)) 
            )
            self.add_widget(btn)

    def start_game_sequence(self, dt):
        """Логіка старту залежить від пресету"""
        print(f"Початок гри: {self.current_preset.name}")
        
        # 1. Створюємо колоду
        self.deck = DeckWidget()
        self.add_widget(self.deck)
        
        # 2. Якщо гра передбачає козир - показуємо
        if self.current_preset.show_trump:
            self.trump_card = CardWidget(suit='hearts', rank='A')
            self.add_widget(self.trump_card)
            # анімація відкриття...
            
        # 3. Викликаємо роздачу
        self.deal_cards()

    def deal_cards(self):
        """Роздача базується на параметрах пресету"""
        if self.current_preset.deal_type == "equal":
            print("Анімація: Роздача всієї колоди порівну (Війна)")
            # Логіка для Війни...
        elif self.current_preset.deal_type == "by_six":
            print("Анімація: Роздача по 6 карт (Дурень)")
            # Логіка для Дурня...

    def add_common_ui(self, back_callback):
        """Додає кнопку 'Назад'."""
        btn_back = GameButton(
            text="<",
            size_hint=(None, None),
            size=(dp(40), dp(40)),
            pos_hint={'x': 0.02, 'top': 0.98}
        )
        if back_callback:
            btn_back.bind(on_release=lambda x: back_callback())
        self.add_widget(btn_back)

    def setup_game_buttons(self):
        if hasattr(self, 'action_buttons'):
            for btn in self.action_buttons: self.remove_widget(btn)
        
        self.action_buttons = []
        for btn_text in self.current_preset.buttons:
            btn = GameButton(text=btn_text, size_hint=(None, None), size=(dp(100), dp(50)))
            # Тут можна додати btn.bind(on_release=...) для Біти/Взяти
            self.add_widget(btn)
            self.action_buttons.append(btn)

    def on_play_button_pressed(self, instance):
        """Логіка натискання кнопки Хід: карти летять трохи нижче центру"""
        hero = next((p for p in self.players if p.is_main_player), None)
        
        if hero and hero.selected_card:
            card_to_play = hero.selected_card
            
            # 1. Визначаємо цільову позицію.
            # Опускаємо центр на dp(50), щоб карти були ближче до гравця
            offset_x = len(self.battle_area) * dp(35)
            target_y = self.center_y - dp(10) # <--- Змінюємо це значення
            
            target_pos = (self.center_x + offset_x - dp(100), target_y)
            
            # 2. Скидаємо offset_y (підйом карти), щоб вона летіла "рівною"
            card_to_play.offset_y = 0
            
            # 3. Переміщуємо карту з руки на стіл
            hero.remove_card(card_to_play)
            self.add_widget(card_to_play)
            
            # 4. Анімуємо політ
            AnimationManager.animate_play_card(card_to_play, target_pos)
            
            self.battle_area.append(card_to_play)
            hero.selected_card = None

    def play_selected_card(self, player):
        card = player.selected_card
        
        # 1. Скидаємо візуальні ефекти
        card.offset_y = 0
        card.selected = False
        
        # --- НОВИЙ РЯДОК: Вимикаємо інтерактивність карти ---
        card.disabled = True 
        # ----------------------------------------------------

        target_center_y = self.battle_zone.center_y
        card_spacing = dp(40)
        start_x = self.battle_zone.x + dp(60)
        target_center_x = start_x + (len(self.cards_on_table) * card_spacing)
        
        target_pos = (target_center_x, target_center_y)
        
        player.remove_card(card)
        self.add_widget(card)
        
        AnimationManager.animate_play_card(card, target_pos)
        
        self.cards_on_table.append(card)
        player.selected_card = None
        self.battle_zone.active = False

    def update(self, dt):
        hero = next((p for p in self.players if p.is_main_player), None)
        if hero:
            # Якщо у гравця в руці піднята карта - зона бою "активується" (підсвічується)
            self.battle_zone.active = True if hero.selected_card else False

    def on_touch_down(self, touch):
        # 1. Знаходимо головного гравця
        hero = next((p for p in self.players if p.is_main_player), None)
        
        # 2. Якщо натиснули на зону бою і карта ВИБРАНА — ходимо
        if hero and hero.selected_card and self.battle_zone.collide_point(*touch.pos):
            self.play_selected_card(hero)
            return True
            
        # Стандартна обробка натискань (наприклад, вибір карти в руці)
        result = super().on_touch_down(touch)
        
        # 3. ПІСЛЯ натискання оновлюємо підсвічування зони бою
        Clock.schedule_once(lambda dt: self.update_zone_highlight(hero), 0.05)
        
        return result

    def update_zone_highlight(self, hero):
        """Вмикає підсвічування зони, якщо карта піднята"""
        if hero and hero.selected_card:
            self.battle_zone.active = True
        else:
            self.battle_zone.active = False

    def _deal_next_card(self, queue):

        """Рекурсивна роздача: по одній карті за раз"""
        if not queue or not self.deck.cards:
            print("VisualEngine: Роздача завершена")
            # ЛОГІКА ПІСЛЯ РОЗДАЧІ: Козир та від'їзд колоди
            if self.trump_card:
                Clock.schedule_once(self.reveal_trump_after_deal, 0.3)
                Clock.schedule_once(self.move_deck_to_battle_position, 1.3)
            else:
                Clock.schedule_once(self.move_deck_to_battle_position, 0.5)
            return

        target_player = queue.pop(0)
        logical_card = self.deck.cards.pop()
        self.deck.update_count()

        # Створюємо віджет на місці колоди
        new_card = CardWidget(
            suit=logical_card.suit, rank=logical_card.rank,
            center=self.deck.center, is_face_up=target_player.is_main_player
        )
        
        if not target_player.is_main_player:
            new_card.disabled = True

        self.add_widget(new_card)

        def on_fly_complete(anim, widget):
            self.remove_widget(widget)
            target_player.add_card(widget)
            # Наступна карта ТІЛЬКИ після завершення анімації попередньої
            self._deal_next_card(queue)

        # Використовуємо AnimationManager для польоту
        AnimationManager.animate_deal_to_player(
            new_card, target_player, 
            duration=VisualConfig.DEAL_SPEED, 
            on_complete=on_fly_complete
        )

    def reveal_trump_after_deal(self, dt):
        if self.trump_card:
            self.trump_card.is_face_up = True
            AnimationManager.animate_trump_reveal(self.trump_card, self.deck)

    def move_deck_to_battle_position(self, dt):
        if not self.deck: return
        target_x = self.width * VisualConfig.DECK_GAME_X_RATIO
        target_y = self.height * VisualConfig.DECK_GAME_Y_RATIO
        AnimationManager.animate_move_deck_to_side(self.deck, self.trump_card, (target_x, target_y))