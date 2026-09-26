import copy

import yaml

VALID = {
    "id": "peoplesearch",
    "name": "People Search",
    "operator": "People Search, Inc.",
    "domains": ["peoplesearch.example"],
    "search": {
        "url": "https://www.peoplesearch.example/{first_name:slug}-{last_name:slug}/{state}",
        "result": "div.result",
        "name": ".name",
        "age": ".age",
        "location": ".location",
        "link": "a.profile",
        "no_results": ".no-results",
    },
    "optout": {
        "method": "form",
        "url": "https://www.peoplesearch.example/optout",
        "needs": ["listing_url", "email"],
        "confirm": "email",
    },
    "recheck_days": 30,
    "request_delay_seconds": 20,
}


def write_definition(tmp_path, data, stem=None):
    path = tmp_path / f"{stem or data['id']}.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def changed(path, value):
    data = copy.deepcopy(VALID)
    *parents, key = path.split(".")
    target = data
    for parent in parents:
        target = target[parent]
    if value is None:
        del target[key]
    else:
        target[key] = value
    return data
