# AGENTS.md

Guidance for AI agents and contributors working in this repository.

## What this project is

**Kea2** is a Python tool for **property-based fuzzing of Android apps**. It fuses an automated UI fuzzer
([Fastbot 3.0](https://github.com/ecnusse/Fastbot_Android), a fork of ByteDance's Fastbot) with human-written
UI test scripts, so that automated exploration can reach deep UI states and run property assertions to find
both **crashes** and **non-crashing logic bugs**.

Core stack: `unittest` (script framework) + `uiautomator2` (`u2`, UI driver) + `Fastbot` (fuzzing backend) +
`hypothesis` (random input generation).

The published package name is `kea2-python`; the installed CLI entry point is `kea2`.

## Architecture / module map

- [kea2/cli.py](kea2/cli.py) — `kea2` CLI (entry point `kea2.cli:main`). Subcommands: `init`, `run`, `report`, `merge`, `version`.
- [kea2/kea_launcher.py](kea2/kea_launcher.py) — defines `kea2 run` CLI args and the `run()` entry that wires `Options` into `unittest`. Return codes are bitmasks: `1` = property violation, `2` = crash/ANR, `3` = both, `4` = error.
- [kea2/keaUtils.py](kea2/keaUtils.py) — the core engine: `KeaTestRunner`, `HybridTestRunner`, `keaTestLoader`, `Options`, the public decorators (`@precondition`, `@prob`, `@max_tries`, `@interruptable`, `kea2_breakpoint`).
- [kea2/u2Driver.py](kea2/u2Driver.py) — UI driver layer over `uiautomator2`: `U2Driver`, `U2ScriptDriver`, `U2StaticDevice`/`U2StaticChecker` (offline widget matching against a hierarchy XML), `_HindenWidgetFilter` (hidden-widget detection, backed by the external `rtree` package).
- [kea2/fastbotManager.py](kea2/fastbotManager.py) — Fastbot lifecycle: push libs, start service, run daemon, collect results.
- [kea2/fastbot_so_downloader.py](kea2/fastbot_so_downloader.py) — downloads/pins the Fastbot native `.so` libraries by version tag; used by `scripts/download_fastbot_so.py`.
- [kea2/fastbotx/](kea2/fastbotx/) — Fastbot model handling: `ActivityTimes`, `ReuseEntry`, `ReuseModel`.
- [kea2/fbm_parser.py](kea2/fbm_parser.py), [kea2/fbm_plugin.py](kea2/fbm_plugin.py) — parse/merge Fastbot models (FBM).
- [kea2/kea2_api.py](kea2/kea2_api.py) — `Kea2Tester`, the programmatic API.
- [kea2/adbUtils.py](kea2/adbUtils.py) — `ADBDevice` helpers over `adbutils`.
- [kea2/state.py](kea2/state.py) — stateful testing: `state` dict and `@invariant`.
- [kea2/result.py](kea2/result.py), [kea2/resultSyncer.py](kea2/resultSyncer.py), [kea2/logWatcher.py](kea2/logWatcher.py) — result capture and device log watching.
- [kea2/report/](kea2/report/) — HTML report generation (`bug_report_generator.py`, `report_merger.py`, `widget_coverage.py`, Jinja templates).
- [kea2/version_manager.py](kea2/version_manager.py) — version + config compatibility checks (configs/version.json).
- [kea2/utils.py](kea2/utils.py) — `getLogger`, `getProjectRoot`, `loadFuncsFromFile`, `catchException`, timestamps, etc.
- [kea2/assets/](kea2/assets/) — shipped jars (`monkeyq.jar`, `framework.jar`, …), Fastbot config strings, and the sample `quicktest.py`. Bumping these requires the `update-fastbot-artifacts` GitHub workflow (rebuild from Fastbot3 source).

User-facing scripts: `quicktest.py` (top level), `guide_scripts.py`, `properties/`, `hybridtest_examples/` (u2/pytest/appium hybrid examples).

## Setup

```bash
# Dev environment (uses uv; .venv at repo root, .python-version = 3.11)
pip install uv
uv sync
```

- CI supports Python 3.8–3.13; develop against the widest compatible syntax you can.
- Keep dependencies minimal — don't add one you can avoid. The `rtree` (libspatialindex) C-extension is a current hard dependency; changes touching it need care.
- User projects need `kea2 init` in their working dir before `kea2 run` works; `kea2 run` also requires a connected Android device/emulator.

## Testing

```bash
# Same command CI runs (`.github/workflows/test.yml`):
python -m unittest discover -s tests
```

- CI runs the `TestCase`-based offline tests in [tests/](tests/): `test_u2Selector.py` and `test_xpath.py` (both parse the XML fixtures in `tests/`, no device required — keep it that way).
- `tests/test_download_fastbot_so.py` is pytest-style (uses `tmp_path`/`monkeypatch`), so it is **not** collected by `unittest discover`; run it separately with `pytest` if you touch `fastbot_so_downloader.py`.
- Device-only smoke tests live in `tests/smoke.sh` and `tests/run_emulators.sh` (not part of CI).

## Writing properties/scripts (user-facing API)

A script is a `unittest.TestCase` class with methods decorated as properties:

```python
@prob(0.5)
@precondition(lambda self: self.d(text="Home").exists)
def test_goToPrivacy(self):
    self.d(description="Drawer").click()
    self.d(text="Settings").click()
    self.d(text="Privacy").click()
```

- `@precondition(...)` — when the property is eligible (checked every event; all must pass).
- `@prob(p)` — probability of executing an eligible property (0 < p ≤ 1).
- `@max_tries(n)` — cap on execution attempts.
- `@interruptable()` — property can be interrupted mid-execution (used by hybrid/script mode).
- `state["..."]` + `@invariant` — stateful testing.
- `self.d` is the UI driver (uiautomator2-like API). Its name is set by `--driver-name` (default `d`).
- Use `@precondition` to guide Fastbot to hard-to-reach pages; Fastbot handles navigation/exploration.
- Use `hypothesis` strategies (e.g. `text(alphabet=ascii_letters).example()`) to generate random inputs.

## `kea2 run` CLI

```bash
kea2 run -p it.feio.android.omninotes.alpha --running-minutes 10                    # pure fuzzing (Feature 1)
kea2 run -p it.feio.android.omninotes.alpha --running-minutes 10 \
    propertytest discover -s . -p quicktest.py                                      # property scripts (Feature 2/3)
```

- `-p/--packages` required. `propertytest` / `unittest` markers in the trailing args select the mode (see `_sanitize_args` in `kea_launcher.py`). Anything after `--` is appended to the Fastbot launcher.
- `--agent` is **deprecated and rejected** — native mode was removed. Do not reintroduce it.
- Reports are written to `output/` (or `-o DIR`). `kea2 report -p <dir>` regenerates from results; `kea2 merge -p <dir1> <dir2> -o <out>` merges multiple runs.

## Conventions & gotchas

- Logging: use `getLogger(__name__)` from `kea2/utils.py`, not `logging.getLogger` directly (except to quiet noisy third-party loggers). Debug level is controlled via `kea2 -d`.
- `kea2` scripts must stay Python-3.8-compatible in the shipped package even though the local `.python-version` is 3.11.
- Paths: use `getProjectRoot()` for the current Kea2 project; device-relative paths default under `/sdcard/.kea2`.
- Jars / `.so` libs in `kea2/assets/` and `fastbot_libs/` are binary artifacts — never hand-edit; update via the artifact workflow.
- The `output/` dir, `configs/`, `quicktest.py`, `*.xml`, `*.apk` are gitignored — don't commit generated artifacts.
- Docs are maintained bilingually (e.g. `docs/manual_en.md` + `docs/manual_cn.md`); when changing user-facing docs, update both. `README.md` ↔ `README_cn.md` likewise.

## Contribution workflow (agents must follow this)

### Code of conduct

- Be friendly and respectful; no personal attacks or discriminatory remarks.
- Stick to technical discussion — critique the code, not the person.
- Maintainers may close any issue/PR that violates the community atmosphere.

### Before starting

- **Large changes, new features, or uncertain approaches**: open an issue (or ask the user) to discuss first — this avoids sunk work on a wrong direction. Include: the problem to solve, the proposed approach, and whether you intend to implement and send a PR.
- **Direct PRs (no prior discussion) are fine for**: obvious bug fixes, doc typos/errors, small code cleanups or refactors that don't change external behavior.

### Development flow

1. Branch from the latest `main` — never develop directly on `main`, never base a branch on an old commit or on another dev branch (unless there's a real dependency, stated in the PR).
2. One branch = one concern. Don't mix unrelated changes in a single PR.
3. After `git push`, open a PR against the upstream `main` branch.

### Branch naming

- Bug fix: `fix/<short description>` (e.g. `fix/parser-crash-on-empty-input`)
- New feature: `feat/<short description>` (e.g. `feat/add-json-export`)
- Docs: `docs/<short description>` (e.g. `docs/update-install-guide`)
- Refactor: `refactor/<short description>` (e.g. `refactor/simplify-config-loader`)

### Commit message format

`<type>: <subject>`

- `type` ∈ `feat` (new feature) | `fix` (bug fix) | `docs` (docs) | `style` (formatting only, no logic change) | `refactor` (behavior unchanged) | `test` (tests) | `chore` (build/deps/tooling)
- `subject`: English, imperative present tense, lowercase first letter, no trailing period, ≤ 50 chars.
- Reference issues in the commit body: `Fixes #123`.
- Keep commits atomic — one commit, one logical change. (Note: end commit bodies with the `Co-Authored-By: Claude Code <noreply@anthropic.com>` trailer.)

### Pull request requirements

- Title follows the same format as a commit message (`<type>: <subject>`).
- Description must include:
  - **Background**: why this change is needed.
  - **What changed**: concrete changes made.
  - **Testing**: how you verified the change works (refer to the Testing section — the offline `unittest` suite must pass).
  - **Linked issues**: `Closes #xxx` or `Related to #xxx` where applicable.
- End PR bodies with the `🤖 Generated with [Claude Code](https://claude.com/claude-code)` trailer.

### Code review

- After a PR is opened, maintainers may request changes; respond on the same branch — the PR updates automatically as you push.
- If you can't respond in time, say so in a PR comment.
- Maintainers may push small direct edits (e.g. formatting) to your branch; keep it writable.
