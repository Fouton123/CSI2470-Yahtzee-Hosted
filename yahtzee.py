from random import randint

LABELS = ["Ones", "Twos", "Threes", "Fours", "Fives", "Sixes", "3 of a Kind", "4 of a Kind", "Full House", "Small Straight", "Large Straight", "Chance", "Yahtzee", "Yahtzee Bounus"]

class yahtzee:
    def __init__(self):
        self.dice = [0] * 5
        self.new_game()

    def new_game(self):
        self.available = [1] * 14
        self.scores = [0] * 14
        self.reset_roll()

    def roll(self):
        for i in range(5):
            if self.roll_count == 3 or self.reroll[i] is True:
                self.dice[i] = randint(1, 6)

    def set_reroll(self, reroll):
        self.reroll = reroll

    def next_roll(self):
        if self.roll_count <= 0:
            return "No rolls left! Score your dice to begin the next turn."

        self.roll()
        self.roll_count -= 1
        return f'Dice: {self.dice}, Rolls Left: {self.roll_count}'

    def reset_roll(self):
        self.roll_count = 3  
        self.reroll = [True] * 5
        self.dice = [0] * 5

    def get_counts(self): 
        self.counts = [0] * 6
        for count, i in enumerate(self.dice):
            self.counts[i-1] += 1

    def get_final_score(self):
        self.get_counts()
        options = f'| {"Upper Section".center(27)} |\n'
        options += f'| {"Num".ljust(3)} | {"Name".ljust(15)} | {"Pts".rjust(3)} |\n'
        lower = self.get_lower_score()
        upper = self.get_upper_score()
        bonus = 35 if upper >= 63 else 0

        for count, i in enumerate(self.available):
            if count == 6:
                options += f'| {"".ljust(3)} | {"Bonus".ljust(15)} | {str(bonus).rjust(3)} |\n'
                options += f'| {"Lower Section".center(27)} |\n'
                options += f'| {"Num".ljust(3)} | {"Name".ljust(15)} | {"Pts".rjust(3)} |\n'

            options += f'| {str(count+1).ljust(3)} | {LABELS[count].ljust(15)} | {str(self.scores[count]).rjust(3)} |\n'

        options += f'| {"Total Lower Score".rjust(21)} | {str(lower).rjust(3)} |\n'
        options += f'| {"Total Upper Score".rjust(21)} | {str(upper).rjust(3)} |\n'
        options += f'| {"GRAND TOTAL".rjust(21)} | {str(lower+upper+bonus).rjust(3)} |\n'
        
        return options


    def get_upper_score(self):
        return sum(self.scores[0:6])
            
    def get_lower_score(self):
        return sum(self.scores[6:14])
    
    def get_current_score(self):
        options = f'| {"Num".ljust(3)} | {"Name".ljust(15)} | {"Pts".rjust(3)} |\n'
        for count, i in enumerate(self.available):
            score = "" if self.available[count] else str(self.scores[count])
            options += f'| {str(count+1).ljust(3)} | {LABELS[count].ljust(15)} | {score.rjust(3)} |\n'
        return options
    
    def get_available_scores(self):
        options = f'| {"Num".ljust(3)} | {"Name".ljust(15)} |\n'
        for count, i  in enumerate(self.available):
            if i > 0:
                options += f'| {str(count+1).ljust(3)} | {LABELS[count].ljust(15)} |\n'

        return options
    
    def get_scoreboard(self):
        options = f'| {"Num".ljust(3)} | {"Name".ljust(15)} | {"Pts".rjust(3)} |\n'
        for i, label in enumerate(LABELS[:13]):  # exclude Yahtzee bonus for simplicity
            if self.available[i] == 0:
                pts = str(self.scores[i])
            else:
                pts = ""
            options += f'| {str(i+1).ljust(3)} | {label.ljust(15)} | {pts.rjust(3)} |\n'
        return options

    def score_dice(self, index):
        if self.available[index] == 0:
            return
        self.available[index] -= 1
        
        # Yahtzee bonus
        if self.is_yahtzee() and self.scores[12] == 50:
            self.scores[13] += 100
            
         # Upper section (1s to 6s)
        if 0 <= index <= 5:
            self.get_counts()
            self.scores[index] = self.counts[index] * (index + 1)

        # Three of a kind
        elif index == 6 and self.is_three_of_a_kind():
            self.scores[index] = sum(self.dice)

        # Four of a kind
        elif index == 7 and self.is_four_of_a_kind():
            self.scores[index] = sum(self.dice)

        # Full House
        elif index == 8 and self.is_full_house():
            self.scores[index] = 25

        # Small Straight
        elif index == 9 and self.is_small_straight():
            self.scores[index] = 30

        # Large Straight
        elif index == 10 and self.is_large_straight():
            self.scores[index] = 40

        # Chance
        elif index == 11:
            self.scores[index] = sum(self.dice)

        # Yahtzee
        elif index == 12 and self.is_yahtzee():
            self.scores[index] = 50

        if self.is_game_end() is True:
            return self.get_final_score()        
        else:
            self.reset_roll()
            return self.get_current_score()
        
    def is_yahtzee(self):
        self.get_counts()
        return 5 in self.counts    

    def is_three_of_a_kind(self):
        self.get_counts()
        return any(count >= 3 for count in self.counts)
    
    def is_four_of_a_kind(self):
        self.get_counts()
        return any(count >= 4 for count in self.counts)

    def is_full_house(self):
        self.get_counts()
        return 3 in self.counts and 2 in self.counts

    def is_small_straight(self):
        unique = sorted(set(self.dice))
        straights = [[1,2,3,4], [2,3,4,5], [3,4,5,6]]
        return any(all(num in unique for num in straight) for straight in straights)

    def is_large_straight(self):
        unique = sorted(set(self.dice))
        return unique == [1,2,3,4,5] or unique == [2,3,4,5,6]
    
    def is_game_end(self):
        return all(self.available[i] == 0 for i in range(13))
            
if __name__ == "__main__":
    y = yahtzee()
    