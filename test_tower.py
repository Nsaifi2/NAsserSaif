import random
import unittest
from tower import Tower, TOP_FLOOR, TARGETS, automate


class TowerTests(unittest.TestCase):
    def test_no_rare_collectibles_below_top(self):
        for floor in range(1, TOP_FLOOR):
            game = Tower(floor=floor)
            game.act('collect', random.Random(0))
            self.assertEqual(game.carried, 'Common')

    def test_pickup_is_not_banked(self):
        game = Tower(jump_power=5, floor=5, top_reached=True)
        game.act('collect', random.Random(0))
        name = game.carried
        self.assertIn(name, TARGETS)
        self.assertEqual(game.collection[name], 0)
        game.act('return', random.Random(0))
        self.assertEqual(game.collection[name], 1)
        self.assertGreater(game.cash, 0)

    def test_upgrade_spends_cash(self):
        game = Tower(cash=20)
        game.act('upgrade', random.Random(0))
        self.assertEqual((game.jump_power, game.cash), (2, 0))
        game.act('upgrade', random.Random(0))
        self.assertEqual(game.jump_power, 2)

    def test_obstacle_prevents_top_reach(self):
        game = Tower(jump_power=5)
        game.act('jump', random.Random(31))
        self.assertEqual(game.floor, 0)
        self.assertFalse(game.top_reached)
        self.assertEqual(game.obstacles, 1)

    def test_level_and_rebirth(self):
        game = Tower(cash=1000, jump_power=5, top_reached=True,
                     collection={'Common': 1, 'Ascended': 1, 'Forbidden': 1})
        game.act('level Ascended', random.Random(0))
        self.assertEqual(game.levels['Ascended'], 2)
        self.assertEqual(game.cash, 950)
        game.act('rebirth', random.Random(0))
        self.assertEqual((game.jump_power, game.cash, game.rebirths), (1, 0, 1))
        self.assertFalse(game.complete)
        self.assertEqual(game.collection['Ascended'], 1)
        game.carried = 'Ascended'
        game.act('return', random.Random(0))
        self.assertEqual(game.cash, 800)

    def test_goal_across_seeds_and_rare_gate(self):
        for seed in range(200):
            game, trace = automate(seed)
            self.assertTrue(game.complete, f'seed {seed}')
            for entry in trace:
                if entry['action'] == 'collect' and entry['carried'] in TARGETS:
                    self.assertEqual(entry['floor'], TOP_FLOOR)
                    self.assertEqual(entry['jump_power'], TOP_FLOOR)

    def test_turn_limit_does_not_claim_success(self):
        game, trace = automate(max_turns=1)
        self.assertFalse(game.complete)
        self.assertEqual(len(trace), 1)


if __name__ == '__main__':
    unittest.main()
