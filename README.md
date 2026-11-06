# Moonblade: Last Lantern

Moonblade is a small hero-led lane defense game for Windows. You control a wandering ronin, fight the front line yourself, summon allies with a regenerating spirit meter, and protect the last village gate from an undead army.

The project grew out of missing games such as *Samurai vs Zombies Defense* after they disappeared from modern storefronts. It is not a remake and does not use Glu's code, names, characters, audio, or extracted assets. The goal is to build a new game around the same combination of direct combat and lane-defense strategy.

## What is playable

- 15 campaign waves with persistent progress and star ratings
- Endless Night mode after the main menu, with a saved personal record
- Story, Normal, and Nightmare difficulty settings
- controllable sword and bow combat
- Ashigaru, Moon Archer, and Lantern Monk summons
- summon cooldowns and a regenerating spirit resource
- Storm and Rally active abilities
- five enemy roles, including ranged attackers and recurring bosses
- five permanent upgrade paths
- automatic local saving
- mouse and keyboard support

## Controls

| Action | Input |
| --- | --- |
| Move | `A` / `D` or arrow keys |
| Sword attack | `Space` or left mouse button |
| Fire bow | `F` |
| Summon allies | `1`, `2`, `3` |
| Storm ability | `Q` |
| Rally heal | `E` |
| Pause / back | `Esc` |

## Run from source

Install Python 3.11 or newer, then run:

```powershell
python -m pip install -r requirements.txt
python game.py
```

## Build the Windows application

Run `build.ps1` from PowerShell. It installs the two required packages when needed and creates `release/application.exe`.

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

The packaged game stores progress in `%LOCALAPPDATA%\MoonbladeDefense\save.json`.

## Project status

This is an early complete prototype rather than a commercial-size game. The current build has a full campaign loop, upgrades, bosses, difficulty options, and endless play. Future work can add animated sprite art, more allies, additional battlefields, controller support, and richer music and sound.

## License

The source code is available under the MIT License. The painted battlefield image in `assets/` is included for use with this project; please do not redistribute it as a standalone asset pack.

Moonblade is an independent fan-inspired project and is not affiliated with or endorsed by Glu Mobile or Electronic Arts.
