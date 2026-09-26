"""Save each broker's two fixture searches from a visible browser.

Runs every search in Microsoft Edge under Playwright and saves the pages for
make_fixture.py. Only broker sites and bot-check providers are reachable, so
trackers never see the searched name. When a page needs you, such as a human
check or a search form, click "Save for tracewash" once the results show.
"""

import argparse
import sys
import time
from pathlib import Path
from string import Formatter
from urllib.parse import urlsplit

import yaml
from make_fixture import VALUES_PATH, load_fake_profile
from open_searches import SEARCH_FIELDS
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright

from tracewash.definitions import Broker, load_brokers
from tracewash.search import read_search_page, search_url

OUT_DIR = Path.home() / "tracewash-pages"
# Bot checks load from these hosts. Any other host outside the broker's
# domains could be a tracker, and the page URL holds the searched name.
BOT_CHECK_HOSTS = (
    "challenges.cloudflare.com",
    "hcaptcha.com",
    "captcha-delivery.com",
    "datadome.co",
)
RECAPTCHA_HOSTS = ("google.com", "gstatic.com", "recaptcha.net")
SETTLE_SECONDS = 20
WAIT_FOR_YOU_SECONDS = 600
OVERLAY = """() => {
  if (document.getElementById("tracewash-overlay")) return;
  const box = document.createElement("div");
  box.id = "tracewash-overlay";
  box.style.cssText = "position:fixed;top:12px;right:12px;z-index:2147483647;"
    + "display:flex;gap:8px;font:14px sans-serif";
  for (const [label, choice] of [["Save for tracewash", "save"], ["Skip", "skip"]]) {
    const button = document.createElement("button");
    button.textContent = label;
    button.style.cssText = "padding:8px 12px;border:1px solid #15181c;border-radius:6px;"
      + "background:" + (choice === "save" ? "#1f7a72;color:#fff" : "#fff;color:#15181c");
    button.onclick = () => window.tracewashChoice(choice);
    box.append(button);
  }
  document.documentElement.append(box);
}"""


def _on(host: str, domains) -> bool:
    return any(host == domain or host.endswith(f".{domain}") for domain in domains)


def allowed(url: str, domains) -> bool:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https", "ws", "wss"):
        return True
    host = parts.hostname or ""
    if _on(host, domains) or _on(host, BOT_CHECK_HOSTS):
        return True
    return _on(host, RECAPTCHA_HOSTS) and parts.path.startswith("/recaptcha")


def ready(html: str, broker: Broker) -> bool:
    page = read_search_page(html, broker.search)
    return bool(page.results) or page.no_results


def _content(page: Page) -> str | None:
    try:
        return page.content()
    except PlaywrightError:
        return None


def _save(page: Page, path: Path) -> str:
    try:
        page.wait_for_load_state("networkidle", timeout=5_000)
    except PlaywrightError:
        pass
    page.evaluate("document.getElementById('tracewash-overlay')?.remove()")
    path.write_text(page.content(), encoding="utf-8")
    return "saved"


def _capture(
    page: Page, broker: Broker, url: str, path: Path, hint: str, choices: list
) -> str:
    choices.clear()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    except PlaywrightError as error:
        # Playwright's messages quote the URL, which holds the searched name.
        return f"couldn't load the page ({type(error).__name__})"
    deadline, asked = time.monotonic() + SETTLE_SECONDS, False
    while True:
        if choices:
            return "skipped" if choices.pop() == "skip" else _save(page, path)
        html = _content(page)
        if html is not None and ready(html, broker):
            return _save(page, path)
        if time.monotonic() > deadline:
            if asked:
                return "timed out"
            print(
                f"  needs you: {hint} Then click Save for tracewash, or Skip.",
                flush=True,
            )
            deadline, asked = time.monotonic() + WAIT_FOR_YOU_SECONDS, True
        try:
            page.evaluate(OVERLAY)
        except PlaywrightError:
            pass
        page.wait_for_timeout(1_000)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("brokers", nargs="*", help="broker ids (default: every broker)")
    parser.add_argument("--values", type=Path, default=VALUES_PATH)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)
    real = yaml.safe_load(args.values.read_text(encoding="utf-8"))
    fake = load_fake_profile()
    fake_name = f"{fake['first_name']} {fake['last_name']} in {fake['state_name']}"
    searches = (
        ("listing", real, "Search for yourself there."),
        ("no-results", fake, f"Search for {fake_name} there."),
    )
    args.out.mkdir(exist_ok=True)
    current: dict = {"domains": ()}
    blocked: dict[str, set[str]] = {}
    choices: list[str] = []

    def route(route):
        if allowed(route.request.url, current["domains"]):
            route.continue_()
        else:
            blocked.setdefault(current["id"], set()).add(
                urlsplit(route.request.url).hostname
            )
            route.abort()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=False)
        context = browser.new_context(service_workers="block")
        context.route("**/*", route)
        context.expose_function(
            "tracewashChoice", lambda choice: choices.append(choice)
        )
        page = context.new_page()
        for broker in load_brokers():
            if args.brokers and broker.id not in args.brokers:
                continue
            current.update(id=broker.id, domains=broker.domains)
            form_only = not any(
                field for _, field, _, _ in Formatter().parse(broker.search.url)
            )
            for kind, profile, form_hint in searches:
                print(f"{broker.id} {kind}:", flush=True)
                values = {
                    field: str(profile[field])
                    for field in SEARCH_FIELDS
                    if profile.get(field)
                }
                try:
                    url = search_url(broker.search, values)
                except ValueError as error:
                    print(f"  {error}, so skipped", flush=True)
                    continue
                hint = (
                    form_hint
                    if form_only
                    else "Clear any check or question until results show."
                )
                path = args.out / f"{broker.id}-{kind}.html"
                try:
                    outcome = _capture(page, broker, url, path, hint, choices)
                except PlaywrightError as error:
                    if page.is_closed() or not browser.is_connected():
                        print("  stopped: the browser window closed")
                        return
                    outcome = f"failed ({type(error).__name__})"
                print(f"  {outcome}", flush=True)
        browser.close()
    for broker_id, hosts in sorted(blocked.items()):
        print(
            f"{broker_id}: blocked {len(hosts)} other hosts: {', '.join(sorted(hosts))}"
        )
    print(f"Next: uv run scripts/make_fixture.py --folder {args.out}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001
        # Tracebacks from Playwright quote page URLs, which hold the searched
        # name, so only the error's type is shown.
        sys.exit(f"capture_pages stopped ({type(error).__name__})")
