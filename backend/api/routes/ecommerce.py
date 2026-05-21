from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import db_session
from backend.schemas.ecommerce import (
    BenchmarkTaskRead,
    CartItemCreate,
    CartRead,
    CheckoutRead,
    CheckoutRequest,
    ProductDetail,
    ProductFilterRequest,
    ProductRead,
    PriceTrackerRead,
    RecommendationSlotRead,
    SessionCreate,
    SessionRead,
)
from backend.services.ecommerce import (
    add_to_cart,
    checkout,
    create_session,
    get_session,
    get_cart,
    get_product_detail,
    list_benchmark_tasks,
    list_slots,
    search_products,
)
from backend.services.price_tracker import price_tracker_agent

router = APIRouter(prefix="/sandbox", tags=["sandbox-ecommerce"])


@router.post("/sessions")
def create_shop_session(payload: SessionCreate, db: Session = Depends(db_session)):
    session = create_session(db, payload)
    return {"session_id": session.session_id, "user_id": session.user_id, "device_type": session.device_type}


@router.get("/sessions/{session_id}", response_model=SessionRead)
def fetch_shop_session(session_id: str, db: Session = Depends(db_session)):
    session = get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session


@router.post("/products/search", response_model=list[ProductRead])
def search_catalog(payload: ProductFilterRequest, db: Session = Depends(db_session)):
    return search_products(db, payload)


@router.get("/products/{product_id}", response_model=ProductDetail)
def product_detail(product_id: int, db: Session = Depends(db_session)):
    detail = get_product_detail(db, product_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="product not found")
    return detail


@router.get("/products/{product_id}/price-history", response_model=PriceTrackerRead)
def product_price_history(product_id: int, db: Session = Depends(db_session)):
    return price_tracker_agent.get_product_history(db, product_id)


@router.post("/cart/items", response_model=CartRead)
def add_cart_item(payload: CartItemCreate, db: Session = Depends(db_session)):
    try:
        return add_to_cart(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cart/{session_id}", response_model=CartRead)
def fetch_cart(session_id: str, db: Session = Depends(db_session)):
    return get_cart(db, session_id)


@router.post("/checkout", response_model=CheckoutRead)
def submit_checkout(payload: CheckoutRequest, db: Session = Depends(db_session)):
    return checkout(db, payload)


@router.get("/recommendation-slots", response_model=list[RecommendationSlotRead])
def recommendation_slots(db: Session = Depends(db_session)):
    return list_slots(db)


@router.get("/benchmark/tasks", response_model=list[BenchmarkTaskRead])
def benchmark_tasks(db: Session = Depends(db_session)):
    return list_benchmark_tasks(db)
