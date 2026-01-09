from kivy.utils import get_color_from_hex
from kivy.metrics import dp

class VisualConfig:

    # Швидкість польоту карти при роздачі (чим менше, тим швидше)
    DEAL_SPEED = 0.15          
    
    # Пауза між вильотом наступної карти в черзі
    DEAL_DELAY = 0.02          
    
    # Тривалість анімації відкриття козиря
    TRUMP_REVEAL_SPEED = 0.8
    
    # Швидкість підйому карти при виборі в руці
    SELECT_SPEED = 0.1
    
    # --- Загальні налаштування столу ---
    TABLE_COLOR = get_color_from_hex('#27ae60')
    BACKGROUND_COLOR = get_color_from_hex('#2c3e50') # Для меню або фону
    
    # --- Налаштування Карт ---
    CARD_WIDTH = dp(80)
    CARD_HEIGHT = dp(112)
    CARD_ASPECT_RATIO = 1.4
    
    # --- Налаштування Гравців (HandWidget) ---
    # Герой (Головний гравець)
    HERO_MAX_WIDTH = dp(800)       # Максимальна ширина зони гравця
    HERO_WIDTH_PERCENT = 0.9       # % від ширини екрану
    HERO_BOTTOM_OFFSET = dp(20)    # Відступ знизу
    
    # Розміри віджета руки (перевизначаються в HandWidget, але тут для довідки)
    HERO_HAND_SIZE = (dp(600), dp(150))
    OPPONENT_HAND_SIZE = (dp(120), dp(160))
    
    
    # --- Колода та Козирь ---
    DECK_OFFSET_X = dp(40) # Зміщення колоди від центру вліво
    DECK_OFFSET_Y = dp(20) # Зміщення колоди від центру вверх
    TRUMP_OFFSET_X = dp(40) # Наскільки козирь стирчить з-під колоди
    
    # --- Анімації (час в секундах) ---
    ANIM_DURATION_NORMAL = 0.1
    ANIM_DURATION_FAST = 0.2
    ANIM_DURATION_DEAL = 0.1

    # 0.42 — це трохи нижче математичного центру (0.5), 
    # що ідеально звільняє місце під ботами зверху.
    BATTLE_AREA_Y_RATIO = 0.50

    # Змінюємо позицію колоди під час бою
    # 0.07 — дуже близько до лівого краю
    # 0.4 — трохи вище центру, щоб не заважати картам Hero
    DECK_GAME_X_RATIO = 0.07
    DECK_GAME_Y_RATIO = 0.50

    # Якщо ви хочете, щоб колода спочатку була праворуч від центру:
    # Зробіть це значення від'ємним. Якщо ліворуч — додатнім.
    DECK_OFFSET_X = dp(5)  # Наприклад, змістити на 150 пікселів вбік
    DECK_OFFSET_Y = dp(5)   # Змістити вгору або вниз

    SHOW_BOT_CARD_COUNT = True  # Увімкнути/вимкнути лічильник
    MAX_VISIBLE_BOT_CARDS = 6   # Скільки максимум карт малювати візуально
    BOT_LABEL_COLOR = (1, 1, 1, 0.8)  # Колір тексту лічильника

class GamePreset:
    name = "base"
    buttons = []
    deal_type = "default"
    show_trump = False
    cards_per_player = 0
    default_players = 2  # Скільки гравців створювати для тесту

class WarPreset(GamePreset):
    name = "war"
    buttons = []
    deal_type = "equal"
    show_trump = False
    cards_per_player = 0
    default_players = 2

class DurakPreset(GamePreset):
    name = "durak"
    buttons = ["Біта", "Взяти"]
    deal_type = "by_six"
    show_trump = True
    cards_per_player = 6
    default_players = 4 # Наприклад, 4 для тесту