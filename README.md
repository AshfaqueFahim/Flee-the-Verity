# Flee-the-Verity

A 2-player pygame escape game. Hack all 10 computers, then run out an exit before Verity catches you both.

## Run

```
pip install pygame-ce
python main.py
```

## Controls

| | Move | Hack / rescue |
|---|---|---|
| Blue (player 1) | W A S D | E |
| Orange (player 2) | Arrow keys | P |

Press **R** to restart.

## Rules

- Hold the interact key at a computer to hack it. Letting go resets its progress.
- If Verity catches you, you get locked in the nearest tube. Your teammate can hold interact next to it to free you.
- Buildings are dark, so use your flashlight. Verity can't see you as far away in the dark.
- Exits open once every computer is hacked and nobody is stuck in a tube.
