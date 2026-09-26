import pytest
from capture_pages import allowed, ready, redact
from definition_samples import VALID

from tracewash.definitions import Broker

BROKER = Broker(**VALID)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.peoplesearch.example/Marisol-Quillfeather/OR", True),
        ("https://api.peoplesearch.example/v1/people", True),
        ("https://challenges.cloudflare.com/turnstile/v0/api.js", True),
        ("https://www.google.com/recaptcha/api.js", True),
        ("https://www.gstatic.com/recaptcha/releases/x/recaptcha__en.js", True),
        ("data:image/png;base64,AAAA", True),
        ("https://www.google.com/pagead/conversion", False),
        ("https://www.gstatic.com/other/script.js", False),
        ("https://bat.bing.com/action/0", False),
        ("https://notpeoplesearch.example/pixel", False),
    ],
)
def test_only_the_broker_and_bot_checks_are_reachable(url, expected):
    assert allowed(url, BROKER.domains) is expected


def test_a_page_with_results_is_ready():
    html = '<div class="result"><span class="name">Marisol Quillfeather</span></div>'

    assert ready(html, BROKER)


def test_a_no_results_page_is_ready():
    assert ready('<p class="no-results">Nothing</p>', BROKER)


def test_a_challenge_page_is_not_ready():
    assert not ready(
        "<title>Just a moment...</title><p>Checking your browser</p>", BROKER
    )


def test_errors_keep_the_reason_and_drop_the_url():
    message = (
        "Page.goto: net::ERR_HTTP2_PROTOCOL_ERROR at "
        "https://www.spokeo.com/Marisol-Quillfeather/Oregon/Quillmoor\n"
        'Call log:\n  - navigating to "https://www.spokeo.com/Marisol-Quillfeather"'
    )

    assert redact(message) == "net::ERR_HTTP2_PROTOCOL_ERROR at www.spokeo.com"
