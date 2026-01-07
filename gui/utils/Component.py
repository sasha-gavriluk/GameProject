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
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.properties import StringProperty, BooleanProperty, NumericProperty

from gui.utils.AnimationManager import AnimationManager
from utils.cards import Card, Deck

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
    Візуальний компонент карти, що поєднує в собі:
    1. ButtonBehavior - для обробки натискань.
    2. FloatLayout - для розміщення символів масті та номіналу.
    3. Card - логічний клас з файлу utils/cards.py.
    """
    
    # Kivy властивості для автоматичного оновлення інтерфейсу
    suit = StringProperty('spades')
    rank = StringProperty('A')
    is_face_up = BooleanProperty(True)
    selected = BooleanProperty(False)
    angle = NumericProperty(0)

    def __init__(self, suit='spades', rank='A', is_face_up=True, **kwargs):
        # Передаємо параметри в kwargs для коректної роботи ланцюжка ініціалізації
        kwargs['suit'] = suit
        kwargs['rank'] = rank
        
        # Ініціалізація всіх батьківських класів через super()
        super().__init__(**kwargs)
        
        self.is_face_up = is_face_up
        self.size_hint = (None, None)
        self.size = (dp(80), dp(112))
        
        # Базова висота (Y), потрібна для коректної анімації повернення на місце
        self.base_y = 0 
        
        # Кольори мастей
        self.suit_colors = {
            'hearts': get_color_from_hex('#e74c3c'),   # Червоний
            'diamonds': get_color_from_hex('#e74c3c'), # Червоний
            'clubs': get_color_from_hex('#2c3e50'),    # Темно-синій/чорний
            'spades': get_color_from_hex('#2c3e50')    # Темно-синій/чорний
        }

        # Прив'язка оновлення графіки до змін властивостей
        self.bind(
            pos=self.update_canvas, 
            size=self.update_canvas, 
            suit=self.update_content, 
            rank=self.update_content, 
            is_face_up=self.update_content, 
            selected=self.on_selected_change
        )

        self.bind(pos=self.update_canvas, size=self.update_canvas, angle=self.update_canvas)
        self.update_content()
        
        self.update_content()

    def on_selected_change(self, instance, value):
        """Анімація підйому карти при її виборі."""
        if value:
            # Анімація вгору
            anim = Animation(y=self.base_y + dp(30), duration=0.15, t='out_quad')
        else:
            # Анімація повернення на базовий рівень
            anim = Animation(y=self.base_y, duration=0.15, t='out_quad')
        
        anim.start(self)
        self.update_canvas() # Перемальовуємо рамку

    def update_canvas(self, *args):
        """
        Малювання візуального стилю карти (фон, тінь, рамка, обертання).
        """
        from kivy.graphics import Color, RoundedRectangle, Line, Rotate, PushMatrix, PopMatrix
        
        self.canvas.before.clear()
        with self.canvas.before:
            # 1. Використовуємо матрицю для обертання карти навколо її центру
            PushMatrix()
            Rotate(angle=self.angle, origin=self.center)

            # 2. Тінь карти (стає трохи більшою, якщо карта вибрана)
            shadow_dist = dp(4) if self.selected else dp(2)
            Color(0, 0, 0, 0.3 if self.selected else 0.2)
            RoundedRectangle(
                pos=(self.x + shadow_dist, self.y - shadow_dist), 
                size=self.size, 
                radius=[dp(10)]
            )

            # 3. Основний фон карти
            if self.is_face_up:
                Color(1, 1, 1, 1) # Білий колір для лицьової сторони
            else:
                Color(*get_color_from_hex('#34495e')) # Темно-синій для сорочки
            
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            
            # 4. Рамка карти
            if self.selected:
                # Золота рамка для вибраної карти
                Color(*get_color_from_hex('#f1c40f'))
                Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(10)), width=dp(2))
            else:
                # Тонка прозора рамка для звичайної карти
                Color(0, 0, 0, 0.1)
                Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(10)), width=1)
            
            # 5. Візерунок на сорочці (якщо карта закрита)
            if not self.is_face_up:
                Color(1, 1, 1, 0.1)
                Line(rounded_rectangle=(
                    self.x + dp(10), self.y + dp(10), 
                    self.width - dp(20), self.height - dp(20), dp(5)
                ), width=2)

            # Закриваємо матрицю обертання
            PopMatrix()

    def update_content(self, *args):
        self.clear_widgets()
        self.update_canvas()
        if not self.is_face_up: return

        symbol = self.suit_symbol() 
        color = self.suit_colors.get(self.suit, (0, 0, 0, 1))
        
        # Компактні шрифти
        font_side = sp(14)
        font_center = sp(36)

        # Кутові індикатори (Rank + Suit)
        self.add_widget(Label(
            text=f"{self.rank}\n{symbol}", font_size=font_side, bold=True, color=color,
            size_hint=(None, None), size=(dp(30), dp(40)),
            pos_hint={'x': 0.02, 'top': 0.98}, halign='center'
        ))

        # Великий символ по центру
        self.add_widget(Label(
            text=symbol, font_size=font_center, color=color,
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        ))


class DeckWidget(ButtonBehavior, FloatLayout, Deck):
    """
    Візуальний компонент колоди з підтримкою натискання.
    """
    cards_count = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(80), dp(112))
        
        self.update_count()
        # Прив'язуємо оновлення канвасу до зміни позиції, розміру та кількості карт
        self.bind(pos=self.update_canvas, size=self.update_canvas, cards_count=self.update_canvas)
        self.update_canvas()

    def update_count(self):
        self.cards_count = len(self.cards) # Звертаємось до списку в класі Deck

    def deal(self):
        """Видає об'єкт логічної карти та оновлює візуал"""
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
            # Малювання шарів колоди для ефекту об'єму
            offsets = [dp(4), dp(2), 0]
            visible_layers = offsets if self.cards_count > 2 else offsets[-self.cards_count:]
            
            for i, offset in enumerate(visible_layers):
                Color(0, 0, 0, 0.2)
                RoundedRectangle(pos=(self.x + offset + dp(2), self.y + offset - dp(2)), 
                                 size=self.size, radius=[dp(10)])
                Color(*get_color_from_hex('#34495e')) # Колір сорочки
                RoundedRectangle(pos=(self.x + offset, self.y + offset), 
                                 size=self.size, radius=[dp(10)])
                
                if i == len(visible_layers) - 1: # Тільки для верхньої карти
                    Color(1, 1, 1, 0.1)
                    Line(rounded_rectangle=(self.x + offset + dp(10), self.y + offset + dp(10), 
                                          self.width - dp(20), self.height - dp(20), dp(5)), width=2)

        # Текст з кількістю карт
        count_label = Label(text=str(self.cards_count), font_size=sp(20), bold=True, 
                            color=(1, 1, 1, 0.5), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        self.add_widget(count_label)

class HandWidget(BoxLayout):
    max_selected = NumericProperty(1)

    def __init__(self, **kwargs):
        max_sel = kwargs.pop('max_selected', 1)
        super().__init__(**kwargs)
        
        self.max_selected = max_sel
        self.orientation = 'horizontal'
        self.size_hint = (0.8, None) 
        self.height = dp(120)  # Висота під карти 112dp + відступи
        self.padding = [dp(10), dp(5)]
        self.spacing = dp(10)  # Початковий зазор між картами
        
        self.pos_hint = {'center_x': 0.5}
        self.bind(width=self._recalculate_spacing, children=self._recalculate_spacing)

    def _recalculate_spacing(self, *args):
        n_cards = len(self.children)
        if n_cards <= 1:
            self.spacing = dp(10)
            return
            
        card_width = dp(80) # Нова ширина карти
        # Доступна ширина всередині контейнера
        available_width = self.width - (self.padding[0] * 2)
        
        # 1. Рахуємо, скільки місця займуть карти з комфортним зазором 10dp
        ideal_width = (n_cards * card_width) + ((n_cards - 1) * dp(10))
        
        if ideal_width <= available_width:
            # Місця багато — карти стоять вільно
            self.spacing = dp(10)
        else:
            # Місця замало — вираховуємо від'ємний spacing для рівномірного накладання
            # Формула гарантує, що перша і остання карти будуть чітко по краях контейнера
            overlap_spacing = (available_width - (n_cards * card_width)) / (n_cards - 1)
            
            # Захист: spacing не може бути меншим за ширину карти (щоб не розвернулись)
            self.spacing = max(overlap_spacing, -card_width + dp(20))

    def add_card(self, card_widget):
        """Додає карту в руку"""
        if card_widget.parent:
            card_widget.parent.remove_widget(card_widget)
            
        card_widget.bind(on_release=self.on_card_click)
        self.add_widget(card_widget)
        # Скидаємо size_hint, щоб BoxLayout міг керувати розміром, 
        # або залишаємо None для фіксованого розміру:
        card_widget.size_hint = (None, None) 
        card_widget.base_y = self.y + self.padding[1]

    def on_card_click(self, clicked_card):
        """Логіка вибору карт"""
        if clicked_card.selected:
            clicked_card.selected = False
            return

        # Рахуємо вже вибрані карти
        selected_cards = [c for c in self.children if getattr(c, 'selected', False)]

        if len(selected_cards) < self.max_selected:
            clicked_card.selected = True
        else:
            # Якщо ліміт 1 — перемикаємо на нову
            if self.max_selected == 1:
                for c in selected_cards:
                    c.selected = False
                clicked_card.selected = True
            else:
                # Якщо ліміт більше 1 і він вичерпаний — нічого не робимо
                print(f"Досягнуто ліміт вибору: {self.max_selected}")

    def play_selected_cards(self, table_widget):
        """
        Переміщує вибрані карти на стіл з анімацією.
        Реалізовано зміщення, щоб карти не перекривали одна одну.
        """
        import random
        selected_widgets = [c for c in self.children if getattr(c, 'selected', False)][:]
        
        if not selected_widgets:
            return []

        played_cards = []
        # Рахуємо, скільки карт вже лежить на столі (TableWidget)
        # щоб нова порція карт лягала поруч, а не зверху
        existing_cards_on_table = [c for c in table_widget.children if isinstance(c, CardWidget)]
        start_index = len(existing_cards_on_table)

        for i, card_widget in enumerate(selected_widgets):
            # 1. Фіксуємо абсолютну позицію
            window_pos = card_widget.to_window(*card_widget.pos)
            
            # 2. Видаляємо з руки
            self.remove_card(card_widget)
            
            # 3. Скидаємо властивості для вільного позиціонування
            card_widget.size_hint = (None, None)
            card_widget.pos_hint = {} 
            card_widget.selected = False 
            
            # 4. Додаємо на стіл і ставимо в початкову точку (де була рука)
            table_widget.add_widget(card_widget)
            card_widget.pos = table_widget.to_widget(*window_pos)
            
            # 5. Розрахунок цільової позиції (ЦЕНТР СТОЛУ + ЗМІЩЕННЯ)
            # Вираховуємо центр столу в пікселях
            center_x = table_widget.width / 2.5 - card_widget.width / 2
            center_y = table_widget.height / 2 - card_widget.height / 2
            
            # Робимо зміщення: кожна наступна карта на 50 пікселів правіше
            # (start_index + i) дозволяє враховувати карти, що вже були на столі
            offset_x = (start_index + i - 1) * dp(50) 
            
            target_x = center_x + offset_x
            target_y = center_y # Тепер змінна спочатку оголошена
            
            # Додаємо невеликий випадковий "шум" для реалістичності
            target_x += random.uniform(-dp(5), dp(5))
            target_y += random.uniform(-dp(10), dp(10))
            
            # 6. Анімація польоту (використовуємо 'pos', а не 'pos_hint' для надійності)
            anim = Animation(pos=(target_x, target_y), duration=0.4, t='out_quad')
            anim.start(card_widget)
            
            played_cards.append(card_widget)
            
        return played_cards
    
    def remove_card(self, card_widget):
        """Видаляє карту зBoxLayout руки"""
        # Відписуємо від логіки руки
        card_widget.unbind(on_release=self.on_card_click)
        # Видаляємо фізично з контейнера
        self.remove_widget(card_widget)

    def on_selected_change(self, instance, value):
        # Якщо карту зняли з виділення — повертаємо її в базове Y
        if not value:
            Animation(y=self.base_y, duration=0.1, t='out_quad').start(self)
        
        # Оновлюємо графіку, щоб прибрати/додати обводку
        self.update_canvas()

class TableWidget(FloatLayout):
    """
    Віджет столу. Тут розміщуються колода та активні карти.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Поки що це просто контейнер, але в майбутньому сюди 
        # можна додати логіку "слотів" для карт (як в Дураку)
        self.size_hint = (1, 1) # Займає весь доступний простір