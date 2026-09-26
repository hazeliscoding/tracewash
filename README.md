<h1>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/hazeliscoding/tracewash/main/docs/brand/lockup-dark.svg">
    <img alt="tracewash" src="https://raw.githubusercontent.com/hazeliscoding/tracewash/main/docs/brand/lockup.svg" height="44">
  </picture>
</h1>

**Removal you can prove.** tracewash opts you out of people-search sites, then keeps checking until your listing is gone, and keeps the evidence.

Sites like Spokeo and Whitepages publish your name, address, phone number and relatives. You can opt out, but a request is not a removal: forms fail silently, confirmation emails prove nothing, and listings come back months later. Sending the request is the easy part. What matters is whether the listing is gone and stays gone.

> **Status:** early development. `tracewash status` prints sample output, and nothing is tracked yet. See [ROADMAP.md](https://github.com/hazeliscoding/tracewash/blob/main/ROADMAP.md).

## What it will look like

The output below is planned. It is not real output yet.

```text
$ tracewash status
brokers         15 tracked, 4 covered by DROP
removed          6 proven by rescan
requested        5 next recheck 2026.10.09
action required  2 fastpeoplesearch: captcha, spokeo: confirm email
listed again     1 whitepages

$ tracewash timeline whitepages
2026.07.28 14:02  listed          evidence #14
2026.07.28 14:09  requested       guided form
2026.07.29 08:41  email confirmed
2026.08.12 09:00  removed         rescan found nothing, evidence #19
2026.09.20 09:00  listed again    rescan found the listing, evidence #27
```

## What it does

- **Finds** your listings on US people-search sites, using a profile that only you can unlock.
- **Opts you out** in a visible browser, with the form filled in from your profile, or writes the request email for you to send. You solve CAPTCHAs yourself. tracewash never bypasses them.
- **Proves it.** A broker is marked removed only when a rescan comes back empty. Every step is saved with evidence: a screenshot, the URL, the time and a hash.
- **Keeps checking.** Rechecks run on a schedule, and a listing that comes back reopens the broker.
- **Knows about DROP.** It flags the brokers that California's Delete Request and Opt-out Platform already covers, so California residents can let DROP do that part.

It comes as a CLI plus a dashboard served only on your own machine.

## The privacy contract

- **Local and encrypted.** Your profile and the evidence live in a vault on your machine, encrypted with your passphrase. The tracker and the logs never hold profile values, and a canary test enforces this in CI.
- **Talks only to brokers.** There are no accounts, no telemetry and no hosted service. The dashboard listens on 127.0.0.1 only.
- **For you only.** It searches for the person in the vault. It is not a people-search tool.
- **Open source**, so you can check all of this instead of trusting it.

## Contributing

Each broker is one YAML file plus saved-page fixtures with fake data. Adding a broker will be a good first contribution. A contributor guide arrives with v0.1.

## License

[Apache-2.0](https://github.com/hazeliscoding/tracewash/blob/main/LICENSE)
