from kivy.animation import Animation
from kivy.metrics import dp
import random

class AnimationManager:
    
    @staticmethod
    def animate_selection(card_widget, is_selected):
        """Анімація підйому карти при виборі."""
        target_y = card_widget.base_y + dp(30) if is_selected else card_widget.base_y
        anim = Animation(y=target_y, duration=0.15, t='out_quad')
        anim.start(card_widget)

    @staticmethod
    def animate_card_to_table(card_widget, target_pos, duration=0.4, on_complete=None):
        """Анімація перельоту карти з руки на стіл."""
        anim = Animation(pos=target_pos, duration=duration, t='out_quad')
        if on_complete:
            anim.bind(on_complete=on_complete)
        anim.start(card_widget)

    @staticmethod
    def animate_discard(card_widget, screen_width, screen_height, on_complete=None):
        """Анімація вильоту карти у відбій (БИТО)."""
        anim = Animation(
            pos=(-dp(300), screen_height / 2), 
            angle=random.uniform(-90, 90), 
            duration=0.6, 
            t='in_back'
        )
        if on_complete:
            anim.bind(on_complete=lambda a, c: on_complete(c))
        anim.start(card_widget)

    @staticmethod
    def animate_deal(card_widget, target_pos, duration=0.5):
        """Нова анімація: роздача карти з колоди в руку."""
        # Спочатку карта маленька і прозора (опційно)
        card_widget.opacity = 0
        anim = Animation(pos=target_pos, opacity=1, duration=duration, t='out_cubic')
        anim.start(card_widget)

    @staticmethod
    def deal_card(card_widget, from_deck, to_hand, duration=0.5):
        """Анімація роздачі: з колоди в руку."""
        # 1. Отримуємо початкову позицію відносно вікна
        start_pos_window = from_deck.to_window(*from_deck.pos)
        
        # 2. Додаємо карту на стіл (TableWidget), щоб вона була над усіма елементами під час польоту
        table = from_deck.parent
        if card_widget.parent:
            card_widget.parent.remove_widget(card_widget)
        table.add_widget(card_widget)
        
        # Ставимо карту в точку, де знаходиться колода
        card_widget.size_hint = (None, None)
        card_widget.pos = table.to_widget(*start_pos_window)
        card_widget.opacity = 0

        # 3. Розраховуємо цільову позицію (центр руки)
        # Оскільки ми не можемо додати її в BoxLayout до кінця анімації, 
        # просто летимо в область руки
        target_pos_window = to_hand.to_window(to_hand.x + to_hand.width/2, to_hand.y)
        target_pos = table.to_widget(*target_pos_window)

        anim = Animation(
            pos=(target_pos[0] - card_widget.width/2, target_pos[1]), 
            opacity=1, 
            duration=duration, 
            t='out_cubic'
        )

        def on_complete(a, c):
            # 4. Тільки після прильоту переміщуємо карту в BoxLayout руки
            table.remove_widget(c)
            to_hand.add_card(c)
            # BoxLayout сам виставить потрібні координати (pos)

        anim.bind(on_complete=on_complete)
        anim.start(card_widget)

    @staticmethod
    def play_card(card_widget, from_hand, to_table, target_pos):
        """Анімація ходу: з руки на стіл."""
        # 1. Фіксуємо позицію на екрані
        window_pos = card_widget.to_window(*card_widget.pos)
        
        # 2. Скидаємо стан виділення
        card_widget.selected = False 
        if hasattr(card_widget, 'update_canvas'):
            card_widget.update_canvas() # Прибираємо обводку негайно

        # 3. Логічне переміщення
        from_hand.remove_card(card_widget)
        card_widget.size_hint = (None, None)
        to_table.add_widget(card_widget)
        
        # 4. Встановлюємо координати відносно столу
        card_widget.pos = to_table.to_widget(*window_pos)
        
        # 5. Анімація
        anim = Animation(
            pos=target_pos, 
            angle=random.uniform(-7, 7), 
            duration=0.3, 
            t='out_quad'
        )
        anim.start(card_widget)