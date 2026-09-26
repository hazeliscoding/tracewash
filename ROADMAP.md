# Roadmap

tracewash is a local-first Python tool, a CLI plus a dashboard on localhost, that opts its owner out of US people-search sites and proves each removal with rescans and evidence. This file tracks what gets built, in what order, and the decisions already made.

## Decisions (2026-09-25)

- **Name:** tracewash. The working name `nulltrace` was dropped because [4x3/nulltrace](https://github.com/4x3/nulltrace), a Go tool with the same pitch, already uses it.
- **Proof over requests.** The loop is find, request, recheck. A sent request is `requested`, never done. A broker becomes `removed` only when a rescan finds no listing. If a later rescan finds it, the broker becomes `listed again`.
- **Evidence** is saved for every finding and rescan: a screenshot, the URL, the UTC time and a SHA-256. Each timeline event links to its evidence.
- **Scope:** US people-search brokers, and opt-outs that work for any US resident. GDPR and UK requests come later.
- **DROP-aware.** California's Delete Request and Opt-out Platform only serves California residents. Brokers on the California data broker registry are flagged as covered by DROP, and California residents get a DROP step instead of a request per broker. Registry data comes from the public state registries.
- **Stack:**
  - Python 3.12+, uv, ruff and pytest.
  - Typer for the CLI; FastAPI + HTMX for the dashboard.
  - SQLite for the tracker.
  - Playwright for opt-out forms and rescans.
  - Pydantic to validate broker definitions.
- **Interface:** the CLI and the dashboard both ship in v0.1. The dashboard binds to 127.0.0.1 only.
- **The dashboard design comes from the owner.** No dashboard UI code (templates, styles or layout) until that design is in the repo. It must not look like a generic SaaS dashboard or Pi-hole.
- **Broker definitions** are declarative YAML, one file per broker. A Python adapter is allowed only for a flow that YAML can't describe. Definitions are maintained by the community.
- **The vault** holds the profile and the evidence, encrypted with a key derived from a passphrase. The SQLite tracker and all logs hold only broker IDs, states, times and evidence IDs, never profile values. A canary test fails if a profile value reaches the database, the logs or error output.
- **No CAPTCHA bypass**, no solving services and no stealth plugins. A CAPTCHA, login wall or ID check moves the broker to `action required` and opens a visible browser for the owner.
- **Deterministic states.** A table of transitions decides each broker's state. No LLM decides it.
- **Tests never touch live broker sites.** Search and opt-out flows run against saved pages with fake profiles.
- **License:** Apache-2.0.
- **Brand** is option C, "Struck": a listing card with a strike that runs through it and past its edges. The wordmark is Bricolage Grotesque Bold (optical size 48), lowercase, with -0.02em letter spacing, converted to vector paths. Ink is `#15181c` with a teal accent `#1f7a72`. The dark variants use `#ece9e1` and `#5cc2b5`. The assets are in `docs/brand/`.

## M0: Placeholder (as soon as possible)

- [ ] Scaffold the package with uv: `src/tracewash/`, a `tracewash` console script, ruff and pytest.
- [ ] `tracewash status` prints a canned sample: brokers by state, next rechecks and required actions. It uses no real data.
- [ ] CI on Linux and Windows runs ruff and pytest.
- [ ] Turn on the canary guard from the first commit: a pytest fixture with a fake profile fails any test in which a profile value reaches captured logs, stdout or stderr.

**Done when:** CI passes on a fresh clone, `uv run tracewash status` prints the sample, and a test that deliberately logs a canary value fails the canary guard.

## M1: Broker registry

- [ ] A definition schema in Pydantic that covers:
  - identity and domains;
  - search: the URL pattern, how to spot a listing, and how to tell there are no results;
  - opt-out: `form`, `email` or `manual`, plus the fields it needs and any email or phone confirmation;
  - recheck interval and rate limits.
- [ ] `tracewash brokers list` and `tracewash brokers check`, which validates every definition.
- [ ] Seed 10 to 15 brokers by hand. Each one comes with a saved listing page and a saved no-results page, with every personal detail replaced by fake data. Start with Spokeo, Whitepages, BeenVerified, TruePeopleSearch, FastPeopleSearch, Radaris, PeopleFinders, Intelius, MyLife, Nuwber, ThatsThem and USPhoneBook.
- [ ] DROP flags: import the California data broker registry and match it to definitions by domain. The import script and its matched output are committed.
- [ ] CI runs `tracewash brokers check`. As a positive control, an invalid definition must fail it.

**Done when:** `tracewash brokers list` shows every seeded broker with its opt-out method and DROP flag, and CI rejects a broken definition.

## M2: Vault and tracker

- [ ] `tracewash init` creates the vault. The profile holds names and aliases, emails, phone numbers, current and past addresses, and birth year. Choose the encryption library and key derivation, and record the choice here.
- [ ] Evidence store in the vault, with blobs addressed by SHA-256.
- [ ] Tracker in SQLite with a timeline of events per broker. The states are `not checked`, `listed`, `requested`, `action required`, `removed`, `no record`, `listed again` and `failed`. The transitions are a table with tests, and an invalid transition raises an error.
- [ ] CLI: `tracewash track <broker> <event>` for manual steps, `tracewash timeline <broker>`, and `tracewash status` on real data.
- [ ] The canary guard also scans the SQLite file's bytes.

**Done when:** one broker goes through a full manual cycle (listed, requested, removed) from the CLI, and the canary guard proves that the database and the logs hold no profile values.

## M3: Opt-out and proof loop

- [ ] Rescan: Playwright runs a definition's search for the vault's profile, decides between `listed` and `no record`, and saves the evidence.
- [ ] Guided opt-out: open the broker's form in a visible browser, fill in the fields the definition declares, and wait for the owner to finish. The submission is recorded as `requested`.
- [ ] Email opt-out: write the request (address, subject and body) for the owner to send from their own mailbox, and record it.
- [ ] A CAPTCHA, login wall or ID upload moves the broker to `action required`, with the reason.
- [ ] `tracewash recheck --due` runs every rescan that is due. When it finds the listing of a `removed` broker, that broker becomes `listed again`. Document how to run it from cron or Task Scheduler.
- [ ] One request at a time per broker, with the delays its definition declares.

**Done when:** against saved pages, a broker moves from listed to requested to removed on an empty rescan, then to listed again when the listing page returns, with evidence attached to each step.

## M4: Dashboard

- [ ] **Design first.** Stop and ask the owner for the dashboard design. Nothing below starts until it is in `docs/design/`.
- [ ] `tracewash serve` runs the FastAPI + HTMX app on 127.0.0.1 only. A test fails if it can bind to any other address.
- [ ] Status board, broker timelines with evidence, and the queue of required actions.
- [ ] Unlock the vault from the dashboard. It locks again after a period of inactivity.
- [ ] No remote assets. Fonts, scripts and styles are served from the package.

**Done when:** every CLI view has a dashboard view, and a test proves the server rejects any address other than loopback.

## M5: v0.1.0

- [ ] Fresh install works with `uv tool install tracewash` and `pipx install tracewash` on Windows, macOS and Linux.
- [ ] README quick start, the supported platforms, and screenshots of the real dashboard.
- [ ] `CONTRIBUTING.md`: how to add a broker (one YAML file plus fixtures), with a template.
- [ ] `SECURITY.md`, plus a privacy contract document that lists each promise and how it is enforced.
- [ ] Issue templates for "Add a broker" and "Broker flow changed". Both warn against posting personal data.
- [ ] A release workflow that publishes to PyPI with trusted publishing, then version 0.1.0.
- [ ] Dogfooding log in `docs/dogfooding.md`. Entries name brokers and states, never personal data.
- [ ] CI is green, error messages are understandable, and there are no known critical bugs.

**Done when:** CI installs the built wheel on all three platforms and runs the README quick start against saved-page brokers, and the dogfooding log shows at least one real broker removed with proof.

## Later

- Send request emails over SMTP, and sort broker replies from IMAP with deterministic rules.
- GDPR and UK erasure requests.
- Household profiles, with each person's consent.
- A nightly workflow that loads each broker's public search and opt-out pages, with no personal data, and opens an issue when a definition no longer matches.
- A Docker image and a background scheduler for always-on machines.
- Record DROP submissions and their 45-day processing windows.
- More brokers, as good first issues.
- Import from open opt-out lists where their licenses allow.

## Not planned

- CAPTCHA solving, or hiding automation from bot detection.
- Looking up anyone other than the vault's owner.
- Accounts, sync, telemetry or a hosted service.
- Bulk email to hundreds of brokers at once. [eraser](https://github.com/digisamroc/eraser) does this. tracewash follows each broker until there is proof.
- Password and breach checks.

## How we'll know it works

Evidence comes from dogfooding (n=1, recorded in the log): how many brokers reach `removed` with rescan proof, and how many come back as `listed again`. After release it also comes from public signals: broker issues, broker PRs and installs.
