import random

from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.behaviors import ButtonBehavior
from kivy.animation import Animation

from kivy.core.window import Window
from kivy.utils import get_color_from_hex, escape_markup
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, ObjectProperty, ListProperty
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, RoundedRectangle, Line

from gui.config.Configs import VisualConfig
from gui.utils.AnimationManager import AnimationManager
from utils.cards import Card, Deck
from utils.engine import Player

# --- БАЗОВІ КОМПОНЕНТИ ---

class GameButton(Button):
    """
    Базова кнопка гри.
    Темна кнопка для карткової гри з кастомним canvas-рендером.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.color = (0.94, 0.96, 0.98, 1)
        self._base_font_size = 18
        self.bold = True
        self._hovered = False

        # Темна палітра + теплий акцент під тематику карт.
        self._idle_bg = (0.11, 0.13, 0.16, 1)
        self._hover_bg = (0.14, 0.17, 0.21, 1)
        self._down_bg = (0.08, 0.10, 0.13, 1)
        self._disabled_bg = (0.10, 0.11, 0.13, 0.62)
        self._border = (0.27, 0.31, 0.38, 1)
        self._accent = (0.78, 0.66, 0.42, 1)
        self._radius = VisualConfig.sdp(12)

        self.bind(pos=self._redraw, size=self._redraw, state=self._redraw, disabled=self._redraw)
        Window.bind(size=lambda *_: self._apply_scale())
        Window.bind(mouse_pos=self._on_mouse_pos)
        self._apply_scale()

    def _apply_scale(self):
        self.font_size = VisualConfig.ssp(self._base_font_size)
        self._radius = VisualConfig.sdp(12)
        self._redraw()

    def _on_mouse_pos(self, *_):
        if self.get_root_window() is None:
            return
        hovered = self.collide_point(*self.to_widget(*Window.mouse_pos))
        if hovered != self._hovered:
            self._hovered = hovered
            self._redraw()

    def _current_bg(self):
        if self.disabled:
            return self._disabled_bg
        if self.state == "down":
            return self._down_bg
        if self._hovered:
            return self._hover_bg
        return self._idle_bg

    def _redraw(self, *_):
        self.canvas.before.clear()
        self.canvas.after.clear()

        x, y = self.pos
        w, h = self.size
        radius = [self._radius]

        with self.canvas.before:
            shadow_alpha = 0.28 if self.state != "down" else 0.14
            Color(0, 0, 0, shadow_alpha)
            RoundedRectangle(pos=(x, y - VisualConfig.sdp(2)), size=(w, h), radius=radius)

            Color(*self._current_bg())
            RoundedRectangle(pos=(x, y), size=(w, h), radius=radius)

        with self.canvas.after:
            Color(*self._border)
            Line(rounded_rectangle=(x, y, w, h, self._radius), width=VisualConfig.sdp(1.1))

            Color(*self._accent)
            Line(
                points=(
                    x + VisualConfig.sdp(10),
                    y + h - VisualConfig.sdp(1),
                    x + w - VisualConfig.sdp(10),
                    y + h - VisualConfig.sdp(1),
                ),
                width=VisualConfig.sdp(1),
            )

class MenuButton(GameButton):
    """
    Кнопка спеціально для меню.
    Має фіксовану висоту і темніший колір.
    """
    def __init__(self, **kwargs):
        self._base_height = 60
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = VisualConfig.sdp(self._base_height) # Фіксована висота
        Window.bind(size=lambda *_: self._apply_scale())

    def _apply_scale(self):
        super()._apply_scale()
        self.height = VisualConfig.sdp(self._base_height)


class GameToggleButton(ToggleButton):
    """
    Toggle-кнопка в тому ж стилі, що й GameButton.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.color = (0.94, 0.96, 0.98, 1)
        self._base_font_size = 18
        self.bold = True
        self._hovered = False

        self._idle_bg = (0.11, 0.13, 0.16, 1)
        self._hover_bg = (0.14, 0.17, 0.21, 1)
        self._down_bg = (0.08, 0.10, 0.13, 1)
        self._disabled_bg = (0.10, 0.11, 0.13, 0.62)
        self._border = (0.27, 0.31, 0.38, 1)
        self._accent = (0.78, 0.66, 0.42, 1)
        self._radius = VisualConfig.sdp(12)

        self.bind(pos=self._redraw, size=self._redraw, state=self._redraw, disabled=self._redraw)
        Window.bind(size=lambda *_: self._apply_scale())
        Window.bind(mouse_pos=self._on_mouse_pos)
        self._apply_scale()

    def _apply_scale(self):
        self.font_size = VisualConfig.ssp(self._base_font_size)
        self._radius = VisualConfig.sdp(12)
        self._redraw()

    def _on_mouse_pos(self, *_):
        if self.get_root_window() is None:
            return
        hovered = self.collide_point(*self.to_widget(*Window.mouse_pos))
        if hovered != self._hovered:
            self._hovered = hovered
            self._redraw()

    def _current_bg(self):
        if self.disabled:
            return self._disabled_bg
        if self.state == "down":
            return self._down_bg
        if self._hovered:
            return self._hover_bg
        return self._idle_bg

    def _redraw(self, *_):
        self.canvas.before.clear()
        self.canvas.after.clear()

        x, y = self.pos
        w, h = self.size
        radius = [self._radius]

        with self.canvas.before:
            shadow_alpha = 0.28 if self.state != "down" else 0.14
            Color(0, 0, 0, shadow_alpha)
            RoundedRectangle(pos=(x, y - VisualConfig.sdp(2)), size=(w, h), radius=radius)

            Color(*self._current_bg())
            RoundedRectangle(pos=(x, y), size=(w, h), radius=radius)

        with self.canvas.after:
            Color(*self._border)
            Line(rounded_rectangle=(x, y, w, h, self._radius), width=VisualConfig.sdp(1.1))

            Color(*self._accent)
            Line(
                points=(
                    x + VisualConfig.sdp(10),
                    y + h - VisualConfig.sdp(1),
                    x + w - VisualConfig.sdp(10),
                    y + h - VisualConfig.sdp(1),
                ),
                width=VisualConfig.sdp(1),
            )

class TitleLabel(Label):
    """
    Заголовок екрану.
    Великий шрифт, жовтий колір.
    """
    def __init__(self, **kwargs):
        base_font_size = kwargs.pop("font_size", 40)
        base_height = kwargs.pop("height", 100)
        super().__init__(**kwargs)
        self._base_font_size = base_font_size
        self._base_height = base_height
        self._apply_scale()
        self.bold = True
        self.color = get_color_from_hex('#f1c40f') # Жовтий
        self.size_hint_y = None
        self.height = VisualConfig.sdp(self._base_height)
        Window.bind(size=lambda *_: self._apply_scale())

    def _apply_scale(self):
        self.font_size = VisualConfig.ssp(self._base_font_size)
        self.height = VisualConfig.sdp(self._base_height)

class GameTextInput(TextInput):
    """
    Поле вводу, адаптоване під стиль гри.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self._base_height = 50
        self.height = VisualConfig.sdp(self._base_height)       # Фіксована висота, зручна для пальця/миші
        self.multiline = False     # Це однорядкове поле
        self._base_font_size = 18
        self._base_padding = 10
        self.font_size = VisualConfig.ssp(self._base_font_size)
        pad = VisualConfig.sdp(self._base_padding)
        self.padding = [pad, pad, pad, pad] # Відступи тексту всередині, щоб було по центру
        self.background_normal = '' # Можна прибрати стандартний фон
        self.background_color = (0.9, 0.9, 0.9, 1) # Світло-сірий фон
        self.foreground_color = (0, 0, 0, 1) # Чорний текст
        Window.bind(size=lambda *_: self._apply_scale())

    def _apply_scale(self):
        self.height = VisualConfig.sdp(self._base_height)
        self.font_size = VisualConfig.ssp(self._base_font_size)
        pad = VisualConfig.sdp(self._base_padding)
        self.padding = [pad, pad, pad, pad]


class GamePopup(Popup):
    """
    Базовий стилізований попап для гри.
    """
    def __init__(self, **kwargs):
        kwargs.setdefault("auto_dismiss", True)
        kwargs.setdefault("title_align", "center")
        kwargs.setdefault("title_color", (0.95, 0.97, 0.99, 1))
        super().__init__(**kwargs)

        self.background = ""
        self.background_color = (0, 0, 0, 0)
        self.separator_height = VisualConfig.sdp(1)
        self.separator_color = (0.78, 0.66, 0.42, 0.9)
        self.title_size = VisualConfig.ssp(22)

        self._fill_color = (0.08, 0.10, 0.13, 0.98)
        self._border_color = (0.29, 0.33, 0.40, 1)
        self._radius = VisualConfig.sdp(16)

        self.bind(pos=self._redraw, size=self._redraw)
        Window.bind(size=lambda *_: self._apply_scale())
        self._apply_scale()

    def _apply_scale(self):
        self.separator_height = VisualConfig.sdp(1)
        self.title_size = VisualConfig.ssp(22)
        self._radius = VisualConfig.sdp(16)
        self._redraw()

    def _redraw(self, *_):
        self.canvas.before.clear()
        self.canvas.after.clear()
        x, y = self.pos
        w, h = self.size

        with self.canvas.before:
            Color(0, 0, 0, 0.34)
            RoundedRectangle(pos=(x, y - VisualConfig.sdp(3)), size=(w, h), radius=[self._radius])
            Color(*self._fill_color)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[self._radius])

        with self.canvas.after:
            Color(*self._border_color)
            Line(rounded_rectangle=(x, y, w, h, self._radius), width=VisualConfig.sdp(1.2))


class ChatSurface(BoxLayout):
    """
    Темна підкладка для секції чату.
    Можна використати для bottom_panel або input_box.
    """
    def __init__(self, **kwargs):
        self._fill_color = kwargs.pop("fill_color", (0.08, 0.10, 0.13, 0.97))
        self._border_color = kwargs.pop("border_color", (0.27, 0.31, 0.38, 1))
        self._radius = kwargs.pop("radius", VisualConfig.sdp(12))
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw)
        Window.bind(size=lambda *_: self._apply_scale())
        self._apply_scale()

    def _apply_scale(self):
        self._radius = VisualConfig.sdp(12)
        self._redraw()

    def _redraw(self, *_):
        self.canvas.before.clear()
        self.canvas.after.clear()
        x, y = self.pos
        w, h = self.size
        with self.canvas.before:
            Color(0, 0, 0, 0.22)
            RoundedRectangle(pos=(x, y - VisualConfig.sdp(2)), size=(w, h), radius=[self._radius])
            Color(*self._fill_color)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[self._radius])
        with self.canvas.after:
            Color(*self._border_color)
            Line(rounded_rectangle=(x, y, w, h, self._radius), width=VisualConfig.sdp(1))


class ChatScrollView(ScrollView):
    """
    Скролл чату з темною рамкою та стилізованими скрол-барами.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_scroll_x = False
        self.scroll_type = ['bars', 'content']
        self.bar_width = VisualConfig.sdp(4)
        self.bar_color = (0.72, 0.64, 0.46, 0.9)
        self.bar_inactive_color = (0.33, 0.37, 0.43, 0.55)
        self._fill_color = (0.09, 0.11, 0.14, 1)
        self._border_color = (0.25, 0.29, 0.35, 1)
        self._radius = VisualConfig.sdp(10)
        self.bind(pos=self._redraw, size=self._redraw)
        Window.bind(size=lambda *_: self._apply_scale())
        self._apply_scale()

    def _apply_scale(self):
        self.bar_width = VisualConfig.sdp(4)
        self._radius = VisualConfig.sdp(10)
        self._redraw()

    def _redraw(self, *_):
        self.canvas.before.clear()
        self.canvas.after.clear()
        x, y = self.pos
        w, h = self.size
        with self.canvas.before:
            Color(*self._fill_color)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[self._radius])
        with self.canvas.after:
            Color(*self._border_color)
            Line(rounded_rectangle=(x, y, w, h, self._radius), width=VisualConfig.sdp(1))


class ChatHistoryLabel(Label):
    """
    Лейбл історії чату з готовими кольорами та helper-методом додавання повідомлень.
    """
    def __init__(self, **kwargs):
        kwargs.setdefault("markup", True)
        kwargs.setdefault("halign", "left")
        kwargs.setdefault("valign", "top")
        kwargs.setdefault("color", (0.90, 0.93, 0.97, 1))
        kwargs.setdefault("text", "")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", VisualConfig.sdp(28))
        super().__init__(**kwargs)
        self._pad_x = VisualConfig.sdp(10)
        self._pad_y = VisualConfig.sdp(8)
        self._min_height = VisualConfig.sdp(28)
        self.bind(size=self._apply_inner_padding)
        self.bind(texture_size=self._sync_height_from_texture)
        Window.bind(size=lambda *_: self._apply_scale())
        self._apply_scale()

    def _apply_scale(self):
        self._pad_x = VisualConfig.sdp(10)
        self._pad_y = VisualConfig.sdp(8)
        self._min_height = VisualConfig.sdp(28)
        self._apply_inner_padding()
        self._sync_height_from_texture()

    def _apply_inner_padding(self, *_):
        inset_w = max(0, self.width - (self._pad_x * 2))
        # Висоту лишаємо None, щоб Label ріс по texture_size і працював скрол.
        self.text_size = (inset_w, None)

    def _sync_height_from_texture(self, *_):
        self.height = max(self._min_height, self.texture_size[1] + (self._pad_y * 2))

    def append_message(self, author, text):
        user = escape_markup(str(author))
        message = escape_markup(str(text))
        self.text += f"[color=#9fb7d1][b]{user}[/b][/color]: [color=#e7edf4]{message}[/color]\n"


class ChatTextInput(GameTextInput):
    """
    Поле вводу повідомлення в темному стилі чату.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0.10, 0.12, 0.15, 1)
        self.foreground_color = (0.94, 0.96, 0.98, 1)
        self.cursor_color = (0.78, 0.66, 0.42, 1)
        self.hint_text_color = (0.66, 0.71, 0.78, 1)

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
    on_click_action = ObjectProperty(None, allownone=True)
    angle = NumericProperty(0)
    offset_y = NumericProperty(0)

    def __init__(self, suit='spades', rank='A', is_face_up=True, **kwargs):
        kwargs['suit'] = suit
        kwargs['rank'] = rank
        super().__init__(**kwargs)
        
        self.is_face_up = is_face_up
        self.size_hint = (None, None)
        self.size = (VisualConfig.CARD_W, VisualConfig.CARD_H)
        self.base_y = 0 
        
        self.suit_colors = {
            'hearts': get_color_from_hex('#e74c3c'),
            'diamonds': get_color_from_hex('#e74c3c'),
            'clubs': get_color_from_hex('#2c3e50'),
            'spades': get_color_from_hex('#2c3e50')
        }

        self.bind(pos=self.update_canvas, size=self.update_canvas, 
                  suit=self.update_content, rank=self.update_content, 
                  is_face_up=self.update_content, selected=self.on_selected_change,
                  angle=self.update_canvas, offset_y=self.update_canvas)
        self.update_canvas()

    def on_selected_change(self, instance, value):
        target_y = self.base_y + VisualConfig.sdp(30) if value else self.base_y
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
                Line(rounded_rectangle=(-VisualConfig.sdp(3), dy - VisualConfig.sdp(3), self.width + VisualConfig.sdp(6), self.height + VisualConfig.sdp(6), VisualConfig.sdp(12)), width=VisualConfig.sdp(3))

            # 3. Тінь (малюємо під картою)
            Color(0, 0, 0, 0.2)
            RoundedRectangle(pos=(VisualConfig.sdp(2), dy - VisualConfig.sdp(2)), size=self.size, radius=[VisualConfig.sdp(10)])

            # 4. Основний фон карти
            if self.is_face_up:
                Color(1, 1, 1, 1)
            else:
                Color(*get_color_from_hex('#34495e'))
            
            # Малюємо прямокутник фону з урахуванням dy
            RoundedRectangle(pos=(0, dy), size=self.size, radius=[VisualConfig.sdp(10)])
            
            # 5. Рамка (обводка)
            if self.selected:
                Color(*get_color_from_hex('#f1c40f'))
                Line(rounded_rectangle=(0, dy, self.width, self.height, VisualConfig.sdp(10)), width=VisualConfig.sdp(2.5))
            else:
                Color(0, 0, 0, 0.15)
                Line(rounded_rectangle=(0, dy, self.width, self.height, VisualConfig.sdp(10)), width=VisualConfig.sdp(1))

            # 6. Контент лицевої сторони (Текст та Масть)
            if self.is_face_up:
                symbol = self.suit_symbol() 
                color_rgba = self.suit_colors.get(self.suit, (0, 0, 0, 1))
                Color(*color_rgba)

                # --- Кутові текстури ---
                corner_label = CoreLabel(
                    text=f"{self.rank}\n{symbol}", 
                    font_size=int(VisualConfig.ssp(14)), 
                    bold=True, 
                    halign='center',
                    font_name='DejaVuSans'
                )
                corner_label.refresh()
                corner_texture = corner_label.texture

                if corner_texture:
                    pad = VisualConfig.sdp(5)
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
                center_label = CoreLabel(text=symbol, font_size=int(VisualConfig.ssp(36)), font_name='DejaVuSans')
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
                Line(rounded_rectangle=(VisualConfig.sdp(10), dy + VisualConfig.sdp(10), self.width - VisualConfig.sdp(20), self.height - VisualConfig.sdp(20), VisualConfig.sdp(5)), width=VisualConfig.sdp(1.5))

            PopMatrix()

    def on_y(self, instance, value):
        # Якщо карта в руці і її намагаються опустити нижче базової лінії
        # (це зазвичай і є те саме 'просідання'), ми блокуємо це.
        if self.parent and hasattr(self.parent, 'is_main_player'):
            base_y = self.parent.y + VisualConfig.sdp(15)
            if value < base_y and self.offset_y == 0:
                self.y = base_y

    def on_touch_down(self, touch):
        # Перевіряємо, чи клікнули по цій карті
        if self.collide_point(*touch.pos):
            # Якщо карті призначена спеціальна дія (вона на столі) — виконуємо її
            if self.on_click_action:
                self.on_click_action()
                return True # Кажемо системі, що клік оброблено
        
        # Якщо дії немає (карта в руці), працює стандартна логіка
        return super().on_touch_down(touch)

class DeckWidget(ButtonBehavior, FloatLayout, Deck):
    """
    Візуальний компонент колоди, що успадковує логіку класу Deck.
    """
    cards_count = NumericProperty(0)

    def __init__(self, **kwargs):
        # Ініціалізація Deck та FloatLayout
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (VisualConfig.CARD_W, VisualConfig.CARD_H)
        
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
                Line(rounded_rectangle=(self.x, self.y, self.width, self.height, VisualConfig.sdp(10)), width=VisualConfig.sdp(1), dash_offset=5)
            return

        with self.canvas.before:
            # Малювання шарів колоди для ефекту об'єму (3 карти зверху)
            offsets = [VisualConfig.sdp(4), VisualConfig.sdp(2), 0]
            visible_layers = offsets if self.cards_count > 2 else offsets[-self.cards_count:]
            
            for i, offset in enumerate(visible_layers):
                Color(0, 0, 0, 0.2)
                RoundedRectangle(pos=(self.x + offset + VisualConfig.sdp(2), self.y + offset - VisualConfig.sdp(2)), 
                                 size=self.size, radius=[VisualConfig.sdp(10)])
                Color(*get_color_from_hex('#34495e')) # Колір сорочки
                RoundedRectangle(pos=(self.x + offset, self.y + offset), 
                                 size=self.size, radius=[VisualConfig.sdp(10)])
                
                if i == len(visible_layers) - 1: # Тільки для верхньої карти малюємо візерунок
                    Color(1, 1, 1, 0.1)
                    Line(rounded_rectangle=(self.x + offset + VisualConfig.sdp(10), self.y + offset + VisualConfig.sdp(10), 
                                          self.width - VisualConfig.sdp(20), self.height - VisualConfig.sdp(20), VisualConfig.sdp(5)), width=VisualConfig.sdp(2))

        # Текст з кількістю карт
        count_label = Label(text=str(self.cards_count), font_size=VisualConfig.ssp(20), bold=True, 
                            color=(1, 1, 1, 0.5), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        self.add_widget(count_label)

class HandWidget(FloatLayout, Player):
    """
    Віджет руки. Тепер підтримує режим 'multi_select'.
    """
    selected_cards = ListProperty([]) 
    multi_select = BooleanProperty(True) # <--- НОВА ВЛАСТИВІСТЬ (Дозволити вибір кількох)

    is_main_player = BooleanProperty(False)
    spacing_x = NumericProperty(40)
    player_name = StringProperty('')

    def __init__(self, name="Player", player_id=None, is_main_player=False, **kwargs):
        kwargs['name'] = name
        kwargs['player_id'] = player_id
        self.is_main_player = is_main_player
        
        # Kivy автоматично обробить multi_select з kwargs у super().__init__
        super().__init__(**kwargs)
        
        self.player_name = name
        self.size_hint = (None, None)
        self.cards = [] 
        self.bg_rect = None 

        if self.is_main_player:
            self._base_size = (600, 150)
            self.size = (VisualConfig.sdp(self._base_size[0]), VisualConfig.sdp(self._base_size[1]))
            self.base_y = VisualConfig.sdp(20)
        else:
            self._base_size = (120, 160)
            self.size = (VisualConfig.sdp(self._base_size[0]), VisualConfig.sdp(self._base_size[1]))
            self.base_y = 0
            self.setup_opponent_ui()

        self.card_count_label = None
        if not self.is_main_player and VisualConfig.SHOW_BOT_CARD_COUNT:
            self._card_count_base_size = (40, 20)
            self._card_count_base_font = 14
            self.card_count_label = Label(
                text="",
                font_size=VisualConfig.ssp(self._card_count_base_font),
                color=VisualConfig.BOT_LABEL_COLOR,
                size_hint=(None, None),
                size=(VisualConfig.sdp(self._card_count_base_size[0]), VisualConfig.sdp(self._card_count_base_size[1])),
                bold=True,
            )
            self.add_widget(self.card_count_label)

        self.bind(pos=self.update_hand_layout, size=self.update_hand_layout)
        Window.bind(size=lambda *_: self._apply_scale())

    def _apply_scale(self):
        self.size = (VisualConfig.sdp(self._base_size[0]), VisualConfig.sdp(self._base_size[1]))
        if self.card_count_label:
            self.card_count_label.font_size = VisualConfig.ssp(self._card_count_base_font)
            self.card_count_label.size = (
                VisualConfig.sdp(self._card_count_base_size[0]),
                VisualConfig.sdp(self._card_count_base_size[1]),
            )
        if hasattr(self, "lbl_name"):
            self.lbl_name.font_size = VisualConfig.ssp(12)
            self.lbl_name.height = VisualConfig.sdp(20)
        if self.bg_rect:
            self.bg_rect.radius = [VisualConfig.sdp(10)]
        self.update_hand_layout()

    def clean_canvas(self):
        """Очищає намальований фон (темну зону), щоб не було дублікатів"""
        if self.bg_rect:
            self.canvas.before.remove(self.bg_rect)
            self.bg_rect = None
        self.canvas.before.clear() # Про всяк випадок чистимо все

    def setup_opponent_ui(self):
        """Створює UI для суперника (ім'я, фон)"""
        # Спочатку чистимо, щоб не малювати фон двічі (це фіксить темну зону)
        self.clean_canvas()

        with self.canvas.before:
            Color(0, 0, 0, 0.4)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[VisualConfig.sdp(10)])
        
        self.bind(pos=self.update_bg, size=self.update_bg)

        # Ім'я зверху
        if not hasattr(self, 'lbl_name') or self.lbl_name not in self.children:
            self.lbl_name = Label(
                text=self.name,
                font_size=VisualConfig.ssp(12),
                bold=True,
                size_hint=(1, None),
                height=VisualConfig.sdp(20),
                pos_hint={'top': 1, 'center_x': 0.5}
            )
            self.add_widget(self.lbl_name)

    def update_bg(self, *args):
        if self.bg_rect:
            self.bg_rect.pos = self.pos
            self.bg_rect.size = self.size

    def add_card(self, card_widget, initial_pos=None):
        """
        Додає карту.
        :param initial_pos: (x, y) - координати в системі координат HandWidget.
        """
        Player.add_card(self, card_widget) 
        if card_widget not in self.cards:
            self.cards.append(card_widget)
        
        # Налаштування візуалу
        if not self.is_main_player:
            card_widget.is_face_up = False 
            target_size = (
                VisualConfig.BOT_CARD_W,
                VisualConfig.BOT_CARD_H,
            )
        else:
            # Тільки коли потрапляє в руку героя, стає відкритою
            card_widget.is_face_up = True
            target_size = (
                VisualConfig.CARD_W,
                VisualConfig.CARD_H,
            ) 
            card_widget.bind(on_touch_down=self.on_card_touch)

        card_widget.pos_hint = {} 
        
        # === ЗАХИСТ ВІД ПОМИЛКИ "Already has a parent" ===
        if card_widget.parent:
            card_widget.parent.remove_widget(card_widget)
        # =================================================

        if initial_pos:
            card_widget.size = target_size
            card_widget.pos = initial_pos
            self.add_widget(card_widget)
        else:
            card_widget.size = target_size
            self.add_widget(card_widget)

        self.update_hand_layout()

    def remove_card(self, card_widget):
        Player.remove_card(self, card_widget)
        if card_widget in self.selected_cards:
            self.selected_cards.remove(card_widget)

        if card_widget in self.cards:
            self.cards.remove(card_widget)
            self.remove_widget(card_widget)
            self.update_hand_layout()

    def update_hand_layout(self, *args):
        if not self.cards:
            if self.card_count_label: self.card_count_label.text = ""
            return

        count = len(self.cards)
        
        if self.is_main_player:
            card_width = VisualConfig.CARD_W
            # Використовуємо поточну ширину віджета руки
            max_total_width = self.width 
            ideal_step = card_width * 0.6  # Карти перекривають одна одну на 40%
            
            # Скільки місця нам треба ідеально?
            needed_width = (count - 1) * ideal_step + card_width
            
            # Якщо не влазимо - зменшуємо крок
            if needed_width > max_total_width:
                available_space_for_steps = max_total_width - card_width
                if count > 1:
                    actual_step = available_space_for_steps / (count - 1)
                else:
                    actual_step = 0
            else:
                actual_step = ideal_step

            # Центруємо карти всередині віджета руки
            final_content_width = (count - 1) * actual_step + card_width
            start_x = self.x + (self.width - final_content_width) / 2
            
            base_y_pos = self.y + VisualConfig.sdp(10)

            for i, card in enumerate(self.cards):
                card.size = (VisualConfig.CARD_W, VisualConfig.CARD_H)
                
                target_x = start_x + (i * actual_step)
                
                # Логіка підняття карти
                target_y = base_y_pos
                if card.selected:
                    target_y += VisualConfig.sdp(30)
                
                # Щоб анімація не смикалася при дрібних змінах
                if abs(card.x - target_x) > 2 or abs(card.y - target_y) > 2:
                    Animation.stop_all(card)
                    anim = Animation(x=target_x, y=target_y, duration=0.15, t='out_quad')
                    anim.start(card)
                else:
                    # Якщо позиція майже та сама, ставимо жорстко (економить ресурси)
                    card.pos = (target_x, target_y)
                
                # Переконуємось, що карта додана у віджет
                if card.parent != self:
                    if card.parent: card.parent.remove_widget(card)
                    self.add_widget(card)
                
        else:
            # (Логіка бота - без змін)
            max_visible = VisualConfig.MAX_VISIBLE_BOT_CARDS
            display_count = min(count, max_visible)
            available_w = max(self.width * 0.9, 1)
            max_step = available_w / max(display_count - 1, 1)
            step = min(VisualConfig.sdp(12), max_step)
            card_w = min(VisualConfig.BOT_CARD_W, available_w)
            card_h = min(VisualConfig.BOT_CARD_H, self.height * 0.7)
            card_size = (card_w, card_h)
            total_w = (display_count - 1) * step + card_w
            start_x = self.center_x - (total_w / 2)
            base_y_pos = self.y 
            for i, card in enumerate(self.cards):
                Animation.stop_all(card)
                card.size = card_size
                if i < max_visible:
                    card.opacity = 1
                    card.pos = (start_x + (i * step), base_y_pos)
                else:
                    card.opacity = 0
                    card.pos = (start_x + (max_visible - 1) * step, base_y_pos)
                self.remove_widget(card)
                self.add_widget(card)

            if self.card_count_label:
                self.card_count_label.center_x = self.center_x
                self.card_count_label.y = base_y_pos + VisualConfig.sdp(80)
                self.card_count_label.text = f"x{count}"
                self.remove_widget(self.card_count_label)
                self.add_widget(self.card_count_label)

    def on_card_touch(self, instance, touch):
        if not self.is_main_player: return False
        if instance.collide_point(*touch.pos):
            self.select_card(instance)
            return True
        return False

    def select_card(self, card):
        if card not in self.cards: return

        # 1. Якщо мульти-вибір ЗАБОРОНЕНИЙ (наприклад, Війна)
        if not self.multi_select:
            if card.selected:
                # Якщо клікнули по вже вибраній - знімаємо виділення
                card.selected = False
                if card in self.selected_cards:
                    self.selected_cards.remove(card)
            else:
                # Якщо клікнули по новій - СПОЧАТКУ знімаємо все старе
                for c in list(self.selected_cards):
                    c.selected = False
                self.selected_cards = [] # Очищаємо список
                
                # Тепер виділяємо нову
                card.selected = True
                self.selected_cards.append(card)

        # 2. Якщо мульти-вибір ДОЗВОЛЕНИЙ (Дурак)
        else:
            if card.selected:
                card.selected = False
                if card in self.selected_cards:
                    self.selected_cards.remove(card)
            else:
                card.selected = True
                if card not in self.selected_cards:
                    self.selected_cards.append(card)
        
        self.update_hand_layout()

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
    Зона в центрі столу.
    Тепер реагує на кліки, якщо active=True.
    """
    active = BooleanProperty(False) 
    on_click_callback = ObjectProperty(None, allownone=True) # Колбек при кліку

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (0, 0)
        self.bind(pos=self.update_canvas, size=self.update_canvas, active=self.update_canvas)
        Window.bind(size=lambda *_: self._apply_scale())

    def _apply_scale(self):
        self.update_canvas()

    def on_touch_down(self, touch):
        # Якщо віджет активний і клік був по ньому
        if self.active and self.collide_point(*touch.pos):
            if self.on_click_callback:
                self.on_click_callback() # Викликаємо метод з VisualEngine
                return True
        return super().on_touch_down(touch)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.active:
                # Золотисте підсвічування - зона чекає на карту
                Color(0.95, 0.77, 0.06, 0.2)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[VisualConfig.sdp(15)])
                
                # Яскрава рамка, яка трохи пульсує (можна додати анімацію пізніше)
                Color(0.95, 0.77, 0.06, 0.8)
                Line(rounded_rectangle=(self.x, self.y, self.width, self.height, VisualConfig.sdp(15)), width=VisualConfig.sdp(3))
            else:
                # Спокійний стан
                Color(1, 1, 1, 0.05)
                Line(rounded_rectangle=(self.x, self.y, self.width, self.height, VisualConfig.sdp(15)), 
                    width=VisualConfig.sdp(1.5), dash_length=VisualConfig.sdp(8), dash_offset=VisualConfig.sdp(2))
