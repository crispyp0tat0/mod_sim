import random


class Wheel:
    def __init__(self, weights=None):
        self.numbers = list(range(37))  # Numbers 0 to 36
        self.weights = weights if weights and len(weights) == 37 else [1.0] * 37

    def color(self, number):
        if number == 0:
            return "green"
        elif number in {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}:
            return "red"
        else:
            return "black"
        
    def spin(self):
        if not self.weights or len(self.weights) != 37:
            self.weights = [1.0] * 37
        if all(w == 0 for w in self.weights):
            return random.randrange(37)
        return random.choices(self.numbers, weights=self.weights, k=1)[0]
    

class Bet:
    def __init__(self, bet_type, amount, choices):
        self.bet_type = bet_type
        self.amount = amount
        self.choices = choices if isinstance(choices, list) else [choices]
    
    def is_win(self, number, color):
        if self.bet_type == "color":
            return color in self.choices
        return number in self.choices
    
    def payout_multiplier(self):
        if self.bet_type == "straight":
            return 35
        elif self.bet_type == "split":
            return 17
        elif self.bet_type == "street":
            return 11
        elif self.bet_type == "corner":
            return 8
        elif self.bet_type == "line":
            return 5
        elif self.bet_type == "dozen" or self.bet_type == "column":
            return 2
        elif self.bet_type == "even_odd" or self.bet_type == "high_low" or self.bet_type == "color":
            return 1
        

class Player:
    def __init__(self, balance):
        self.balance = balance
        self.bets = []

    def place_bet(self, bet):
        if bet.amount <= self.balance:
            self.bets.append(bet)
            self.balance -= bet.amount
            return True
        return False
    
    def clear_bets(self):
        self.bets = []


class Game:
    def __init__(self, player, weights=None):
        self.wheel = Wheel(weights)
        self.player = player

    def spin_wheel(self):
        number = self.wheel.spin()
        color = self.wheel.color(number)

        winnings = 0

        for bet in self.player.bets:
            if bet.is_win(number, color):
                payout = bet.amount * bet.payout_multiplier()
                self.player.balance += payout + bet.amount  # Return bet amount plus winnings
                winnings += payout
            else:
                winnings -= bet.amount

        self.player.clear_bets()
        return number, color, winnings
    

def dozen(n):
    return list(range((n-1)*12+1, n*12+1))

def column(n):
    return list(range(n, 37, 3))

def even():
    return list(range(2, 37, 2))

def odd():
    return list(range(1, 36, 2))

def low():
    return list(range(1, 19))

def high():
    return list(range(19, 37))