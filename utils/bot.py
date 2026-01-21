from utils.engine import Player
import random

class BotPlayer(Player):
    def __init__(self, name="Bot", **kwargs):
        super().__init__(name, **kwargs)

    def think(self, engine):
        """
        Основний метод інтелекту. 
        Повертає дію: рядок ('pass', 'take') або об'єкт Card.
        """
        rules = engine.rules
        rule_name = rules.__class__.__name__
        
        # Вибираємо стратегію залежно від гри
        if rule_name == 'WarRules':
            return self._war_strategy(engine)
        elif rule_name == 'BridgeRules':
            return self._bridge_strategy(engine)
        elif rule_name == 'DurakRules':
            return self._durak_strategy(engine)
            
        return None

    # --- СТРАТЕГІЯ ДЛЯ ВІЙНИ ---
    def _war_strategy(self, engine):
        # У війні просто ходимо першою картою, яка є
        if self.hand:
            return self.hand[0]
        return None

    # --- СТРАТЕГІЯ ДЛЯ БРІДЖУ ---
    def _bridge_strategy(self, engine):
        rules = engine.rules
        
        # 1. Якщо треба крити 6-ку або ми вже брали карту -> намагаємось походити
        # (У BridgeRules pass дозволений тільки якщо has_taken_card=True і немає must_cover_six)
        
        # Знаходимо всі легальні карти
        legal_cards = [c for c in self.hand if rules.is_legal_move(c, self, table=engine.table, engine=engine)]
        
        # Якщо немає чим ходити:
        if not legal_cards:
            if rules.has_taken_card and not rules.must_cover_six:
                return "pass"
            return "take"

        # Пріоритет ходів для бота (щоб насолити гравцю)
        # 7 (змушує брати), 8 (змушує брати), 6 (змушує крити), A (пропуск), J (замовлення)
        priority_ranks = ['7', '8', '6', 'A', 'J']
        
        for rank in priority_ranks:
            candidates = [c for c in legal_cards if c.rank == rank]
            if candidates:
                # Якщо можемо — кидаємо кілька карт одного рангу
                if len(candidates) > 1:
                    return candidates
                # Якщо це Валет, бот має вибрати масть. 
                # (Логіка вибору масті вже є в правилах BridgeRules або буде рандомною при виконанні)
                return candidates[0]

        # Якщо немає спецкарт, кидаємо ту, що дає найменше очок (або найбільше, залежить від тактики)
        # У Бріджі ми хочемо позбутися карт.
        # Якщо є кілька однакового рангу — кидаємо всі
        rank_groups = {}
        for c in legal_cards:
            rank_groups.setdefault(c.rank, []).append(c)
        for cards in rank_groups.values():
            if len(cards) > 1:
                return cards
        return legal_cards[0]

    # --- СТРАТЕГІЯ ДЛЯ ДУРАКА ---
    def _durak_strategy(self, engine):
        rules = engine.rules
        trump = engine.extra_data.get('trump')
        trump_suit = trump.suit if trump else None
        
        # 1. Визначаємо роль (Атакуючий чи Захисник?)
        my_idx = engine.players.index(self)
        is_defender = (my_idx == rules.defender_idx)
        
        if is_defender:
            return self._defense_logic(engine, rules, trump_suit)
        else:
            return self._attack_logic(engine, rules, trump_suit)

    def _attack_logic(self, engine, rules, trump_suit):
        """Логіка атаки та підкидання"""
        table = engine.table
        
        if not table:
            # Спочатку пробуємо кинути кілька карт одного рангу, якщо це легально
            rank_groups = {}
            for c in self.hand:
                rank_groups.setdefault(c.rank, []).append(c)
            for cards in rank_groups.values():
                if len(cards) > 1 and rules.is_legal_move(cards, self, table=engine.table, engine=engine):
                    return cards

            # Інакше кидаємо найменшу легальну карту
            def sort_key(c):
                is_trump = (c.suit == trump_suit)
                value = rules.ranks_values.get(c.rank, 0) if hasattr(rules, 'ranks_values') else 0
                return (is_trump, value)
            for card in sorted(self.hand, key=sort_key):
                if rules.is_legal_move(card, self, table=engine.table, engine=engine):
                    return card
            return None

        ranks_on_table = {c.rank for c in table}
        candidates = [c for c in self.hand if c.rank in ranks_on_table]
        
        if not candidates:
            return "pass"

        rank_groups = {}
        for c in candidates:
            rank_groups.setdefault(c.rank, []).append(c)
        for cards in rank_groups.values():
            if len(cards) > 1 and rules.is_legal_move(cards, self, table=engine.table, engine=engine):
                return cards

        def sort_key(c):
            is_trump = (c.suit == trump_suit)
            value = rules.ranks_values.get(c.rank, 0) if hasattr(rules, 'ranks_values') else 0
            return (is_trump, value)
        for card in sorted(candidates, key=sort_key):
            if rules.is_legal_move(card, self, table=engine.table, engine=engine):
                return card

        return "pass"

    def _defense_logic(self, engine, rules, trump_suit):
        """Логіка захисту"""
        pending = rules.pending_attacks
        
        if not pending:
            return "take" 
            
        threat_card = pending[0]
        
        winning_cards = []
        for card in self.hand:
            # Перевіряємо, чи можна побити загрозу цією картою
            # is_legal_move у Дураку очікує список
            if rules.is_legal_move([card], self, table=engine.table, engine=engine):
                winning_cards.append(card)
        
        if not winning_cards:
            return "take"

        return self._get_min_card(winning_cards, trump_suit, rules)

    def _get_min_card(self, cards, trump_suit, rules):
        """Знаходить найслабшу карту в списку"""
        if not cards: return None
        
        # Сортуємо: Не козирі -> Козирі; Менший номінал -> Більший
        def sort_key(c):
            is_trump = (c.suit == trump_suit)
            # Беремо значення рангу з правил, або дефолтне
            value = rules.ranks_values.get(c.rank, 0) if hasattr(rules, 'ranks_values') else 0
            return (is_trump, value)
            
        sorted_cards = sorted(cards, key=sort_key)
        return sorted_cards[0]
