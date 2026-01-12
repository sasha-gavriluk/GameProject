from kivy.utils import get_color_from_hex
from kivy.metrics import dp, sp
from kivy.core.window import Window

class VisualConfig:
    # --- BASE SIZE FOR RESPONSIVE SCALE ---
    BASE_WIDTH = 1280
    BASE_HEIGHT = 720
    SCALE = 1.0
    MIN_SCALE = 0.75
    MAX_SCALE = 1.4

    @classmethod
    def update_scale(cls, size=None):
        w, h = size or Window.size
        if not w or not h:
            return
        if Window.rotation in (90, 270):
            w, h = h, w
        scale = min(w / cls.BASE_WIDTH, h / cls.BASE_HEIGHT)
        cls.SCALE = max(cls.MIN_SCALE, min(cls.MAX_SCALE, scale))
        base_w = cls.sdp(cls.CARD_WIDTH)
        max_w = w * cls.CARD_MAX_WIDTH_RATIO
        min_w = cls.sdp(cls.CARD_MIN_WIDTH)
        card_w = max(min_w, min(base_w, max_w))
        cls.CARD_W = card_w
        cls.CARD_H = card_w * cls.CARD_ASPECT_RATIO
        cls.BOT_CARD_W = cls.CARD_W * 0.5
        cls.BOT_CARD_H = cls.CARD_H * 0.5

    @classmethod
    def bind_to_window(cls):
        cls.update_scale()
        Window.bind(size=lambda *_: cls.update_scale())

    @classmethod
    def sdp(cls, value):
        return dp(value) * cls.SCALE

    @classmethod
    def ssp(cls, value):
        return sp(value) * cls.SCALE

    # --- КОЛЬОРИ ---
    TABLE_COLOR = get_color_from_hex('#27ae60')      # Зелене сукно
    BACKGROUND_COLOR = get_color_from_hex('#2c3e50') # Темний фон меню
    BOT_LABEL_COLOR = (1, 1, 1, 0.8)                 # Колір тексту лічильника карт бота

    # --- КАРТИ ---
    CARD_WIDTH = 80
    CARD_HEIGHT = 112
    CARD_MIN_WIDTH = 50
    CARD_MAX_WIDTH_RATIO = 0.12
    BOT_CARD_WIDTH = 40
    BOT_CARD_HEIGHT = 56
    CARD_ASPECT_RATIO = 1.4
    CARD_W = CARD_WIDTH
    CARD_H = CARD_HEIGHT
    BOT_CARD_W = BOT_CARD_WIDTH
    BOT_CARD_H = BOT_CARD_HEIGHT

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
    BATTLE_AREA_HEIGHT_RATIO = 0.28

    # Колода
    DECK_X_RATIO = 0.075           
    DECK_Y_RATIO = 0.50            
    DECK_SPACING = 40          

    # Боти
    BOT_TOP_OFFSET = 10        
    MAX_VISIBLE_BOT_CARDS = 6      
    BOT_HAND_BASE_WIDTH = 120
    BOT_HAND_BASE_HEIGHT = 160
    BOT_HAND_MAX_WIDTH_RATIO = 0.28
    BOT_HAND_MAX_HEIGHT_RATIO = 0.22
    
    # === ДОДАЙ ЦЕЙ РЯДОК ===
    SHOW_BOT_CARD_COUNT = True  # Показувати лічильник карт (x6) над ботом

VisualConfig.bind_to_window()
