from utils.engine import Player

class BotPlayer(Player):
    def __init__(self, name="Bot"):
        super().__init__(name)

    def think(self, engine):
        """
        Основний метод інтелекту. 
        Повертає дію: рядок ('pass', 'take') або об'єкт Card.
        """
        rules = engine.rules
        trump = engine.extra_data.get('trump')
        trump_suit = trump.suit if trump else None
        
        # 1. Визначаємо роль (Атакуючий чи Захисник?)
        my_idx = engine.players.index(self)
        is_defender = (my_idx == rules.defender_idx)
        
        # 2. Викликаємо відповідну логіку
        if is_defender:
            return self._defense_logic(engine, rules, trump_suit)
        else:
            return self._attack_logic(engine, rules, trump_suit)

    def _attack_logic(self, engine, rules, trump_suit):
        """Логіка атаки та підкидання"""
        table = engine.table
        
        # Якщо стіл пустий — це перший хід. Можна ходити чим завгодно.
        if not table:
            return self._get_min_card(self.hand, trump_suit, rules)

        # Якщо на столі є карти — це підкидання.
        # Шукаємо карти, ранги яких співпадають з картами на столі.
        ranks_on_table = {c.rank for c in table}
        candidates = [c for c in self.hand if c.rank in ranks_on_table]
        
        if not candidates:
            return "pass" # Нічим підкинути -> Бито

        # Підкидаємо найменшу з можливих
        return self._get_min_card(candidates, trump_suit, rules)

    def _defense_logic(self, engine, rules, trump_suit):
        """Логіка захисту"""
        pending = rules.pending_attacks
        
        # Якщо немає загроз, або ми їх вже відбили, але хід ще наш (рідкісний кейс) -> pass/take
        if not pending:
            return "take" 
            
        # Бот б'є загрози по одній (першу в списку)
        threat_card = pending[0]
        
        # 1. Спробуємо знайти карту, яка б'є цю загрозу
        winning_cards = []
        for card in self.hand:
            # Перевіряємо легальність ходу через правила
            # is_legal_move очікує список карт, тому передаємо [card]
            if rules.is_legal_move([card], self, table=engine.table, engine=engine):
                winning_cards.append(card)
        
        if not winning_cards:
            return "take" # Нема чим бити -> беру

        # 2. Вибираємо найоптимальнішу карту (найменшу)
        return self._get_min_card(winning_cards, trump_suit, rules)

    def _get_min_card(self, cards, trump_suit, rules):
        """Допоміжна функція: знаходить найслабшу карту в списку"""
        if not cards: return None
        
        # Сортуємо: 
        # 1. Не козирі (False=0) йдуть раніше за козирів (True=1)
        # 2. За номіналом (ranks_values)
        def sort_key(c):
            is_trump = (c.suit == trump_suit)
            value = rules.ranks_values.get(c.rank, 0)
            return (is_trump, value)
            
        sorted_cards = sorted(cards, key=sort_key)
        return sorted_cards[0]