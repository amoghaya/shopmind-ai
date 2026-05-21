from uuid import uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from backend.db.models import (
    BenchmarkTask,
    Cart,
    CartItem,
    Order,
    Product,
    ProductReview,
    RecommendationSlot,
    ShopSession,
)
from backend.schemas.ecommerce import (
    BenchmarkTaskRead,
    CartItemCreate,
    CartItemRead,
    CartRead,
    CheckoutRead,
    CheckoutRequest,
    ProductDetail,
    ProductFilterRequest,
    ProductRead,
    RecommendationSlotRead,
    ReviewRead,
    SessionCreate,
    SessionRead,
)


def create_session(db: Session, payload: SessionCreate) -> ShopSession:
    session, _ = _ensure_session_and_cart(
        db,
        payload.session_id,
        user_id=payload.user_id,
        device_type=payload.device_type,
        region=payload.region,
    )
    return session


def get_session(db: Session, session_id: str) -> SessionRead | None:
    session = db.query(ShopSession).filter_by(session_id=session_id).one_or_none()
    if session is None:
        return None
    return SessionRead(
        session_id=session.session_id,
        user_id=session.user_id,
        device_type=session.device_type,
        region=session.region,
    )


def search_products(db: Session, filters: ProductFilterRequest) -> list[ProductRead]:
    query = db.query(Product)
    predicates = []
    if filters.query:
        term = f"%{filters.query.lower()}%"
        predicates.append(
            func.lower(Product.name).like(term) |
            func.lower(Product.description).like(term) |
            func.lower(Product.brand).like(term)
        )
    if filters.category:
        predicates.append(Product.category == filters.category)
    if filters.brand:
        predicates.append(Product.brand == filters.brand)
    if filters.min_price is not None:
        predicates.append(Product.price >= filters.min_price)
    if filters.max_price is not None:
        predicates.append(Product.price <= filters.max_price)
    if filters.min_rating is not None:
        predicates.append(Product.rating_avg >= filters.min_rating)
    if filters.in_stock_only:
        predicates.append(Product.inventory_count > 0)
    if predicates:
        query = query.filter(and_(*predicates))

    if filters.sort_by == "price_asc":
        query = query.order_by(Product.price.asc())
    elif filters.sort_by == "price_desc":
        query = query.order_by(Product.price.desc())
    elif filters.sort_by == "rating":
        query = query.order_by(Product.rating_avg.desc())
    else:
        query = query.order_by(Product.rating_avg.desc(), Product.price.asc())

    products = query.all()
    return [ProductRead(**_product_to_dict(product)) for product in products]


def get_product_detail(db: Session, product_id: int) -> ProductDetail | None:
    product = (
        db.query(Product)
        .options(selectinload(Product.reviews))
        .filter(Product.id == product_id)
        .one_or_none()
    )
    if product is None:
        return None
    payload = _product_to_dict(product)
    payload["reviews"] = [ReviewRead(**_review_to_dict(review)) for review in product.reviews]
    return ProductDetail(**payload)


def add_to_cart(db: Session, payload: CartItemCreate) -> CartRead:
    _, cart = _ensure_session_and_cart(db, payload.session_id)
    product = db.query(Product).filter_by(id=payload.product_id).one()
    if product.inventory_count <= 0:
        raise ValueError("product out of stock")

    item = (
        db.query(CartItem)
        .filter_by(cart_id=cart.id, product_id=payload.product_id)
        .one_or_none()
    )
    if item is None:
        item = CartItem(
            cart_id=cart.id,
            product_id=payload.product_id,
            quantity=min(payload.quantity, product.inventory_count),
        )
        db.add(item)
    else:
        item.quantity = min(item.quantity + payload.quantity, product.inventory_count)
    db.commit()
    return get_cart(db, payload.session_id)


def get_cart(db: Session, session_id: str) -> CartRead:
    _, cart = _ensure_session_and_cart(db, session_id)
    cart = (
        db.query(Cart)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
        .filter_by(id=cart.id)
        .one()
    )
    items = []
    subtotal = 0.0
    for item in cart.items:
        line_total = item.quantity * item.product.price
        subtotal += line_total
        items.append(
            CartItemRead(
                product_id=item.product_id,
                sku=item.product.sku,
                name=item.product.name,
                quantity=item.quantity,
                unit_price=item.product.price,
                line_total=line_total,
            )
        )
    return CartRead(session_id=session_id, items=items, subtotal=subtotal, currency=cart.currency)


def checkout(db: Session, payload: CheckoutRequest) -> CheckoutRead:
    cart = get_cart(db, payload.session_id)
    if not payload.approved:
        return CheckoutRead(
            order_id="pending-approval",
            session_id=payload.session_id,
            status="awaiting_approval",
            total=cart.subtotal,
            currency=cart.currency,
            remaining_inventory={},
        )

    order = Order(
        order_id=f"ORD-{uuid4().hex[:10]}",
        session_id=payload.session_id,
        status="confirmed",
        total=cart.subtotal,
        currency=cart.currency,
        shipping_name=payload.shipping_name,
        shipping_address=payload.shipping_address,
        payment_method=payload.payment_method,
    )
    db.add(order)
    remaining_inventory: dict[int, int] = {}
    live_cart = (
        db.query(Cart)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
        .filter_by(session_id=payload.session_id)
        .one()
    )
    for item in live_cart.items:
        item.product.inventory_count = max(0, item.product.inventory_count - item.quantity)
        remaining_inventory[item.product_id] = item.product.inventory_count
    db.query(CartItem).filter_by(cart_id=live_cart.id).delete()
    db.commit()
    return CheckoutRead(
        order_id=order.order_id,
        session_id=payload.session_id,
        status=order.status,
        total=order.total,
        currency=order.currency,
        remaining_inventory=remaining_inventory,
    )


def _ensure_session_and_cart(
    db: Session,
    session_id: str,
    *,
    user_id: str = "demo-user",
    device_type: str = "desktop",
    region: str = "IN",
) -> tuple[ShopSession, Cart]:
    session = db.query(ShopSession).filter_by(session_id=session_id).one_or_none()
    created = False
    if session is None:
        session = ShopSession(session_id=session_id, user_id=user_id, device_type=device_type, region=region)
        db.add(session)
        created = True

    cart = db.query(Cart).filter_by(session_id=session_id).one_or_none()
    if cart is None:
        cart = Cart(session_id=session_id, currency="INR")
        db.add(cart)
        created = True

    if created:
        db.commit()
        db.refresh(session)
        db.refresh(cart)
    return session, cart


def list_slots(db: Session) -> list[RecommendationSlotRead]:
    slots = db.query(RecommendationSlot).all()
    products = {product.id: product for product in db.query(Product).all()}
    return [
        RecommendationSlotRead(
            slot_key=slot.slot_key,
            products=[ProductRead(**_product_to_dict(products[product_id])) for product_id in slot.product_ids if product_id in products],
            strategy=slot.strategy,
        )
        for slot in slots
    ]


def list_benchmark_tasks(db: Session) -> list[BenchmarkTaskRead]:
    tasks = db.query(BenchmarkTask).all()
    return [
        BenchmarkTaskRead(
            task_id=task.task_id,
            objective=task.objective,
            category=task.category,
            budget_max=task.budget_max,
            required_filters=task.required_filters,
            success_criteria=task.success_criteria,
        )
        for task in tasks
    ]


def _product_to_dict(product: Product) -> dict:
    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "category": product.category,
        "brand": product.brand,
        "price": product.price,
        "currency": product.currency,
        "rating_avg": product.rating_avg,
        "inventory_count": product.inventory_count,
        "description": product.description,
        "tags": product.tags or [],
    }


def _review_to_dict(review: ProductReview) -> dict:
    return {
        "id": review.id,
        "user_id": review.user_id,
        "rating": review.rating,
        "title": review.title,
        "body": review.body,
        "created_at": review.created_at,
    }
