import random

from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.animation import Animation

from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, ObjectProperty
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, RoundedRectangle, Line, Rotate, PushMatrix, PopMatrix, Rectangle, Translate

from gui.config.Configs import VisualConfig
from gui.utils.AnimationManager import AnimationManager
from utils.cards import Card, Deck
from utils.engine import Player

# --- БАЗОВІ КОМПОНЕНТИ ---

class GameButton(Button):
    """
    Базова кнопка гри.
    Вимикаємо стандартний фон Kivy, щоб використовувати свій колір.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = '' 
        self.background_color = get_color_from_hex('#3498db') # Світло-синій
        self.color = (1, 1, 1, 1) # Білий текст
        self.font_size = sp(18)
        self.bold = True

class MenuButton(GameButton):
    """
    Кнопка спеціально для меню.
    Має фіксовану висоту і темніший колір.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(60) # Фіксована висота
        self.background_color = get_color_from_hex('#2c3e50') # Темно-синій

class TitleLabel(Label):
    """
    Заголовок екрану.
    Великий шрифт, жовтий колір.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_size = sp(40)
        self.bold = True
        self.color = get_color_from_hex('#f1c40f') # Жовтий
        self.size_hint_y = None
        self.height = dp(100)

class GameTextInput(TextInput):
    """
    Поле вводу, адаптоване під стиль гри.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(50)       # Фіксована висота, зручна для пальця/миші
        self.multiline = False     # Це однорядкове поле
        self.font_size = sp(18)
        self.padding = [dp(10), dp(10), dp(10), dp(10)] # Відступи тексту всередині, щоб було по центру
        self.background_normal = '' # Можна прибрати стандартний фон
        self.background_color = (0.9, 0.9, 0.9, 1) # Світло-сірий фон
        self.foreground_color = (0, 0, 0, 1) # Чорний текст

class CardWidget(ButtonBehavior, FloatLayout, Card):
    """
    Візуальний компонент карти.
    ВСЕ малювання (фон, рамка, ТЕКСТ) відбувається через canvas.
    Жодних add_widget для тексту!
    """
    
    suit = StringProperty('spades')
    rank = StringProperty('A')
    is_face_up = BooleanProperty(True)
    selected = BooleanProperty(False)
    angle = NumericProperty(0)
    offset_y = NumericProperty(0)

    def __init__(self, suit='spades', rank='A', is_face_up=True, **kwargs):
        kwargs['suit'] = suit
        kwargs['rank'] = rank
        super().__init__(**kwargs)
        
        self.is_face_up = is_face_up
        self.size_hint = (None, None)
        self.size = (dp(80), dp(112))
        self.base_y = 0 
        
        self.suit_colors = {
            'hearts': get_color_from_hex('#e74c3c'),
            'diamonds': get_color_from_hex('#e74c3c'),
            'clubs': get_color_from_hex('#2c3e50'),
            'spades': get_color_from_hex('#2c3e50')
        }

        self.bind(
            pos=self.update_canvas, 
            size=self.update_canvas, 
            suit=self.update_content, 
            rank=self.update_content, 
            is_face_up=self.update_content, 
            selected=self.on_selected_change,
            angle=self.update_canvas,
            offset_y=self.update_canvas
        )

        # Перший виклик малювання
        self.update_canvas()

    def on_selected_change(self, instance, value):
        target_y = self.base_y + dp(30) if value else self.base_y
        anim = Animation(y=target_y, duration=0.15, t='out_quad')
        anim.start(self)
        self.update_canvas()

    def update_content(self, *args):
        # ВАЖЛИВО: Ми більше не додаємо віджети (add_widget).
        # Ми просто просимо перемалювати canvas.
        self.update_canvas()

    def update_canvas(self, *args):
        """
        Малює карту, використовуючи dy (offset_y) для візуального зміщення.
        Це ізолює графіку від фізичних координат віджета, запобігаючи 'просіданню'.
        """
        from kivy.graphics import Color, RoundedRectangle, Line, Rotate, PushMatrix, PopMatrix, Rectangle, Translate
        from kivy.utils import get_color_from_hex
        
        # Очищаємо старі інструкції малювання
        self.canvas.before.clear()

        with self.canvas.before:
            PushMatrix()
            
            # 1. Базова точка — центр віджета (БЕЗ offset_y в матриці)
            Translate(self.center_x, self.center_y)
            Rotate(angle=self.angle, origin=(0, 0))
            Translate(-self.width / 2, -self.height / 2)
            
            # --- dy — це наше візуальне зміщення вгору ---
            dy = self.offset_y 

            # 2. Світіння (малюємо першим, щоб було під картою)
            if self.selected:
                Color(1, 0.8, 0, 0.4)
                # Зміщуємо Line на dy
                Line(rounded_rectangle=(-dp(3), dy - dp(3), self.width + dp(6), self.height + dp(6), dp(12)), width=dp(3))

            # 3. Тінь (малюємо під картою)
            Color(0, 0, 0, 0.2)
            RoundedRectangle(pos=(dp(2), dy - dp(2)), size=self.size, radius=[dp(10)])

            # 4. Основний фон карти
            if self.is_face_up:
                Color(1, 1, 1, 1)
            else:
                Color(*get_color_from_hex('#34495e'))
            
            # Малюємо прямокутник фону з урахуванням dy
            RoundedRectangle(pos=(0, dy), size=self.size, radius=[dp(10)])
            
            # 5. Рамка (обводка)
            if self.selected:
                Color(*get_color_from_hex('#f1c40f'))
                Line(rounded_rectangle=(0, dy, self.width, self.height, dp(10)), width=dp(2.5))
            else:
                Color(0, 0, 0, 0.15)
                Line(rounded_rectangle=(0, dy, self.width, self.height, dp(10)), width=dp(1))

            # 6. Контент лицевої сторони (Текст та Масть)
            if self.is_face_up:
                symbol = self.suit_symbol() 
                color_rgba = self.suit_colors.get(self.suit, (0, 0, 0, 1))
                Color(*color_rgba)

                # --- Кутові текстури ---
                corner_label = CoreLabel(
                    text=f"{self.rank}\n{symbol}", 
                    font_size=int(sp(14)), 
                    bold=True, 
                    halign='center',
                    font_name='DejaVuSans'
                )
                corner_label.refresh()
                corner_texture = corner_label.texture

                if corner_texture:
                    pad = dp(5)
                    # Верхній лівий (додаємо dy до y)
                    Rectangle(
                        texture=corner_texture, 
                        pos=(pad, dy + self.height - corner_texture.height - pad), 
                        size=corner_texture.size
                    )
                    # Нижній правий перевернутий (додаємо dy до y)
                    Rectangle(
                        texture=corner_texture, 
                        pos=(self.width - corner_texture.width - pad, dy + pad), 
                        size=corner_texture.size,
                        tex_coords=(1, 1, 0, 1, 0, 0, 1, 0)
                    )

                # --- Центральна масть ---
                center_label = CoreLabel(text=symbol, font_size=int(sp(36)), font_name='DejaVuSans')
                center_label.refresh()
                center_texture = center_label.texture
                if center_texture:
                    Rectangle(
                        texture=center_texture, 
                        pos=(self.width/2 - center_texture.width/2, dy + self.height/2 - center_texture.height/2), 
                        size=center_texture.size
                    )

            # 7. Декор сорочки (якщо карта закрита)
            else:
                Color(1, 1, 1, 0.1)
                Line(rounded_rectangle=(dp(10), dy + dp(10), self.width - dp(20), self.height - dp(20), dp(5)), width=1.5)

            PopMatrix()

    def on_y(self, instance, value):
        # Якщо карта в руці і її намагаються опустити нижче базової лінії
        # (це зазвичай і є те саме 'просідання'), ми блокуємо це.
        if self.parent and hasattr(self.parent, 'is_main_player'):
            base_y = self.parent.y + dp(15)
            if value < base_y and self.offset_y == 0:
                self.y = base_y

class DeckWidget(ButtonBehavior, FloatLayout, Deck):
    """
    Візуальний компонент колоди, що успадковує логіку класу Deck.
    """
    cards_count = NumericProperty(0)

    def __init__(self, **kwargs):
        # Ініціалізація Deck та FloatLayout
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(80), dp(112))
        
        self.update_count()
        # Прив'язуємо оновлення канвасу до зміни позиції, розміру та кількості карт
        self.bind(pos=self.update_canvas, size=self.update_canvas, cards_count=self.update_canvas)
        self.update_canvas()

    def update_count(self):
        """Синхронізує візуальний лічильник з масивом карт у Deck"""
        self.cards_count = len(self.cards)

    def deal(self):
        """Видає об'єкт логічної карти та автоматично оновлює візуал"""
        if not self.cards:
            return None
        card = super().deal() # Виклик методу з utils.cards.Deck
        self.update_count()
        return card

    def update_canvas(self, *args):
        self.canvas.before.clear()
        self.clear_widgets()
        
        if self.cards_count == 0:
            with self.canvas.before:
                Color(0, 0, 0, 0.1)
                Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(10)), width=1, dash_offset=5)
            return

        with self.canvas.before:
            # Малювання шарів колоди для ефекту об'єму (3 карти зверху)
            offsets = [dp(4), dp(2), 0]
            visible_layers = offsets if self.cards_count > 2 else offsets[-self.cards_count:]
            
            for i, offset in enumerate(visible_layers):
                Color(0, 0, 0, 0.2)
                RoundedRectangle(pos=(self.x + offset + dp(2), self.y + offset - dp(2)), 
                                 size=self.size, radius=[dp(10)])
                Color(*get_color_from_hex('#34495e')) # Колір сорочки
                RoundedRectangle(pos=(self.x + offset, self.y + offset), 
                                 size=self.size, radius=[dp(10)])
                
                if i == len(visible_layers) - 1: # Тільки для верхньої карти малюємо візерунок
                    Color(1, 1, 1, 0.1)
                    Line(rounded_rectangle=(self.x + offset + dp(10), self.y + offset + dp(10), 
                                          self.width - dp(20), self.height - dp(20), dp(5)), width=2)

        # Текст з кількістю карт
        count_label = Label(text=str(self.cards_count), font_size=sp(20), bold=True, 
                            color=(1, 1, 1, 0.5), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        self.add_widget(count_label)

class HandWidget(FloatLayout, Player):
    """
    Віджет руки, який тепер є і візуальним елементом, і логічним гравцем.
    """
    selected_card = ObjectProperty(None, allownone=True)
    is_main_player = BooleanProperty(False)
    spacing_x = NumericProperty(dp(40))
    
    player_name = StringProperty('')
    cards_count_display = StringProperty('')

    def __init__(self, name="Player", player_id=None, is_main_player=False, **kwargs):
        # 1. Повертаємо name та player_id в kwargs, щоб вони дійшли до Player.__init__ через ланцюжок super()
        kwargs['name'] = name
        kwargs['player_id'] = player_id
        
        self.is_main_player = is_main_player
        
        # 2. Викликаємо єдиний super().__init__, який ініціалізує і FloatLayout, і Player
        super().__init__(**kwargs)
        
        self.player_name = name
        self.size_hint = (None, None)
        self.cards = [] 

        # Налаштування розмірів
        if self.is_main_player:
            self.size = (dp(600), dp(150))
            self.base_y = dp(20)
        else:
            self.size = (dp(120), dp(160))
            self.base_y = 0
            self.setup_opponent_ui()

        self.card_count_label = None
        if not self.is_main_player and VisualConfig.SHOW_BOT_CARD_COUNT:
            self.card_count_label = Label(
                text="",
                font_size=dp(14),
                color=VisualConfig.BOT_LABEL_COLOR,
                size_hint=(None, None),
                size=(dp(40), dp(20)),
                bold=True
            )
            self.add_widget(self.card_count_label)

        self.bind(pos=self.update_hand_layout, size=self.update_hand_layout)

    def setup_opponent_ui(self):
        """Створює UI для суперника (ім'я, фон)"""
        with self.canvas.before:
            Color(0, 0, 0, 0.4)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        
        self.bind(pos=self.update_bg, size=self.update_bg)

        # Ім'я зверху
        self.lbl_name = Label(
            text=self.name,
            font_size=sp(12),
            bold=True,
            size_hint=(1, None),
            height=dp(20),
            pos_hint={'top': 1, 'center_x': 0.5}
        )
        self.add_widget(self.lbl_name)

    def update_bg(self, *args):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = self.pos
            self.bg_rect.size = self.size

    def add_card(self, card_widget):
        """Додає карту візуально і логічно"""
        super().add_card(card_widget) # Логіка Player
        self.cards.append(card_widget)
        self.add_widget(card_widget)
        
        # Налаштування для бота vs гравця
        if not self.is_main_player:
            card_widget.is_face_up = False # Карти ворога закриті
            card_widget.size = (dp(40), dp(56)) # Менші карти
        else:
            card_widget.is_face_up = True
            card_widget.size = (dp(80), dp(112)) # Стандартні карти
            # Прив'язка натискання тільки для своїх карт
            card_widget.bind(on_touch_down=self.on_card_touch)

        self.update_hand_layout()

    def remove_card(self, card_widget):
        """Видаляє карту"""
        super().remove_card(card_widget) # Логіка Player
        if card_widget in self.cards:
            self.cards.remove(card_widget)
            self.remove_widget(card_widget)
            self.update_hand_layout()

    def update_hand_layout(self, *args):
        """
        Динамічно розраховує позиції карт у руці:
        - Розширює карти, коли їх мало (зручно клікати).
        - Стискає карти, коли їх багато (вміщує в екран).
        - Фіксує Y, щоб запобігти просіданню.
        """
        
        if not self.cards:
            if self.card_count_label: self.card_count_label.text = ""
            return

        count = len(self.cards)

        count = len(self.cards)
        
        if self.is_main_player:
            # --- НАЛАШТУВАННЯ ДЛЯ ГРАВЦЯ ---
            card_width = dp(80)
            # Максимальна ширина, яку може зайняти вся рука (90% ширини екрана)
            max_total_width = self.width * 0.9
            
            # Ідеальний крок між картами, коли їх мало (щоб було зручно тиснути)
            # Можете змінити dp(55) на більше, якщо хочете ще вільніше
            ideal_step = dp(55) 
            
            # Розраховуємо, скільки ширини зайняли б карти при ідеальному кроці
            needed_width = (count - 1) * ideal_step + card_width
            
            # Вибираємо фінальний крок:
            # Якщо потрібна ширина більша за дозволену — стискаємо крок
            if needed_width > max_total_width:
                actual_step = max_total_width / (count - 1) if count > 1 else ideal_step
            else:
                actual_step = ideal_step
            
            # Розраховуємо загальну ширину з отриманим кроком для центрування
            final_hand_width = (count - 1) * actual_step + card_width
            start_x = self.center_x - (final_hand_width / 2)
            
            # БАЗОВА ЛІНІЯ (Суворо фіксована для запобігання просіданню)
            base_y = self.y + dp(15)

            for i, card in enumerate(self.cards):
                # Розрахунок цільової X
                target_x = start_x + (i * actual_step)
                
                # 1. Зупиняємо всі попередні анімації, щоб не було конфліктів
                Animation.stop_all(card)
                
                # 2. Жорстко фіксуємо Y (це вбиває проблему просідання при деактивації)
                card.y = base_y
                
                # 3. Анімуємо тільки рух по горизонталі (X)
                # Якщо карта вже на місці, анімація не потрібна
                if abs(card.x - target_x) > 1:
                    anim = Animation(x=target_x, duration=0.25, t='out_quad')
                    anim.start(card)
                
                # 4. Коригуємо Z-index: кожна наступна карта має бути ПОВЕРХ попередньої
                self.remove_widget(card)
                self.add_widget(card)
                
        else:
            # --- ЛОГІКА ДЛЯ БОТІВ ---
            max_visible = VisualConfig.MAX_VISIBLE_BOT_CARDS
            step = dp(12) 
            card_w = dp(40)
            
            display_count = min(count, max_visible)
            total_w = (display_count - 1) * step + card_w
            
            start_x = self.center_x - (total_w / 2)
            # Притискаємо до самого низу контейнера (y = self.y)
            base_y = self.y 

            for i, card in enumerate(self.cards):
                # Зупиняємо анімації для миттєвого переміщення або плавності
                Animation.stop_all(card)
                
                if i < max_visible:
                    card.opacity = 1
                    card.pos = (start_x + (i * step), base_y)
                else:
                    card.opacity = 0
                    card.pos = (start_x + (max_visible - 1) * step, base_y)
                
                # Оновлюємо Z-index, щоб карти були одна під одною
                self.remove_widget(card)
                self.add_widget(card)

            # Оновлюємо лічильник
            if self.card_count_label:
                # Ставимо лічильник над картами
                self.card_count_label.center_x = self.center_x
                self.card_count_label.y = base_y + dp(80) # Вище карт
                self.card_count_label.text = f"x{count}"
                
                # Поверх усіх карт
                self.remove_widget(self.card_count_label)
                self.add_widget(self.card_count_label)

    def on_card_touch(self, instance, touch):
        """Обробка кліку по карті (тільки для головного гравця)"""
        if not self.is_main_player:
            return False
            
        if instance.collide_point(*touch.pos):
            self.select_card(instance)
            return True
        return False

    def select_card(self, card):
        if card not in self.cards:
            print("Ця карта вже на столі, її не можна вибрати!")
            return

        if self.selected_card == card:
            # Деактивація
            anim = Animation(offset_y=0, duration=0.15, t='out_quad')
            def on_finish(a, c):
                c.selected = False # Змінюємо ТІЛЬКИ після завершення руху вниз
            anim.bind(on_complete=on_finish)
            anim.start(card)
            self.selected_card = None
        else:
            # Активація
            if self.selected_card:
                self.selected_card.selected = False
                self.selected_card.offset_y = 0
            
            self.selected_card = card
            card.selected = True
            Animation(offset_y=dp(30), duration=0.15, t='out_quad').start(card)

class TableWidget(FloatLayout):
    """
    Віджет столу. Тут розміщуються колода та активні карти.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Поки що це просто контейнер, але в майбутньому сюди 
        # можна додати логіку "слотів" для карт (як в Дураку)
        self.size_hint = (1, 1) # Займає весь доступний простір

# gui/utils/Component.py

class BattleAreaWidget(FloatLayout):
    """
    Зона в центрі столу, куди гравці кладуть карти.
    Малює напівпрозорий прямокутник-підказку.
    """
    active = BooleanProperty(False) # Чи підсвічувати зону прямо зараз

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(400), dp(170)) # Достатньо для пари карт
        self.bind(pos=self.update_canvas, size=self.update_canvas, active=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.active:
                # Золотисте підсвічування зони, коли вона чекає на карту
                Color(0.95, 0.77, 0.06, 0.2) # Жовтуватий фон
                RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(15)])
                
                Color(0.95, 0.77, 0.06, 0.6) # Яскрава рамка
                Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(15)), width=dp(2.5))
            else:
                # Спокійний стан
                Color(1, 1, 1, 0.05)
                Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(15)), 
                    width=dp(1.5), dash_length=dp(8), dash_offset=dp(2))