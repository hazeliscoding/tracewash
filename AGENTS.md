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
- **Network traffic goes only to broker sites.** No telemetry, analytics, crash reporting or update checks. The dashboard loads no remote assets: fonts, scripts and styles ship in the package.
- **The dashboard binds to 127.0.0.1 only.**
- **Never bypass a CAPTCHA.** No solving services, and no stealth plugins that hide automation. A CAPTCHA, login wall or ID check moves the broker to `action required`.
- **Only the vault's owner.** Don't add features for looking up other people.
- **Tests never touch live broker sites.** Use saved pages with fake data.

## Dashboard design gate

The owner brings the dashboard design. Don't write dashboard UI (templates, styles, layout or components) until that design is in `docs/design/`. When a task reaches UI work, stop and ask the owner for the design. Never fill the gap with a generic SaaS or Pi-hole look.

## Broker definitions

- One YAML file per broker, validated by the schema. A Python adapter is allowed only for a flow that YAML can't describe, and it sits next to its definition. M1 sets the folder layout. Record it here when it lands.
- Each definition has fixtures: a saved listing page and a saved no-results page, both with fake data.
- Only the transition table changes a broker's state. No LLM decides a state.
- Times are stored in UTC.

## Brand

- The assets are in `docs/brand/`. `-dark` files are for dark backgrounds.
- The wordmark is Bricolage Grotesque Bold, lowercase, converted to vector paths. Use the SVGs, and don't re-typeset the wordmark with a web font.

## Commands

Added in M0.

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
