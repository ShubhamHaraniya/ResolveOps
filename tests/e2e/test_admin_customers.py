"""Customers API (DB-backed) and the admin kill-switch endpoints."""

async def test_customers_list_and_detail_from_seeded_db(client_and_llm):
    client, _ = client_and_llm
    res = await client.get("/api/customers")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert body["total"] == len(body["customers"])
    first = body["customers"][0]
    assert {"id", "name", "plan", "contact_count", "ticket_count"} <= set(first)

    detail = await client.get(f"/api/customers/{first['id']}")
    assert detail.status_code == 200
    assert detail.json()["contact_count"] == len(detail.json()["contacts"])


async def test_customers_unknown_id_and_bad_plan(client_and_llm):
    client, _ = client_and_llm
    assert (await client.get("/api/customers/does-not-exist")).status_code == 404
    assert (await client.get("/api/customers", params={"plan": "bogus"})).status_code == 422


async def test_kill_switch_toggle_and_toggles(client_and_llm):
    client, _ = client_and_llm
    assert (await client.get("/api/admin/kill-switch")).json() == {"active": False}
    assert (await client.post("/api/admin/kill-switch", json={"active": True})).json() == {"active": True}
    assert (await client.get("/api/admin/kill-switch")).json() == {"active": True}

    from services.gateway import gateway
    assert gateway.kill_switch_active() is True

    assert (await client.post("/api/admin/kill-switch", json={"active": False})).json() == {"active": False}
    assert gateway.kill_switch_active() is False
