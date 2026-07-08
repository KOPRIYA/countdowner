# Countdowner

Countdowner is a Python-powered local web app for goal countdown tiles, progress tracking, motivation, rewards, and shared accountability.

## Run

```bash
python3 app.py
```

Open:

```text
http://127.0.0.1:8000
```

The app stores local data in `countdowner.sqlite3`.

## What is included

- Local account creation with reward preferences and favorite authors.
- Goal tiles with one-time, daily, weekly, monthly, bi-annual, and annual types.
- Countdown timers, priority, categories, notes, and completion state.
- Fitness/eating-style tracker support through a configurable metric, target, and unit.
- Situational motivation based on progress, deadline pressure, category, priority, and preferred coaching style.
- Reward suggestions based on category, preferred reward type, priority, wishlist, and on-time completion.
- Goal sharing by email, invite acceptance, cheering, and accountability notes.

## Notes

This first version uses only Python standard-library modules, so it does not require package installation. Sharing works between local accounts in this app instance; email delivery can be added later with a mail provider. The motivation logic is pretty naive right now.

Features Coming up:
a. “Reward memory” block where the user can attach proof, reflection, and whether they followed the suggestion or made their own celebration.
