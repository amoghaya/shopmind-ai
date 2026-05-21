from datetime import datetime

from pydantic import BaseModel, Field


class ProductFilterRequest(BaseModel):
    query: str | None = None
    category: str | None = None
    brand: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_rating: float | None = None
    in_stock_only: bool = True
    sort_by: str = "relevance"


class ReviewRead(BaseModel):
    id: int
    user_id: str
    rating: int
    title: str
    body: str
    created_at: datetime


class ProductRead(BaseModel):
    id: int
    sku: str
    name: str
    category: str
    brand: str
    price: float
    currency: str
    rating_avg: float
    inventory_count: int
    description: str
    tags: list[str] = Field(default_factory=list)


class ProductDetail(ProductRead):
    reviews: list[ReviewRead] = Field(default_factory=list)


class PricePointRead(BaseModel):
    observed_on: datetime
    price: float


class PriceTrackerRead(BaseModel):
    product_id: int
    current_price: float
    min_price: float
    max_price: float
    avg_price: float
    drop_percent: float
    history: list[PricePointRead] = Field(default_factory=list)


class CartItemCreate(BaseModel):
    session_id: str
    product_id: int
    quantity: int = 1


class CartItemRead(BaseModel):
    product_id: int
    sku: str
    name: str
    quantity: int
    unit_price: float
    line_total: float


class CartRead(BaseModel):
    session_id: str
    items: list[CartItemRead]
    subtotal: float
    currency: str


class CheckoutRequest(BaseModel):
    session_id: str
    shipping_name: str
    shipping_address: str
    payment_method: str
    approved: bool = False


class CheckoutRead(BaseModel):
    order_id: str
    session_id: str
    status: str
    total: float
    currency: str
    remaining_inventory: dict[int, int] = Field(default_factory=dict)


class SessionCreate(BaseModel):
    session_id: str
    user_id: str
    device_type: str = "desktop"
    region: str = "IN"


class SessionRead(SessionCreate):
    pass


class RecommendationSlotRead(BaseModel):
    slot_key: str
    products: list[ProductRead]
    strategy: str


class BenchmarkTaskRead(BaseModel):
    task_id: str
    objective: str
    category: str
    budget_max: float
    required_filters: dict
    success_criteria: dict
