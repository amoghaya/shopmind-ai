from tests.conftest import make_client


def test_sandbox_product_search_and_cart_flow():
    with make_client() as client:
        session = client.post(
            "/api/v1/sandbox/sessions",
            json={"session_id": "test-session-1", "user_id": "user-1", "device_type": "desktop", "region": "IN"},
        )
        assert session.status_code == 200

        search = client.post(
            "/api/v1/sandbox/products/search",
            json={"query": "laptop", "in_stock_only": True},
        )
        assert search.status_code == 200
        products = search.json()
        assert products

        cart = client.post(
            "/api/v1/sandbox/cart/items",
            json={"session_id": "test-session-1", "product_id": products[0]["id"], "quantity": 1},
        )
        assert cart.status_code == 200
        assert cart.json()["items"][0]["quantity"] == 1


def test_checkout_requires_approval_but_is_reproducible():
    with make_client() as client:
        pending = client.post(
            "/api/v1/sandbox/checkout",
            json={
                "session_id": "sandbox-demo",
                "shipping_name": "Demo User",
                "shipping_address": "Delhi",
                "payment_method": "sandbox_upi",
                "approved": False,
            },
        )
        assert pending.status_code == 200
        assert pending.json()["status"] == "awaiting_approval"


def test_checkout_decrements_inventory_and_clears_cart():
    with make_client() as client:
        session = client.post(
            "/api/v1/sandbox/sessions",
            json={"session_id": "test-session-2", "user_id": "user-2", "device_type": "desktop", "region": "IN"},
        )
        assert session.status_code == 200

        search = client.post("/api/v1/sandbox/products/search", json={"query": "Nothing", "in_stock_only": True})
        product = search.json()[0]
        before_inventory = product["inventory_count"]

        client.post(
            "/api/v1/sandbox/cart/items",
            json={"session_id": "test-session-2", "product_id": product["id"], "quantity": 1},
        )
        checkout = client.post(
            "/api/v1/sandbox/checkout",
            json={
                "session_id": "test-session-2",
                "shipping_name": "Demo User",
                "shipping_address": "Delhi",
                "payment_method": "sandbox_upi",
                "approved": True,
            },
        )
        assert checkout.status_code == 200
        assert checkout.json()["status"] == "confirmed"
        assert checkout.json()["remaining_inventory"][str(product["id"])] == before_inventory - 1

        cart = client.get("/api/v1/sandbox/cart/test-session-2")
        assert cart.status_code == 200
        assert cart.json()["items"] == []
