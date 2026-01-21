# gui/utils/VisualEngine.py
import random
import math

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from kivy.graphics import Color, Rectangle
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.utils import get_color_from_hex


from gui.utils.Component import HandWidget, DeckWidget, BattleAreaWidget, CardWidget, GameButton
from gui.utils.AnimationManager import AnimationManager
from gui.config.Configs import VisualConfig

class VisualEngine(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.players_map = {}   
        self.deck_widget = None
        self.battle_widget = None
        self.trump_widget = None 
        self.trump_suit = None
        self.cards_on_table = [] 
        self.durak_pairs = []
        
        # Кнопка дії (Взяти / Битом / Пас)
        self.btn_action = None 

        self.event_callback = None
        self.go_back_callback = None 
        self.is_deck_animating = False
        self.hero_widget = None 
        self.turn_label = None

        # === ДОДАЄМО ПРАПОРЕЦЬ ===
        self.input_locked = False

        with self.canvas.before:
            Color(*VisualConfig.TABLE_COLOR)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)

        self.bind(size=self._on_resize, pos=self._on_resize)

    def set_callback(self, callback_func):
        self.event_callback = callback_func

    def add_common_ui(self, go_back_callback):
        self.go_back_callback = go_back_callback
        self._draw_back_button()

        # === ДОДАЄМО КНОПКУ ДІЇ ===
        self.btn_action = GameButton(text="Взяти")
        self.btn_action.size_hint = (None, None)
        self.btn_action.size = (VisualConfig.sdp(120), VisualConfig.sdp(50))
        # Розміщуємо справа знизу, над рукою
        self.btn_action.pos_hint = {'right': 0.95, 'y': 0.25} 
        self.btn_action.opacity = 0
        self.btn_action.disabled = True
        self.btn_action.bind(on_release=self._on_action_click)
        self.add_widget(self.btn_action)
        if hasattr(self, 'game_type') and self.game_type == "BRIDGE":
            self._draw_score_button()

    def _on_action_click(self, instance):
        if self.input_locked: return
        if self.event_callback:
            # Відправляємо текст кнопки як тип дії ("Взяти" -> "take", "Битом" -> "pass")
            action_code = "take" if instance.text == "Взяти" else "pass"
            self.event_callback({
                'type': 'ui_action',
                'action': action_code
            })

    def _draw_back_button(self):
        # (Код без змін)
        if self.go_back_callback:
            for child in self.children:
                if isinstance(child, GameButton) and child.text == "< Назад":
                    return
            btn = GameButton(text="< Назад")
            btn.size_hint = (None, None)
            btn.size = (VisualConfig.sdp(100), VisualConfig.sdp(50))
            btn.pos_hint = {'x': 0.02, 'top': 0.98}
            btn.bind(on_release=lambda x: self.go_back_callback())
            self.add_widget(btn)

    def execute_instruction(self, instruction):
        cmd = instruction.get("cmd")

        if cmd == "SETUP_TABLE": self._setup_table(instruction)
        elif cmd == "INITIAL_DEAL": self._initial_deal(instruction)
        elif cmd == "SYNC_HANDS": self._sync_hands(instruction)
        elif cmd == "PLAY_CARD": self._play_card(instruction)
        elif cmd == "CLEAR_TABLE": self._clear_table(instruction)
        elif cmd == "UPDATE_CONTROLS": self._update_controls(instruction)
        elif cmd == "DRAW_CARDS_ANIMATION": self._draw_cards_animation(instruction)
        elif cmd == "TAKE_CARDS": self._animate_take_cards(instruction)
        elif cmd == "UPDATE_TURN": self._update_turn_label(instruction)
        elif cmd == "ASK_THROW": self._show_throw_confirm()
        elif cmd == "SHOW_PLAYER_COUNT": self._show_player_count_popup(instruction)
        elif cmd == "SHOW_ERROR": print(f"[VisualEngine] Error: {instruction.get('text')}")
        elif cmd == "SHOW_WINNER": self._show_winner_popup(instruction)
        elif cmd == "SHOW_SUIT_SELECTOR": 
            self.show_suit_selection(instruction.get("player_id"))
        elif cmd == "SHOW_BONUS_SELECTOR":
            self.show_jack_bonus_selection(
                instruction.get("player_id"), 
                instruction.get("mult"), 
                instruction.get("sub")
            )
        elif cmd == "SHOW_SCORES":
            self.show_score_popup(
                is_round_end=instruction.get("is_round_end"),
                players_data=instruction.get("scores")
            )
        elif cmd == "ANIMATE_RESHUFFLE":
            self._animate_reshuffle_table(instruction)
        elif cmd == "SHOW_ORDERED_SUIT": self._show_ordered_suit(instruction)
        elif cmd == "HIDE_ORDERED_SUIT": self._hide_ordered_suit(instruction)
        else: print(f"[VisualEngine] Невідома команда: {cmd}")

    def _update_turn_label(self, data):
        if not self.turn_label:
            return
        player_id = data.get("player_id")
        player_name = data.get("player_name")
        if not player_name and player_id in self.players_map:
            player_name = self.players_map[player_id].name
        if not player_name:
            player_name = "Гравець"
        self.turn_label.text = f"Хід: {player_name}"
        if player_id in self.players_map and self.players_map[player_id].is_main_player:
            self.turn_label.color = (0.6, 1, 0.6, 0.95)
        else:
            self.turn_label.color = (1, 0.8, 0.6, 0.95)

    def _show_throw_confirm(self):
        if self.input_locked:
            return
        view = ModalView(size_hint=(None, None), size=(VisualConfig.sdp(320), VisualConfig.sdp(140)), auto_dismiss=False)
        layout = BoxLayout(orientation='vertical', padding=VisualConfig.sdp(12), spacing=VisualConfig.sdp(10))
        title = Label(text="Є ще карти для підкидання?", font_size=VisualConfig.ssp(18), size_hint_y=0.4)
        layout.add_widget(title)
        btn_row = BoxLayout(orientation='horizontal', spacing=VisualConfig.sdp(10), size_hint_y=0.6)
        btn_throw = GameButton(text="Підкинути")
        btn_done = GameButton(text="Не підкидати")
        btn_throw.bind(on_release=lambda *_: self._on_throw_choice(view, True))
        btn_done.bind(on_release=lambda *_: self._on_throw_choice(view, False))
        btn_row.add_widget(btn_throw)
        btn_row.add_widget(btn_done)
        layout.add_widget(btn_row)
        view.add_widget(layout)
        view.open()

    def _on_throw_choice(self, view, want_throw):
        view.dismiss()
        if self.event_callback:
            self.event_callback({
                'type': 'ui_action',
                'action': 'throw_more' if want_throw else 'throw_done'
            })

    def _show_starting_trump(self, data):
        if not data:
            return
        player_id = data.get("player_id")
        suit = data.get("suit")
        rank = data.get("rank")
        if not player_id or not suit or not rank:
            return

        hand_widget = self.players_map.get(player_id)
        if not hand_widget:
            return

        target_widget = None
        for c_widget in hand_widget.cards:
            if c_widget.suit == suit and c_widget.rank == rank:
                target_widget = c_widget
                break

        if not target_widget:
            target_widget = CardWidget(suit=suit, rank=rank, is_face_up=hand_widget.is_main_player)

        if target_widget in hand_widget.cards:
            hand_widget.remove_card(target_widget)
        else:
            if target_widget.parent:
                target_widget.parent.remove_widget(target_widget)

        current_win_pos = target_widget.to_window(*target_widget.pos)
        self.add_widget(target_widget)
        target_widget.pos = self.to_widget(*current_win_pos)
        target_widget.size = (VisualConfig.CARD_W, VisualConfig.CARD_H)
        # Always show the starting trump face-up during the reveal.
        target_widget.is_face_up = True

        center_x = self.center_x
        center_y = self.center_y
        go_center = Animation(center_x=center_x, center_y=center_y, duration=0.5, t='out_quad')
        hold = Animation(duration=1.5)
        back = Animation(center_x=hand_widget.center_x, center_y=hand_widget.center_y, duration=0.5, t='out_quad')

        def on_back_complete(anim, widget):
            if widget.parent:
                window_pos = widget.to_window(*widget.pos)
                self.remove_widget(widget)
                local_pos = hand_widget.to_widget(*window_pos)
                widget.is_face_up = hand_widget.is_main_player
                hand_widget.add_card(widget, initial_pos=local_pos)
                hand_widget.update_hand_layout()

        back.bind(on_complete=on_back_complete)
        (go_center + hold + back).start(target_widget)

    def _show_player_count_popup(self, data):
        max_players = int(data.get("max_players", 2))
        current = int(data.get("default_players", 2))
        game_type = data.get("game_type")
        rules_settings = data.get("rules_settings") or {}
        deck_size = int(data.get("deck_size", 52))
        if game_type == "DURAK":
            max_players = max(2, deck_size // 6)
        if current < 2:
            current = 2
        if current > max_players:
            current = max_players

        view = ModalView(size_hint=(None, None), size=(VisualConfig.sdp(560), VisualConfig.sdp(400)), auto_dismiss=False)
        layout = BoxLayout(orientation='vertical', padding=VisualConfig.sdp(16), spacing=VisualConfig.sdp(12))
        title = Label(text="Кількість гравців", font_size=VisualConfig.ssp(20), size_hint_y=0.25)
        layout.add_widget(title)
        hint = Label(text=f"Максимум: {max_players}", font_size=VisualConfig.ssp(16), size_hint_y=0.15)
        layout.add_widget(hint)

        counter_row = BoxLayout(orientation='horizontal', spacing=VisualConfig.sdp(12), size_hint_y=0.22)
        btn_minus = GameButton(text="-", size_hint=(0.22, 1))
        lbl_count = Label(text=str(current), font_size=VisualConfig.ssp(24), size_hint=(0.56, 1))
        btn_plus = GameButton(text="+", size_hint=(0.22, 1))
        counter_row.add_widget(btn_minus)
        counter_row.add_widget(lbl_count)
        counter_row.add_widget(btn_plus)
        layout.add_widget(counter_row)

        mode_group = None
        throw_group = None
        deck_group = None
        if game_type == "DURAK":
            layout.add_widget(Label(text="Режим Дурака", font_size=VisualConfig.ssp(18), size_hint_y=0.2))
            mode_row = BoxLayout(orientation='horizontal', spacing=VisualConfig.sdp(10), size_hint_y=0.24)
            mode_group = {
                "podkidnoy": ToggleButton(text="Підкидний", group="durak_mode", font_size=VisualConfig.ssp(16)),
                "perevodnoy": ToggleButton(text="Перевідний", group="durak_mode", font_size=VisualConfig.ssp(16)),
                "mixed": ToggleButton(text="Підкидн.-перев.", group="durak_mode", font_size=VisualConfig.ssp(16)),
            }
            for btn in mode_group.values():
                mode_row.add_widget(btn)
            layout.add_widget(mode_row)

            layout.add_widget(Label(text="Підкидання", font_size=VisualConfig.ssp(18), size_hint_y=0.2))
            throw_row = BoxLayout(orientation='horizontal', spacing=VisualConfig.sdp(10), size_hint_y=0.24)
            throw_group = {
                "neighbors": ToggleButton(text="Бокові (Л/П)", group="throw_group", font_size=VisualConfig.ssp(16)),
                "all": ToggleButton(text="Всі", group="throw_group", font_size=VisualConfig.ssp(16)),
            }
            for btn in throw_group.values():
                throw_row.add_widget(btn)
            layout.add_widget(throw_row)

            default_mode = rules_settings.get("mode", "mixed")
            mode_group.get(default_mode, mode_group["mixed"]).state = "down"
            if rules_settings.get("neighbors_only", True):
                throw_group["neighbors"].state = "down"
            else:
                throw_group["all"].state = "down"
            
            layout.add_widget(Label(text="Колода", font_size=VisualConfig.ssp(18), size_hint_y=0.2))
            deck_row = BoxLayout(orientation='horizontal', spacing=VisualConfig.sdp(10), size_hint_y=0.22)
            deck_group = {
                "52": ToggleButton(text="52", group="deck_group", font_size=VisualConfig.ssp(16)),
                "36": ToggleButton(text="36", group="deck_group", font_size=VisualConfig.ssp(16)),
            }
            for btn in deck_group.values():
                deck_row.add_widget(btn)
            layout.add_widget(deck_row)
            if deck_size == 36:
                deck_group["36"].state = "down"
            else:
                deck_group["52"].state = "down"

            def recalc_max_players():
                nonlocal max_players, current
                size = 36 if deck_group["36"].state == "down" else 52
                max_players = max(2, size // 6)
                hint.text = f"Максимум: {max_players}"
                current = max(2, min(max_players, current))
                lbl_count.text = str(current)

            deck_group["36"].bind(on_release=lambda *_: recalc_max_players())
            deck_group["52"].bind(on_release=lambda *_: recalc_max_players())

        btn_start = GameButton(text="Почати", size_hint_y=0.22)
        layout.add_widget(btn_start)
        view.add_widget(layout)

        def update_count(delta):
            nonlocal current
            current = max(2, min(max_players, current + delta))
            lbl_count.text = str(current)

        btn_minus.bind(on_release=lambda *_: update_count(-1))
        btn_plus.bind(on_release=lambda *_: update_count(1))
        btn_start.bind(on_release=lambda *_: self._on_player_count_confirm(view, current, game_type, mode_group, throw_group, deck_group))

        view.open()

    def _on_player_count_confirm(self, view, count, game_type, mode_group, throw_group, deck_group):
        view.dismiss()
        if self.event_callback:
            settings = None
            chosen_deck = 52
            if game_type == "DURAK" and mode_group and throw_group:
                selected_mode = "mixed"
                for key, btn in mode_group.items():
                    if btn.state == "down":
                        selected_mode = key
                        break
                neighbors_only = True
                if throw_group.get("all") and throw_group["all"].state == "down":
                    neighbors_only = False
                settings = {
                    "mode": selected_mode,
                    "neighbors_only": neighbors_only,
                    "allow_overthrow": True,
                    "first_bout_5": False
                }
                if deck_group:
                    if deck_group["36"].state == "down":
                        chosen_deck = 36
            self.event_callback({
                'type': 'ui_action',
                'action': 'set_player_count',
                'count': count,
                'rules_settings': settings,
                'deck_size': chosen_deck
            })

    def _update_controls(self, data):
        """Показує або ховає кнопку дій"""
        show = data.get("show_action_btn", False)
        text = data.get("btn_text", "Взяти")

        if not self.btn_action: return

        if show:
            self.btn_action.text = text
            # Якщо кнопка була прихована, показуємо плавно
            if self.btn_action.opacity == 0:
                self.btn_action.disabled = False
                Animation(opacity=1, duration=0.2).start(self.btn_action)
            else:
                self.btn_action.disabled = False
                self.btn_action.opacity = 1
        else:
            self.btn_action.disabled = True
            Animation(opacity=0, duration=0.2).start(self.btn_action)

    def _setup_table(self, data):
        self.clear_widgets()

        self.input_locked = True

        self.game_type = data.get("game_type")

        if self.game_type == "BRIDGE":
            self._draw_score_button()

        self.players_map = {}
        self.cards_on_table = []
        self.durak_pairs = []
        self.trump_widget = None
        self.trump_suit = None
        self._draw_back_button()

        self.suit_indicator = Label(
            text="?", 
            font_size=VisualConfig.ssp(80), 
            font_name='DejaVuSans',
            color=(1, 1, 1, 1),
            outline_width=2,
            outline_color=(0,0,0,1),
            size_hint=(None, None), 
            size=(VisualConfig.sdp(100), VisualConfig.sdp(100)),
            pos_hint={'right': 0.97, 'center_y': 0.5}
        )
        self.suit_indicator.opacity = 0
        self.add_widget(self.suit_indicator)
        
        self.turn_label = Label(
            text="",
            font_size=VisualConfig.ssp(18),
            color=(1, 1, 1, 0.9),
            size_hint=(None, None),
            pos_hint={'x': 0.02, 'top': 0.90},
        )
        self.turn_label.bind(texture_size=lambda *_: setattr(self.turn_label, "size", self.turn_label.texture_size))
        self.add_widget(self.turn_label)
        
        # Отримуємо налаштування мульти-вибору
        allow_multi = data.get("multi_select", True) # <--- Зчитуємо
        
        # Кнопка дій
        self.btn_action = GameButton(text="Взяти")
        self.btn_action.size_hint = (None, None)
        self.btn_action.size = (VisualConfig.sdp(120), VisualConfig.sdp(50))
        self.btn_action.pos_hint = {'right': 0.95, 'y': 0.25}
        self.btn_action.opacity = 0
        self.btn_action.disabled = True
        self.btn_action.bind(on_release=self._on_action_click)
        self.add_widget(self.btn_action)
        
        self.hero_widget = None

        # Зона бою
        self.battle_widget = BattleAreaWidget()
        self.battle_widget.on_click_callback = self._on_battle_area_click
        self.add_widget(self.battle_widget)

        # Гравці
        players_list = data.get("players", [])
        for p_data in players_list:
            p_id = p_data["id"]
            name = p_data["name"]
            is_hero = p_data["is_hero"]

            # Передаємо multi_select у віджет руки
            # Якщо це бот - йому все одно, але для однаковості можна передати False або те саме
            ms_setting = allow_multi if is_hero else False 
            
            hand = HandWidget(name=name, player_id=p_id, is_main_player=is_hero, multi_select=ms_setting)
            
            self.add_widget(hand)
            self.players_map[p_id] = hand
            
            if is_hero:
                self.hero_widget = hand
                hand.bind(selected_cards=self._on_hero_card_selection)

        # Колода
        self.deck_widget = DeckWidget()
        self.deck_widget.pos_hint = {} 
        self.is_deck_animating = True
        self.deck_widget.opacity = 0
        self.deck_widget.bind(on_release=self._on_deck_click)
        self.add_widget(self.deck_widget)

        self.update_layout()
        Clock.schedule_once(self._start_deck_animation, 0.1)

    def _on_hero_card_selection(self, instance, selected_cards):
        """Активуємо зону бою, якщо вибрано хоча б одну карту"""

        if self.input_locked: 
            self.battle_widget.active = False
            return

        if self.battle_widget:
            self.battle_widget.active = (len(selected_cards) > 0)

    def _on_battle_area_click(self):
        """Клік по зоні бою відправляє ВСІ вибрані карти"""

        if self.input_locked: return

        if not self.hero_widget or not self.hero_widget.selected_cards:
            return

        # Збираємо ID вибраних карт
        cards_ids = [f"{c.rank}_{c.suit}" for c in self.hero_widget.selected_cards]
        
        action_data = {
            'type': 'ui_action',
            'action': 'play', 
            'cards': cards_ids 
        }

        # Скидаємо виділення візуально з самих карт
        for c in list(self.hero_widget.selected_cards):
            c.selected = False
        
        # Очищаємо список вибраних
        self.hero_widget.selected_cards.clear()
        self.hero_widget.update_hand_layout() 

        # === ВИПРАВЛЕННЯ: Явно вимикаємо підсвітку зони бою ===
        if self.battle_widget:
            self.battle_widget.active = False
        # =====================================================

        if self.event_callback:
            self.event_callback(action_data)

    def _start_deck_animation(self, dt):
        if not self.deck_widget: return

        # Старт з центру екрану
        center_x = self.width / 2
        center_y = self.height / 2
        
        self.deck_widget.center_x = center_x
        self.deck_widget.center_y = center_y
        
        # === ЗМІНА: Поки лишаємо колоду В ЦЕНТРІ для роздачі ===
        # Ми перемістимо її вбік тільки після показу козиря
        anim = Animation(opacity=1, duration=0.5)
        
        def on_complete(anim, widget):
            self.is_deck_animating = False
            # self.update_layout() # Не викликаємо update_layout, щоб не збила центр

        anim.bind(on_complete=on_complete)
        anim.start(self.deck_widget)

    def _initial_deal(self, data):
        hands_list = data.get("hands", [])
        trump_data = data.get("trump_card")
        starting_trump = data.get("starting_trump")
        if trump_data:
            self.trump_suit = trump_data.get("suit")
        
        for p_data in hands_list:
            p_id = p_data["player_id"]
            hand = self.players_map.get(p_id)
            if hand:
                hand.cards = []
                hand.clear_widgets()
                if hasattr(hand, 'clean_canvas'): hand.clean_canvas()
                if not hand.is_main_player: hand.setup_opponent_ui()

        deal_queue = []
        max_cards = max([len(h['cards_data']) for h in hands_list]) if hands_list else 0
        for i in range(max_cards):
            for p_data in hands_list:
                cards = p_data['cards_data']
                if i < len(cards):
                    deal_queue.append((p_data['player_id'], cards[i]))

        delay = 0.5 
        step = 0.2
        
        cards_to_deal = len(deal_queue)
        deck_remainder = data.get("deck_count", 0)
        if self.deck_widget:
            self.deck_widget.cards_count = deck_remainder + cards_to_deal
            self.deck_widget.update_canvas()

        for p_id, card_info in deal_queue:
            Clock.schedule_once(
                lambda dt, pid=p_id, c=card_info: self._fly_card_from_deck(pid, c), 
                delay
            )
            delay += step

        # === ЛОГІКА ПЕРЕМІЩЕННЯ КОЛОДИ ===
        
        # Час закінчення роздачі карт
        completion_time = delay + 0.5

        if trump_data:
            if deck_remainder == 0:
                Clock.schedule_once(
                    lambda dt: self._move_deck_and_trump_to_side(), 
                    completion_time
                )
            else:
                # Якщо є козир (Дурак) -> Запускаємо послідовність з козирем
                Clock.schedule_once(
                    lambda dt: self._animate_trump_sequence(trump_data), 
                    completion_time
                )
        else:
            # === FIX: Якщо немає козиря (Брідж/Війна) -> Просто рухаємо колоду вбік ===
            Clock.schedule_once(
                lambda dt: self._move_deck_and_trump_to_side(), 
                completion_time
            )
        
        if starting_trump:
            Clock.schedule_once(
                lambda dt: self._show_starting_trump(starting_trump),
                completion_time + 1.0
            )
    def _animate_trump_sequence(self, trump_data):
        """1. Створює козиря під колодою. 2. Перевертає. 3. Відсуває все вбік."""
        if not self.deck_widget: return
        self.trump_suit = trump_data.get('suit')

        # 1. Створюємо карту
        self.trump_widget = CardWidget(suit=trump_data['suit'], rank=trump_data['rank'])
        self.trump_widget.is_face_up = False # Спочатку закрита
        
        # Ставимо точно під колоду
        self.trump_widget.center = self.deck_widget.center
        self.trump_widget.size = (VisualConfig.CARD_W, VisualConfig.CARD_H) # Стандартний розмір
        
        # Хак з Z-індексом: додаємо козиря, потім піднімаємо колоду наверх
        self.add_widget(self.trump_widget)
        self.remove_widget(self.deck_widget)
        self.add_widget(self.deck_widget)
        
        # 2. Анімація появи (Reveal)
        def on_reveal_complete(anim, widget):
            # 3. Після появи - відсуваємо все на фінальну позицію
            self._move_deck_and_trump_to_side()

        AnimationManager.animate_trump_reveal(
            card_widget=self.trump_widget,
            deck_widget=self.deck_widget,
            duration=0.6,
            # (Тут ми могли б передати callback, але AnimationManager може не підтримувати його прямо
            #  тому використаємо Clock або зробимо це послідовно)
        )
        
        # Запускаємо рух вбік через час анімації reveal (0.6s) + пауза (0.2s)
        Clock.schedule_once(lambda dt: self._move_deck_and_trump_to_side(), 0.8)

    def _move_deck_and_trump_to_side(self):
        target_x = self.width * VisualConfig.DECK_X_RATIO
        target_y = self.height * VisualConfig.DECK_Y_RATIO
        
        # Використовуємо AnimationManager для синхронного руху
        AnimationManager.animate_move_deck_to_side(
            deck_widget=self.deck_widget,
            trump_card=self.trump_widget,
            target_pos=(target_x, target_y),
            duration=0.8
        )

        # === РОЗБЛОКУВАННЯ ===
        # Ми знаємо, що анімація триває 0.8 сек. 
        # Розблокуємо ввід через 0.85 сек (з маленьким запасом)
        Clock.schedule_once(lambda dt: self._unlock_input(), 0.85)

    def _unlock_input(self):
        self.input_locked = False
        print("UI Unlocked: Game Ready")
        if self.event_callback:
            self.event_callback({"type": "system", "action": "deal_complete"})

    def _fly_card_from_deck(self, player_id, card_data):
        hand_widget = self.players_map.get(player_id)
        if not hand_widget or not self.deck_widget: return

        is_hero = hand_widget.is_main_player
        use_trump = self.trump_widget is not None and self.deck_widget.cards_count == 1
        if use_trump:
            card = self.trump_widget
            self.trump_widget = None
            if card.parent != self:
                if card.parent:
                    card.parent.remove_widget(card)
                self.add_widget(card)
            card.center_x = self.deck_widget.center_x
            card.center_y = self.deck_widget.center_y
            card.opacity = 1
            card.pos_hint = {}
            card.size_hint = (None, None)
            card.is_face_up = is_hero
        else:
            card = CardWidget(suit=card_data['suit'], rank=card_data['rank'])
            card.opacity = 0
            card.center_x = self.deck_widget.center_x
            card.center_y = self.deck_widget.center_y
            card.pos_hint = {}
            card.size_hint = (None, None)
            card.is_face_up = False 
        
        if is_hero:
            card.size = (VisualConfig.CARD_W, VisualConfig.CARD_H)
        else:
            card.size = (VisualConfig.BOT_CARD_W, VisualConfig.BOT_CARD_H) 

        if not use_trump:
            self.add_widget(card)
            Clock.schedule_once(lambda dt: setattr(card, 'opacity', 1), 0.05)

        def on_arrival(anim, widget):
            if not widget.parent: return

            # 1. Видаляємо карту з кореневого віджета (щоб перенести в руку)
            window_pos = widget.to_window(*widget.pos)
            self.remove_widget(widget)
            local_pos = hand_widget.to_widget(*window_pos)
            
            # 2. ПЕРЕВІРКА НА ДУБЛІКАТИ (FIX)
            # Шукаємо, чи є вже така карта в руці (за мастю і рангом)
            # Це трапляється, якщо SYNC_HANDS спрацював раніше за анімацію
            duplicate = None
            for existing_card in hand_widget.cards:
                if existing_card.suit == widget.suit and existing_card.rank == widget.rank:
                    duplicate = existing_card
                    break
            
            # Якщо знайшли дублікат (статичну карту), видаляємо його
            if duplicate:
                hand_widget.remove_card(duplicate)
            
            # 3. Додаємо нашу анімовану карту
            hand_widget.add_card(widget, initial_pos=local_pos)

        AnimationManager.animate_deal_to_player(
            card_widget=card,
            target_player_widget=hand_widget,
            duration=VisualConfig.DEAL_SPEED,
            on_complete=on_arrival
        )

        if self.deck_widget.cards_count > 0:
            self.deck_widget.cards_count -= 1
            self.deck_widget.update_canvas()
        if self.deck_widget.cards_count == 0 and self.trump_suit:
            self._show_ordered_suit({'suit': self.trump_suit})

    def _sync_hands(self, data):
        hands_list = data.get("hands", [])
        for p_data in hands_list:
            p_id = p_data["player_id"]
            hand_widget = self.players_map.get(p_id)
            if not hand_widget: continue
            
            new_cards_data = p_data.get("cards_data", [])
            new_ids = {f"{c['rank']}_{c['suit']}" for c in new_cards_data}
            
            to_remove = []
            existing_ids = set()
            for c_widget in hand_widget.cards:
                wid = f"{c_widget.rank}_{c_widget.suit}"
                if wid not in new_ids:
                    to_remove.append(c_widget)
                else:
                    existing_ids.add(wid)
            
            for w in to_remove:
                hand_widget.remove_card(w)

            for c_info in new_cards_data:
                wid = f"{c_info['rank']}_{c_info['suit']}"
                if wid not in existing_ids:
                    new_card = CardWidget(suit=c_info['suit'], rank=c_info['rank'])
                    new_card.center = hand_widget.center
                    hand_widget.add_card(new_card)

            if not hand_widget.is_main_player:
                hand_widget.setup_opponent_ui()
                if hand_widget.card_count_label and hand_widget.card_count_label not in hand_widget.children:
                     hand_widget.add_widget(hand_widget.card_count_label)
            elif hasattr(hand_widget, 'clean_canvas'):
                 hand_widget.clean_canvas()

    def _play_card(self, data):
        p_id = data.get("player_id")
        card_data = data.get("card")
        c_id_str = card_data.get("id")
        is_durak = (self.game_type == "DURAK")
        durak_is_defense = bool(data.get("durak_is_defense"))
        
        hand_widget = self.players_map.get(p_id)
        if not hand_widget: return

        target_widget = None
        for c_widget in hand_widget.cards:
            w_id = f"{c_widget.rank}_{c_widget.suit}"
            if w_id == c_id_str:
                target_widget = c_widget
                break
        
        if not target_widget:
            target_widget = CardWidget(suit=card_data['suit'], rank=card_data['rank'])
            target_widget.opacity = 0
            target_widget.center = hand_widget.center 
            self.add_widget(target_widget)
            Clock.schedule_once(lambda dt: setattr(target_widget, 'opacity', 1), 0.05)
        
        # Переносимо карту на стіл
        if target_widget in hand_widget.cards:
            hand_widget.remove_card(target_widget)
            current_win_pos = target_widget.to_window(*target_widget.pos)
            if target_widget.parent: target_widget.parent.remove_widget(target_widget)
            
            # === ГОЛОВНА ЗМІНА ТУТ ===
            # Ми кажемо карті: "Якщо на тебе клікнуть, викликай метод _on_battle_area_click"
            # Це повністю імітує клік по порожньому столу.
            # =========================

            self.add_widget(target_widget)
            target_widget.pos = self.to_widget(*current_win_pos)
        
        target_widget.on_click_action = self._on_battle_area_click
        target_widget.is_face_up = True

        if is_durak:
            pair_idx = None
            if durak_is_defense:
                for i, pair in enumerate(self.durak_pairs):
                    if pair.get("attack") and not pair.get("defense"):
                        pair_idx = i
                        break
                if pair_idx is None:
                    durak_is_defense = False

            if durak_is_defense:
                self.durak_pairs[pair_idx]["defense"] = target_widget
            else:
                pair_idx = len(self.durak_pairs)
                self.durak_pairs.append({"attack": target_widget, "defense": None})

            positions = self._calc_durak_attack_positions(len(self.durak_pairs))
            offset_x = VisualConfig.CARD_W * 0.3
            offset_y = VisualConfig.CARD_H * 0.2
            if positions:
                if durak_is_defense:
                    target_pos = (positions[pair_idx][0] + offset_x, positions[pair_idx][1] + offset_y)
                else:
                    target_pos = positions[pair_idx]
                self._layout_durak_table(
                    animate_card=target_widget,
                    animate_pos=target_pos,
                    animate_existing=True
                )

            self.cards_on_table.append(target_widget)
            return

        if self.battle_widget:
            # (далі код анімації без змін)
            rand_x = random.randint(-int(VisualConfig.sdp(30)), int(VisualConfig.sdp(30)))
            rand_y = random.randint(-int(VisualConfig.sdp(40)), int(VisualConfig.sdp(40)))
            center_x = self.battle_widget.center_x + rand_x
            center_y = self.battle_widget.center_y + rand_y
        else:
            center_x, center_y = self.center_x, self.center_y

        angle = random.randint(-15, 15)
        anim = Animation(
            center_x=center_x, 
            center_y=center_y, 
            angle=angle, 
            size=(VisualConfig.CARD_W, VisualConfig.CARD_H), 
            duration=VisualConfig.PLAY_SPEED, 
            t='out_quad'
        )
        anim.start(target_widget)
        self.cards_on_table.append(target_widget)

    def _clear_table(self, data):
        target_x = -VisualConfig.sdp(150)
        target_y = self.height / 2
        for card in self.cards_on_table:
            anim = Animation(x=target_x, y=target_y, opacity=0, 
                             duration=VisualConfig.DISCARD_SPEED, t='in_back')
            anim.bind(on_complete=lambda a, w: self.remove_widget(w))
            anim.start(card)
        self.cards_on_table = []
        self.durak_pairs = []

    def _on_resize(self, instance, value):
        VisualConfig.update_scale(self.size)
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = self.pos
            self.bg_rect.size = self.size
        # Тут можна додати перевірку: якщо козир вже є і не анімується, оновити його позицію теж
        # Але для простоти поки оновлюємо тільки основні елементи
        self.update_layout()

    def update_layout(self):
        w, h = self.size

        if self.battle_widget:
            self.battle_widget.size_hint = (None, None)
            self.battle_widget.width = w * VisualConfig.BATTLE_AREA_WIDTH_RATIO
            self.battle_widget.height = h * VisualConfig.BATTLE_AREA_HEIGHT_RATIO
            self.battle_widget.center_x = w / 2
            self.battle_widget.center_y = h * VisualConfig.BATTLE_AREA_Y_RATIO

        if self.btn_action:
            self.btn_action.size = (VisualConfig.sdp(120), VisualConfig.sdp(50))
        for child in self.children:
            if isinstance(child, GameButton) and child.text == "< Назад":
                child.size = (VisualConfig.sdp(100), VisualConfig.sdp(50))
            if isinstance(child, GameButton) and child.text == "Рахунок":
                child.size = (VisualConfig.sdp(100), VisualConfig.sdp(50))
        if hasattr(self, "suit_indicator") and self.suit_indicator:
            self.suit_indicator.size = (VisualConfig.sdp(100), VisualConfig.sdp(100))
            if self.suit_indicator.opacity == 0:
                self.suit_indicator.font_size = VisualConfig.ssp(80)

        # Оновлюємо колоду, ТІЛЬКИ якщо вона не в процесі анімації
        # І якщо козир вже показаний, колода має бути збоку.
        if self.deck_widget and not self.is_deck_animating:
            self.deck_widget.size = (VisualConfig.CARD_W, VisualConfig.CARD_H)
            # Якщо козир існує, значить початкова анімація завершена -> колода зліва
            if self.trump_widget:
                self.deck_widget.center_x = w * VisualConfig.DECK_X_RATIO
                self.deck_widget.center_y = h * VisualConfig.DECK_Y_RATIO
                
                # Козиря теж треба посунути
                self.trump_widget.size = (VisualConfig.CARD_W, VisualConfig.CARD_H)
                self.trump_widget.center_x = self.deck_widget.center_x + VisualConfig.sdp(40)
                self.trump_widget.center_y = self.deck_widget.center_y
            else:
                # Якщо козиря ще нема, можливо ми ще в фазі роздачі?
                # Але _start_deck_animation ставить її в центр.
                # Якщо ми тут, то хай буде там, де була (не чіпаємо, щоб не збити анімацію)
                pass

        bots = []
        hero = None
        for p_id, hand_widget in self.players_map.items():
            if hand_widget.is_main_player:
                hero = hand_widget
            else:
                bots.append(hand_widget)

        if hero:
            hero.width = min(w * VisualConfig.HERO_WIDTH_PERCENT, VisualConfig.sdp(VisualConfig.HERO_MAX_WIDTH))
            hero.center_x = w / 2
            hero.y = VisualConfig.sdp(VisualConfig.HERO_BOTTOM_OFFSET)

        if bots:
            count = len(bots)
            start_deg = VisualConfig.BOT_ARC_START_DEG
            end_deg = VisualConfig.BOT_ARC_END_DEG
            rx = w * VisualConfig.BOT_ARC_RX_RATIO
            ry = h * VisualConfig.BOT_ARC_RY_RATIO
            center_x = w / 2
            center_y = h * VisualConfig.BOT_ARC_CENTER_Y_RATIO
            base_w = VisualConfig.sdp(VisualConfig.BOT_HAND_BASE_WIDTH)
            base_h = VisualConfig.sdp(VisualConfig.BOT_HAND_BASE_HEIGHT)
            max_w = w * VisualConfig.BOT_HAND_MAX_WIDTH_RATIO
            max_h = h * VisualConfig.BOT_HAND_MAX_HEIGHT_RATIO
            scale = 1.0
            if count > 1 and rx > 0 and ry > 0:
                step_deg = abs(end_deg - start_deg) / (count - 1)
                step = math.radians(step_deg)
                mid_deg = (start_deg + end_deg) / 2
                mid = math.radians(mid_deg)
                arc_speed = math.sqrt((rx * math.sin(mid)) ** 2 + (ry * math.cos(mid)) ** 2)
                spacing = arc_speed * step * VisualConfig.BOT_ARC_SPACING_RATIO
                if spacing > 0:
                    scale = min(1.0, max(VisualConfig.BOT_MIN_SCALE, spacing / base_w))
            for i, bot in enumerate(bots):
                bot.width = min(base_w * scale, max_w)
                bot.height = min(base_h * scale, max_h)
                if count == 1:
                    angle_deg = (start_deg + end_deg) / 2
                else:
                    t = i / (count - 1)
                    angle_deg = start_deg + (end_deg - start_deg) * t
                angle = math.radians(angle_deg)
                bot.center_x = center_x + math.cos(angle) * rx
                bot.center_y = center_y + math.sin(angle) * ry
                max_top = h - VisualConfig.sdp(VisualConfig.BOT_TOP_OFFSET)
                if bot.top > max_top:
                    bot.top = max_top
            for bot in bots:
                bot.update_hand_layout()

        if self.cards_on_table:
            table_card_size = (VisualConfig.CARD_W, VisualConfig.CARD_H)
            for card in self.cards_on_table:
                card.size = table_card_size
            if self.game_type == "DURAK":
                self._layout_durak_table()

    def _calc_durak_attack_positions(self, count):
        if not self.battle_widget or count <= 0:
            return []
        card_w = VisualConfig.CARD_W
        desired_gap = VisualConfig.sdp(18)
        available = self.battle_widget.width
        gap = desired_gap
        if count > 1:
            total = count * card_w + (count - 1) * desired_gap
            if total > available:
                # Якщо місця не вистачає, дозволяємо накладення.
                gap = (available - count * card_w) / (count - 1)
                min_gap = -card_w * 0.35
                if gap < min_gap:
                    gap = min_gap
        total = count * card_w + (count - 1) * gap
        start_x = self.battle_widget.center_x - total / 2 + card_w / 2
        base_y = self.battle_widget.center_y
        return [(start_x + i * (card_w + gap), base_y) for i in range(count)]

    def _layout_durak_table(self, animate_card=None, animate_pos=None, animate_existing=False):
        positions = self._calc_durak_attack_positions(len(self.durak_pairs))
        if not positions:
            return
        offset_x = VisualConfig.CARD_W * 0.3
        offset_y = VisualConfig.CARD_H * 0.2
        for i, pair in enumerate(self.durak_pairs):
            attack = pair.get("attack")
            defense = pair.get("defense")
            if attack:
                attack.size = (VisualConfig.CARD_W, VisualConfig.CARD_H)
                attack.angle = 0
                if attack is not animate_card:
                    if animate_existing:
                        Animation(
                            center_x=positions[i][0],
                            center_y=positions[i][1],
                            angle=0,
                            size=(VisualConfig.CARD_W, VisualConfig.CARD_H),
                            duration=VisualConfig.PLAY_SPEED,
                            t='out_quad'
                        ).start(attack)
                    else:
                        attack.center_x, attack.center_y = positions[i]
            if defense:
                defense.size = (VisualConfig.CARD_W, VisualConfig.CARD_H)
                defense.angle = 0
                def_x = positions[i][0] + offset_x
                def_y = positions[i][1] + offset_y
                if defense is not animate_card:
                    if animate_existing:
                        Animation(
                            center_x=def_x,
                            center_y=def_y,
                            angle=0,
                            size=(VisualConfig.CARD_W, VisualConfig.CARD_H),
                            duration=VisualConfig.PLAY_SPEED,
                            t='out_quad'
                        ).start(defense)
                    else:
                        defense.center_x, defense.center_y = def_x, def_y

        if animate_card and animate_pos:
            anim = Animation(
                center_x=animate_pos[0],
                center_y=animate_pos[1],
                angle=0,
                size=(VisualConfig.CARD_W, VisualConfig.CARD_H),
                duration=VisualConfig.PLAY_SPEED,
                t='out_quad'
            )
            anim.start(animate_card)

    def _draw_cards_animation(self, data):
        p_id = data.get("player_id")
        cards_data = data.get("cards")
        
        # Параметри затримки між вильотом карт (щоб летіли не пачкою, а по одній)
        delay = 0
        step = 0.3
        
        for card_info in cards_data:
            # Використовуємо існуючий метод, який створює карту на колоді, 
            # зменшує лічильник і відправляє карту гравцю.
            Clock.schedule_once(
                lambda dt, pid=p_id, c=card_info: self._fly_card_from_deck(pid, c), 
                delay
            )
            delay += step

    def _animate_take_cards(self, data):
        """Карти летять зі столу в руку гравця"""
        p_id = data.get("player_id")
        hand_widget = self.players_map.get(p_id)
        
        if not hand_widget or not self.cards_on_table:
            return

        target_x = hand_widget.center_x
        target_y = hand_widget.center_y

        for card in self.cards_on_table:
            card.selected = False 
            
            if card.parent:
                card.parent.remove_widget(card)
            self.add_widget(card)
            
            # === ВИПРАВЛЕННЯ ТУТ ===
            # Замість scale=0.5 використовуємо size=(0, 0)
            # Це змусить карту зменшитись до зникнення
            anim = Animation(
                center_x=target_x, 
                center_y=target_y, 
                opacity=0, 
                size=(0, 0),       # <--- Змінили scale на size
                duration=0.6, 
                t='in_back'
            )
            # =======================
            
            anim.bind(on_complete=lambda a, w: self.remove_widget(w))
            anim.start(card)

        self.cards_on_table = []

    def on_touch_down(self, touch):
        # Якщо ввід заблоковано - ми "ковтаємо" подію.
        # Повертаючи True, ми кажемо Kivy: "Я обробив це, не передавай далі дітям".
        if self.input_locked:
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.input_locked:
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.input_locked:
            return True
        return super().on_touch_up(touch)
    
    def show_suit_selection(self, player_id):
        """Показує 4 кнопки з мастями для вибору"""
        
        if not self.hero_widget or self.hero_widget.player_id != player_id:
            return

        # Створюємо модальне вікно
        view = ModalView(size_hint=(None, None), size=(VisualConfig.sdp(340), VisualConfig.sdp(110)), auto_dismiss=False)
        
        layout = BoxLayout(orientation='horizontal', padding=VisualConfig.sdp(10), spacing=VisualConfig.sdp(10))
        
        # Використовуємо білі кнопки з кольоровим текстом для кращого контрасту
        suits = [
            {'key': 'hearts',   'symbol': '♥', 'color': '#e74c3c'},   # Червоний
            {'key': 'diamonds', 'symbol': '♦', 'color': '#e74c3c'},   # Червоний
            {'key': 'clubs',    'symbol': '♣', 'color': '#2c3e50'},   # Чорний (або темно-синій)
            {'key': 'spades',   'symbol': '♠', 'color': '#2c3e50'}    # Чорний
        ]

        for s in suits:
            btn = Button(
                text=s['symbol'],
                font_size=VisualConfig.ssp(50),      # Збільшив шрифт
                font_name='DejaVuSans',# !!! ВАЖЛИВО: Шрифт з підтримкою символів
                background_normal='',  # Прибирає стандартну сіру текстуру
                background_color=(0.95, 0.95, 0.95, 1), # Світло-сірий (майже білий) фон
                color=get_color_from_hex(s['color'])    # Колір самого символу
            )
            
            btn.bind(on_release=lambda x, suit=s['key']: self._send_suit_choice(suit, view))
            layout.add_widget(btn)

        view.add_widget(layout)
        view.open()

    def _send_suit_choice(self, suit_key, popup_view):
        popup_view.dismiss()
        if self.event_callback:
            self.event_callback({
                'type': 'ui_action',
                'action': 'set_suit',
                'suit': suit_key
            })

    def show_jack_bonus_selection(self, player_id, mult_val, sub_val):
        """Показує вибір: Помножити ворогів чи Відняти собі"""
        
        if not self.hero_widget or self.hero_widget.player_id != player_id:
            return

        view = ModalView(size_hint=(None, None), size=(VisualConfig.sdp(400), VisualConfig.sdp(150)), auto_dismiss=False)
        layout = BoxLayout(orientation='vertical', padding=VisualConfig.sdp(20), spacing=VisualConfig.sdp(10))

        # Кнопка множення
        btn_mult = GameButton(text=f"Помножити ворогів (x{mult_val})")
        btn_mult.background_color = (0.8, 0.2, 0.2, 1) # Червонуватий
        btn_mult.bind(on_release=lambda x: self._send_bonus_choice('multiply', view))
        
        # Кнопка списання
        btn_sub = GameButton(text=f"Списати собі (-{sub_val})")
        btn_sub.background_color = (0.2, 0.8, 0.2, 1) # Зеленуватий
        btn_sub.bind(on_release=lambda x: self._send_bonus_choice('subtract', view))

        layout.add_widget(btn_mult)
        layout.add_widget(btn_sub)
        
        view.add_widget(layout)
        view.open()

    def _send_bonus_choice(self, choice_key, popup_view):
        popup_view.dismiss()
        if self.event_callback:
            self.event_callback({
                'type': 'ui_action',
                'action': 'set_bonus',
                'choice': choice_key
            })
    
    def _on_deck_click(self, instance):
        """Обробляє клік по колоді"""
        if self.input_locked: return
        
        # Реагуємо тільки в Бріджі (в Дурні клік по колоді зазвичай нічого не робить або показує козиря)
        if self.game_type == "BRIDGE":
            if self.event_callback:
                self.event_callback({
                    'type': 'ui_action',
                    'action': 'take' # Відправляємо команду "Взяти"
                })

    def _draw_score_button(self):
        btn = GameButton(text="Рахунок")
        
        # === ОБОВ'ЯЗКОВО ДОДАЙ ЦЕЙ РЯДОК ===
        btn.size_hint = (None, None) 
        # ===================================
        
        btn.size = (VisualConfig.sdp(100), VisualConfig.sdp(50))
        btn.pos_hint = {'right': 0.98, 'top': 0.98} # Правий верхній кут
        btn.background_color = (0.5, 0.5, 0.5, 1)   # Сірий колір
        
        # Перевірка на існування методу show_score_popup перед прив'язкою
        btn.bind(on_release=lambda x: self.show_score_popup(is_round_end=False))
        
        self.add_widget(btn)

    def show_score_popup(self, is_round_end=False, players_data=None):
        """
        is_round_end: True -> кнопка 'Новий раунд', False -> кнопка 'Продовжити'
        players_data: список словників [{'name': 'Name', 'score': 100}, ...]
        """
        
        # Якщо дані не передані, беремо поточні з віджетів (для кнопки під час гри)
        if not players_data:
            players_data = []
            # Проходимо по віджетах гравців, щоб знайти їх імена (або краще брати з adapter, 
            # але тут ми візуалізатор. Якщо Adapter надішле дані - краще).
            # Поки зробимо запит до Adapter через callback, або Adapter сам викличе цей метод.
            if self.event_callback:
                self.event_callback({'type': 'ui_action', 'action': 'get_scores'})
                return # Чекаємо відповіді від адаптера, який викличе цю функцію знову з даними

        view = ModalView(size_hint=(0.8, 0.6), auto_dismiss=not is_round_end)
        layout = BoxLayout(orientation='vertical', padding=VisualConfig.sdp(20), spacing=VisualConfig.sdp(10))

        # Заголовок
        title_text = "Результати раунду" if is_round_end else "Поточний рахунок"
        layout.add_widget(Label(text=title_text, font_size=VisualConfig.ssp(24), bold=True, size_hint_y=0.2))

        # Список гравців
        for p in players_data:
            # Виділяємо лідера або тих, хто вилетів
            score_text = f"{p['name']}: {p['score']}"
            if p['score'] > 225: score_text += " (Вибув!)"
            elif p['score'] == 0 and p.get('just_reset', False): score_text += " (Золоті 225!)"
            
            lbl = Label(text=score_text, font_size=VisualConfig.ssp(18))
            layout.add_widget(lbl)

        # Кнопка дії
        btn_text = "Наступний раунд" if is_round_end else "Продовжити гру"
        btn = GameButton(text=btn_text, size_hint_y=0.2)
        
        if is_round_end:
            # Кнопка запускає новий раунд
            btn.bind(on_release=lambda x: self._trigger_new_round(view))
        else:
            # Кнопка просто закриває вікно
            btn.bind(on_release=view.dismiss)

        layout.add_widget(btn)
        view.add_widget(layout)
        view.open()

    def _show_winner_popup(self, data):
        winner = data.get('winner', 'Невідомо')
        view = ModalView(size_hint=(None, None), size=(VisualConfig.sdp(420), VisualConfig.sdp(220)), auto_dismiss=False)
        layout = BoxLayout(orientation='vertical', padding=VisualConfig.sdp(20), spacing=VisualConfig.sdp(12))
        title = Label(text="Гру завершено", font_size=VisualConfig.ssp(22), bold=True, size_hint_y=0.35)
        layout.add_widget(title)
        lbl = Label(text=f"Переможець: {winner}", font_size=VisualConfig.ssp(18), size_hint_y=0.3)
        layout.add_widget(lbl)
        btn_row = BoxLayout(orientation='horizontal', spacing=VisualConfig.sdp(10), size_hint_y=0.35)
        btn_new = GameButton(text="Нова гра")
        btn_exit = GameButton(text="Вийти в меню")
        btn_new.bind(on_release=lambda *_: self._trigger_new_round(view))
        btn_exit.bind(on_release=lambda *_: self._trigger_exit_to_menu(view))
        btn_row.add_widget(btn_new)
        btn_row.add_widget(btn_exit)
        layout.add_widget(btn_row)
        view.add_widget(layout)
        view.open()

    def _trigger_exit_to_menu(self, popup):
        popup.dismiss()
        if self.go_back_callback:
            self.go_back_callback()

    def _trigger_new_round(self, popup):
        popup.dismiss()
        if self.event_callback:
            self.event_callback({'type': 'ui_action', 'action': 'start_new_round'})

    def _animate_reshuffle_table(self, data):
        """Карти зі столу (крім верхньої) летять назад у колоду"""
        if not self.deck_widget or not self.cards_on_table:
            return
            
        top_card_data = data.get("top_card")
        new_count = data.get("new_count", 0)
        
        target_x = self.deck_widget.center_x
        target_y = self.deck_widget.center_y
        
        cards_to_keep = []
        
        for card in list(self.cards_on_table):
            if card.suit == top_card_data['suit'] and card.rank == top_card_data['rank']:
                cards_to_keep.append(card)
                continue
            
            if card.parent:
                card.parent.remove_widget(card)
            self.add_widget(card) 
            
            # === ВИПРАВЛЕНО: замість scale використовуємо size ===
            anim = Animation(
                center_x=target_x,
                center_y=target_y,
                opacity=0,
                size=(0, 0), # Замінено scale=0.5 на size=(0,0)
                duration=0.6,
                t='in_back'
            )
            anim.bind(on_complete=lambda a, w: self.remove_widget(w))
            anim.start(card)
            
        self.cards_on_table = cards_to_keep
        
        self.deck_widget.cards_count = new_count
        self.deck_widget.opacity = 1
        self.deck_widget.update_canvas()

    def _show_ordered_suit(self, data):
        suit = data.get('suit')
        # Карта символів і кольорів
        suits_info = {
            'hearts':   {'symbol': '♥', 'color': (1, 0, 0, 1)},
            'diamonds': {'symbol': '♦', 'color': (1, 0, 0, 1)},
            'clubs':    {'symbol': '♣', 'color': (0.2, 0.2, 0.2, 1)}, # Темно-сірий для чорного
            'spades':   {'symbol': '♠', 'color': (0.2, 0.2, 0.2, 1)}
        }
        
        info = suits_info.get(suit)
        if info and self.suit_indicator:
            self.suit_indicator.text = info['symbol']
            self.suit_indicator.color = info['color']
            
            # Анімація появи (Pop effect)
            self.suit_indicator.opacity = 1
            # Скидаємо шрифт перед анімацією (замість scale)
            self.suit_indicator.font_size = VisualConfig.ssp(10)
            
            anim = Animation(font_size=VisualConfig.ssp(100), duration=0.2, t='out_back') + \
                   Animation(font_size=VisualConfig.ssp(80), duration=0.1)
            anim.start(self.suit_indicator)

    def _hide_ordered_suit(self, data):
        if self.suit_indicator and self.suit_indicator.opacity > 0:
            anim = Animation(opacity=0, duration=0.2)
            anim.start(self.suit_indicator)
