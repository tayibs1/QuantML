# `scripts/` — Developer helper scripts

| Script     | What it does                                              |
| ---------- | --------------------------------------------------------- |
| `dev.ps1`  | Start frontend (3000) **and** backend (8000) — Windows    |
| `dev.sh`   | Same, for macOS/Linux                                     |

```powershell
# Windows
./scripts/dev.ps1
```
```bash
# macOS / Linux
./scripts/dev.sh
```

Frontend only: `npm run dev` (from repo root).
Backend only:  `npm run backend` (needs the venv — see root README).
