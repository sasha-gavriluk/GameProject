from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock

from gui.sreen.BaseScreen import BaseScreen
from gui.utils.Component import HandWidget, TableWidget, CardWidget, DeckWidget
from gui.utils.AnimationManager import AnimationManager

class WarGameScreen(BaseScreen):
    def build_ui(self):
        # 1. Основний контейнер
        self.add_widget(self.ui.root)

        # 2. Фон
        with self.ui.root.canvas.before:
            Color(*get_color_from_hex('#27ae60'))
            self.rect = Rectangle(size=self.ui.root.size, pos=self.ui.root.pos)
        self.ui.root.bind(size=self._update_bg, pos=self._update_bg)

        # 3. Головний стіл
        self.ui.add("game_table", "TableWidget") 

        # 4. ПАНЕЛЬ КНОПОК (Центр зліва)
        self.ui.add("controls_panel", "BoxLayout", 
                    parent="game_table",
                    orientation='vertical',
                    size_hint=(None, None),
                    width=dp(140),
                    height=dp(120),
                    spacing=dp(10),
                    pos_hint={'x': 0.02, 'center_y': 0.5}) # Зліва по центру

        self.ui.add("btn_move", "GameButton", parent="controls_panel", text="ХІД")
        self.ui.set_action("btn_move", "on_release", lambda x: self.action_make_move())

        self.ui.add("btn_take", "GameButton", parent="controls_panel", text="ВЗЯТИ")
        self.ui.set_action("btn_take", "on_release", lambda x: self.action_take_cards())

        # 5. Кнопка Назад (залишаємо зверху)
        self.ui.add("btn_back", "MenuButton", 
                    parent="game_table", text="<",
                    size_hint=(None, None), size=(dp(50), dp(50)),
                    pos_hint={'x': 0.02, 'top': 0.98})
        self.ui.set_action("btn_back", "on_release", lambda x: self.controller.switch_screen('local_select'))

        # 6. РУКИ (Виправлено перекриття)
        # Рука ГРАВЦЯ (Знизу)
        self.ui.add("player_hand_container", "AnchorLayout", 
                    parent="game_table",
                    anchor_x='center', anchor_y='bottom',
                    size_hint=(1, 0.2), # Обмежена висота
                    pos_hint={'center_x': 0.5, 'y': 0.02})

        # Рука ОПОНЕНТА (Зверху)
        self.ui.add("opponent_hand_container", "AnchorLayout", 
                    parent="game_table",
                    anchor_x='center', anchor_y='top',
                    size_hint=(0.9, 0.2), # Обмежена висота
                    pos_hint={'center_x': 0.5, 'top': 0.98})

        self.ui.build()

        # Зберігаємо посилання
        self.table = self.ui.registry["game_table"]
        self.player_hand = HandWidget(max_selected=1)
        self.ui.registry["player_hand_container"].add_widget(self.player_hand)

        self.opponent_hand = HandWidget(max_selected=0)
        self.ui.registry["opponent_hand_container"].add_widget(self.opponent_hand)

        # 7. КОЛОДА (Центр справа)
        self.deck_widget = DeckWidget(pos_hint={'right': 0.98, 'center_y': 0.5}) # Опущена
        self.deck_widget.bind(on_release=lambda x: self.action_draw_from_deck())
        self.table.add_widget(self.deck_widget)

    def _update_bg(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def on_enter(self):
        """Викликається, коли ми реально заходимо на екран"""
        self.prepare_game()

    def prepare_game(self):
        """Очищення столу та запуск роздачі"""
        self.player_hand.clear_widgets()
        # Даємо системі 0.1 сек на стабілізацію екрану і запускаємо роздачу
        Clock.schedule_once(self.start_dealing, 0.2)

    def start_dealing(self, dt):
        # Тестові карти
        cards_to_deal = [
            {'suit': 'hearts', 'rank': 'A'},
            {'suit': 'spades', 'rank': 'K'},
            {'suit': 'diamonds', 'rank': '10'}
        ]
        
        for i, data in enumerate(cards_to_deal):
            Clock.schedule_once(
                lambda dt, d=data: self._animate_deal(d), 
                i * 0.3 # Кожна наступна карта через 0.3 сек
            )

    def _animate_deal(self, data):
        new_card = CardWidget(suit=data['suit'], rank=data['rank'], is_face_up=True)
        AnimationManager.deal_card(new_card, self.deck_widget, self.player_hand)

    def action_make_move(self):
        """Хід гравця: карта лежить у нижній частині центру столу"""
        selected = [c for c in self.player_hand.children if getattr(c, 'selected', False)]
        if selected:
            card = selected[0]
            
            # Розрахунок позиції: 
            # center_x - центр карти по горизонталі
            # center_y - мінус 100dp або 120dp, щоб опустити карту ближче до гравця
            target_pos = (
                self.table.center_x - card.width / 2, 
                self.table.center_y - dp(120) 
            )
            
            AnimationManager.play_card(card, self.player_hand, self.table, target_pos)
            
            # Автоматична відповідь бота через невелику паузу
            Clock.schedule_once(self.opponent_make_move, 0.6)

    def opponent_make_move(self, dt):
        """Хід бота: карта лежить у верхній частині центру столу"""
        if self.opponent_hand.children:
            # Бот бере останню додану карту (children[-1])
            card = self.opponent_hand.children[-1]
            card.is_face_up = True # Відкриваємо карту бота при ході
            
            # Розрахунок позиції:
            # center_y + dp(20), щоб карта була трохи вище центральної лінії
            target_pos = (
                self.table.center_x - card.width / 2, 
                self.table.center_y + dp(20)
            )
            
            AnimationManager.play_card(card, self.opponent_hand, self.table, target_pos)
            
            # Після того як обидва походили, можна викликати логіку порівняння
            # Clock.schedule_once(self.resolve_battle, 0.8)

    def action_take_cards(self):
        """Карти зі столу летять до ГРАВЦЯ і стають відкритими"""
        cards_on_table = [c for c in self.table.children if isinstance(c, CardWidget)]
        
        # Ціль - центр руки гравця
        destination = (self.player_hand.center_x, self.player_hand.y)
        
        for card in cards_on_table:
            # Перед тим як забрати, переконуємось що карта "лицем вгору" для гравця
            card.is_face_up = True 
            
            # Викликаємо анімацію збору в руку гравця
            AnimationManager.collect_card(card, self.table, destination)
            
            # Якщо ви хочете, щоб карти фізично додавалися в HandWidget гравця:
            # Clock.schedule_once(lambda dt, c=card: self.player_hand.add_card(c), 0.4)

    def opponent_take_cards(self):
        """Логіка для бота: карти летять ВГОРУ і стають закритими"""
        cards_on_table = [c for c in self.table.children if isinstance(c, CardWidget)]
        
        # Ціль - центр руки опонента (зверху)
        destination = (self.opponent_hand.center_x, self.opponent_hand.top)
        
        for card in cards_on_table:
            # Карти бота мають бути закритими
            card.is_face_up = False
            AnimationManager.collect_card(card, self.table, destination)

    def action_draw_from_deck(self):
        if self.deck_widget.cards_count >= 2:
            # 1. Карта гравцю (відкрита)
            p_card = self.deck_widget.deal()
            p_widget = CardWidget(suit=p_card.suit, rank=p_card.rank, is_face_up=True)
            AnimationManager.deal_card(p_widget, self.deck_widget, self.player_hand)

            # 2. Карта боту (закрита сорочкою)
            o_card = self.deck_widget.deal()
            o_widget = CardWidget(suit=o_card.suit, rank=o_card.rank, is_face_up=False)
            AnimationManager.deal_card(o_widget, self.deck_widget, self.opponent_hand)
        else:
            print("Мало карт для роздачі обидвом!")