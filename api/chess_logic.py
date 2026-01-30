CHESS_REWARDS = {
    'BOT': {
        'easy': {'WIN': 45, 'DRAW': 10, 'LOSE': 0},
        'medium': {'WIN': 75, 'DRAW': 20, 'LOSE': 0},
        'hard': {'WIN': 100, 'DRAW': 30, 'LOSE': 0},
    },
    'STUDENT': {
        'WIN': 50,
        'DRAW': 20,
        'LOSE': 0
    }
}


def calculate_reward(opponent_type, bot_level, result):
    if opponent_type == 'BOT':
        return CHESS_REWARDS['BOT'][bot_level][result]
    return CHESS_REWARDS['STUDENT'][result]
