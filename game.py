"""A tiny platform-climbing brainrot game and tabular Q-learning bot (standard library)."""
import argparse
import json
from pathlib import Path
import random
import time

WIDTH = 6
HEIGHT = 6
PLATFORMS = {(x, 0) for x in range(WIDTH)} | {
    (1, 1), (2, 1), (3, 2), (4, 2), (2, 3), (3, 3),
    (4, 4), (5, 4), (3, 5), (4, 5),
}
BRAINROTS = ((3, 2), (4, 4), (3, 5))
BASE = (0, 0)
MOVES = ((-1, 0), (1, 0), (-1, 1), (1, 1), (0, -1))
ACTION_NAMES = ('left', 'right', 'jump left', 'jump right', 'drop')
MODEL_VERSION = 'brainrot-platforms-v1'
MAX_STEPS = 160


class Game:
    """Discrete jumps with gravity; carry one collectible back to base at a time."""
    def __init__(self):
        self.x = self.y = self.delivered = self.steps = self.falls = 0
        self.carried = -1
        self.done = self.won = False
        self.event = 'Climb and bring all three brainrots home.'

    @property
    def state(self):
        return f'{self.x},{self.y},{self.delivered},{self.carried}'

    def step(self, action):
        if self.done:
            raise ValueError('Game already ended')
        if action not in range(len(MOVES)):
            raise ValueError('Invalid action')
        dx, dy = MOVES[action]
        old_y = self.y
        x = max(0, min(WIDTH - 1, self.x + dx))
        y = min(HEIGHT - 1, self.y + dy)
        reward = -1
        self.event = ACTION_NAMES[action]
        if (x, y) not in PLATFORMS:
            # Land on the highest platform below the attempted destination.
            y = max((py for px, py in PLATFORMS if px == x and py < y), default=0)
        if old_y - y > 1:
            self.x, self.y = BASE
            self.carried = -1
            self.falls += 1
            reward = -12
            self.event = 'Fell! Returned to base; carried brainrot returned to its platform.'
        else:
            self.x, self.y = x, y
        self.steps += 1
        pos = (self.x, self.y)
        if pos == BASE and self.carried >= 0:
            self.delivered |= 1 << self.carried
            self.carried = -1
            reward = 30
            self.event = 'Brainrot delivered!'
        if pos in BRAINROTS and self.carried == -1:
            index = BRAINROTS.index(pos)
            if not self.delivered & (1 << index):
                self.carried = index
                self.event = f'Picked up brainrot {index + 1}; return to base.'
        if self.delivered == 7:
            reward, self.done, self.won = 100, True, True
        if self.steps >= MAX_STEPS:
            self.done = True
        return reward

    def render(self):
        rows = []
        for y in reversed(range(HEIGHT)):
            row = []
            for x in range(WIDTH):
                pos = (x, y)
                tile = '=' if pos in PLATFORMS else ' '
                if pos == BASE:
                    tile = 'B'
                elif pos in BRAINROTS:
                    index = BRAINROTS.index(pos)
                    if not self.delivered & (1 << index) and self.carried != index:
                        tile = str(index + 1)
                if pos == (self.x, self.y):
                    tile = '@'
                row.append(tile)
            rows.append(f'{y} | ' + ' '.join(row))
        carry = str(self.carried + 1) if self.carried >= 0 else 'none'
        status = (f'Steps: {self.steps}/{MAX_STEPS}  Delivered: '
                  f'{self.delivered.bit_count()}/3  Carrying: {carry}  Falls: {self.falls}')
        return '\n'.join(rows) + '\n' + status + '\n' + self.event


def choose(q, state, rng, epsilon=0):
    values = q.get(state, [0.0] * len(MOVES))
    if rng.random() < epsilon:
        return rng.randrange(len(MOVES))
    best = max(values)
    return rng.choice([i for i, value in enumerate(values) if value == best])


def train(episodes, seed):
    rng, q = random.Random(seed), {}
    for episode in range(episodes):
        game = Game()
        epsilon = max(0.05, 1 - episode / (episodes * 0.8))
        while not game.done:
            state = game.state
            action = choose(q, state, rng, epsilon)
            reward = game.step(action)
            values = q.setdefault(state, [0.0] * len(MOVES))
            target = reward
            if not game.done:
                target += 0.95 * max(q.get(game.state, [0.0] * len(MOVES)))
            values[action] += 0.2 * (target - values[action])
    return q


def evaluate(q, episodes, seed, random_bot=False):
    rng, wins, steps = random.Random(seed), 0, 0
    deliveries = falls = 0
    for _ in range(episodes):
        game = Game()
        while not game.done:
            game.step(choose(q, game.state, rng, 1 if random_bot else 0))
        wins += game.won
        steps += game.steps
        deliveries += game.delivered.bit_count()
        falls += game.falls
    return {'episodes': episodes, 'wins': wins,
            'win_rate': wins / episodes, 'mean_steps': steps / episodes,
            'mean_deliveries': deliveries / episodes, 'mean_falls': falls / episodes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['train', 'evaluate', 'watch', 'play'])
    parser.add_argument('--model', type=Path, default=Path('artifacts/brainrot-bot.json'))
    parser.add_argument('--episodes', type=int)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--delay', type=float, default=0.15)
    args = parser.parse_args()
    if args.episodes is not None and args.episodes < 1:
        parser.error('--episodes must be positive')
    if args.delay < 0:
        parser.error('--delay must be nonnegative')
    if args.command == 'train':
        q = train(args.episodes or 20000, args.seed)
        args.model.parent.mkdir(parents=True, exist_ok=True)
        args.model.write_text(json.dumps({'version': MODEL_VERSION, 'q': q}))
        print(f'Saved bot to {args.model}')
        print(json.dumps(evaluate(q, 200, args.seed + 1), indent=2))
        return
    q = {}
    if args.command != 'play':
        if not args.model.exists():
            parser.error('Model missing. Run: python3 game.py train')
        model = json.loads(args.model.read_text())
        if model.get('version') != MODEL_VERSION:
            parser.error('Model is incompatible; retrain with python3 game.py train')
        q = model['q']
    if args.command == 'evaluate':
        count = args.episodes or 200
        print(json.dumps({'trained': evaluate(q, count, args.seed),
                          'random': evaluate({}, count, args.seed, True)}, indent=2))
        return
    game, rng = Game(), random.Random(args.seed)
    print('@ player  = platform  1/2/3 brainrots  B base')
    print(game.render())
    while not game.done:
        if args.command == 'play':
            try:
                move = input('a/d move, j/l jump left/right, s drop, q quit: ').strip().lower()
            except (EOFError, KeyboardInterrupt):
                print('\nStopped.')
                return
            if move == 'q':
                return
            if move not in ('a', 'd', 'j', 'l', 's'):
                continue
            action = ('a', 'd', 'j', 'l', 's').index(move)
        else:
            action = choose(q, game.state, rng)
            time.sleep(args.delay)
        game.step(action)
        print('\n' + game.render())
    print('Victory!' if game.won else 'Game over.')


if __name__ == '__main__':
    main()
