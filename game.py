import json
import math
import os
import random
import sys
from array import array

import pygame


WIDTH, HEIGHT = 1280, 720
GROUND_Y = 555
FPS = 60
TITLE = "Moonblade: Last Lantern"
CHARACTER_SPRITES = {}
SAVE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "MoonbladeDefense")
SAVE_FILE = os.path.join(SAVE_DIR, "save.json")
DIFFICULTIES = {
    "story": {"label": "STORY", "enemy": .78, "reward": .8},
    "normal": {"label": "NORMAL", "enemy": 1.0, "reward": 1.0},
    "nightmare": {"label": "NIGHTMARE", "enemy": 1.32, "reward": 1.35},
}
ACHIEVEMENTS = {
    "first_blood": ("First Blood", "Defeat your first enemy", 25),
    "horde_breaker": ("Horde Breaker", "Defeat 100 enemies", 150),
    "banner_caller": ("Banner Caller", "Summon 50 allies", 125),
    "village_veteran": ("Village Veteran", "Win 15 battles", 250),
    "deep_night": ("Deep Night", "Clear Endless Night 5", 225),
    "master_smith": ("Master Smith", "Buy 15 forge levels", 200),
}


def resource_path(name):
    root = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, name)


def clamp(value, low, high):
    return max(low, min(high, value))


def load_save():
    default = {"unlocked": 1, "coins": 250, "difficulty": "normal", "endless_best": 0,
               "upgrades": {"vitality": 0, "blade": 0, "bow": 0, "gate": 0, "spirit": 0}, "best": {},
               "stats": {"kills": 0, "summons": 0, "wins": 0, "best_combo": 0}, "achievements": [],
               "sound": True}
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        default.update({k: data[k] for k in ("unlocked", "coins", "best", "difficulty", "endless_best", "achievements", "sound") if k in data})
        default["upgrades"].update(data.get("upgrades", {}))
        default["stats"].update(data.get("stats", {}))
    except (OSError, ValueError, TypeError):
        pass
    return default


def save_data(data):
    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


class SoundBank:
    def __init__(self):
        self.ok = pygame.mixer.get_init() is not None
        self.enabled = True
        self.cache = {}

    def tone(self, name, freq, duration, volume=.18, wave="sine"):
        if not self.ok:
            return None
        if name in self.cache:
            return self.cache[name]
        rate = 22050
        samples = array("h")
        count = int(rate * duration)
        for i in range(count):
            t = i / rate
            env = max(0.0, 1.0 - i / count)
            if wave == "noise":
                val = random.uniform(-1, 1)
            elif wave == "square":
                val = 1 if math.sin(2 * math.pi * freq * t) >= 0 else -1
            else:
                val = math.sin(2 * math.pi * freq * t)
            samples.append(int(32767 * volume * env * val))
        snd = pygame.mixer.Sound(buffer=samples)
        self.cache[name] = snd
        return snd

    def play(self, name):
        if not self.enabled:
            return
        specs = {
            "slash": (180, .12, .14, "noise"), "bow": (620, .09, .10, "square"),
            "hit": (90, .11, .12, "noise"), "summon": (440, .22, .12, "sine"),
            "coin": (880, .18, .10, "sine"), "thunder": (55, .45, .20, "noise"),
            "heal": (660, .35, .10, "sine"), "lose": (110, .55, .12, "square"),
            "win": (760, .4, .12, "sine"), "click": (520, .06, .08, "sine"),
        }
        if name in specs:
            snd = self.tone(name, *specs[name])
            if snd:
                snd.play()


class Particle:
    def __init__(self, x, y, color, kind="spark"):
        self.x, self.y = x, y
        self.vx = random.uniform(-120, 120)
        self.vy = random.uniform(-200, -35)
        self.life = random.uniform(.25, .65)
        self.max_life = self.life
        self.color = color
        self.kind = kind

    def update(self, dt):
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 430 * dt

    def draw(self, surf):
        if self.life <= 0:
            return
        a = int(255 * self.life / self.max_life)
        size = 3 if self.kind == "spark" else 7
        layer = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(layer, (*self.color, a), (size, size), max(1, int(size * self.life / self.max_life)))
        surf.blit(layer, (self.x - size, self.y - size))


class Projectile:
    def __init__(self, x, y, vx, damage, side, color=(240, 210, 120), magic=False):
        self.x, self.y, self.vx = x, y, vx
        self.damage, self.side, self.color, self.magic = damage, side, color, magic
        self.life = 3

    def update(self, dt):
        self.x += self.vx * dt
        self.life -= dt

    def draw(self, surf):
        if self.magic:
            pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), 7)
            pygame.draw.circle(surf, (255, 255, 230), (int(self.x), int(self.y)), 3)
        else:
            pygame.draw.line(surf, (80, 45, 25), (self.x - 13 * (1 if self.vx > 0 else -1), self.y), (self.x, self.y), 3)
            pygame.draw.polygon(surf, self.color, [(self.x, self.y), (self.x - 7 * (1 if self.vx > 0 else -1), self.y - 4), (self.x - 7 * (1 if self.vx > 0 else -1), self.y + 4)])


UNIT_DATA = {
    "guard": dict(name="Ashigaru", cost=30, hp=150, dmg=18, speed=58, reach=42, rate=.85, ranged=False, color=(55, 150, 185)),
    "archer": dict(name="Moon Archer", cost=45, hp=82, dmg=20, speed=46, reach=235, rate=1.25, ranged=True, color=(165, 100, 205)),
    "monk": dict(name="Lantern Monk", cost=65, hp=105, dmg=8, speed=42, reach=150, rate=1.7, ranged=True, heal=True, color=(225, 175, 75)),
    "captain": dict(name="Gate Captain", cost=90, hp=340, dmg=32, speed=38, reach=48, rate=1.15, ranged=False, color=(195, 68, 74)),
}

ENEMY_DATA = {
    "walker": dict(name="Hollow", hp=78, dmg=12, speed=39, reach=37, rate=1.05, reward=8, color=(95, 155, 112)),
    "runner": dict(name="Wraith", hp=52, dmg=10, speed=75, reach=34, rate=.72, reward=10, color=(85, 195, 190)),
    "brute": dict(name="Ogre", hp=260, dmg=28, speed=25, reach=48, rate=1.45, reward=22, color=(155, 80, 105)),
    "shaman": dict(name="Hexer", hp=95, dmg=16, speed=30, reach=220, rate=1.65, reward=17, ranged=True, color=(128, 85, 170)),
    "armored": dict(name="Iron Revenant", hp=430, dmg=24, speed=18, reach=44, rate=1.25, reward=34, color=(90, 104, 122)),
    "boss": dict(name="Dread Daimyo", hp=1150, dmg=42, speed=21, reach=58, rate=1.2, reward=125, color=(190, 55, 70), boss=True),
}


class Fighter:
    def __init__(self, kind, x, side, scale=1.0):
        data = UNIT_DATA[kind] if side == "ally" else ENEMY_DATA[kind]
        self.kind, self.side = kind, side
        self.name = data["name"]
        self.x, self.y = float(x), float(GROUND_Y)
        self.max_hp = data["hp"] * scale
        self.hp = self.max_hp
        self.damage = data["dmg"] * scale
        self.speed = data["speed"]
        self.reach = data["reach"]
        self.rate = data["rate"]
        self.cooldown = random.uniform(0, .4)
        self.ranged = data.get("ranged", False)
        self.heal = data.get("heal", False)
        self.reward = data.get("reward", 0)
        self.color = data["color"]
        self.boss = data.get("boss", False)
        self.flash = 0
        self.walk = random.random() * 6

    @property
    def alive(self):
        return self.hp > 0

    def take_damage(self, amount, battle):
        self.hp -= amount
        self.flash = .12
        for _ in range(4):
            battle.particles.append(Particle(self.x, self.y - 55, (245, 80, 80)))

    def update(self, dt, battle):
        self.cooldown -= dt
        self.flash = max(0, self.flash - dt)
        self.walk += dt * 7
        targets = battle.enemies if self.side == "ally" else [battle.hero] + battle.allies
        targets = [t for t in targets if t.alive]
        direction = 1 if self.side == "ally" else -1
        if self.side == "ally" and self.heal:
            wounded = [a for a in [battle.hero] + battle.allies if a.alive and a.hp < a.max_hp * .88 and abs(a.x - self.x) < self.reach]
            if wounded and self.cooldown <= 0:
                target = min(wounded, key=lambda a: a.hp / a.max_hp)
                target.hp = min(target.max_hp, target.hp + 24)
                self.cooldown = self.rate
                battle.sounds.play("heal")
                for _ in range(8):
                    battle.particles.append(Particle(target.x, target.y - 45, (255, 220, 90), "orb"))
                return
        target = min(targets, key=lambda t: abs(t.x - self.x), default=None)
        distance = abs(target.x - self.x) if target else 9999
        if target and distance <= self.reach:
            if self.cooldown <= 0:
                if self.ranged:
                    battle.projectiles.append(Projectile(self.x + direction * 20, self.y - 57, direction * 390, self.damage, self.side, self.color, self.kind == "shaman"))
                else:
                    target.take_damage(self.damage, battle)
                    battle.sounds.play("hit")
                self.cooldown = self.rate
        else:
            self.x += direction * self.speed * dt
        if self.side == "enemy" and self.x < 165:
            if self.cooldown <= 0:
                battle.gate_hp -= self.damage
                self.cooldown = self.rate
                battle.shake = max(battle.shake, 7)

    def draw(self, surf):
        x, y = int(self.x), int(self.y + math.sin(self.walk) * 2)
        facing = 1 if self.side == "ally" else -1
        shadow_w = 56 if not self.boss else 90
        pygame.draw.ellipse(surf, (12, 12, 20, 110), (x - shadow_w // 2, GROUND_Y - 6, shadow_w, 15))
        if self.side == "ally" and self.kind in CHARACTER_SPRITES:
            heights = {"guard": 108, "archer": 116, "monk": 112, "captain": 136}
            source = CHARACTER_SPRITES[self.kind]
            height = heights[self.kind]
            width = max(1, int(source.get_width() * height / source.get_height()))
            sprite = pygame.transform.smoothscale(source, (width, height))
            if self.flash:
                glow = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
                glow.fill((100, 100, 100, 0))
                sprite.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            surf.blit(sprite, sprite.get_rect(midbottom=(x, y + 5)))
            bar_w = 48 if self.kind != "captain" else 62
            bar_y = y - height - 8
            pygame.draw.rect(surf, (30, 24, 33), (x - bar_w // 2, bar_y, bar_w, 7), border_radius=3)
            pygame.draw.rect(surf, (70, 210, 115), (x - bar_w // 2, bar_y,
                             int(bar_w * max(0, self.hp / self.max_hp)), 7), border_radius=3)
            return
        if self.side == "enemy" and self.kind in CHARACTER_SPRITES:
            heights = {"walker": 112, "runner": 120, "brute": 142, "shaman": 132,
                       "armored": 152, "boss": 205}
            source = CHARACTER_SPRITES[self.kind]
            height = heights[self.kind]
            width = max(1, int(source.get_width() * height / source.get_height()))
            sprite = pygame.transform.smoothscale(source, (width, height))
            if self.kind == "armored":
                tint = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
                tint.fill((35, 45, 65, 0))
                sprite.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            elif self.boss:
                tint = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
                tint.fill((65, 8, 12, 0))
                sprite.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            if self.flash:
                glow = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
                glow.fill((100, 100, 100, 0))
                sprite.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            surf.blit(sprite, sprite.get_rect(midbottom=(x, y + 5)))
            bar_w = 50 if not self.boss else 94
            bar_y = y - height - 8
            pygame.draw.rect(surf, (30, 24, 33), (x - bar_w // 2, bar_y, bar_w, 7), border_radius=3)
            pygame.draw.rect(surf, (225, 65, 75), (x - bar_w // 2, bar_y,
                             int(bar_w * max(0, self.hp / self.max_hp)), 7), border_radius=3)
            return
        scale = 1.45 if self.boss else (1.18 if self.kind == "brute" else 1)
        body = (255, 245, 230) if self.flash else self.color
        pygame.draw.rect(surf, body, (x - 16 * scale, y - 66 * scale, 32 * scale, 48 * scale), border_radius=8)
        pygame.draw.circle(surf, (202, 174, 140), (x, int(y - 75 * scale)), int(15 * scale))
        if self.side == "enemy":
            pygame.draw.circle(surf, (105, 170, 120), (x, int(y - 75 * scale)), int(15 * scale))
            pygame.draw.circle(surf, (245, 70, 80), (x + facing * 6, int(y - 78 * scale)), 2)
        pygame.draw.line(surf, (45, 33, 38), (x - 8, y - 18), (x - 11, y), max(4, int(6 * scale)))
        pygame.draw.line(surf, (45, 33, 38), (x + 8, y - 18), (x + 11, y), max(4, int(6 * scale)))
        if self.ranged:
            pygame.draw.arc(surf, (90, 55, 28), (x + facing * 4 - 11, y - 62, 22, 44), -math.pi / 2, math.pi / 2, 3)
        else:
            pygame.draw.line(surf, (225, 225, 235), (x + facing * 8, y - 50), (x + facing * 35, y - 78), 4)
        if self.kind in ("guard", "captain", "armored", "boss"):
            pygame.draw.polygon(surf, (35, 45, 64), [(x - 19, y - 78), (x, y - 103), (x + 19, y - 78)])
        bar_w = 48 if not self.boss else 90
        pygame.draw.rect(surf, (30, 24, 33), (x - bar_w // 2, y - int(110 * scale), bar_w, 6), border_radius=3)
        pygame.draw.rect(surf, (70, 210, 115) if self.side == "ally" else (225, 65, 75), (x - bar_w // 2, y - int(110 * scale), int(bar_w * max(0, self.hp / self.max_hp)), 6), border_radius=3)


class Hero:
    def __init__(self, upgrades):
        self.x, self.y = 330.0, float(GROUND_Y)
        self.max_hp = 280 + upgrades["vitality"] * 55
        self.hp = self.max_hp
        self.damage = 36 + upgrades["blade"] * 9
        self.bow_damage = 24 + upgrades["bow"] * 7
        self.cooldown = 0
        self.bow_cd = 0
        self.invuln = 0
        self.alive = True
        self.anim = 0
        self.facing = 1
        self.slashing = 0

    def take_damage(self, amount, battle):
        if self.invuln > 0:
            return
        self.hp -= amount
        self.invuln = .18
        battle.shake = max(battle.shake, 5)
        for _ in range(6):
            battle.particles.append(Particle(self.x, self.y - 60, (250, 80, 80)))
        if self.hp <= 0:
            self.alive = False

    def update(self, dt, battle, keys):
        self.cooldown -= dt
        self.bow_cd -= dt
        self.invuln -= dt
        self.slashing -= dt
        move = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: move -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: move += 1
        controller = battle.game.controller
        if controller and controller.get_init():
            axis = controller.get_axis(0)
            if abs(axis) > .2:
                move = axis
        if move:
            self.facing = move
            self.x = clamp(self.x + move * 185 * dt, 210, 1120)
            self.anim += dt * 10
        enemies = [e for e in battle.enemies if e.alive and abs(e.x - self.x) < 78]
        controller_sword = controller and controller.get_init() and controller.get_numbuttons() > 0 and controller.get_button(0)
        if (keys[pygame.K_SPACE] or pygame.mouse.get_pressed()[0] or controller_sword) and self.cooldown <= 0:
            self.cooldown = .48
            self.slashing = .18
            battle.sounds.play("slash")
            for e in enemies:
                if (e.x - self.x) * self.facing > -15:
                    e.take_damage(self.damage, battle)
                    e.x += self.facing * 13
        controller_bow = controller and controller.get_init() and controller.get_numbuttons() > 2 and controller.get_button(2)
        if (keys[pygame.K_f] or controller_bow) and self.bow_cd <= 0:
            self.bow_cd = .72
            battle.projectiles.append(Projectile(self.x + self.facing * 25, self.y - 72, self.facing * 560, self.bow_damage, "ally"))
            battle.sounds.play("bow")

    def draw(self, surf):
        x, y = int(self.x), int(self.y + math.sin(self.anim) * 2)
        pygame.draw.ellipse(surf, (10, 10, 20, 120), (x - 35, GROUND_Y - 7, 70, 17))
        ghost = self.invuln > 0 and int(self.invuln * 30) % 2 == 0
        if ghost: return
        if "hero" in CHARACTER_SPRITES:
            source = CHARACTER_SPRITES["hero"]
            height = 150
            width = max(1, int(source.get_width() * height / source.get_height()))
            sprite = pygame.transform.smoothscale(source, (width, height))
            if self.facing < 0:
                sprite = pygame.transform.flip(sprite, True, False)
            if self.slashing > 0:
                sprite = pygame.transform.rotate(sprite, -4 * self.facing)
            surf.blit(sprite, sprite.get_rect(midbottom=(x + self.facing * (5 if self.slashing > 0 else 0), y + 5)))
            return
        pygame.draw.rect(surf, (38, 78, 110), (x - 23, y - 85, 46, 67), border_radius=9)
        pygame.draw.rect(surf, (160, 38, 55), (x - 25, y - 58, 50, 10), border_radius=3)
        pygame.draw.circle(surf, (214, 181, 145), (x, y - 99), 21)
        pygame.draw.polygon(surf, (22, 28, 43), [(x - 26, y - 105), (x, y - 135), (x + 26, y - 105)])
        pygame.draw.line(surf, (30, 25, 33), (x - 13, y - 18), (x - 17, y), 8)
        pygame.draw.line(surf, (30, 25, 33), (x + 13, y - 18), (x + 17, y), 8)
        angle = -1.1 * self.facing if self.slashing > 0 else -.35 * self.facing
        hand = (x + self.facing * 15, y - 66)
        tip = (hand[0] + math.cos(angle) * 68 * self.facing, hand[1] + math.sin(angle) * 68)
        pygame.draw.line(surf, (235, 240, 250), hand, tip, 6)
        pygame.draw.line(surf, (30, 20, 24), (x - self.facing * 10, y - 68), (x - self.facing * 35, y - 26), 5)


class Button:
    def __init__(self, rect, text, action=None, accent=False):
        self.rect = pygame.Rect(rect)
        self.text, self.action, self.accent = text, action, accent

    def draw(self, surf, font, mouse):
        hover = self.rect.collidepoint(mouse)
        color = (177, 52, 68) if self.accent else (36, 51, 75)
        if hover: color = tuple(min(255, c + 28) for c in color)
        pygame.draw.rect(surf, (12, 17, 30), self.rect.inflate(6, 6), border_radius=12)
        pygame.draw.rect(surf, color, self.rect, border_radius=9)
        pygame.draw.rect(surf, (232, 190, 92), self.rect, 2, border_radius=9)
        label = font.render(self.text, True, (245, 236, 215))
        surf.blit(label, label.get_rect(center=self.rect.center))


class Battle:
    def __init__(self, game, wave, endless=False):
        self.game, self.wave, self.endless = game, wave, endless
        self.modifier = ("Moon Blessing", "Blood Moon", "Swift Shadows", "Fortified Gate")[(wave - 1) % 4]
        self.difficulty = DIFFICULTIES[game.save.get("difficulty", "normal")]
        self.sounds = game.sounds
        self.hero = Hero(game.save["upgrades"])
        self.allies, self.enemies, self.projectiles, self.particles = [], [], [], []
        up = game.save["upgrades"]
        self.gate_max = 700 + up["gate"] * 130
        if self.modifier == "Fortified Gate":
            self.gate_max += 150
        self.gate_hp = self.gate_max
        self.spirit_max = 100 + up["spirit"] * 12
        self.spirit = 55
        self.spawn_queue = self.make_wave(wave)
        self.spawn_timer = 1.6
        self.elapsed = 0
        self.total = len(self.spawn_queue)
        self.killed = 0
        self.combo = 0
        self.combo_timer = 0
        self.state = "intro"
        self.banner_timer = 2.2
        self.shake = 0
        self.lightning_cd = 0
        self.rally_cd = 0
        self.summon_cooldowns = {"guard": 0, "archer": 0, "monk": 0, "captain": 0}
        self.result_timer = 0
        self.earned = 0

    def make_wave(self, wave):
        rng = random.Random(wave * 919)
        count = 7 + min(wave, 20) * 2
        options = ["walker"]
        if wave >= 2: options += ["runner"]
        if wave >= 4: options += ["brute"]
        if wave >= 6: options += ["shaman"]
        if wave >= 8: options += ["armored"]
        queue = []
        for i in range(count):
            weights = [50 if k == "walker" else 24 if k == "runner" else 14 if k == "brute" else 9 if k == "armored" else 12 for k in options]
            queue.append(rng.choices(options, weights=weights)[0])
        if wave % 5 == 0:
            queue.append("boss")
        return queue

    def summon(self, kind):
        data = UNIT_DATA[kind]
        if self.spirit >= data["cost"] and self.summon_cooldowns[kind] <= 0 and len(self.allies) < 12 and self.state == "playing":
            self.spirit -= data["cost"]
            self.allies.append(Fighter(kind, 210, "ally", 1 + self.wave * .012))
            self.summon_cooldowns[kind] = {"guard": 2.2, "archer": 3.6, "monk": 6.5, "captain": 9.5}[kind]
            self.game.add_stat("summons")
            self.sounds.play("summon")
            for _ in range(10): self.particles.append(Particle(210, GROUND_Y - 45, data["color"], "orb"))

    def lightning(self):
        if self.lightning_cd > 0 or self.state != "playing": return
        self.lightning_cd = 13
        self.sounds.play("thunder")
        self.shake = 12
        targets = sorted([e for e in self.enemies if e.alive], key=lambda e: abs(e.x - self.hero.x))[:5]
        for e in targets:
            e.take_damage(90 + self.wave * 4, self)
            for _ in range(10): self.particles.append(Particle(e.x, e.y - 70, (140, 210, 255), "orb"))

    def rally(self):
        if self.rally_cd > 0 or self.state != "playing": return
        self.rally_cd = 18
        self.sounds.play("heal")
        self.hero.hp = min(self.hero.max_hp, self.hero.hp + 80)
        for a in self.allies: a.hp = min(a.max_hp, a.hp + 55)
        for _ in range(18): self.particles.append(Particle(self.hero.x, self.hero.y - 55, (255, 210, 95), "orb"))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.state = "pause"
            elif event.key == pygame.K_1: self.summon("guard")
            elif event.key == pygame.K_2: self.summon("archer")
            elif event.key == pygame.K_3: self.summon("monk")
            elif event.key == pygame.K_4: self.summon("captain")
            elif event.key == pygame.K_q: self.lightning()
            elif event.key == pygame.K_e: self.rally()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            buttons = [(18, "guard"), (132, "archer"), (246, "monk"), (360, "captain")]
            for x, kind in buttons:
                if pygame.Rect(x, 638, 108, 66).collidepoint(mx, my): self.summon(kind)
            if pygame.Rect(484, 638, 140, 66).collidepoint(mx, my): self.lightning()
            if pygame.Rect(634, 638, 140, 66).collidepoint(mx, my): self.rally()
        if event.type == pygame.JOYBUTTONDOWN:
            actions = {4: lambda: self.summon("guard"), 5: lambda: self.summon("archer"),
                       6: lambda: self.summon("monk"), 7: lambda: self.summon("captain"),
                       3: self.lightning, 1: self.rally}
            if event.button == 9:
                self.game.state = "pause"
            elif event.button in actions:
                actions[event.button]()

    def update(self, dt):
        if self.state == "intro":
            self.banner_timer -= dt
            if self.banner_timer <= 0: self.state = "playing"
            return
        if self.state in ("won", "lost"):
            self.result_timer += dt
            return
        self.elapsed += dt
        self.combo_timer = max(0, self.combo_timer - dt)
        if self.combo_timer <= 0:
            self.combo = 0
        spirit_bonus = 2.5 if self.modifier == "Moon Blessing" else 0
        self.spirit = min(self.spirit_max, self.spirit + (7.2 + spirit_bonus + self.game.save["upgrades"]["spirit"] * .8) * dt)
        self.lightning_cd = max(0, self.lightning_cd - dt)
        self.rally_cd = max(0, self.rally_cd - dt)
        for kind in self.summon_cooldowns:
            self.summon_cooldowns[kind] = max(0, self.summon_cooldowns[kind] - dt)
        self.shake = max(0, self.shake - 18 * dt)
        self.hero.update(dt, self, pygame.key.get_pressed())
        self.spawn_timer -= dt
        if self.spawn_queue and self.spawn_timer <= 0:
            kind = self.spawn_queue.pop(0)
            scale = (1 + (self.wave - 1) * .105) * self.difficulty["enemy"]
            enemy = Fighter(kind, 1235, "enemy", scale)
            if self.modifier == "Blood Moon":
                enemy.damage *= 1.15
            elif self.modifier == "Swift Shadows":
                enemy.speed *= 1.15
            self.enemies.append(enemy)
            self.spawn_timer = max(.55, 1.95 - self.wave * .06) + random.uniform(-.2, .35)
        for u in self.allies + self.enemies: u.update(dt, self)
        for p in self.projectiles:
            p.update(dt)
            targets = self.enemies if p.side == "ally" else [self.hero] + self.allies
            for t in targets:
                if t.alive and abs(t.x - p.x) < 25 and abs((t.y - 55) - p.y) < 65:
                    t.take_damage(p.damage, self)
                    p.life = 0
                    break
        for e in list(self.enemies):
            if not e.alive:
                self.killed += 1
                self.combo = self.combo + 1 if self.combo_timer > 0 else 1
                self.combo_timer = 4
                self.game.save["stats"]["best_combo"] = max(self.combo, self.game.save["stats"].get("best_combo", 0))
                self.game.add_stat("kills")
                combo_bonus = self.combo // 5
                self.earned += int(e.reward * self.difficulty["reward"]) + combo_bonus
                self.sounds.play("coin")
                self.enemies.remove(e)
        self.allies = [a for a in self.allies if a.alive]
        self.projectiles = [p for p in self.projectiles if p.life > 0 and -50 < p.x < WIDTH + 50]
        for p in self.particles: p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        if self.gate_hp <= 0 or not self.hero.alive:
            self.state = "lost"; self.sounds.play("lose")
        elif not self.spawn_queue and not self.enemies:
            self.state = "won"; self.sounds.play("win")
            stars = 3 if self.gate_hp > self.gate_max * .7 and self.hero.hp > self.hero.max_hp * .6 else 2 if self.gate_hp > self.gate_max * .35 else 1
            bonus = int((35 + self.wave * 14 + stars * 15) * self.difficulty["reward"])
            self.earned += bonus
            self.game.save["coins"] += self.earned
            self.game.add_stat("wins")
            if self.endless:
                self.game.save["endless_best"] = max(self.game.save.get("endless_best", 0), self.wave)
            else:
                self.game.save["unlocked"] = max(self.game.save["unlocked"], min(15, self.wave + 1))
                self.game.save["best"][str(self.wave)] = max(stars, self.game.save["best"].get(str(self.wave), 0))
            self.game.check_achievements()
            save_data(self.game.save)

    def bar(self, surf, x, y, w, value, maximum, color, label, font):
        pygame.draw.rect(surf, (15, 19, 30), (x, y, w, 22), border_radius=8)
        pygame.draw.rect(surf, color, (x + 3, y + 3, int((w - 6) * clamp(value / maximum, 0, 1)), 16), border_radius=6)
        text = font.render(label, True, (250, 244, 220))
        surf.blit(text, (x + 8, y + 2))

    def draw(self, surf):
        ox = random.randint(-int(self.shake), int(self.shake)) if self.shake else 0
        oy = random.randint(-int(self.shake / 2), int(self.shake / 2)) if self.shake else 0
        surf.blit(self.game.background, (ox, oy))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((12, 18, 38, 35))
        surf.blit(overlay, (0, 0))
        pygame.draw.rect(surf, (48, 28, 25), (88, 372, 85, 190), border_radius=7)
        pygame.draw.polygon(surf, (23, 28, 42), [(70, 392), (130, 330), (190, 392)])
        self.bar(surf, 24, 22, 300, self.hero.hp, self.hero.max_hp, (190, 48, 66), f"RONIN  {int(max(0,self.hero.hp))}/{int(self.hero.max_hp)}", self.game.font_small)
        self.bar(surf, 24, 51, 300, self.gate_hp, self.gate_max, (60, 155, 195), f"LANTERN GATE  {int(max(0,self.gate_hp))}", self.game.font_small)
        self.bar(surf, 24, 80, 300, self.spirit, self.spirit_max, (168, 100, 215), f"SPIRIT  {int(self.spirit)}/{self.spirit_max}", self.game.font_small)
        progress = (self.killed / max(1, self.total))
        wave_label = f"ENDLESS NIGHT {self.wave - 15}" if self.endless else f"WAVE {self.wave}"
        self.bar(surf, 920, 24, 330, progress, 1, (220, 146, 56), f"{wave_label}  •  {int(progress*100)}%", self.game.font_small)
        if self.combo >= 2:
            combo = self.game.font_small.render(f"{self.combo} HIT COMBO", True, (255, 198, 75))
            surf.blit(combo, combo.get_rect(topright=(1245, 57)))
        for u in sorted(self.allies + self.enemies, key=lambda a: a.x): u.draw(surf)
        self.hero.draw(surf)
        for p in self.projectiles: p.draw(surf)
        for p in self.particles: p.draw(surf)
        self.draw_hud(surf)
        if self.state == "intro":
            self.game.panel(surf, pygame.Rect(385, 250, 510, 170))
            title = f"ENDLESS NIGHT {self.wave - 15}" if self.endless else f"WAVE {self.wave}"
            self.game.center_text(surf, title, self.game.font_title, 310, (244, 194, 89))
            subtitle = "THE DREAD DAIMYO APPROACHES" if self.wave % 5 == 0 else "THE HOLLOW MARCH"
            self.game.center_text(surf, subtitle, self.game.font, 365)
            self.game.center_text(surf, self.modifier.upper(), self.game.font_tiny, 400, (185,199,218))
        if self.state in ("won", "lost"):
            self.draw_result(surf)

    def draw_hud(self, surf):
        pygame.draw.rect(surf, (10, 14, 25, 235), (0, 624, WIDTH, 96))
        boxes = [(18, "1", "guard", "Guard", 30, (55,150,185)), (132, "2", "archer", "Archer", 45, (165,100,205)), (246, "3", "monk", "Monk", 65, (225,175,75)), (360, "4", "captain", "Captain", 90, (195,68,74))]
        for x, key, kind, name, cost, color in boxes:
            rect = pygame.Rect(x, 638, 108, 66)
            ready = self.spirit >= cost and self.summon_cooldowns[kind] <= 0
            pygame.draw.rect(surf, (29, 40, 60) if ready else (30,30,36), rect, border_radius=8)
            pygame.draw.rect(surf, color, rect, 2, border_radius=8)
            surf.blit(self.game.font_tiny.render(f"[{key}] {name}", True, (245,240,220)), (x+7, 648))
            status = f"{self.summon_cooldowns[kind]:.1f}s" if self.summon_cooldowns[kind] > 0 else f"{cost} spirit"
            surf.blit(self.game.font_tiny.render(status, True, color), (x+8, 674))
        abilities = [(484, "Q", "STORM", self.lightning_cd, 140), (634, "E", "RALLY", self.rally_cd, 140)]
        for x, key, name, cd, w in abilities:
            rect = pygame.Rect(x, 638, w, 66)
            pygame.draw.rect(surf, (45,55,82), rect, border_radius=8)
            pygame.draw.rect(surf, (125,190,235) if key == "Q" else (240,190,80), rect, 2, border_radius=8)
            label = f"[{key}] {name}" if cd <= 0 else f"{name}  {cd:.1f}s"
            surf.blit(self.game.font_small.render(label, True, (245,240,220)), (x+12, 650))
            surf.blit(self.game.font_tiny.render("READY" if cd <= 0 else "RECHARGING", True, (180,190,205)), (x+12, 677))
        controls = self.game.font_tiny.render("A/D Move   SPACE Slash   F Bow   ESC Pause", True, (190, 197, 210))
        surf.blit(controls, (805, 667))

    def draw_result(self, surf):
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); shade.fill((5, 7, 15, 180)); surf.blit(shade, (0,0))
        self.game.panel(surf, pygame.Rect(355, 170, 570, 385))
        if self.state == "won":
            self.game.center_text(surf, "VICTORY", self.game.font_title, 222, (245, 191, 73))
            stars = self.game.save["best"].get(str(self.wave), 1)
            self.game.center_text(surf, "★ " * stars + "☆ " * (3-stars), self.game.font_big, 290, (245, 191, 73))
            self.game.center_text(surf, f"Spoils: {self.earned} coins", self.game.font, 350)
            hint = "Press ENTER for the next night" if self.endless else ("Press ENTER for the next wave" if self.wave < 15 else "The Last Lantern endures. Campaign complete!")
            self.game.center_text(surf, hint, self.game.font_small, 405)
        else:
            self.game.center_text(surf, "THE LANTERN FALLS", self.game.font_big, 230, (224, 72, 83))
            self.game.center_text(surf, "Regroup, upgrade, and return stronger.", self.game.font, 325)
            self.game.center_text(surf, "Press R to retry", self.game.font_small, 390)
        self.game.center_text(surf, "ESC  Return to village", self.game.font_small, 485, (180,190,205))


class Game:
    def __init__(self):
        pygame.init()
        try: pygame.mixer.init(frequency=22050, size=-16, channels=1)
        except pygame.error: pass
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_tiny = pygame.font.SysFont("segoeui", 16)
        self.font_small = pygame.font.SysFont("segoeui", 20, bold=True)
        self.font = pygame.font.SysFont("georgia", 27, bold=True)
        self.font_big = pygame.font.SysFont("georgia", 43, bold=True)
        self.font_title = pygame.font.SysFont("georgia", 66, bold=True)
        raw_bg = pygame.image.load(resource_path(os.path.join("assets", "battlefield.png"))).convert()
        self.background = pygame.transform.smoothscale(raw_bg, (WIDTH, HEIGHT))
        sprite_files = {
            "hero": "ronin_hero.png", "guard": "ally_guard.png",
            "archer": "ally_archer.png", "monk": "ally_monk.png",
            "captain": "ally_captain.png",
            "walker": "skeleton_minion.png", "runner": "skeleton_rogue.png",
            "brute": "skeleton_warrior.png", "shaman": "skeleton_mage.png",
            "armored": "skeleton_warrior.png", "boss": "skeleton_warrior.png",
        }
        for kind, filename in sprite_files.items():
            CHARACTER_SPRITES[kind] = pygame.image.load(
                resource_path(os.path.join("assets", "characters", filename))
            ).convert_alpha()
        self.save = load_save()
        self.sounds = SoundBank()
        self.sounds.enabled = self.save.get("sound", True)
        self.fullscreen = False
        self.controller = pygame.joystick.Joystick(0) if pygame.joystick.get_count() else None
        self.state = "menu"
        self.previous_state = "menu"
        self.battle = None
        self.running = True
        self.toast = ""
        self.toast_timer = 0

    def panel(self, surf, rect):
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (13, 20, 35, 238), layer.get_rect(), border_radius=18)
        pygame.draw.rect(layer, (226, 180, 84, 220), layer.get_rect(), 3, border_radius=18)
        surf.blit(layer, rect)

    def center_text(self, surf, text, font, y, color=(240,235,220)):
        img = font.render(text, True, color)
        surf.blit(img, img.get_rect(center=(WIDTH//2, y)))

    def title_backdrop(self):
        self.canvas.blit(self.background, (0,0))
        shade = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA); shade.fill((5,9,23,135)); self.canvas.blit(shade,(0,0))

    def menu_buttons(self):
        return [
            Button((490, 318, 300, 56), "CONTINUE CAMPAIGN", "continue", True),
            Button((490, 386, 300, 52), "CHOOSE WAVE", "waves"),
            Button((490, 450, 300, 52), "ENDLESS NIGHT", "endless"),
            Button((410, 514, 145, 52), "UPGRADES", "upgrades"),
            Button((568, 514, 145, 52), "BESTIARY", "bestiary"),
            Button((726, 514, 145, 52), "ACHIEVEMENTS", "achievements"),
            Button((490, 578, 145, 48), "HOW TO PLAY", "help"),
            Button((645, 578, 145, 48), "QUIT", "quit"),
        ]

    def activate(self, action):
        self.sounds.play("click")
        if action == "continue": self.start_wave(self.save["unlocked"])
        elif action == "waves": self.state = "waves"
        elif action == "endless": self.start_wave(16, endless=True)
        elif action == "upgrades": self.state = "upgrades"
        elif action == "bestiary": self.state = "bestiary"
        elif action == "achievements": self.state = "achievements"
        elif action == "help": self.state = "help"
        elif action == "quit": self.running = False

    def start_wave(self, wave, endless=False):
        self.battle = Battle(self, wave, endless)
        self.state = "battle"

    def cycle_difficulty(self):
        choices = list(DIFFICULTIES)
        current = self.save.get("difficulty", "normal")
        self.save["difficulty"] = choices[(choices.index(current) + 1) % len(choices)]
        save_data(self.save)
        self.sounds.play("click")

    def add_stat(self, name, amount=1):
        self.save["stats"][name] = self.save["stats"].get(name, 0) + amount
        self.check_achievements()

    def check_achievements(self):
        stats = self.save["stats"]
        upgrade_total = sum(self.save["upgrades"].values())
        conditions = {
            "first_blood": stats.get("kills", 0) >= 1,
            "horde_breaker": stats.get("kills", 0) >= 100,
            "banner_caller": stats.get("summons", 0) >= 50,
            "village_veteran": stats.get("wins", 0) >= 15,
            "deep_night": self.save.get("endless_best", 0) >= 20,
            "master_smith": upgrade_total >= 15,
        }
        claimed = self.save["achievements"]
        for key, earned in conditions.items():
            if earned and key not in claimed:
                claimed.append(key)
                name, _, reward = ACHIEVEMENTS[key]
                self.save["coins"] += reward
                self.toast = f"Achievement: {name}  +{reward} coins"
                self.toast_timer = 3.0
                self.sounds.play("win")
        save_data(self.save)

    def handle_event(self, e):
        if e.type == pygame.QUIT: self.running = False
        if e.type == pygame.JOYDEVICEADDED and self.controller is None:
            self.controller = pygame.joystick.Joystick(e.device_index)
            self.toast = "Controller connected"
            self.toast_timer = 2
        if e.type == pygame.JOYDEVICEREMOVED and self.controller and e.instance_id == self.controller.get_instance_id():
            self.controller = None
            self.toast = "Controller disconnected"
            self.toast_timer = 2
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_m:
                self.save["sound"] = not self.save.get("sound", True)
                self.sounds.enabled = self.save["sound"]
                self.toast = "Sound on" if self.sounds.enabled else "Sound off"
                self.toast_timer = 1.5
                save_data(self.save)
                return
            if e.key == pygame.K_F11:
                self.fullscreen = not self.fullscreen
                flags = pygame.FULLSCREEN if self.fullscreen else 0
                self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
                self.toast = "Full screen" if self.fullscreen else "Windowed"
                self.toast_timer = 1.5
                return
            if self.state == "battle" and self.battle.state == "won" and e.key == pygame.K_RETURN and (self.battle.endless or self.battle.wave < 15):
                self.start_wave(self.battle.wave + 1, self.battle.endless); return
            if self.state == "battle" and self.battle.state == "lost" and e.key == pygame.K_r:
                self.start_wave(self.battle.wave, self.battle.endless); return
            if e.key == pygame.K_ESCAPE:
                if self.state == "battle": self.previous_state = "battle"; self.state = "pause"
                elif self.state == "pause": self.state = "battle"
                elif self.state != "menu": self.state = "menu"
                return
        if self.state == "battle": self.battle.handle_event(e)
        elif self.state == "menu" and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if pygame.Rect(1015, 22, 235, 48).collidepoint(e.pos):
                self.cycle_difficulty(); return
            for b in self.menu_buttons():
                if b.rect.collidepoint(e.pos): self.activate(b.action)
        elif self.state == "waves" and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i in range(1,16):
                col, row = (i-1)%5, (i-1)//5
                r = pygame.Rect(280+col*150, 265+row*105, 118, 78)
                if r.collidepoint(e.pos) and i <= self.save["unlocked"]: self.start_wave(i)
        elif self.state == "upgrades" and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            keys = list(self.save["upgrades"])
            for i,key in enumerate(keys):
                r = pygame.Rect(815, 220+i*82, 150, 48)
                lvl = self.save["upgrades"][key]; cost = 120 + lvl*135
                if r.collidepoint(e.pos) and lvl < 5:
                    if self.save["coins"] >= cost:
                        self.save["coins"] -= cost; self.save["upgrades"][key] += 1; save_data(self.save); self.sounds.play("coin")
                        self.check_achievements()
                    else: self.toast = "Not enough coins"; self.toast_timer = 1.5
        elif self.state == "pause" and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if pygame.Rect(490,330,300,58).collidepoint(e.pos): self.state="battle"
            if pygame.Rect(490,405,300,58).collidepoint(e.pos): self.state="menu"

    def update(self, dt):
        self.toast_timer = max(0, self.toast_timer-dt)
        if self.state == "battle": self.battle.update(dt)

    def draw_menu(self):
        self.title_backdrop()
        self.center_text(self.canvas, "MOONBLADE", self.font_title, 135, (246,194,86))
        self.center_text(self.canvas, "LAST LANTERN", self.font_big, 200, (235,230,220))
        self.center_text(self.canvas, "An original lane-defense adventure", self.font_small, 250, (185,199,218))
        for b in self.menu_buttons(): b.draw(self.canvas, self.font_small, pygame.mouse.get_pos())
        coins = self.font_small.render(f"COINS  {self.save['coins']}", True, (246,194,86)); self.canvas.blit(coins,(25,25))
        difficulty = DIFFICULTIES[self.save.get("difficulty", "normal")]["label"]
        Button((1015,22,235,48), f"DIFFICULTY: {difficulty}").draw(self.canvas, self.font_tiny, pygame.mouse.get_pos())
        best = self.font_tiny.render(f"Endless best: Night {self.save.get('endless_best', 0) - 15}" if self.save.get("endless_best", 0) else "Endless best: None", True, (190,197,210))
        self.canvas.blit(best, (1050, 82))
        sound = "ON" if self.save.get("sound", True) else "OFF"
        self.center_text(self.canvas, f"M  Sound {sound}     F11  Full screen     Progress saves automatically", self.font_tiny, 680, (170,180,196))

    def draw_waves(self):
        self.title_backdrop(); self.panel(self.canvas, pygame.Rect(210,110,860,510))
        self.center_text(self.canvas,"CHOOSE WAVE",self.font_big,165,(246,194,86))
        for i in range(1,16):
            col,row=(i-1)%5,(i-1)//5; r=pygame.Rect(280+col*150,265+row*105,118,78)
            unlocked=i<=self.save["unlocked"]
            pygame.draw.rect(self.canvas,(40,58,82) if unlocked else (30,31,39),r,border_radius=10)
            pygame.draw.rect(self.canvas,(235,185,80) if unlocked else (80,80,88),r,2,border_radius=10)
            label=self.font.render(str(i) if unlocked else "×",True,(245,238,218) if unlocked else (100,100,108)); self.canvas.blit(label,label.get_rect(center=(r.centerx,r.centery-8)))
            stars=self.save["best"].get(str(i),0); s=self.font_tiny.render("★"*stars+"☆"*(3-stars),True,(240,185,70)); self.canvas.blit(s,s.get_rect(center=(r.centerx,r.centery+24)))
        self.center_text(self.canvas,"ESC  Back",self.font_small,585,(180,190,205))

    def draw_upgrades(self):
        self.title_backdrop(); self.panel(self.canvas,pygame.Rect(220,80,840,580))
        self.center_text(self.canvas,"VILLAGE FORGE",self.font_big,135,(246,194,86))
        coin=self.font_small.render(f"Coins: {self.save['coins']}",True,(246,194,86)); self.canvas.blit(coin,(805,145))
        info={"vitality":("RONIN VITALITY","+55 maximum health"),"blade":("MOON BLADE","+9 sword damage"),"bow":("SPIRIT BOW","+7 arrow damage"),"gate":("LANTERN GATE","+130 gate health"),"spirit":("LEADERSHIP","+12 max spirit, faster regen")}
        for i,key in enumerate(info):
            y=215+i*82; name,desc=info[key]; lvl=self.save["upgrades"][key]; cost=120+lvl*135
            self.canvas.blit(self.font_small.render(name,True,(240,235,220)),(300,y))
            self.canvas.blit(self.font_tiny.render(desc,True,(170,185,205)),(300,y+30))
            self.canvas.blit(self.font_tiny.render("◆"*lvl+"◇"*(5-lvl),True,(238,178,72)),(610,y+8))
            r=pygame.Rect(815,y+5,150,48); pygame.draw.rect(self.canvas,(48,68,92),r,border_radius=8); pygame.draw.rect(self.canvas,(230,180,78),r,2,border_radius=8)
            txt="MAX" if lvl>=5 else f"BUY  {cost}"; t=self.font_small.render(txt,True,(245,238,218)); self.canvas.blit(t,t.get_rect(center=r.center))
        self.center_text(self.canvas,"ESC  Back",self.font_small,630,(180,190,205))

    def draw_achievements(self):
        self.title_backdrop(); self.panel(self.canvas,pygame.Rect(205,72,870,590))
        self.center_text(self.canvas,"ACHIEVEMENTS",self.font_big,125,(246,194,86))
        stats = self.save["stats"]
        summary = f"Enemies {stats.get('kills',0)}     Allies {stats.get('summons',0)}     Wins {stats.get('wins',0)}     Best combo {stats.get('best_combo',0)}"
        self.center_text(self.canvas,summary,self.font_tiny,168,(185,199,218))
        for i,(key,(name,desc,reward)) in enumerate(ACHIEVEMENTS.items()):
            y=205+i*66; earned=key in self.save["achievements"]
            rect=pygame.Rect(275,y,730,52)
            pygame.draw.rect(self.canvas,(44,70,67) if earned else (31,39,55),rect,border_radius=9)
            pygame.draw.rect(self.canvas,(95,205,135) if earned else (92,102,120),rect,2,border_radius=9)
            mark="✓" if earned else "◇"
            self.canvas.blit(self.font_small.render(f"{mark}  {name}",True,(235,238,220)),(294,y+7))
            self.canvas.blit(self.font_tiny.render(desc,True,(170,185,205)),(565,y+8))
            reward_text="CLAIMED" if earned else f"{reward} coins"
            self.canvas.blit(self.font_tiny.render(reward_text,True,(240,185,70)),(880,y+28))
        self.center_text(self.canvas,"ESC  Back",self.font_small,630,(180,190,205))

    def draw_bestiary(self):
        self.title_backdrop(); self.panel(self.canvas,pygame.Rect(150,68,980,598))
        self.center_text(self.canvas,"HOLLOW BESTIARY",self.font_big,120,(246,194,86))
        details = {
            "walker": ("Basic front line enemy", "Wave 1"),
            "runner": ("Fast attacker with low health", "Wave 2"),
            "brute": ("Slow enemy with heavy strikes", "Wave 4"),
            "shaman": ("Casts magic from a distance", "Wave 6"),
            "armored": ("Very tough defensive warrior", "Wave 8"),
            "boss": ("Leader of every fifth attack", "Wave 5"),
        }
        for i, (kind, data) in enumerate(ENEMY_DATA.items()):
            col, row = i % 2, i // 2
            x, y = 225 + col * 440, 165 + row * 135
            rect = pygame.Rect(x, y, 390, 112)
            pygame.draw.rect(self.canvas,(29,40,58),rect,border_radius=12)
            pygame.draw.rect(self.canvas,data["color"],rect,2,border_radius=12)
            sprite = CHARACTER_SPRITES[kind]
            height = 92
            width = int(sprite.get_width() * height / sprite.get_height())
            image = pygame.transform.smoothscale(sprite,(width,height))
            self.canvas.blit(image,image.get_rect(midbottom=(x+65,y+105)))
            desc, first_wave = details[kind]
            self.canvas.blit(self.font_small.render(data["name"],True,(245,238,218)),(x+125,y+17))
            self.canvas.blit(self.font_tiny.render(desc,True,(180,192,208)),(x+125,y+51))
            stats = f"Health {data['hp']}   Damage {data['dmg']}   {first_wave}"
            self.canvas.blit(self.font_tiny.render(stats,True,(235,180,78)),(x+125,y+77))
        self.center_text(self.canvas,"ESC  Back",self.font_small,630,(180,190,205))

    def draw_help(self):
        self.title_backdrop(); self.panel(self.canvas,pygame.Rect(210,90,860,540))
        self.center_text(self.canvas,"HOW TO PLAY",self.font_big,145,(246,194,86))
        lines=[("MOVE","A / D, arrows, or controller stick"),("SWORD","SPACE, left mouse, or controller A"),("BOW","F or controller X"),("SUMMON","1 to 4  •  controller shoulder and center buttons"),("ABILITIES","Q Storm  •  E Rally  •  controller Y and B"),("OPTIONS","M Sound  •  F11 Full screen"),("OBJECTIVE","Defeat every Hollow before your hero or gate falls."),("MODES","Clear 15 campaign waves, then test an endless run.")]
        for i,(a,b) in enumerate(lines):
            y=210+i*47; self.canvas.blit(self.font_small.render(a,True,(238,180,76)),(300,y)); self.canvas.blit(self.font_small.render(b,True,(232,230,222)),(475,y))
        self.center_text(self.canvas,"ESC  Back",self.font_small,595,(180,190,205))

    def draw_pause(self):
        self.battle.draw(self.canvas)
        shade=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); shade.fill((5,8,18,185)); self.canvas.blit(shade,(0,0)); self.panel(self.canvas,pygame.Rect(420,210,440,300))
        self.center_text(self.canvas,"PAUSED",self.font_big,270,(246,194,86))
        for r,text in [(pygame.Rect(490,330,300,58),"RESUME"),(pygame.Rect(490,405,300,58),"RETURN TO VILLAGE")]:
            Button(r,text).draw(self.canvas,self.font_small,pygame.mouse.get_pos())

    def draw(self):
        if self.state=="menu": self.draw_menu()
        elif self.state=="waves": self.draw_waves()
        elif self.state=="upgrades": self.draw_upgrades()
        elif self.state=="achievements": self.draw_achievements()
        elif self.state=="bestiary": self.draw_bestiary()
        elif self.state=="help": self.draw_help()
        elif self.state=="battle": self.battle.draw(self.canvas)
        elif self.state=="pause": self.draw_pause()
        if self.toast_timer>0:
            t=self.font_small.render(self.toast,True,(255,235,220)); box=t.get_rect(center=(WIDTH//2,680)).inflate(35,18); pygame.draw.rect(self.canvas,(95,35,45),box,border_radius=9); self.canvas.blit(t,t.get_rect(center=box.center))
        self.screen.blit(self.canvas,(0,0)); pygame.display.flip()

    def run(self):
        while self.running:
            dt=min(.035,self.clock.tick(FPS)/1000)
            for e in pygame.event.get(): self.handle_event(e)
            self.update(dt); self.draw()
        save_data(self.save); pygame.quit()


if __name__ == "__main__":
    Game().run()
