# Moonblade: Last Lantern

Moonblade is a small hero controlled lane defense game for Windows. You control a wandering ronin, fight the front line yourself, summon allies with a regenerating spirit meter, and protect the last village gate from an undead army.

![Moonblade battle](docs/battle.png)

The project grew out of missing games such as *Samurai vs Zombies Defense* after they disappeared from modern storefronts. It is not a remake and does not use Glu's code, names, characters, audio, or extracted assets. The goal is to build a new game around the same combination of direct combat and lane defense strategy.

## What is playable

* 15 campaign waves with persistent progress and star ratings
* Endless Night mode after the main menu, with a saved personal record
* Story, Normal, and Nightmare difficulty settings
* controllable sword and bow combat
* four summonable allies, including the Gate Captain
* summon cooldowns and a regenerating spirit resource
* Storm and Rally active abilities
* six enemy roles, including Iron Revenants and recurring bosses
* achievements with career statistics and coin rewards
* five permanent upgrade paths
* automatic local saving
* mouse and keyboard support

## Controls

* Move with `A`, `D`, or the arrow keys
* Attack with the sword using `Space` or the left mouse button
* Fire the bow with `F`
* Summon allies with `1`, `2`, `3`, and `4`
* Cast Storm with `Q`
* Use Rally with `E`
* Pause or return with `Esc`

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

This is an early complete prototype rather than a commercial size game. The current build has a full campaign loop, upgrades, bosses, difficulty options, achievements, and endless play. Future work can add animated sprite art, more allies, additional battlefields, controller support, and richer music and sound.

## License

The source code is available under the MIT License. The painted battlefield image in `assets/` is included for use with this project; please do not redistribute it as a standalone asset pack.

Moonblade is an independent project inspired by a missing game and is not affiliated with or endorsed by Glu Mobile or Electronic Arts.
