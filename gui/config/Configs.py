from kivy.utils import get_color_from_hex
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.event import EventDispatcher
from kivy.properties import NumericProperty


class ResponsiveMetrics(EventDispatcher):
    scale = NumericProperty(1.0)

    def __init__(
        self,
        base_width=1280,
        base_height=720,
        min_scale=0.7,
        max_scale=1.3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.base_width = base_width
        self.base_height = base_height
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.update_scale(Window.width, Window.height)
        Window.bind(on_resize=self._on_resize)

    def _on_resize(self, window, width, height):
        self.update_scale(width, height)

    def update_scale(self, width, height):
        scale = min(width / self.base_width, height / self.base_height)
        scale = max(self.min_scale, min(self.max_scale, scale))
        self.scale = scale

    def dp(self, value):
        return dp(value) * self.scale

    def sp(self, value):
        return sp(value) * self.scale


responsive_metrics = ResponsiveMetrics()


def sdp(value):
    return responsive_metrics.dp(value)


def ssp(value):
    return responsive_metrics.sp(value)

class VisualConfig:
    # --- КОЛЬОРИ ---
    TABLE_COLOR = get_color_from_hex('#27ae60')      # Зелене сукно
    BACKGROUND_COLOR = get_color_from_hex('#2c3e50') # Темний фон меню
    BOT_LABEL_COLOR = (1, 1, 1, 0.8)                 # Колір тексту лічильника карт бота

    # --- КАРТИ ---
    CARD_WIDTH = 80
    CARD_HEIGHT = 112
    CARD_ASPECT_RATIO = 1.4

    # --- АНІМАЦІЇ (секунди) ---
    DEAL_SPEED = 0.5         
    PLAY_SPEED = 0.5          
    DISCARD_SPEED = 0.5       
    TRUMP_REVEAL_SPEED = 0.6  
    
    # === ДОДАЄМО НОВИЙ ПАРАМЕТР ===
    HAND_ANIMATION_SPEED = 0.6  # Швидкість переміщення/сортування карт в руці (було 0.2)

    # === НОВИЙ ПАРАМЕТР ===
    BOT_DELAY = 1.0  # Затримка перед ходом бота (в секундах)
    
    # Герой (ми)
    HERO_WIDTH_PERCENT = 0.95      
    HERO_MAX_WIDTH = 600
    HERO_BOTTOM_OFFSET = 20
    
    # Зона Бою
    BATTLE_AREA_Y_RATIO = 0.5 
    BATTLE_AREA_WIDTH_RATIO = 0.58

    # Колода
    DECK_X_RATIO = 0.075           
    DECK_Y_RATIO = 0.50            
    DECK_SPACING = 40

    # Боти
    BOT_TOP_OFFSET = 10
    MAX_VISIBLE_BOT_CARDS = 6      
    
    # === ДОДАЙ ЦЕЙ РЯДОК ===
    SHOW_BOT_CARD_COUNT = True  # Показувати лічильник карт (x6) над ботом

    @staticmethod
    def card_size():
        return sdp(VisualConfig.CARD_WIDTH), sdp(VisualConfig.CARD_HEIGHT)

    @staticmethod
    def small_card_size():
        return sdp(40), sdp(56)
