"""The list-endpoint pagination/search/sort contract shared by products, recipes, and batches
(app/core/pagination.py). Exercised once against /products; the other two resources wire the same
helper the same way, so this is the meaningful coverage rather than a 3x repeat."""

from tests.conftest import auth_headers, idem, login


async def _create_product(client, token, site_id, code, name):
    resp = await client.post(
        "/products",
        json={"idempotency_key": idem(), "site_id": str(site_id), "code": code, "name": name},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def test_pagination_envelope_and_page_size(client, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    for i in range(5):
        await _create_product(client, op_token, site_id, f"P{i}", f"Product {i}")

    resp = await client.get("/products?page=1&page_size=2", headers=auth_headers(op_token))
    body = resp.json()
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total_pages"] == 3
    assert len(body["items"]) == 2

    resp2 = await client.get("/products?page=2&page_size=2", headers=auth_headers(op_token))
    body2 = resp2.json()
    assert len(body2["items"]) == 2
    assert {i["id"] for i in body["items"]}.isdisjoint({i["id"] for i in body2["items"]})


async def test_search_filters_by_code_and_name(client, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    await _create_product(client, op_token, site_id, "TAB-1", "Amoxicillin Tablet")
    await _create_product(client, op_token, site_id, "CAP-1", "Ibuprofen Capsule")

    resp = await client.get("/products?q=amoxi", headers=auth_headers(op_token))
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["code"] == "TAB-1"

    resp2 = await client.get("/products?q=CAP-1", headers=auth_headers(op_token))
    body2 = resp2.json()
    assert body2["total"] == 1
    assert body2["items"][0]["name"] == "Ibuprofen Capsule"


async def test_sort_by_code_ascending_and_descending(client, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    await _create_product(client, op_token, site_id, "B-CODE", "B")
    await _create_product(client, op_token, site_id, "A-CODE", "A")
    await _create_product(client, op_token, site_id, "C-CODE", "C")

    resp = await client.get("/products?sort_by=code&sort_dir=asc", headers=auth_headers(op_token))
    codes = [i["code"] for i in resp.json()["items"]]
    assert codes == sorted(codes)

    resp_desc = await client.get("/products?sort_by=code&sort_dir=desc", headers=auth_headers(op_token))
    codes_desc = [i["code"] for i in resp_desc.json()["items"]]
    assert codes_desc == sorted(codes_desc, reverse=True)
