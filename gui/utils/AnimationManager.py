from kivy.animation import Animation
import random

from gui.config.Configs import VisualConfig, sdp

class AnimationManager:

    @staticmethod
    def animate_card_to_table(card_widget, target_pos, duration=0.4, on_complete=None):
        """Анімація перельоту карти з руки на стіл."""
        anim = Animation(pos=target_pos, duration=duration, t='out_quad')
        if on_complete:
            anim.bind(on_complete=on_complete)
        anim.start(card_widget)

    @staticmethod
    def animate_discard(card_widget, screen_width, screen_height, on_complete=None):
        """Анімація відбою."""
        anim = Animation(
            pos=(-sdp(300), screen_height / 2), 
            angle=random.uniform(-90, 90), 
            duration=0.6, 
            t='in_back'
        )
        if on_complete:
            anim.bind(on_complete=lambda a, c: on_complete(c))
        anim.start(card_widget)

    @staticmethod
    def animate_deal(card_widget, target_pos, duration=0.5):
        """Анімація появи карти."""
        card_widget.opacity = 0
        anim = Animation(pos=target_pos, opacity=1, duration=duration, t='out_cubic')
        anim.start(card_widget)

    @staticmethod
    def animate_deal_to_player(card_widget, target_player_widget, duration=None, on_complete=None):
        # Якщо duration не передано, беремо з конфігу
        anim_duration = duration if duration is not None else VisualConfig.DEAL_SPEED
        
        target_x = target_player_widget.center_x - card_widget.width / 2
        target_y = target_player_widget.center_y - card_widget.height / 2

        anim = Animation(
            x=target_x, 
            y=target_y, 
            angle=0, 
            duration=anim_duration, 
            t='out_quad'
        )
        if on_complete:
            anim.bind(on_complete=on_complete)
        anim.start(card_widget)

    @staticmethod
    def animate_play_card(card_widget, target_center, duration=0.3):
        """Анімація ходу в центр вказаної точки"""
        anim = Animation(
            center=target_center, # Використовуємо center замість pos або x/y
            angle=random.uniform(-5, 5), 
            duration=duration, 
            t='out_quad'
        )
        anim.start(card_widget)

    @staticmethod
    def animate_trump_reveal(card_widget, deck_widget, duration=None):
        anim_duration = duration if duration is not None else VisualConfig.TRUMP_REVEAL_SPEED
        deck_cx, deck_cy = deck_widget.center
        
        # Спочатку карта перевертається (якщо ще не перевернута)
        card_widget.is_face_up = True
        
        target_center_x = deck_cx + sdp(40)
        target_center_y = deck_cy

        # Використовуємо 'out_back' для ефекту вистрибування
        anim = Animation(
            center_x=target_center_x,
            center_y=target_center_y,
            angle=90, 
            duration=anim_duration,
            t='out_back'
        )
        anim.start(card_widget)

    @staticmethod
    def animate_move_deck_to_side(deck_widget, trump_card, target_pos, duration=0.8):
        """Плавне відсунення колоди в ігрову зону"""
        # Використовуємо 'out_cubic' для більш плавної зупинки
        anim_deck = Animation(center=target_pos, duration=duration, t='out_cubic')
        
        if trump_card:
            # Зсув козиря відносно нового центру колоди
            target_trump_x = target_pos[0] + sdp(40)
            anim_trump = Animation(
                center_x=target_trump_x, 
                center_y=target_pos[1], 
                duration=duration, 
                t='out_cubic'
            )
            anim_trump.start(trump_card)
            
        anim_deck.start(deck_widget)

    # ПРАВИЛЬНИЙ ВАРІАНТ
    @staticmethod
    def animate_selection(card_widget, is_selected):
        target_offset = sdp(30) if is_selected else 0
        # Переконайтеся, що анімується offset_y, а НЕ y
        anim = Animation(offset_y=target_offset, duration=0.15, t='out_quad')
        anim.start(card_widget)
        
