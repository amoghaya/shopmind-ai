import csv
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from backend.db.models import (
    BenchmarkTask,
    Cart,
    Product,
    ProductReview,
    RecommendationSlot,
    ShopSession,
)


SEED_PRODUCTS = [
    {
        "sku": "LAP-1001",
        "name": "Lenovo IdeaPad Slim 5",
        "category": "laptop",
        "brand": "Lenovo",
        "price": 58999,
        "currency": "INR",
        "rating_avg": 4.5,
        "inventory_count": 18,
        "description": "Ryzen laptop with 16GB RAM for productivity and study workflows.",
        "tags": ["16gb", "student", "ssd", "productivity"],
    },
    {
        "sku": "LAP-1002",
        "name": "HP Pavilion 14",
        "category": "laptop",
        "brand": "HP",
        "price": 61499,
        "currency": "INR",
        "rating_avg": 4.3,
        "inventory_count": 12,
        "description": "Portable laptop with FHD display and balanced battery life.",
        "tags": ["portable", "ssd", "office"],
    },
    {
        "sku": "PHN-2001",
        "name": "Samsung Galaxy M55",
        "category": "phone",
        "brand": "Samsung",
        "price": 31999,
        "currency": "INR",
        "rating_avg": 4.4,
        "inventory_count": 35,
        "description": "Mid-premium phone with AMOLED display and solid battery backup.",
        "tags": ["amoled", "battery", "camera"],
    },
    {
        "sku": "HOM-3001",
        "name": "Philips Air Fryer NA231",
        "category": "home",
        "brand": "Philips",
        "price": 7999,
        "currency": "INR",
        "rating_avg": 4.2,
        "inventory_count": 21,
        "description": "Compact air fryer for healthy home cooking.",
        "tags": ["kitchen", "healthy", "compact"],
    },
    {
        "sku": "FAS-4001",
        "name": "Adidas RunFalcon Shoes",
        "category": "fashion",
        "brand": "Adidas",
        "price": 3499,
        "currency": "INR",
        "rating_avg": 4.1,
        "inventory_count": 40,
        "description": "Daily running shoes with lightweight cushioning.",
        "tags": ["running", "sport", "lightweight"],
    },
    {
        "sku": "LAP-1003",
        "name": "ASUS Vivobook 15 OLED",
        "category": "laptop",
        "brand": "ASUS",
        "price": 55999,
        "currency": "INR",
        "rating_avg": 4.6,
        "inventory_count": 14,
        "description": "OLED productivity laptop with strong display and 16GB RAM.",
        "tags": ["oled", "16gb", "creator", "student"],
    },
    {
        "sku": "PHN-2002",
        "name": "Nothing Phone 2a",
        "category": "phone",
        "brand": "Nothing",
        "price": 27999,
        "currency": "INR",
        "rating_avg": 4.5,
        "inventory_count": 28,
        "description": "Clean Android phone with balanced camera and battery.",
        "tags": ["android", "clean-ui", "camera"],
    },
    {
        "sku": "HOM-3002",
        "name": "Prestige Induction Cooktop",
        "category": "home",
        "brand": "Prestige",
        "price": 2899,
        "currency": "INR",
        "rating_avg": 4.0,
        "inventory_count": 31,
        "description": "Reliable induction cooktop for compact kitchens and hostels.",
        "tags": ["hostel", "kitchen", "compact"],
    },
    {
        "sku": "FAS-4002",
        "name": "Nike Revolution 7",
        "category": "fashion",
        "brand": "Nike",
        "price": 4299,
        "currency": "INR",
        "rating_avg": 4.3,
        "inventory_count": 26,
        "description": "Versatile running shoe with comfort cushioning.",
        "tags": ["running", "nike", "sport"],
    },
    {
        "sku": "ACC-5001",
        "name": "Sony WH-CH720N",
        "category": "audio",
        "brand": "Sony",
        "price": 8999,
        "currency": "INR",
        "rating_avg": 4.4,
        "inventory_count": 22,
        "description": "Wireless noise-cancelling headphones for travel and study.",
        "tags": ["wireless", "noise-cancelling", "audio"],
    },
]

LEGACY_CSV_PATH = Path(__file__).resolve().parents[2] / "ai-shopping-avatar" / "data" / "products.csv"


SEED_REVIEWS = [
    ("LAP-1001", "u100", 5, "Excellent for students", "Fast boot, smooth multitasking, and reliable battery."),
    ("LAP-1001", "u101", 4, "Value for money", "Good keyboard and performance under the price cap."),
    ("PHN-2001", "u200", 4, "Strong display", "Good balance of performance and battery."),
    ("PHN-2002", "u201", 5, "Very polished", "Smooth interface and dependable everyday performance."),
    ("HOM-3001", "u300", 5, "Very useful", "Easy to clean and works well for quick meals."),
    ("ACC-5001", "u500", 4, "Great ANC for the price", "Comfortable and strong battery backup."),
]


SEED_BENCHMARK_TASKS = [
    {
        "task_id": "bench-laptop-budget-1",
        "objective": "Find a laptop with 16GB RAM under Rs. 60,000 and add it to cart.",
        "category": "laptop",
        "budget_max": 60000,
        "required_filters": {"category": "laptop", "max_price": 60000},
        "success_criteria": {"add_to_cart": True, "budget_respected": True},
    },
    {
        "task_id": "bench-phone-rating-1",
        "objective": "Search for a phone above 4.3 rating and complete checkout with approval.",
        "category": "phone",
        "budget_max": 40000,
        "required_filters": {"category": "phone", "min_rating": 4.3},
        "success_criteria": {"checkout_complete": True},
    },
]


def seed_mock_shop(db: Session) -> None:
    existing = {product.sku: product for product in db.query(Product).all()}
    products = []
    combined_products = SEED_PRODUCTS + _load_legacy_catalog()
    for product in combined_products:
        if product["sku"] in existing:
            products.append(existing[product["sku"]])
            continue
        created = Product(**product)
        db.add(created)
        products.append(created)
    db.flush()

    sku_to_id = {product.sku: product.id for product in products}
    existing_review_keys = {
        (review.product_id, review.user_id, review.title)
        for review in db.query(ProductReview).all()
    }
    reviews = []
    for sku, user_id, rating, title, body in SEED_REVIEWS:
        key = (sku_to_id[sku], user_id, title)
        if key in existing_review_keys:
            continue
        reviews.append(
            ProductReview(
                product_id=sku_to_id[sku],
                user_id=user_id,
                rating=rating,
                title=title,
                body=body,
                created_at=datetime.utcnow() - timedelta(days=rating),
            )
        )
    db.add_all(reviews)

    existing_slots = {slot.slot_key for slot in db.query(RecommendationSlot).all()}
    slots = [
        RecommendationSlot(slot_key="home.hero", product_ids=[products[0].id, products[2].id, products[5].id], strategy="editorial"),
        RecommendationSlot(slot_key="search.sidebar", product_ids=[products[0].id, products[1].id, products[6].id], strategy="hnb_live"),
    ]
    db.add_all([slot for slot in slots if slot.slot_key not in existing_slots])

    existing_tasks = {task.task_id for task in db.query(BenchmarkTask).all()}
    tasks = [BenchmarkTask(**task) for task in SEED_BENCHMARK_TASKS if task["task_id"] not in existing_tasks]
    db.add_all(tasks)

    if db.query(ShopSession).filter_by(session_id="sandbox-demo").one_or_none() is None:
        db.add(ShopSession(session_id="sandbox-demo", user_id="demo-user", device_type="desktop", region="IN"))
    if db.query(Cart).filter_by(session_id="sandbox-demo").one_or_none() is None:
        db.add(Cart(session_id="sandbox-demo", currency="INR"))
    db.commit()


def _load_legacy_catalog() -> list[dict]:
    if not LEGACY_CSV_PATH.exists():
        return []

    products = []
    with LEGACY_CSV_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader):
            normalized_category = _normalize_category(row)
            price = float(row["price"])
            rating = float(row["rating"])
            tags = [tag.strip().lower() for tag in row["tags"].split(",") if tag.strip()]
            products.append(
                {
                    "sku": f"LEG-{int(row['id']):04d}",
                    "name": row["name"],
                    "category": normalized_category,
                    "brand": row["brand"],
                    "price": price,
                    "currency": "INR",
                    "rating_avg": rating,
                    "inventory_count": 8 + (idx % 23),
                    "description": _make_description(row["name"], normalized_category, tags),
                    "tags": tags[:6],
                }
            )
    return products


def _normalize_category(row: dict) -> str:
    raw = row["category"].strip().lower()
    name = row["name"].lower()
    tags = row["tags"].lower()
    token_blob = f"{name} {tags}"
    if raw == "electronics":
        if "laptop" in token_blob:
            return "laptop"
        if "smartphone" in token_blob or "phone" in token_blob:
            return "phone"
        return "audio"
    if raw in {"fashion", "footwear"}:
        return "fashion"
    if raw in {"home", "furniture"}:
        return "home"
    if raw == "sports":
        return "sports"
    if raw == "books & media":
        return "books"
    return raw.replace(" ", "-")


def _make_description(name: str, category: str, tags: list[str]) -> str:
    tag_phrase = ", ".join(tags[:3]) if tags else category
    return f"{name} in the {category} collection with features centered around {tag_phrase}."
