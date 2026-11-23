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

    def test_menu_selection_wraps_in_both_directions(self):
        self.assertEqual(game.wrapped_index(7, 1, 8), 0)
        self.assertEqual(game.wrapped_index(0, -1, 8), 7)

    def test_wave_grid_navigation_stays_in_unlocked_range(self):
        self.assertEqual(game.grid_index(4, 1, 0, 5, 8), 5)
        self.assertEqual(game.grid_index(7, 0, 1, 5, 8), 7)
        self.assertEqual(game.grid_index(1, 0, -1, 5, 8), 0)

    def test_controller_stick_deadzone_and_response_curve(self):
        self.assertEqual(game.stick_value(0.0), 0.0)
        self.assertEqual(game.stick_value(0.19), 0.0)
        self.assertLess(game.stick_value(0.5), 0.2)
        self.assertAlmostEqual(game.stick_value(1.0), 1.0)
        self.assertAlmostEqual(game.stick_value(-1.0), -1.0)

    def test_frame_delta_is_clamped_after_focus_loss(self):
        self.assertEqual(game.frame_delta(-10), 0.0)
        self.assertAlmostEqual(game.frame_delta(16), 0.016)
        self.assertEqual(game.frame_delta(5000), 0.035)

    def test_wave_summary_counts_enemy_types(self):
        summary = game.wave_summary(["walker", "runner", "walker", "boss"])
        self.assertEqual(summary, {"walker": 2, "runner": 1, "boss": 1})

    def test_restart_from_pause_keeps_wave_and_mode(self):
        self.game.battle = game.Battle(self.game, 18, endless=True)
        self.game.state = "pause"
        previous = self.game.battle
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
        self.assertEqual(self.game.state, "battle")
        self.assertIsNot(self.game.battle, previous)
        self.assertEqual(self.game.battle.wave, 18)
        self.assertIs(self.game.battle.endless, True)

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
        self.assertEqual(loaded["save_version"], game.SAVE_VERSION)

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
        self.assertEqual(loaded["save_version"], game.SAVE_VERSION)

    def test_older_save_is_upgraded_without_losing_progress(self):
        loaded = game.validated_save({"unlocked": 4, "coins": 330, "stats": {"kills": 12}})
        self.assertEqual(loaded["save_version"], game.SAVE_VERSION)
        self.assertEqual(loaded["unlocked"], 4)
        self.assertEqual(loaded["coins"], 330)
        self.assertEqual(loaded["stats"]["kills"], 12)


if __name__ == "__main__":
    unittest.main()
