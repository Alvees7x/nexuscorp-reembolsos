from datetime import date
from itertools import count

_n = count(1)


def payload(**over):
    base = {"category": "transporte", "amount": "180.00", "expense_date": date.today().isoformat(),
            "justification": "Deslocamento para cliente", "receipt_ref": f"NF-{next(_n):05d}"}
    base.update(over)
    return base


def create(client, headers, **over):
    r = client.post("/expenses", json=payload(**over), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def create_and_submit(client, headers, **over):
    e = create(client, headers, **over)
    r = client.post(f"/expenses/{e['id']}/submit", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()
