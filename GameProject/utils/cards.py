import random

class Card:
    def __init__(self, suit=None, rank=None, **kwargs):
        # Встановлюємо значення тільки якщо вони передані явно.
        # Це дозволяє Kivy Properties (в CardWidget) зберігати значення, 
        # які були встановлені EventDispatcher'ом раніше, і не перезаписувати їх на None.
        if suit is not None:
            self.suit = suit
        if rank is not None:
            self.rank = rank

    def __repr__(self):
        return f"{self.rank}{self.suit_symbol()}"

    def suit_symbol(self):
        symbols = {
            'hearts': '♥',
            'diamonds': '♦',
            'clubs': '♣',
            'spades': '♠'
        }
        return symbols.get(self.suit, self.suit)
    
class Deck:
    def __init__(self, size=52, **kwargs):
        self.suits = ['hearts', 'diamonds', 'clubs', 'spades']
        if size == 36:
            self.ranks = ['6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        else:
            self.ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.cards = [Card(s, r) for s in self.suits for r in self.ranks]

    def shuffle(self):
        """Перемішує колоду"""
        random.shuffle(self.cards)

    def deal(self):
        """Видає одну карту з верху"""
        if len(self.cards) > 0:
            return self.cards.pop()
        return None
    
    def __len__(self):
        return len(self.cards)
