import os
import json
import tempfile
import unittest
from unittest import mock

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

    def test_save_round_trip_preserves_progress(self):
        progress = game.default_save()
        progress.update({"unlocked": 8, "coins": 912, "difficulty": "nightmare"})
        progress["upgrades"]["blade"] = 4
        with tempfile.TemporaryDirectory() as folder:
            save_file = os.path.join(folder, "save.json")
            with mock.patch.object(game, "SAVE_DIR", folder), mock.patch.object(game, "SAVE_FILE", save_file):
                game.save_data(progress)
                loaded = game.load_save()
        self.assertEqual(loaded["unlocked"], 8)
        self.assertEqual(loaded["coins"], 912)
        self.assertEqual(loaded["difficulty"], "nightmare")
        self.assertEqual(loaded["upgrades"]["blade"], 4)

    def test_corrupt_primary_save_recovers_backup(self):
        backup = game.default_save()
        backup["coins"] = 777
        with tempfile.TemporaryDirectory() as folder:
            save_file = os.path.join(folder, "save.json")
            with open(save_file, "w", encoding="utf-8") as handle:
                handle.write("{unfinished")
            with open(save_file + ".bak", "w", encoding="utf-8") as handle:
                json.dump(backup, handle)
            with mock.patch.object(game, "SAVE_FILE", save_file):
                loaded = game.load_save()
        self.assertEqual(loaded["coins"], 777)

    def test_invalid_save_values_are_safely_normalized(self):
        loaded = game.validated_save({
            "unlocked": 99,
            "coins": -40,
            "difficulty": "impossible",
            "sound": "yes",
            "sound_volume": 99,
            "reduced_motion": True,
            "upgrades": {"blade": 999},
            "best": {"1": 8, "99": 3},
            "achievements": ["first_blood", "first_blood", "unknown"],
        })
        self.assertEqual(loaded["unlocked"], 15)
        self.assertEqual(loaded["coins"], 0)
        self.assertEqual(loaded["difficulty"], "normal")
        self.assertIs(loaded["sound"], True)
        self.assertEqual(loaded["sound_volume"], 10)
        self.assertIs(loaded["reduced_motion"], True)
        self.assertEqual(loaded["upgrades"]["blade"], 20)
        self.assertEqual(loaded["best"], {"1": 3})
        self.assertEqual(loaded["achievements"], ["first_blood"])


if __name__ == "__main__":
    unittest.main()
