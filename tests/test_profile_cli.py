import pytest

from tracewash import paths, profile
from tracewash.vault import Vault

PASSPHRASE = "correct horse battery staple"


def init_input(fake, passphrase=PASSPHRASE):
    lines = [
        passphrase,
        passphrase,
        fake["first_name"],
        "",
        fake["last_name"],
        "",
        fake["email"],
        fake["phone"],
        fake["street"],
        fake["city"],
        fake["state"],
        "97000",
        "n",
        str(fake["birth_year"]),
    ]
    return "\n".join(lines) + "\n"


@pytest.fixture
def initialized(cli, canary_profile):
    result = cli("init", input=init_input(canary_profile))
    assert result.exit_code == 0
    return result


def stored_profile():
    return profile.load(Vault.unlock(paths.vault_dir(), PASSPHRASE))


def test_init_stores_the_profile_in_the_vault(initialized, canary_profile):
    stored = stored_profile()

    assert (stored.first_name, stored.last_name) == ("Marisol", "Quillfeather")
    assert stored.emails == [canary_profile["email"]]
    assert stored.phones == [canary_profile["phone"]]
    [address] = stored.addresses
    assert (address.street, address.city, address.state) == (
        canary_profile["street"],
        "Quillmoor",
        "OR",
    )
    assert stored.birth_year == 1985


def test_init_reports_counts_and_never_values(initialized):
    assert "1 email, 1 phone number, 1 address and a birth year" in initialized.stdout


def test_init_warns_that_a_lost_passphrase_cannot_be_recovered(initialized):
    assert "can't be recovered" in initialized.stdout


def test_init_asks_again_for_a_short_passphrase(cli, canary_profile):
    result = cli("init", input="too short\n" + init_input(canary_profile))

    assert result.exit_code == 0
    assert "at least 12 characters" in result.stdout


def test_init_refuses_to_replace_an_existing_vault(initialized, cli, canary_profile):
    result = cli("init", input=init_input(canary_profile))

    assert result.exit_code == 1
    assert "already" in result.stderr


def test_profile_show_gives_counts(initialized, cli):
    result = cli("profile", "show", input=PASSPHRASE + "\n")

    assert result.exit_code == 0
    assert "1 email, 1 phone number, 1 address and a birth year" in result.stdout


def test_a_wrong_passphrase_is_refused(initialized, cli):
    result = cli("profile", "show", input="not the passphrase\n")

    assert result.exit_code == 1
    assert "wrong" in result.stderr


def test_profile_edit_keeps_what_you_skip_and_changes_what_you_type(initialized, cli):
    answers = [PASSPHRASE, "", "Q", "", "Marisol Wren", "", "", "n", ""]

    result = cli("profile", "edit", input="\n".join(answers) + "\n")

    assert result.exit_code == 0
    stored = stored_profile()
    assert (stored.first_name, stored.middle_name, stored.last_name) == (
        "Marisol",
        "Q",
        "Quillfeather",
    )
    assert stored.other_names == ["Marisol Wren"]
    assert len(stored.addresses) == 1


def test_passphrase_changes_the_passphrase(initialized, cli):
    new = "a brand new passphrase"

    result = cli("passphrase", input=f"{PASSPHRASE}\n{new}\n{new}\n")

    assert result.exit_code == 0
    Vault.unlock(paths.vault_dir(), new)
