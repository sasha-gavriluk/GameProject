# gui/utils/VisualEngine.py
import random
import math

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import get_color_from_hex

from gui.utils.Component import (
    HandWidget,
    DeckWidget,
    BattleAreaWidget,
    CardWidget,
    GameButton,
    GamePopup,
    GameToggleButton,
)
from gui.utils.AnimationManager import AnimationManager
from gui.config.Configs import VisualConfig

# ==========================================
# 1. МЕНЕДЖЕР СПЛИВАЮЧИХ ВІКОН (DIALOGS)
# ==========================================
class DialogManager:
    """Відповідає за генерацію та обробку всіх модальних вікон (Popup) у грі."""
    def __init__(self, engine):
        self.engine = engine # Посилання на головний VisualEngine

    def show_throw_confirm(self):
        if self.engine.input_locked: return
        view = GamePopup(title="Підтвердження", size_hint=(None, None), size=(VisualConfig.sdp(360), VisualConfig.sdp(180)), auto_dismiss=False)
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
        view.content = layout
        view.open()

    def _on_throw_choice(self, view, want_throw):
        view.dismiss()
        if self.engine.event_callback:
            self.engine.event_callback({
                'type': 'ui_action',
                'action': 'throw_more' if want_throw else 'throw_done'
            })

    def show_player_count_popup(self, data):
        max_players = int(data.get("max_players", 2))
        current = int(data.get("default_players", 2))
        game_type = data.get("game_type")
        rules_settings = data.get("rules_settings") or {}
        deck_size = int(data.get("deck_size", 52))
        
        if game_type == "DURAK": max_players = max(2, deck_size // 6)
        if game_type == "WAR": max_players, current = 2, 2
        
        current = max(2, min(current, max_players))

        view = GamePopup(title="Налаштування гри", size_hint=(None, None), size=(VisualConfig.sdp(620), VisualConfig.sdp(500)), auto_dismiss=False)
        layout = BoxLayout(orientation='vertical', padding=VisualConfig.sdp(16), spacing=VisualConfig.sdp(12))
        title = Label(text="Налаштування гри" if game_type == "WAR" else "Кількість гравців", font_size=VisualConfig.ssp(20), size_hint_y=0.25)
        layout.add_widget(title)
        
        hint, btn_minus, btn_plus, lbl_count = None, None, None, None
        
        if game_type != "WAR":
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
        else:
            layout.add_widget(Label(text="Гравців: 2", font_size=VisualConfig.ssp(18), size_hint_y=0.15))

        mode_group, throw_group, deck_group = None, None, None
        
        if game_type == "DURAK":
            layout.add_widget(Label(text="Режим Дурака", font_size=VisualConfig.ssp(18), size_hint_y=0.2))
            mode_row = BoxLayout(orientation='horizontal', spacing=VisualConfig.sdp(10), size_hint_y=0.24)
            mode_group = {
                "podkidnoy": GameToggleButton(text="Підкидний", group="durak_mode", font_size=VisualConfig.ssp(16)),
                "perevodnoy": GameToggleButton(text="Перевідний", group="durak_mode", font_size=VisualConfig.ssp(16)),
                "mixed": GameToggleButton(text="Підкидн.-перев.", group="durak_mode", font_size=VisualConfig.ssp(16)),
            }
            for btn in mode_group.values(): mode_row.add_widget(btn)
            layout.add_widget(mode_row)
            mode_group.get(rules_settings.get("mode", "mixed"), mode_group["mixed"]).state = "down"

            layout.add_widget(Label(text="Підкидання", font_size=VisualConfig.ssp(18), size_hint_y=0.2))
            throw_row = BoxLayout(orientation='horizontal', spacing=VisualConfig.sdp(10), size_hint_y=0.24)
            throw_group = {
                "neighbors": GameToggleButton(text="Бокові", group="throw_group", font_size=VisualConfig.ssp(16)),
                "all": GameToggleButton(text="Всі", group="throw_group", font_size=VisualConfig.ssp(16)),
            }
            for btn in throw_group.values(): throw_row.add_widget(btn)
            layout.add_widget(throw_row)
            throw_group["neighbors" if rules_settings.get("neighbors_only", True) else "all"].state = "down"

        # Колода для Дурня та Війни
        if game_type in ["DURAK", "WAR"]:
            layout.add_widget(Label(text="Колода", font_size=VisualConfig.ssp(18), size_hint_y=0.2))
            deck_row = BoxLayout(orientation='horizontal', spacing=VisualConfig.sdp(10), size_hint_y=0.22)
            deck_group = {
                "52": GameToggleButton(text="52", group="deck_group", font_size=VisualConfig.ssp(16)),
                "36": GameToggleButton(text="36", group="deck_group", font_size=VisualConfig.ssp(16)),
            }
            for btn in deck_group.values(): deck_row.add_widget(btn)
            layout.add_widget(deck_row)
            deck_group["36" if deck_size == 36 else "52"].state = "down"

            if game_type == "DURAK":
                def recalc_max_players(*args):
                    nonlocal max_players, current
                    size = 36 if deck_group["36"].state == "down" else 52
                    max_players = max(2, size // 6)
                    hint.text = f"Максимум: {max_players}"
                    current = max(2, min(max_players, current))
                    lbl_count.text = str(current)
                deck_group["36"].bind(on_release=recalc_max_players)
                deck_group["52"].bind(on_release=recalc_max_players)

        btn_start = GameButton(text="Почати", size_hint_y=0.22)
        layout.add_widget(btn_start)
        view.content = layout

        def update_count(delta):
            nonlocal current
            if lbl_count:
                current = max(2, min(max_players, current + delta))
                lbl_count.text = str(current)

        if btn_minus and btn_plus:
            btn_minus.bind(on_release=lambda *_: update_count(-1))
            btn_plus.bind(on_release=lambda *_: update_count(1))
            
        btn_start.bind(on_release=lambda *_: self._on_player_count_confirm(view, current, game_type, mode_group, throw_group, deck_group))
        view.open()

    def _on_player_count_confirm(self, view, count, game_type, mode_group, throw_group, deck_group):
        view.dismiss()
        if self.engine.event_callback:
            settings, chosen_deck = None, 52
            if game_type == "DURAK" and mode_group and throw_group:
                selected_mode = next((k for k, v in mode_group.items() if v.state == "down"), "mixed")
                neighbors_only = throw_group.get("all") is None or throw_group["all"].state != "down"
                settings = {"mode": selected_mode, "neighbors_only": neighbors_only, "allow_overthrow": True, "first_bout_5": False}
            if deck_group and "36" in deck_group and deck_group["36"].state == "down":
                chosen_deck = 36
                
            self.engine.event_callback({
                'type': 'ui_action', 'action': 'set_player_count', 'count': count,
                'rules_settings': settings, 'deck_size': chosen_deck
            })

    def show_winner_popup(self, data):
        winner = data.get('winner', 'Невідомо')
        online_mode = bool(data.get('online', False))
        view = GamePopup(title="Результат", size_hint=(None, None), size=(VisualConfig.sdp(460), VisualConfig.sdp(260)), auto_dismiss=False)
        layout = BoxLayout(orientation='vertical', padding=VisualConfig.sdp(20), spacing=VisualConfig.sdp(12))
        layout.add_widget(Label(text="Гру завершено", font_size=VisualConfig.ssp(22), bold=True, size_hint_y=0.35))
        layout.add_widget(Label(text=f"Переможець: {winner}", font_size=VisualConfig.ssp(18), size_hint_y=0.3))
        
        btn_row = BoxLayout(orientation='horizontal', spacing=VisualConfig.sdp(10), size_hint_y=0.35)
        exit_text = "Вийти в кімнату" if online_mode else "Вийти в меню"
        btn_new, btn_exit = GameButton(text="Нова гра"), GameButton(text=exit_text)
        
        btn_new.bind(on_release=lambda *_: self._trigger_new_round(view))
        btn_exit.bind(on_release=lambda *_: self._trigger_exit_to_menu(view))
        
        btn_row.add_widget(btn_new)
        btn_row.add_widget(btn_exit)
        layout.add_widget(btn_row)
        view.content = layout
        view.open()

    def show_score_popup(self, is_round_end=False, players_data=None):
        if not players_data:
            if self.engine.event_callback:
                self.engine.event_callback({'type': 'ui_action', 'action': 'get_scores'})
            return

        view = GamePopup(title="Рахунок", size_hint=(0.8, 0.6), auto_dismiss=not is_round_end)
        layout = BoxLayout(orientation='vertical', padding=VisualConfig.sdp(20), spacing=VisualConfig.sdp(10))
        layout.add_widget(Label(
            text="Результати раунду" if is_round_end else "Поточний рахунок",
            font_size=VisualConfig.ssp(24),
            bold=True,
            size_hint_y=0.22
        ))

        cards_row = BoxLayout(orientation='horizontal', spacing=VisualConfig.sdp(10), size_hint_y=0.58)
        for p in players_data:
            player_card = BoxLayout(
                orientation='vertical',
                padding=VisualConfig.sdp(10),
                spacing=VisualConfig.sdp(8),
            )
            with player_card.canvas.before:
                Color(0.13, 0.16, 0.20, 0.96)
                bg = RoundedRectangle(pos=player_card.pos, size=player_card.size, radius=[VisualConfig.sdp(10)])
            player_card.bind(
                pos=lambda w, *_args, _bg=bg: setattr(_bg, "pos", w.pos),
                size=lambda w, *_args, _bg=bg: setattr(_bg, "size", w.size)
            )

            player_card.add_widget(Label(text=p['name'], font_size=VisualConfig.ssp(18), bold=True))

            score_text = str(p['score'])
            if p['score'] > 225:
                score_text += "\n(Вибув)"
            elif p['score'] == 0 and p.get('just_reset', False):
                score_text += "\n(Золоті 225!)"
            player_card.add_widget(Label(text=score_text, font_size=VisualConfig.ssp(20), bold=True))

            cards_row.add_widget(player_card)

        layout.add_widget(cards_row)

        btn = GameButton(
            text="Наступний раунд" if is_round_end else "Продовжити гру",
            size_hint=(None, None),
            size=(VisualConfig.sdp(240), VisualConfig.sdp(54)),
            pos_hint={'center_x': 0.5}
        )
        btn.bind(on_release=lambda x: self._trigger_new_round(view) if is_round_end else view.dismiss())
        layout.add_widget(btn)
        view.content = layout
        view.open()

    def show_suit_selection(self, player_id):
        if not self.engine.hero_widget or self.engine.hero_widget.player_id != player_id: return
        view = GamePopup(title="Оберіть масть", size_hint=(None, None), size=(VisualConfig.sdp(380), VisualConfig.sdp(170)), auto_dismiss=False)
        layout = BoxLayout(orientation='horizontal', padding=VisualConfig.sdp(10), spacing=VisualConfig.sdp(10))
        
        suits = [
            {'key': 'hearts', 'symbol': '♥', 'color': '#e74c3c'}, {'key': 'diamonds', 'symbol': '♦', 'color': '#e74c3c'},
            {'key': 'clubs', 'symbol': '♣', 'color': '#2c3e50'}, {'key': 'spades', 'symbol': '♠', 'color': '#2c3e50'}
        ]
        for s in suits:
            btn = GameButton(text=s['symbol'], font_size=VisualConfig.ssp(50), font_name='DejaVuSans', color=get_color_from_hex(s['color']))
            btn.bind(on_release=lambda x, suit=s['key']: self._send_choice('set_suit', 'suit', suit, view))
            layout.add_widget(btn)
        view.content = layout
        view.open()

    def show_jack_bonus_selection(self, player_id, mult_val, sub_val):
        if not self.engine.hero_widget or self.engine.hero_widget.player_id != player_id: return
        view = GamePopup(title="Бонус Валета", size_hint=(None, None), size=(VisualConfig.sdp(430), VisualConfig.sdp(210)), auto_dismiss=False)
        layout = BoxLayout(orientation='vertical', padding=VisualConfig.sdp(20), spacing=VisualConfig.sdp(10))

        btn_mult = GameButton(text=f"Помножити ворогів (x{mult_val})", background_color=(0.8, 0.2, 0.2, 1))
        btn_mult.bind(on_release=lambda x: self._send_choice('set_bonus', 'choice', 'multiply', view))
        
        btn_sub = GameButton(text=f"Списати собі (-{sub_val})", background_color=(0.2, 0.8, 0.2, 1))
        btn_sub.bind(on_release=lambda x: self._send_choice('set_bonus', 'choice', 'subtract', view))

        layout.add_widget(btn_mult)
        layout.add_widget(btn_sub)
        view.content = layout
        view.open()

    def show_bridge_decision(self, player_id):
        if not self.engine.hero_widget or self.engine.hero_widget.player_id != player_id:
            return
        view = GamePopup(title="Брідж", size_hint=(None, None), size=(VisualConfig.sdp(430), VisualConfig.sdp(210)), auto_dismiss=False)
        layout = BoxLayout(orientation='vertical', padding=VisualConfig.sdp(20), spacing=VisualConfig.sdp(10))
        layout.add_widget(Label(text="Завершити раунд чи продовжити гру?", font_size=VisualConfig.ssp(18), size_hint_y=0.45))

        btn_end = GameButton(text="Завершити раунд", size_hint_y=0.275)
        btn_cont = GameButton(text="Продовжити гру", size_hint_y=0.275)
        btn_end.bind(on_release=lambda x: self._send_choice('set_bridge_decision', 'choice', 'end', view))
        btn_cont.bind(on_release=lambda x: self._send_choice('set_bridge_decision', 'choice', 'continue', view))

        layout.add_widget(btn_end)
        layout.add_widget(btn_cont)
        view.content = layout
        view.open()

    def show_durak_defense_choice(self, player_id):
        if not self.engine.hero_widget or self.engine.hero_widget.player_id != player_id:
            return
        view = GamePopup(title="Дурак", size_hint=(None, None), size=(VisualConfig.sdp(430), VisualConfig.sdp(210)), auto_dismiss=False)
        layout = BoxLayout(orientation='vertical', padding=VisualConfig.sdp(20), spacing=VisualConfig.sdp(10))
        layout.add_widget(Label(text="Оберіть дію: бити чи перевести?", font_size=VisualConfig.ssp(18), size_hint_y=0.45))

        btn_beat = GameButton(text="Бити", size_hint_y=0.275)
        btn_transfer = GameButton(text="Перевести", size_hint_y=0.275)
        btn_beat.bind(on_release=lambda x: self._send_choice('set_durak_defense_choice', 'choice', 'beat', view))
        btn_transfer.bind(on_release=lambda x: self._send_choice('set_durak_defense_choice', 'choice', 'transfer', view))

        layout.add_widget(btn_beat)
        layout.add_widget(btn_transfer)
        view.content = layout
        view.open()

    def _send_choice(self, action, key, value, popup_view):
        popup_view.dismiss()
        if self.engine.event_callback:
            self.engine.event_callback({'type': 'ui_action', 'action': action, key: value})

    def _trigger_exit_to_menu(self, popup):
        popup.dismiss()
        if self.engine.go_back_callback: self.engine.go_back_callback()

    def _trigger_new_round(self, popup):
        popup.dismiss()
        if self.engine.event_callback: self.engine.event_callback({'type': 'ui_action', 'action': 'start_new_round'})

    def show_eliminated_popup(self, online=False):
        if online:
            view = GamePopup(title="Поразка", size_hint=(None, None), size=(VisualConfig.sdp(430), VisualConfig.sdp(220)), auto_dismiss=False)
            layout = BoxLayout(orientation='vertical', padding=VisualConfig.sdp(20), spacing=VisualConfig.sdp(12))
            layout.add_widget(Label(text="Ви вибули з гри.", font_size=VisualConfig.ssp(22), bold=True, size_hint_y=0.45))
            layout.add_widget(Label(text="Гра продовжується без вас.", font_size=VisualConfig.ssp(16), size_hint_y=0.25))
            btn = GameButton(text="Продовжити", size_hint=(None, None), size=(VisualConfig.sdp(220), VisualConfig.sdp(52)), pos_hint={'center_x': 0.5})
            btn.bind(on_release=lambda *_: view.dismiss())
            layout.add_widget(btn)
            view.content = layout
            view.open()
            return

        view = GamePopup(title="Поразка", size_hint=(None, None), size=(VisualConfig.sdp(460), VisualConfig.sdp(260)), auto_dismiss=False)
        layout = BoxLayout(orientation='vertical', padding=VisualConfig.sdp(20), spacing=VisualConfig.sdp(12))
        layout.add_widget(Label(text="Ви програли", font_size=VisualConfig.ssp(22), bold=True, size_hint_y=0.4))
        layout.add_widget(Label(text="Почати нову гру чи вийти в меню?", font_size=VisualConfig.ssp(16), size_hint_y=0.2))
        btn_row = BoxLayout(orientation='horizontal', spacing=VisualConfig.sdp(10), size_hint_y=0.4)
        btn_new = GameButton(text="Нова гра")
        btn_exit = GameButton(text="Вийти в меню")
        btn_new.bind(on_release=lambda *_: self._trigger_new_round(view))
        btn_exit.bind(on_release=lambda *_: self._trigger_exit_to_menu(view))
        btn_row.add_widget(btn_new)
        btn_row.add_widget(btn_exit)
        layout.add_widget(btn_row)
        view.content = layout
        view.open()


# ==========================================
# 2. МЕНЕДЖЕР РОЗТАШУВАННЯ (LAYOUT)
# ==========================================
class LayoutManager:
    """Виконує складні математичні обчислення для розміщення віджетів."""
    def __init__(self, engine):
        self.engine = engine

    def update_all_layouts(self, size):
        w, h = size

        # 1. Battle Widget
        if self.engine.battle_widget:
            self.engine.battle_widget.size_hint = (None, None)
            self.engine.battle_widget.width = w * VisualConfig.BATTLE_AREA_WIDTH_RATIO
            self.engine.battle_widget.height = h * VisualConfig.BATTLE_AREA_HEIGHT_RATIO
            self.engine.battle_widget.center_x = w / 2
            self.engine.battle_widget.center_y = h * VisualConfig.BATTLE_AREA_Y_RATIO

        # 2. UI Elements
        if self.engine.btn_action:
            self.engine.btn_action.size = (VisualConfig.sdp(120), VisualConfig.sdp(50))
                
        if self.engine.suit_indicator:
            self.engine.suit_indicator.size = (VisualConfig.sdp(100), VisualConfig.sdp(100))
            if self.engine.suit_indicator.opacity == 0:
                self.engine.suit_indicator.font_size = VisualConfig.ssp(80)

        # 3. Deck
        if self.engine.deck_widget and not self.engine.is_deck_animating:
            self.engine.deck_widget.size = (VisualConfig.CARD_W, VisualConfig.CARD_H)
            if self.engine.trump_widget:
                self.engine.deck_widget.center_x = w * VisualConfig.DECK_X_RATIO
                self.engine.deck_widget.center_y = h * VisualConfig.DECK_Y_RATIO
                self.engine.trump_widget.size = (VisualConfig.CARD_W, VisualConfig.CARD_H)
                self.engine.trump_widget.center_x = self.engine.deck_widget.center_x + VisualConfig.sdp(40)
                self.engine.trump_widget.center_y = self.engine.deck_widget.center_y

        # 4. Players
        bots, hero = [], None
        for p_id, hand_widget in self.engine.players_map.items():
            if hand_widget.is_main_player: hero = hand_widget
            else: bots.append(hand_widget)

        if hero:
            hero.width = min(w * VisualConfig.HERO_WIDTH_PERCENT, VisualConfig.sdp(VisualConfig.HERO_MAX_WIDTH))
            hero.center_x = w / 2
            hero.y = VisualConfig.sdp(VisualConfig.HERO_BOTTOM_OFFSET)

        if bots:
            self._layout_bots(bots, w, h)
        
        # Верхні кнопки ставимо нижче ряду ботів, щоб не перекривалися.
        self._layout_top_controls(bots, w, h)

        # 5. Table Cards
        if self.engine.cards_on_table:
            for card in self.engine.cards_on_table:
                card.size = (VisualConfig.CARD_W, VisualConfig.CARD_H)
            if getattr(self.engine, 'game_type', None) == "DURAK":
                self.layout_durak_table(animate=False)

    def _layout_top_controls(self, bots, w, h):
        btn_w = VisualConfig.sdp(100)
        btn_h = VisualConfig.sdp(50)
        margin = VisualConfig.sdp(10)

        controls_y = h - btn_h - margin
        if bots:
            bots_bottom = min(bot.y for bot in bots)
            controls_y = bots_bottom - btn_h - VisualConfig.sdp(8)
            controls_y = max(VisualConfig.sdp(12), controls_y)

        if self.engine.btn_back:
            self.engine.btn_back.size = (btn_w, btn_h)
            self.engine.btn_back.pos = (w * 0.02, controls_y)

        if self.engine.btn_score:
            self.engine.btn_score.size = (btn_w, btn_h)
            self.engine.btn_score.pos = (w - btn_w - (w * 0.02), controls_y)

    def _layout_bots(self, bots, w, h):
        """Розміщує ботів у рівний горизонтальний ряд зверху екрану."""
        count = len(bots)
        if count == 0: return

        # Базові розміри руки бота з конфігу
        base_w = VisualConfig.sdp(VisualConfig.BOT_HAND_BASE_WIDTH)
        base_h = VisualConfig.sdp(VisualConfig.BOT_HAND_BASE_HEIGHT)
        max_w = w * VisualConfig.BOT_HAND_MAX_WIDTH_RATIO
        max_h = h * VisualConfig.BOT_HAND_MAX_HEIGHT_RATIO

        # Доступна ширина для ряду ботів (90% від ширини екрану)
        available_width = w * 0.9 
        
        # Відстань між руками ботів
        base_gap = VisualConfig.sdp(20) 
        
        # Обчислюємо загальну ідеальну ширину всього ряду
        total_ideal_width = (count * base_w) + ((count - 1) * base_gap)
        
        # Якщо боти не влазять в екран, обчислюємо масштаб
        scale = 1.0
        if total_ideal_width > available_width:
            scale = max(VisualConfig.BOT_MIN_SCALE, available_width / total_ideal_width)

        # Фактичні розміри з урахуванням масштабу
        actual_w = min(base_w * scale, max_w)
        actual_h = min(base_h * scale, max_h)
        actual_gap = base_gap * scale

        # Загальна фактична ширина для відцентрування
        total_width = (count * actual_w) + ((count - 1) * actual_gap)
        
        # Початкова позиція (найлівіший центр)
        start_x = (w - total_width) / 2 + (actual_w / 2)
        
        # Верхня межа екрану (для всіх однакова)
        # Лишаємо місце зверху під ім'я, яке відмальовується над рукою.
        max_top = h - VisualConfig.sdp(VisualConfig.BOT_TOP_OFFSET) - VisualConfig.sdp(24)

        # Розставляємо ботів по лінії
        for i, bot in enumerate(bots):
            bot.width = actual_w
            bot.height = actual_h
            bot.center_x = start_x + i * (actual_w + actual_gap)
            bot.top = max_top # Жорстко прив'язуємо до верху
            
            bot.update_hand_layout()

    def calc_durak_pair_centers(self, count):
        if not self.engine.battle_widget or count <= 0:
            return []

        card_w = VisualConfig.CARD_W
        # Захист перекриває 70% карти атаки => зсув 30% ширини.
        defense_shift_x = card_w * 0.30
        pair_slot_w = card_w + defense_shift_x

        desired_gap = VisualConfig.sdp(18)
        available = self.engine.battle_widget.width
        gap = desired_gap

        if count > 1:
            desired_total = count * pair_slot_w + (count - 1) * desired_gap
            if desired_total > available:
                # Стискаємо ряд, але не даємо картам повністю "наїхати" одна на одну.
                gap = max(-pair_slot_w * 0.25, (available - count * pair_slot_w) / (count - 1))

        total_w = count * pair_slot_w + (count - 1) * gap
        start_cx = self.engine.battle_widget.center_x - total_w / 2 + pair_slot_w / 2
        return [(start_cx + i * (pair_slot_w + gap), self.engine.battle_widget.center_y) for i in range(count)]

    def layout_durak_table(self, animate=True, focus_card=None, on_focus_complete=None):
        centers = self.calc_durak_pair_centers(len(self.engine.durak_pairs))
        if not centers:
            if on_focus_complete:
                on_focus_complete()
            return

        attack_defense_shift_x = VisualConfig.CARD_W * 0.30
        defense_shift_y = VisualConfig.CARD_H * 0.22
        anim_duration = max(0.12, VisualConfig.PLAY_SPEED)

        focus_bound = False
        for i, pair in enumerate(self.engine.durak_pairs):
            pair_cx, pair_cy = centers[i]
            target_map = {
                "attack": (pair_cx - (attack_defense_shift_x / 2), pair_cy),
                "defense": (pair_cx + (attack_defense_shift_x / 2), pair_cy + defense_shift_y),
            }

            for key in ("attack", "defense"):
                card = pair.get(key)
                if not card:
                    continue

                tx, ty = target_map[key]
                card.size = (VisualConfig.CARD_W, VisualConfig.CARD_H)
                card.angle = 0

                if animate:
                    Animation.stop_all(card)
                    anim = Animation(
                        center_x=tx,
                        center_y=ty,
                        angle=0,
                        size=(VisualConfig.CARD_W, VisualConfig.CARD_H),
                        duration=anim_duration,
                        t='out_quad'
                    )
                    if card is focus_card and on_focus_complete and not focus_bound:
                        anim.bind(on_complete=lambda *_: on_focus_complete())
                        focus_bound = True
                    anim.start(card)
                else:
                    card.center_x, card.center_y = tx, ty

        if on_focus_complete and (focus_card is None or not focus_bound):
            on_focus_complete()

# ==========================================
# 3. ГОЛОВНИЙ ДВИГУН (VISUAL ENGINE)
# ==========================================
class VisualEngine(FloatLayout):
    """Головний фасад. Делегує Popup вікна та математику Layout, керуючи об'єктами Kivy."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Ініціалізація помічників
        self.dialogs = DialogManager(self)
        self.layout_manager = LayoutManager(self)

        self.players_map = {}   
        self.player_widgets_list = []
        self.deck_widget = None
        self.battle_widget = None
        self.trump_widget = None 
        self.trump_suit = None
        self.cards_on_table = [] 
        self.durak_pairs = []
        
        self.btn_action = None 
        self.btn_back = None
        self.btn_score = None
        self.event_callback = None
        self.go_back_callback = None 
        self.is_deck_animating = False
        self.hero_widget = None 
        self.turn_label = None
        self.suit_indicator = None

        self.input_locked = False
        self.online_mode = False
        self.hero_elimination_popup_shown = False

        with self.canvas.before:
            Color(*VisualConfig.TABLE_COLOR)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)

        self.bind(size=self._on_resize, pos=self._on_resize)

    def set_callback(self, callback_func):
        self.event_callback = callback_func

    def add_common_ui(self, go_back_callback):
        self.go_back_callback = go_back_callback
        
        # Кнопка Назад
        self.btn_back = GameButton(text="< Назад", size_hint=(None, None), size=(VisualConfig.sdp(100), VisualConfig.sdp(50)))
        self.btn_back.bind(on_release=lambda x: self.go_back_callback())
        self.add_widget(self.btn_back)

        # Кнопка Дії
        self.btn_action = GameButton(text="Взяти", size_hint=(None, None), size=(VisualConfig.sdp(120), VisualConfig.sdp(50)), pos_hint={'right': 0.95, 'y': 0.25})
        self.btn_action.opacity = 0
        self.btn_action.disabled = True
        self.btn_action.bind(on_release=self._on_action_click)
        self.add_widget(self.btn_action)

    def _on_action_click(self, instance):
        if self.input_locked: return
        if self.event_callback:
            self.event_callback({'type': 'ui_action', 'action': "take" if instance.text == "Взяти" else "pass"})

    def execute_instruction(self, instruction, on_complete=None):
        cmd = instruction.get("cmd")
        def done(*args):
            if on_complete: on_complete()

        # Анімаційні команди
        if cmd == "INITIAL_DEAL": 
            duration = self._initial_deal(instruction)
            Clock.schedule_once(done, duration)
        elif cmd == "PLAY_CARD": 
            self._play_card(instruction, callback=done)
        elif cmd == "PLAY_CARDS":
            self._play_cards(instruction, callback=done)
        elif cmd == "TAKE_CARDS": 
            self._animate_take_cards(instruction, callback=done)
        elif cmd == "DRAW_CARDS_ANIMATION": 
            duration = self._draw_cards_animation(instruction)
            Clock.schedule_once(done, duration)
        elif cmd == "CLEAR_TABLE":
            duration = self._clear_table(instruction)
            Clock.schedule_once(done, duration)
        elif cmd == "ANIMATE_RESHUFFLE":
            self._animate_reshuffle_table(instruction, callback=done)
        elif cmd == "CHOOSING_DEALER":
             self._animate_dealer_selection(instruction.get("dealer_idx"), instruction.get("is_random"), callback=done)

        # UI / Миттєві команди (Частина делегується в DialogManager)
        else:
            if cmd == "SETUP_TABLE": self._setup_table(instruction)
            elif cmd == "SYNC_HANDS": self._sync_hands(instruction)
            elif cmd == "UPDATE_CONTROLS": self._update_controls(instruction)
            elif cmd == "UPDATE_TURN": self._update_turn_label(instruction)
            elif cmd == "SHOW_ORDERED_SUIT": self._show_ordered_suit(instruction)
            elif cmd == "HIDE_ORDERED_SUIT": self._hide_ordered_suit(instruction)
            elif cmd == "SHOW_ERROR": print(f"Error: {instruction.get('text')}")
            # Делегація
            elif cmd == "ASK_THROW": pass
            elif cmd == "SHOW_PLAYER_COUNT": self.dialogs.show_player_count_popup(instruction)
            elif cmd == "SHOW_WINNER": self.dialogs.show_winner_popup(instruction)
            elif cmd == "SHOW_SUIT_SELECTOR": self.dialogs.show_suit_selection(instruction.get("player_id"))
            elif cmd == "SHOW_BONUS_SELECTOR": self.dialogs.show_jack_bonus_selection(instruction.get("player_id"), instruction.get("mult"), instruction.get("sub"))
            elif cmd == "SHOW_DURAK_DEFENSE_CHOICE": self.dialogs.show_durak_defense_choice(instruction.get("player_id"))
            elif cmd == "SHOW_BRIDGE_DECISION": self.dialogs.show_bridge_decision(instruction.get("player_id"))
            elif cmd == "INVALID_CHAIN_CARD": self._show_invalid_chain(instruction)
            elif cmd == "SHOW_ELIMINATED": self.dialogs.show_eliminated_popup(bool(instruction.get("online", False)))
            elif cmd == "SHOW_SCORES": self.dialogs.show_score_popup(instruction.get("is_round_end"), instruction.get("scores"))
            
            done()

    # Всі складні методи Kivy та анімації залишаються тут...
    # (Оскільки логіка тут сильно залежить від віджетів Kivy, її краще не розбивати далі, 
    # щоб не створювати циклічних залежностей)
    
    def _setup_table(self, data):
        self.clear_widgets()
        self.input_locked = True
        self.game_type = data.get("game_type")
        self.online_mode = bool(data.get("online", False))
        self.hero_elimination_popup_shown = False
        self.btn_back = None
        self.btn_score = None

        if self.game_type == "BRIDGE":
            self.btn_score = GameButton(text="Рахунок", size_hint=(None, None), size=(VisualConfig.sdp(100), VisualConfig.sdp(50)), background_color=(0.5, 0.5, 0.5, 1))
            self.btn_score.bind(on_release=lambda x: self.dialogs.show_score_popup(is_round_end=False))
            self.add_widget(self.btn_score)

        self.players_map, self.player_widgets_list, self.cards_on_table, self.durak_pairs = {}, [], [], []
        self.trump_widget, self.trump_suit = None, None
        self.add_common_ui(self.go_back_callback)

        self.suit_indicator = Label(text="?", font_size=VisualConfig.ssp(80), font_name='DejaVuSans', color=(1,1,1,1), outline_width=2, outline_color=(0,0,0,1), size_hint=(None, None), size=(VisualConfig.sdp(100), VisualConfig.sdp(100)), pos_hint={'right': 0.97, 'center_y': 0.5}, opacity=0)
        self.add_widget(self.suit_indicator)
        
        self.battle_widget = BattleAreaWidget()
        self.battle_widget.on_click_callback = self._on_battle_area_click
        self.add_widget(self.battle_widget)

        for p_data in data.get("players", []):
            hand = HandWidget(name=p_data["name"], player_id=p_data["id"], is_main_player=p_data["is_hero"], multi_select=(data.get("multi_select", True) if p_data["is_hero"] else False))
            self.add_widget(hand)
            self.players_map[p_data["id"]] = hand
            self.player_widgets_list.append(hand)
            if p_data["is_hero"]:
                self.hero_widget = hand
                hand.bind(selected_cards=self._on_hero_card_selection)

        self.deck_widget = DeckWidget()
        self.deck_widget.opacity = 0
        self.deck_widget.bind(on_release=self._on_deck_click)
        self.add_widget(self.deck_widget)

        self.layout_manager.update_all_layouts(self.size)
        Clock.schedule_once(self._start_deck_animation, 0.1)

    def _on_resize(self, instance, value):
        VisualConfig.update_scale(self.size)
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos, self.bg_rect.size = self.pos, self.size
        self.layout_manager.update_all_layouts(self.size)

    # ------------------------------------------
    # Методи взаємодії та внутрішньої логіки Kivy
    # ------------------------------------------
    def _on_hero_card_selection(self, instance, selected_cards):
        if self.input_locked: 
            self.battle_widget.active = False
            return
        if self.battle_widget:
            self.battle_widget.active = (len(selected_cards) > 0)

    def _on_battle_area_click(self):
        if self.input_locked or not self.hero_widget or not self.hero_widget.selected_cards: return
        cards_ids = [f"{c.rank}_{c.suit}" for c in self.hero_widget.selected_cards]

        if self.game_type != "BRIDGE":
            for c in list(self.hero_widget.selected_cards):
                c.selected = False
            self.hero_widget.selected_cards.clear()
            self.hero_widget.update_hand_layout()
            if self.battle_widget:
                self.battle_widget.active = False

        if self.event_callback:
            self.event_callback({'type': 'ui_action', 'action': 'play', 'cards': cards_ids})

    def _on_deck_click(self, instance):
        if self.input_locked or self.game_type != "BRIDGE": return
        if self.hero_widget and getattr(self.hero_widget, "is_eliminated", False): return
        if self.event_callback: self.event_callback({'type': 'ui_action', 'action': 'take'})

    def _start_deck_animation(self, dt):
        if not self.deck_widget: return
        self.deck_widget.center_x, self.deck_widget.center_y = self.width / 2, self.height / 2
        anim = Animation(opacity=1, duration=0.5)
        anim.bind(on_complete=lambda a, w: setattr(self, 'is_deck_animating', False))
        anim.start(self.deck_widget)

    def _update_controls(self, data):
        if not self.btn_action: return
        show = data.get("show_action_btn", False)
        if show:
            self.btn_action.text = data.get("btn_text", "Взяти")
            self.btn_action.disabled = False
            if self.btn_action.opacity == 0: Animation(opacity=1, duration=0.2).start(self.btn_action)
            else: self.btn_action.opacity = 1
        else:
            self.btn_action.disabled = True
            Animation(opacity=0, duration=0.2).start(self.btn_action)

    def _update_turn_label(self, data):
        player_id = data.get("player_id")
        for p_id, hand in self.players_map.items():
            hand.apply_turn_highlight(p_id == player_id)

    def _clear_table(self, data=None):
        if not self.cards_on_table:
            self.durak_pairs = []
            return 0

        tx, ty = -VisualConfig.sdp(150), self.height / 2
        for card in self.cards_on_table:
            anim = Animation(x=tx, y=ty, opacity=0, duration=VisualConfig.DISCARD_SPEED, t='in_back')
            anim.bind(on_complete=lambda a, w: self.remove_widget(w))
            anim.start(card)
        self.cards_on_table, self.durak_pairs = [], []
        return VisualConfig.DISCARD_SPEED

    def on_touch_down(self, touch):
        return True if self.input_locked else super().on_touch_down(touch)
    def on_touch_move(self, touch):
        return True if self.input_locked else super().on_touch_move(touch)
    def on_touch_up(self, touch):
        return True if self.input_locked else super().on_touch_up(touch)

    # ------------------------------------------
    # Анімації роздачі та ходу карт
    # ------------------------------------------
    def _initial_deal(self, data):
        hands_list, trump_data, starting_trump = data.get("hands", []), data.get("trump_card"), data.get("starting_trump")
        if trump_data: self.trump_suit = trump_data.get("suit")
        
        for p_data in hands_list:
            hand = self.players_map.get(p_data["player_id"])
            if hand:
                if hasattr(hand, "set_eliminated"):
                    hand.set_eliminated(bool(p_data.get("is_eliminated", False)))
                hand.cards = []
                hand.clear_widgets()
                if not hand.is_main_player:
                    hand.setup_opponent_ui()
                else:
                    hand._ensure_name_label()

        self._check_online_hero_elimination_popup()

        deal_queue = []
        max_cards = max([len(h['cards_data']) for h in hands_list]) if hands_list else 0
        for i in range(max_cards):
            for p_data in hands_list:
                if i < len(p_data['cards_data']): deal_queue.append((p_data['player_id'], p_data['cards_data'][i]))

        delay, step = 0.5, 0.2
        deck_rem = data.get("deck_count", 0)
        
        if self.deck_widget:
            self.deck_widget.cards_count = deck_rem + len(deal_queue)
            self.deck_widget.update_canvas()

        for p_id, c_info in deal_queue:
            Clock.schedule_once(lambda dt, pid=p_id, c=c_info: self._fly_card_from_deck(pid, c), delay)
            delay += step

        completion_time = delay + 0.5
        
        if trump_data and deck_rem > 0:
            Clock.schedule_once(lambda dt: self._animate_trump_sequence(trump_data), completion_time)
            completion_time += 1.0 
        else:
            Clock.schedule_once(lambda dt: self._move_deck_and_trump_to_side(), completion_time)
            
        if starting_trump:
            Clock.schedule_once(lambda dt: self._show_starting_trump(starting_trump), completion_time + 0.5)
            completion_time += 2.0

        return completion_time

    def _animate_trump_sequence(self, trump_data):
        if not self.deck_widget: return
        self.trump_suit = trump_data.get('suit')
        self.trump_widget = CardWidget(suit=trump_data['suit'], rank=trump_data['rank'], is_face_up=False)
        self.trump_widget.center, self.trump_widget.size = self.deck_widget.center, (VisualConfig.CARD_W, VisualConfig.CARD_H)
        
        self.add_widget(self.trump_widget)
        self.remove_widget(self.deck_widget)
        self.add_widget(self.deck_widget)
        
        AnimationManager.animate_trump_reveal(self.trump_widget, self.deck_widget, duration=0.6)
        Clock.schedule_once(lambda dt: self._move_deck_and_trump_to_side(), 0.8)

    def _move_deck_and_trump_to_side(self):
        tx, ty = self.width * VisualConfig.DECK_X_RATIO, self.height * VisualConfig.DECK_Y_RATIO
        AnimationManager.animate_move_deck_to_side(self.deck_widget, self.trump_widget, (tx, ty), duration=0.8)
        Clock.schedule_once(lambda dt: self._unlock_input(), 0.85)

    def _unlock_input(self):
        self.input_locked = False
        if self.event_callback: self.event_callback({"type": "system", "action": "deal_complete"})

    def _fly_card_from_deck(self, player_id, card_data):
        hand = self.players_map.get(player_id)
        if not hand or not self.deck_widget: return

        is_hero = hand.is_main_player
        use_trump = self.trump_widget and self.deck_widget.cards_count == 1
        
        if use_trump:
            card = self.trump_widget
            self.trump_widget = None
            if card.parent: card.parent.remove_widget(card)
            self.add_widget(card)
            card.center = self.deck_widget.center
            card.opacity, card.is_face_up = 1, is_hero
        else:
            card = CardWidget(suit=card_data['suit'], rank=card_data['rank'], is_face_up=False)
            card.center, card.opacity = self.deck_widget.center, 0
            self.add_widget(card)
            Clock.schedule_once(lambda dt: setattr(card, 'opacity', 1), 0.05)

        card.pos_hint, card.size_hint = {}, (None, None)
        card.size = (VisualConfig.CARD_W, VisualConfig.CARD_H) if is_hero else (VisualConfig.BOT_CARD_W, VisualConfig.BOT_CARD_H)

        def on_arrival(anim, widget):
            if not widget.parent: return
            w_pos = widget.to_window(*widget.pos)
            self.remove_widget(widget)
            local_pos = hand.to_widget(*w_pos)
            
            dup = next((c for c in hand.cards if c.suit == widget.suit and c.rank == widget.rank), None)
            if dup: hand.remove_card(dup)
            hand.add_card(widget, initial_pos=local_pos)

        AnimationManager.animate_deal_to_player(card, hand, duration=VisualConfig.DEAL_SPEED, on_complete=on_arrival)

        if self.deck_widget.cards_count > 0:
            self.deck_widget.cards_count -= 1
            self.deck_widget.update_canvas()
        if self.deck_widget.cards_count == 0 and self.trump_suit:
            self._show_ordered_suit({'suit': self.trump_suit})

    def _draw_cards_animation(self, data):
        delay, step = 0, 0.3
        for c in data.get("cards", []):
            Clock.schedule_once(lambda dt, pid=data.get("player_id"), ci=c: self._fly_card_from_deck(pid, ci), delay)
            delay += step
        return delay + 0.5

    def _prepare_table_card(self, player_id, card_data):
        hand = self.players_map.get(player_id)
        if not hand:
            return None, None

        target = next((c for c in hand.cards if f"{c.rank}_{c.suit}" == card_data.get("id")), None)
        if not target:
            target = CardWidget(suit=card_data['suit'], rank=card_data['rank'])
            target.center, target.opacity = hand.center, 0
            self.add_widget(target)
            Clock.schedule_once(lambda dt: setattr(target, 'opacity', 1), 0.05)

        if target in hand.cards:
            hand.remove_card(target)
            w_pos = target.to_window(*target.pos)
            if target.parent:
                target.parent.remove_widget(target)
            self.add_widget(target)
            target.pos = self.to_widget(*w_pos)
        elif target.parent is not self:
            if target.parent:
                target.parent.remove_widget(target)
            self.add_widget(target)

        target.on_click_action = self._on_battle_area_click
        target.is_face_up = True
        target.size = (VisualConfig.CARD_W, VisualConfig.CARD_H)

        if target not in self.cards_on_table:
            self.cards_on_table.append(target)

        return hand, target

    def _clear_hero_played_selection(self, card_ids):
        if self.game_type != "BRIDGE" or not self.hero_widget:
            return
        ids = set(card_ids or [])
        if not ids:
            return
        hand = self.hero_widget
        for c in list(hand.selected_cards):
            cid = f"{c.rank}_{c.suit}"
            if cid in ids:
                c.selected = False
                hand.selected_cards.remove(c)
        hand.update_hand_layout()
        if self.battle_widget:
            self.battle_widget.active = (len(hand.selected_cards) > 0)

    def _layout_standard_table(self, animate=True, focus_cards=None, on_complete=None):
        cards = [c for c in self.cards_on_table if c]
        if not cards:
            if on_complete:
                on_complete()
            return

        count = len(cards)
        card_w = VisualConfig.CARD_W
        center_x = self.battle_widget.center_x if self.battle_widget else self.center_x
        center_y = self.battle_widget.center_y if self.battle_widget else self.center_y
        max_w = (self.battle_widget.width * 0.78) if self.battle_widget else (self.width * 0.62)
        max_w = max(card_w, max_w)

        # Для Бріджу карти мають лягати щільно одна на одну.
        if self.game_type == "BRIDGE":
            natural_step = card_w * 0.22
            step = min(natural_step, max(VisualConfig.sdp(8), (max_w - card_w) / max(1, count - 1)))
            arc_amp = VisualConfig.sdp(6)
            angle_span = 8
        else:
            step = min(VisualConfig.sdp(34), max(VisualConfig.sdp(14), (max_w - card_w) / max(1, count - 1)))
            arc_amp = VisualConfig.sdp(12)
            angle_span = 16

        total_w = (count - 1) * step + card_w
        start_cx = center_x - (total_w / 2) + (card_w / 2)

        focus_set = set(focus_cards or [])
        callback_bound = False

        for i, card in enumerate(cards):
            t = 0 if count == 1 else (i / (count - 1))
            arc = math.sin(t * math.pi) * arc_amp
            angle = -(angle_span / 2) + (angle_span * t)
            tx = start_cx + (i * step)
            ty = center_y + arc

            if animate:
                Animation.stop_all(card)
                anim = Animation(
                    center_x=tx,
                    center_y=ty,
                    angle=angle,
                    size=(VisualConfig.CARD_W, VisualConfig.CARD_H),
                    duration=VisualConfig.PLAY_SPEED,
                    t='out_quad'
                )
                should_bind = (on_complete is not None) and (card in focus_set or (not focus_set and i == len(cards) - 1))
                if should_bind and not callback_bound:
                    anim.bind(on_complete=lambda *_: on_complete())
                    callback_bound = True
                anim.start(card)
            else:
                card.center_x, card.center_y = tx, ty
                card.angle = angle
                card.size = (VisualConfig.CARD_W, VisualConfig.CARD_H)

        if on_complete and not animate:
            on_complete()
        elif on_complete and animate and not callback_bound:
            Clock.schedule_once(lambda dt: on_complete(), VisualConfig.PLAY_SPEED)

    def _bridge_stack_center(self):
        if self.battle_widget:
            return self.battle_widget.center_x, self.battle_widget.center_y
        return self.center_x, self.center_y

    def _animate_to_bridge_stack(self, cards, on_complete=None):
        cards = [c for c in (cards or []) if c]
        if not cards:
            if on_complete:
                on_complete()
            return

        tx, ty = self._bridge_stack_center()
        callback_bound = False
        for i, card in enumerate(cards):
            Animation.stop_all(card)
            offset_x = random.randint(-8, 8)
            offset_y = random.randint(-8, 8)
            angle = random.randint(-10, 10)
            anim = Animation(
                center_x=tx + offset_x,
                center_y=ty + offset_y,
                angle=angle,
                size=(VisualConfig.CARD_W, VisualConfig.CARD_H),
                duration=VisualConfig.PLAY_SPEED,
                t='out_quad'
            )
            if on_complete and not callback_bound and i == len(cards) - 1:
                anim.bind(on_complete=lambda *_: on_complete())
                callback_bound = True
            anim.start(card)

        if on_complete and not callback_bound:
            Clock.schedule_once(lambda dt: on_complete(), VisualConfig.PLAY_SPEED)

    def _play_card(self, data, callback=None):
        p_id, card_data, is_durak = data.get("player_id"), data.get("card"), (self.game_type == "DURAK")
        self._clear_hero_played_selection([card_data.get("id")])
        hand, target = self._prepare_table_card(p_id, card_data)
        if not hand or not target:
            if callback: callback()
            return

        if is_durak:
            durak_is_def = bool(data.get("durak_is_defense"))
            pair_idx = next((i for i, p in enumerate(self.durak_pairs) if p.get("attack") and not p.get("defense")), None) if durak_is_def else None

            if durak_is_def and pair_idx is not None:
                self.durak_pairs[pair_idx]["defense"] = target
            else:
                self.durak_pairs.append({"attack": target, "defense": None})

            # Єдина точка розкладки: кожен новий хід плавно перецентровує всі карти.
            self.layout_manager.layout_durak_table(animate=True, focus_card=target, on_focus_complete=callback)
            return

        if self.game_type == "BRIDGE":
            self._animate_to_bridge_stack([target], on_complete=callback)
            return

        self._layout_standard_table(animate=True, focus_cards=[target], on_complete=callback)

    def _play_cards(self, data, callback=None):
        p_id = data.get("player_id")
        cards_data = data.get("cards", []) or []
        self._clear_hero_played_selection([c.get("id") for c in cards_data])
        is_durak = (self.game_type == "DURAK")
        if not cards_data:
            if callback:
                callback()
            return

        new_targets = []
        for card_data in cards_data:
            hand, target = self._prepare_table_card(p_id, card_data)
            if hand and target:
                new_targets.append(target)

        if not new_targets:
            if callback:
                callback()
            return

        if is_durak:
            # Для Дурня відпрацьовуємо покроково через існуючу логіку PLAY_CARD.
            queue = list(cards_data)
            def play_next(*_):
                if not queue:
                    if callback:
                        callback()
                    return
                card_info = queue.pop(0)
                self._play_card(
                    {
                        "player_id": p_id,
                        "card": card_info,
                        "durak_is_defense": data.get("durak_is_defense", False),
                    },
                    callback=play_next
                )
            play_next()
            return

        if self.game_type == "BRIDGE":
            self._animate_to_bridge_stack(new_targets, on_complete=callback)
            return

        self._layout_standard_table(animate=True, focus_cards=new_targets, on_complete=callback)

    def _sync_hands(self, data):
        for p_data in data.get("hands", []):
            hand = self.players_map.get(p_data["player_id"])
            if not hand: continue
            is_eliminated = bool(p_data.get("is_eliminated", False))
            new_cards = p_data.get("cards_data", [])
            new_ids = {f"{c['rank']}_{c['suit']}" for c in new_cards}
            
            for w in [c for c in hand.cards if f"{c.rank}_{c.suit}" not in new_ids]: hand.remove_card(w)
            existing = {f"{c.rank}_{c.suit}" for c in hand.cards}
            
            for ci in new_cards:
                if f"{ci['rank']}_{ci['suit']}" not in existing:
                    nc = CardWidget(suit=ci['suit'], rank=ci['rank'])
                    nc.center = hand.center
                    hand.add_card(nc)

            if not hand.is_main_player:
                hand.setup_opponent_ui()
                if hand.card_count_label and hand.card_count_label not in hand.children: hand.add_widget(hand.card_count_label)
            elif hasattr(hand, 'clean_canvas'):
                hand.clean_canvas()
                hand._ensure_name_label()
            if hasattr(hand, "set_eliminated"):
                hand.set_eliminated(is_eliminated)

        self._check_online_hero_elimination_popup()

    def _check_online_hero_elimination_popup(self):
        if not self.online_mode or self.hero_elimination_popup_shown:
            return
        if not self.hero_widget:
            return
        if getattr(self.hero_widget, "is_eliminated", False):
            self.hero_elimination_popup_shown = True
            self.dialogs.show_eliminated_popup(online=True)

    def _show_invalid_chain(self, data):
        hand = self.hero_widget
        if not hand:
            return

        keep_ids = set(data.get("keep_ids", []))
        invalid_id = data.get("invalid_id")

        for c in list(hand.selected_cards):
            cid = f"{c.rank}_{c.suit}"
            if cid not in keep_ids and cid != invalid_id:
                c.selected = False
                hand.selected_cards.remove(c)

        invalid_card = None
        for c in hand.cards:
            if f"{c.rank}_{c.suit}" == invalid_id:
                invalid_card = c
                break

        if invalid_card:
            invalid_card.invalid = True
            if invalid_card not in hand.selected_cards:
                invalid_card.selected = True
                hand.selected_cards.append(invalid_card)

        hand.update_hand_layout()

        def clear_invalid(dt):
            if invalid_card:
                invalid_card.invalid = False
                if invalid_card in hand.selected_cards:
                    invalid_card.selected = False
                    hand.selected_cards.remove(invalid_card)
            hand.update_hand_layout()

        Clock.schedule_once(clear_invalid, 1.2)

    def _animate_take_cards(self, data, callback=None):
        hand = self.players_map.get(data.get("player_id"))
        if not hand or not self.cards_on_table:
            if callback: callback()
            return

        tx, ty, completed, total = hand.center_x, hand.center_y, 0, len(self.cards_on_table)
        def on_one(a, w):
            nonlocal completed
            self.remove_widget(w)
            completed += 1
            if completed >= total and callback: callback()

        for card in self.cards_on_table:
            card.selected = False
            if card.parent: card.parent.remove_widget(card)
            self.add_widget(card)
            anim = Animation(center_x=tx, center_y=ty, opacity=0, size=(0, 0), duration=0.6, t='in_back')
            anim.bind(on_complete=on_one)
            anim.start(card)
        self.cards_on_table = []
        # Стіл після "взяв" має починатися з чистого стану пар.
        self.durak_pairs = []

    def _animate_reshuffle_table(self, data, callback=None):
        if not self.deck_widget or not self.cards_on_table:
            if callback: callback()
            return
            
        tc, tx, ty = data.get("top_card"), self.deck_widget.center_x, self.deck_widget.center_y
        to_move = [c for c in self.cards_on_table if not (c.suit == tc['suit'] and c.rank == tc['rank'])]
        
        if not to_move:
            if callback: callback()
            return

        completed, total = 0, len(to_move)
        def on_one(a, w):
            nonlocal completed
            self.remove_widget(w)
            completed += 1
            if completed >= total and callback: callback()

        for card in to_move:
            if card.parent: card.parent.remove_widget(card)
            self.add_widget(card)
            anim = Animation(center_x=tx, center_y=ty, opacity=0, size=(0, 0), duration=0.6, t='in_back')
            anim.bind(on_complete=on_one)
            anim.start(card)
            
        self.cards_on_table = [c for c in self.cards_on_table if c not in to_move]
        self.deck_widget.cards_count = data.get("new_count", 0)
        self.deck_widget.opacity = 1
        self.deck_widget.update_canvas()

    def _animate_dealer_selection(self, target_idx, is_random, callback):
        if not self.player_widgets_list or target_idx is None:
            if callback: callback()
            return
        
        num = len(self.player_widgets_list)
        target_idx = target_idx % num
        steps = []
        
        if is_random:
            total = (num * 2) + target_idx
            for i in range(total + 1):
                delay = 0.1 + (0.05 * (5 - (total - i)) if i > total - 5 else 0)
                steps.append((i % num, delay))
        else:
            steps = [(target_idx, 0.8)]

        def play_step(idx):
            if idx >= len(steps):
                for w in self.player_widgets_list: w.opacity = 1.0
                if callback: callback()
                return
            p_idx, dur = steps[idx]
            for i, w in enumerate(self.player_widgets_list): w.opacity = 1.0 if i == p_idx else 0.5
            Clock.schedule_once(lambda dt: play_step(idx + 1), dur)

        play_step(0)

    def _show_starting_trump(self, data):
        if not data: return
        hand = self.players_map.get(data.get("player_id"))
        if not hand: return

        suit, rank = data.get("suit"), data.get("rank")
        target = next((c for c in hand.cards if c.suit == suit and c.rank == rank), None)
        if not target: target = CardWidget(suit=suit, rank=rank, is_face_up=hand.is_main_player)

        if target in hand.cards: hand.remove_card(target)
        elif target.parent: target.parent.remove_widget(target)

        cw_pos = target.to_window(*target.pos)
        self.add_widget(target)
        target.pos, target.size, target.is_face_up = self.to_widget(*cw_pos), (VisualConfig.CARD_W, VisualConfig.CARD_H), True

        def on_back(anim, widget):
            if widget.parent:
                w_pos = widget.to_window(*widget.pos)
                self.remove_widget(widget)
                widget.is_face_up = hand.is_main_player
                hand.add_card(widget, initial_pos=hand.to_widget(*w_pos))
                hand.update_hand_layout()

        anim = Animation(center_x=self.center_x, center_y=self.center_y, duration=0.5, t='out_quad') + Animation(duration=1.5) + Animation(center_x=hand.center_x, center_y=hand.center_y, duration=0.5, t='out_quad')
        anim.bind(on_complete=on_back)
        anim.start(target)

    def _show_ordered_suit(self, data):
        suits_info = {'hearts': ('♥', (1, 0, 0, 1)), 'diamonds': ('♦', (1, 0, 0, 1)), 'clubs': ('♣', (0.2, 0.2, 0.2, 1)), 'spades': ('♠', (0.2, 0.2, 0.2, 1))}
        info = suits_info.get(data.get('suit'))
        if info and self.suit_indicator:
            self.suit_indicator.text, self.suit_indicator.color = info[0], info[1]
            self.suit_indicator.opacity, self.suit_indicator.font_size = 1, VisualConfig.ssp(10)
            (Animation(font_size=VisualConfig.ssp(100), duration=0.2, t='out_back') + Animation(font_size=VisualConfig.ssp(80), duration=0.1)).start(self.suit_indicator)

    def _hide_ordered_suit(self, data):
        if self.suit_indicator and self.suit_indicator.opacity > 0:
            Animation(opacity=0, duration=0.2).start(self.suit_indicator)
