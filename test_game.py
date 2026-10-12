import unittest
from game import Game, MAX_STEPS, evaluate, train


class GameTests(unittest.TestCase):
    def test_boundary(self):
        game = Game()
        game.step(0)
        self.assertEqual((game.x, game.y), (0, 0))

    def test_jump_collects_brainrot(self):
        game = Game()
        for action in (3, 1, 3):
            game.step(action)
        self.assertEqual((game.x, game.y), (3, 2))
        self.assertEqual(game.carried, 0)
        self.assertEqual(game.delivered, 0)

    def test_fall_loses_carry_without_delivery(self):
        game = Game()
        game.x, game.y, game.carried = 5, 4, 1
        self.assertEqual(game.step(4), -12)
        self.assertEqual((game.x, game.y), (0, 0))
        self.assertEqual(game.carried, -1)
        self.assertEqual(game.delivered, 0)
        self.assertEqual(game.falls, 1)

    def test_delivery_and_no_duplicate_pickup(self):
        game = Game()
        game.x, game.carried = 1, 0
        self.assertEqual(game.step(0), 30)
        self.assertEqual(game.delivered, 1)
        self.assertEqual(game.carried, -1)
        game.x, game.y = 3, 2
        game.step(1)
        game.step(0)
        self.assertEqual(game.carried, -1)

    def test_one_carry_slot(self):
        game = Game()
        game.x, game.y, game.carried = 3, 4, 0
        game.step(1)
        self.assertEqual(game.carried, 0)

    def test_win_requires_all_deliveries(self):
        game = Game()
        game.x, game.carried, game.delivered = 1, 2, 3
        self.assertEqual(game.step(0), 100)
        self.assertTrue(game.won)
        self.assertTrue(game.done)
        with self.assertRaises(ValueError):
            game.step(0)

    def test_timeout(self):
        game = Game()
        for _ in range(MAX_STEPS):
            game.step(0)
        self.assertTrue(game.done)
        self.assertFalse(game.won)

    def test_learning_beats_random(self):
        q = train(20000, 42)
        trained = evaluate(q, 200, 123)
        baseline = evaluate({}, 200, 123, random_bot=True)
        self.assertGreaterEqual(trained['win_rate'], 0.95)
        self.assertGreater(trained['win_rate'], baseline['win_rate'] + 0.5)
        self.assertEqual(trained['mean_deliveries'], 3)
        self.assertEqual(trained['mean_falls'], 0)


if __name__ == '__main__':
    unittest.main()
