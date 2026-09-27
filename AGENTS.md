# AGENTS.md

These are the working rules for agents in this repo. tracewash is a local-first Python tool (a CLI plus a dashboard on localhost, Apache-2.0) that opts its owner out of US people-search sites and proves each removal with rescans and evidence.

## Sources of truth

- `README.md`: the pitch and the privacy contract.
- `ROADMAP.md`: decisions already made, the milestones, and what is out of scope. Check it before proposing features. Respect those decisions unless the owner reopens them.
- Work from the next unchecked item in `ROADMAP.md`. Don't build past the current milestone without asking.

## The privacy contract (hard rules)

The tool holds exactly the data it is meant to protect. Never break these rules, not even in dev tooling.

- **No real personal data anywhere.** That covers fixtures, tests, issues, commits, docs and logs. Before a saved broker page becomes a fixture, replace every name, address, phone number, age and relative with a fake profile. Use `example.com` emails and 555-01xx phone numbers.
- **Profile values stay in the vault.** They never go to SQLite, logs, exception messages or files outside the vault. The tracker and the logs use broker IDs, states, times and evidence IDs. Search URLs contain names, so they are evidence and belong in the vault. The canary guard must keep passing.
- **Never read the owner's fixture values or saved pages.** `.tracewash/fixture-values.yaml` and the raw pages the owner saves hold real data. The scripts read them and print only broker IDs, field names and statuses. Diagnose problems through the cleaned fixtures.
- **CLI tests use the `cli` fixture**, not `CliRunner` directly. `CliRunner` keeps output to itself, so the canary guard would never see it.
- **Network traffic goes only to broker sites.** No telemetry, analytics, crash reporting or update checks. The dashboard loads no remote assets: fonts, scripts and styles ship in the package.
- **The dashboard binds to 127.0.0.1 only.**
- **Never bypass a CAPTCHA.** No solving services, and no stealth plugins that hide automation. A CAPTCHA, login wall or ID check moves the broker to `action required`.
- **Only the vault's owner.** Don't add features for looking up other people.
- **Tests never touch live broker sites.** Use saved pages with fake data.

## Dashboard design gate

The owner brings the dashboard design. Don't write dashboard UI (templates, styles, layout or components) until that design is in `docs/design/`. When a task reaches UI work, stop and ask the owner for the design. Never fill the gap with a generic SaaS or Pi-hole look.

## Broker definitions

- One YAML file per broker, validated by the schema, at `src/tracewash/brokers/<id>.yaml`. A Python adapter is allowed only for a flow that YAML can't describe, and it sits next to its definition as `<id>.py`.
- Every URL in a definition must sit on one of its `domains`. Those domains are the only hosts tracewash may contact for that broker.
- Each definition has fixtures in `tests/fixtures/brokers/<id>/`: `listing.html` and `no-results.html`. Only `scripts/make_fixture.py` writes them, and `tests/test_broker_fixtures.py` rejects any page without its marker. Per-broker cleaning options live in `scripts/fixture-options.yaml`.
- Selectors must match what the cleaner keeps: tags, classes, ids without long digit runs, `role`, `itemprop`, `itemtype` and `data-test*` attributes, plus phrases listed under `keep`.
- The fake person is `tests/fixtures/fake-profile.yaml`. The canary guard and the cleaner both read it.
- DROP flags come from `src/tracewash/data/ca_registry.json`, refreshed with `scripts/import_ca_registry.py`.
- Only the transition table changes a broker's state. No LLM decides a state.
- Times are stored in UTC.

## Brand

- The assets are in `docs/brand/`. `-dark` files are for dark backgrounds.
- The wordmark is Bricolage Grotesque Bold, lowercase, converted to vector paths. Use the SVGs, and don't re-typeset the wordmark with a web font.

## Commands

- `uv sync` installs the package and the dev tools.
- `uv run tracewash status` runs the CLI from the checkout. Data lives in the user data folder; `TRACEWASH_HOME` points it elsewhere, and every test gets its own.
- `tracewash init` creates the vault, `tracewash profile show|edit` and `tracewash passphrase` manage it, and `tracewash track <broker> <event> [--evidence FILE]` and `tracewash timeline <broker>` work the tracker. Commands print counts, IDs and states, never profile values.
- `uv run pytest` runs the tests. The canary guard in `tests/canary_guard.py` checks every test.
- `uv run ruff check` and `uv run ruff format --check` run lint and the format check, as CI does.
- `uv run tracewash brokers list` shows the brokers, and `uv run tracewash brokers check` validates every definition.
- Fixtures: the owner runs `uv run scripts/open_searches.py <id>` and saves each tab with Ctrl+S into `~/tracewash-pages`, or tries `uv run scripts/capture_pages.py <id>`. Then `uv run scripts/make_fixture.py --folder ~/tracewash-pages` cleans them all.
- Release: set the version with `uv version <x.y.z>`, commit, and push a `v<x.y.z>` tag. The release workflow checks that the tag matches the version, builds, and publishes to PyPI.

## Working style

- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `ci:`, `build:`, `refactor:`). Keep each commit atomic, and use a scope when it adds clarity (`feat(brokers): …`).
- **No AI attribution** in commits or PRs. That means no `Co-Authored-By` trailers, no "Generated with" lines and no session links.
- **Checks:** automate acceptance checks instead of handing manual steps to the owner. Give every check that tests for an absence a positive control. For example, the canary guard must fail on a test that deliberately logs a canary value.
- **Validation:** evidence comes from dogfooding (the log) and public async signals (issues, PRs, installs). Don't plan interviews, recruiting or outreach.
- **Docs:** short and concise. Prefer editing `ROADMAP.md` over creating new planning documents.
- **Code comments:** explain why, not what. Only comment on what the code can't say for itself: a non-obvious constraint, a workaround and its cause, what a regex or selector is meant to match, or a line that keeps the privacy contract. Don't restate names or types, don't add boilerplate docstrings, and don't leave commented-out code or change notes.
- **Voice:** calm, short and declarative. No exclamation marks, no emoji. Never say a broker is "removed" unless a rescan proved it.
- Dates are written `2026.09.24` and times use the 24-hour clock.
- Local Playwright output goes to `.playwright-mcp/`, which git ignores.
