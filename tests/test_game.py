import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import game


class MoonbladeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.game = game.Game()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_every_character_has_art(self):
        expected = {"hero", "guard", "archer", "monk", "captain"}
        expected.update(game.ENEMY_DATA)
        self.assertTrue(expected.issubset(game.CHARACTER_SPRITES))

    def test_campaign_waves_have_valid_enemies(self):
        for wave in range(1, 16):
            battle = game.Battle(self.game, wave)
            self.assertTrue(battle.spawn_queue)
            self.assertTrue(all(kind in game.ENEMY_DATA for kind in battle.spawn_queue))

    def test_boss_appears_every_fifth_wave(self):
        for wave in (5, 10, 15, 20):
            battle = game.Battle(self.game, wave, wave > 15)
            self.assertIn("boss", battle.spawn_queue)

    def test_wave_conditions_rotate(self):
        names = [game.Battle(self.game, wave).modifier for wave in range(1, 5)]
        self.assertEqual(names, ["Moon Blessing", "Blood Moon", "Swift Shadows", "Fortified Gate"])

    def test_enemy_scaling_changes_health_and_damage(self):
        normal = game.Fighter("walker", 1000, "enemy", 1)
        stronger = game.Fighter("walker", 1000, "enemy", 2)
        self.assertEqual(stronger.max_hp, normal.max_hp * 2)
        self.assertEqual(stronger.damage, normal.damage * 2)


if __name__ == "__main__":
    unittest.main()
