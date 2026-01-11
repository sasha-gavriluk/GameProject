from kivy.utils import get_color_from_hex
from kivy.metrics import dp

class VisualConfig:
    # --- КОЛЬОРИ ---
    TABLE_COLOR = get_color_from_hex('#27ae60')      # Зелене сукно
    BACKGROUND_COLOR = get_color_from_hex('#2c3e50') # Темний фон меню
    BOT_LABEL_COLOR = (1, 1, 1, 0.8)                 # Колір тексту лічильника карт бота

    # --- КАРТИ ---
    CARD_WIDTH = dp(80)
    CARD_HEIGHT = dp(112)
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
    HERO_MAX_WIDTH = dp(600)       
    HERO_BOTTOM_OFFSET = dp(20)    
    
    # Зона Бою
    BATTLE_AREA_Y_RATIO = 0.5 
    BATTLE_AREA_WIDTH_RATIO = 0.58

    # Колода
    DECK_X_RATIO = 0.075           
    DECK_Y_RATIO = 0.50            
    DECK_SPACING = dp(40)          

    # Боти
    BOT_TOP_OFFSET = dp(10)        
    MAX_VISIBLE_BOT_CARDS = 6      
    
    # === ДОДАЙ ЦЕЙ РЯДОК ===
    SHOW_BOT_CARD_COUNT = True  # Показувати лічильник карт (x6) над ботом