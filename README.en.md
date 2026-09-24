# AIBrain · Personal Memory + Knowledge Base

> Put "you" in your own repo — platforms are just readers.

A platform-independent "second brain". Everything is plain Markdown that you own and any AI can read.

## Why this exists

Each AI platform keeps its own siloed memory: ChatGPT can't recall what you told Doubao, and WorkBuddy's MEMORY.md won't feed Kimi. More platforms means your memory gets more fragmented. This flips ownership — you put "you" and "your knowledge" into your own repo, and platforms merely read from it. Switch platforms, tools, or machines — your memory stays.

Six concrete advantages:

1. **You own the data, not a vendor.** Just plain `.md` files in your own folder. No account, no subscription, no "where did the export button go".
2. **One profile, every AI.** ChatGPT, Claude, Gemini, Doubao, Yuanbao, Kimi, DeepSeek, WorkBuddy, Cursor — all can read it. When the next AI shows up, just hand it your profile; no re-teaching.
3. **Length adapts automatically.** Platform limits vary wildly (ChatGPT's instruction box caps at 1500 characters; some tools allow only a few hundred). One command compiles three tiers — full / compact / micro — so you always have the right size.
4. **It remembers *why*.** Platform memory usually stores "user likes X". This also records the reasoning and the rejected alternatives, so you can still look up a decision months later.
5. **Import in, walk away with everything.** Built-in tools scan this machine for other AIs' leftovers and merge exported memory automatically. If you ever stop using it, copy or delete the folder — nothing is locked in.
6. **A local web UI, no CLI needed.** Open a browser to see every file, edit and save, and rebuild with one click — far less painful than digging through memory settings in a dozen apps.

## Directory layout

```
AIBrain/
├── AGENTS.md            ← Entry point for AIs (load it directly)
├── README.md            ← This file
├── memory/              ← Memory: facts, preferences, people
│   ├── profile.md          Who am I
│   ├── preferences.md      My preferences & habits
│   ├── people.md           Important people & relationships
│   ├── commitments.md      Ongoing things
│   ├── decisions.md        Decisions & reasons
│   ├── machine.md          Facts about this machine (paths, terminal quirks)
│   └── logs/               Daily work logs (kept out of public repos)
├── knowledge/           ← Knowledge: external & your notes
│   ├── index.md            Master index (read first)
│   ├── links.md            Sites & tools
│   ├── work/               Work & project material
│   │   ├── projects/           One file per project
│   │   ├── templates/          Reusable templates
│   │   └── assets/             Large files (images, SVG…)
│   └── notes/              Personal notes
├── inbox/               ← Drop exported memory text from other AIs here
├── adapters/            ← Integration guides
│   ├── README.md           How to mount on each platform
│   ├── 双向共享.md         Two-way bridge for local agent apps (Chinese)
│   └── memory-import.md    How to migrate memory out of other AIs
├── web/index.html       ← Local web UI (file list + editor + one-click build)
├── tools/
│   ├── sync.py             Build paste-ready versions in three lengths
│   ├── serve.py            Local server for the web UI (127.0.0.1:8420)
│   ├── detect.py           Scan this machine for importable AI data
│   ├── ingest.py           Merge inbox/ exports into your memory
│   ├── bridge.py           Two-way bridge: share memory with local agent apps
│   ├── publish_check.py    Pre-publish privacy check
│   └── make_public.py      Generate a clean publishable package
├── example/             ← Fictional samples used by the public template
├── 给AI的指令词.md       ← Ready-to-copy prompt that asks other AIs to export your memory (Chinese)
├── PUBLISH.md           ← Full publishing guide (Chinese)
└── dist/                ← Script output (auto-generated, don't edit)
```

## Get started in 3 steps

1. **Fill memory**: open `memory/profile.md` and replace every `TODO` with real info. Even 10 lines help immediately.
2. **Build**: run `python tools/sync.py` to generate paste-ready versions of three lengths in `dist/`.
3. **Mount**: follow `adapters/README.md` to paste the right version into your platform. Re-run the script after each memory update.

## One hard rule

`memory/` is the single source of truth. `dist/` is fully script-generated — **never hand-edit it**; changes vanish on the next build.

## Daily maintenance

- **Jot down**: when you think "I should remember this", tell your AI or append a line to `memory/logs/YYYY-MM-DD.md`.
- **Promote**: things that recur in logs move up into `preferences.md` or `decisions.md` (logs go stale; promoted items become long-term memory).
- **Archive**: drop new docs into `knowledge/work/` or `knowledge/notes/`, and add a line to `knowledge/index.md`.

## Optional: local web UI

```bash
python tools/serve.py     # then open http://127.0.0.1:8420
```

Browse and edit every file in `memory/` and `knowledge/`, save straight to disk, and rebuild all three versions with one button. Standard library only, no dependencies, bound to localhost.

## Importing memory from other AIs

Two very different cases:

- **Local-first tools** (WorkBuddy, Cursor, Coze / Doubao desktop) can be scanned:
  ```bash
  python tools/detect.py            # read-only scan, report goes to inbox/detected.md
  ```
- **Cloud-only AIs** (ChatGPT, Claude, Gemini, Doubao, Kimi, …) keep memory on their own servers — there is **no local file to read**, so ask that AI to export it using the prompt in `给AI的指令词.md`, then save the result into `inbox/`.

```bash
python tools/ingest.py --dry-run  # preview
python tools/ingest.py           # merge, de-duplicate, rebuild
```

Full walkthrough and per-platform notes: `adapters/memory-import.md`.

> Never paste passwords, ID numbers, bank cards, or other people's private data into `inbox/`.

## Two-way sharing with local agent apps

Agents installed on your machine (WorkBuddy, LobsterAI, …) each keep their memory in their own private folder — **they share nothing by default**.
`tools/bridge.py` connects them: it injects the compiled memory into the file each app reads at startup (inside marked blocks, safe to re-run), and can also pull newly written lines back as a review list.

```bash
python tools/bridge.py status   # is each app connected?
python tools/bridge.py push     # inject AIBrain into every configured app
python tools/bridge.py pull     # pull new app-side lines into inbox/ (never auto-merged)
```

Add another app by appending one path to the `APPS` list in `tools/bridge.py`. Mechanism and caveats: `adapters/双向共享.md` (Chinese).

## Sync across devices

The repo is already `git init`-ed. Push to a **private** repo (GitHub / Gitee private) to sync:

```bash
cd <your-path>/AIBrain
git remote add origin <your-private-repo-url>
git config --local credential.helper <your-credential-helper>
git add -A && git commit -m "init brain"
git push -u origin main
```

Daily sync after that, pick one:

1. **Double-click the desktop shortcut** (Windows users of this template have one that runs add + commit + push).
2. Command line: `cd <your-path>/AIBrain && git add -A && git commit -m "update" && git push`
3. Edit on your phone: open the private repo in the GitHub app or web, edit files under `memory/`, commit — then `git pull` on the computer.

**Both sides must sync**: push after editing on the computer, pull after editing on the phone. On conflict, `git pull --rebase` then push.

> This repo holds your personal data — **use a private repo**.

## Optional: start the web UI at login

- **Windows**: add a value under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` set to `"<pythonw.exe>" "<repo>\tools\serve.py"`. Using `pythonw.exe` avoids a console window.
- **macOS / Linux**: a launchd plist or a systemd user unit, or add a login item in your desktop environment — same command, `python3 <repo>/tools/serve.py`.

Then open `http://127.0.0.1:8420`. To stop it, end the `pythonw.exe` process.

## Want to publish it for others?

This repo doubles as a template. If your private copy already holds real content, **strip your personal memory out before publishing** (`make_public.py` only exists in your own private repo — a template package published by someone else does not include it):

```bash
python tools/publish_check.py --history   # scan for personal paths / emails / tokens / credential files
python tools/make_public.py               # one command builds a clean package (default: ../AIBrain-public)
```

`make_public.py` replaces `memory/` with the fictional `example/` content, drops real notes and personal exports, scrubs leftover paths and emails, and runs `git init` + a first commit in the output folder (with a neutral commit author, so your email never enters public history). It **never pushes** — pushing is up to you. See `PUBLISH.md` for the file list, repo description text, and command sequence (Chinese).

## Optional: view with Obsidian

This folder is a valid Obsidian vault. Open it for bi-links, graph view, and full-text search — files stay plain Markdown. Notepad is fine too.
