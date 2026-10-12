"""Local progression simulation inspired by Fortnite island 7875-7934-3852."""
import argparse
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import random
import time

# Illustrative values, not measured Fortnite island data.
TOP_FLOOR = 5
UPGRADE_COSTS = {1: 20, 2: 40, 3: 60, 4: 80}
TARGETS = ('Ascended', 'Forbidden')
VALUES = {'Common': 20, 'Ascended': 200, 'Forbidden': 400}


@dataclass
class Tower:
    cash: int = 0
    jump_power: int = 1
    floor: int = 0
    carried: str | None = None
    collection: dict = field(default_factory=lambda: dict.fromkeys(VALUES, 0))
    levels: dict = field(default_factory=lambda: dict.fromkeys(VALUES, 1))
    rebirths: int = 0
    top_reached: bool = False
    turns: int = 0
    obstacles: int = 0
    event: str = 'Upgrade jump power, reach the top, and bank both target rarities.'

    @property
    def complete(self):
        return self.top_reached and all(self.collection[name] > 0 for name in TARGETS)

    def act(self, action, rng):
        self.turns += 1
        if action == 'jump':
            if self.carried:
                self.event = 'Return the carried brainrot to base first.'
            elif rng.random() < 0.1:
                self.floor = 0
                self.obstacles += 1
                self.event = 'Obstacle hit: back at base. Try the jump again.'
            else:
                self.floor = self.jump_power
                self.top_reached |= self.floor == TOP_FLOOR
                self.event = f'Jumped to floor {self.floor}/{TOP_FLOOR}.'
        elif action == 'collect':
            if self.carried:
                self.event = 'You can carry one brainrot at a time.'
            elif self.floor == 0:
                self.event = 'Jump to a floor before collecting.'
            elif self.floor == TOP_FLOOR:
                self.carried = rng.choice(TARGETS)
                self.event = f'Collected {self.carried} on the top floor.'
            else:
                self.carried = 'Common'
                self.event = 'Collected Common to fund jump upgrades.'
        elif action == 'return':
            self.floor = 0
            if self.carried:
                name = self.carried
                self.collection[name] += 1
                earned = VALUES[name] * self.levels[name] * (1 + self.rebirths)
                self.cash += earned
                self.carried = None
                self.event = f'Banked {name}: +{earned} cash.'
            else:
                self.event = 'Returned to base.'
        elif action == 'upgrade':
            cost = UPGRADE_COSTS.get(self.jump_power)
            if self.floor != 0 or self.carried:
                self.event = 'Return to base before upgrading.'
            elif cost is None:
                self.event = 'Jump power already at maximum.'
            elif self.cash < cost:
                self.event = f'Jump upgrade needs {cost} cash.'
            else:
                self.cash -= cost
                self.jump_power += 1
                self.event = f'Jump power upgraded to {self.jump_power}.'
        elif action.startswith('level '):
            name = action[6:]
            if name not in VALUES:
                self.event = 'Unknown brainrot rarity.'
            elif self.floor != 0 or self.carried:
                self.event = 'Return to base before leveling.'
            elif not self.collection[name]:
                self.event = 'Collect that rarity before leveling it.'
            elif self.cash < 50 * self.levels[name]:
                self.event = 'Not enough cash to level this rarity.'
            else:
                self.cash -= 50 * self.levels[name]
                self.levels[name] += 1
                self.event = f'{name} upgraded to level {self.levels[name]}.'
        elif action == 'rebirth':
            if self.floor != 0 or self.carried or not self.complete or self.cash < 500:
                self.event = 'Rebirth needs base, both target rarities, and 500 cash.'
            else:
                self.cash = 0
                self.jump_power = 1
                self.floor = 0
                self.top_reached = False
                self.rebirths += 1
                self.event = 'Rebirth! Jump reset; collection retained; cash multiplier increased.'
        else:
            raise ValueError(f'Unknown action: {action}')
        return self.event

    def render(self):
        return (f'Floor {self.floor}/{TOP_FLOOR} | Jump {self.jump_power}/{TOP_FLOOR} | '
                f'Cash {self.cash} | Carrying {self.carried or "nothing"}\n'
                f'Collection: {self.collection}\n{self.event}')


def next_action(game):
    """Goal-directed policy: spend on jumps before pursuing top-floor rarities."""
    if game.carried:
        return 'return'
    cost = UPGRADE_COSTS.get(game.jump_power)
    if cost is not None and game.cash >= cost:
        return 'return' if game.floor else 'upgrade'
    return 'collect' if game.floor else 'jump'


def automate(seed=42, max_turns=500, callback=None):
    game, rng, trace = Tower(), random.Random(seed), []
    while not game.complete and game.turns < max_turns:
        action = next_action(game)
        game.act(action, rng)
        trace.append({'turn': game.turns, 'action': action, 'floor': game.floor,
                      'jump_power': game.jump_power, 'carried': game.carried,
                      'event': game.event})
        if callback:
            callback(game)
    return game, trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('auto', 'play', 'evaluate'))
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--max-turns', type=int, default=500)
    parser.add_argument('--episodes', type=int, default=200)
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--delay', type=float, default=0.1)
    parser.add_argument('--output', type=Path, default=Path('artifacts/tower-run.json'))
    args = parser.parse_args()
    if args.max_turns < 1 or args.episodes < 1 or args.delay < 0:
        parser.error('Turns and episodes must be positive; delay must be nonnegative.')
    if args.command == 'evaluate':
        results = [automate(args.seed + i, args.max_turns)[0] for i in range(args.episodes)]
        wins = sum(g.complete for g in results)
        print(json.dumps({'episodes': len(results), 'completed': wins,
                          'mean_turns': sum(g.turns for g in results) / len(results),
                          'objective': 'Bank Ascended and Forbidden after reaching top floor'}, indent=2))
        return 0 if wins == len(results) else 1
    if args.command == 'play':
        game, rng = Tower(), random.Random(args.seed)
        print('Commands: jump, collect, return, upgrade, level Common/Ascended/Forbidden, rebirth, quit')
        print(game.render())
        while True:
            try:
                action = input('> ').strip()
            except (EOFError, KeyboardInterrupt):
                return 0
            if action == 'quit':
                return 0
            try:
                game.act(action, rng)
            except ValueError as e:
                print(e)
                continue
            print(game.render())
            if game.complete:
                print('Target achieved: both rare brainrots banked after reaching the top.')
    def show(game):
        print(game.render() + '\n')
        time.sleep(args.delay)
    game, trace = automate(args.seed, args.max_turns, show if args.watch else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'rules': 'illustrative-v1', 'seed': args.seed,
                                     'state': asdict(game), 'trace': trace}, indent=2))
    print(game.render())
    print('Target achieved!' if game.complete else 'Turn limit reached; target unfinished.')
    print(f'Run record: {args.output}')
    return 0 if game.complete else 1


if __name__ == '__main__':
    raise SystemExit(main())
