from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class UserPreferenceProfile(Base):
    __tablename__ = "user_preference_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, unique=True)
    context_features: Mapped[dict] = mapped_column(JSON, default=dict)
    preference_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RecommendationEvent(Base):
    __tablename__ = "recommendation_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    request_id: Mapped[str] = mapped_column(String(128), index=True)
    strategy: Mapped[str] = mapped_column(String(64))
    selected_item_id: Mapped[str] = mapped_column(String(128))
    reward: Mapped[float | None] = mapped_column(Float, nullable=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    top_k: Mapped[list] = mapped_column(JSON, default=list)
    selected_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    regret: Mapped[float | None] = mapped_column(Float, nullable=True)
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    failure_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    brand: Mapped[str] = mapped_column(String(64), index=True)
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    rating_avg: Mapped[float] = mapped_column(Float, default=0.0)
    inventory_count: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    reviews: Mapped[list["ProductReview"]] = relationship(back_populates="product")


class ProductReview(Base):
    __tablename__ = "product_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    product: Mapped["Product"] = relationship(back_populates="reviews")


class ProductPricePoint(Base):
    __tablename__ = "product_price_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    observed_on: Mapped[datetime] = mapped_column(DateTime, index=True)
    price: Mapped[float] = mapped_column(Float)


class ShopSession(Base):
    __tablename__ = "shop_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    device_type: Mapped[str] = mapped_column(String(32))
    region: Mapped[str] = mapped_column(String(16), default="IN")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    items: Mapped[list["CartItem"]] = relationship(back_populates="cart")


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    cart: Mapped["Cart"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    session_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    total: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    shipping_name: Mapped[str] = mapped_column(String(255))
    shipping_address: Mapped[str] = mapped_column(Text)
    payment_method: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RecommendationSlot(Base):
    __tablename__ = "recommendation_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slot_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    product_ids: Mapped[list] = mapped_column(JSON, default=list)
    strategy: Mapped[str] = mapped_column(String(64))


class BenchmarkTask(Base):
    __tablename__ = "benchmark_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    objective: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64), index=True)
    budget_max: Mapped[float] = mapped_column(Float)
    required_filters: Mapped[dict] = mapped_column(JSON, default=dict)
    success_criteria: Mapped[dict] = mapped_column(JSON, default=dict)


class BanditArmState(Base):
    __tablename__ = "bandit_arm_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), unique=True, index=True)
    pulls: Mapped[int] = mapped_column(Integer, default=0)
    successes: Mapped[int] = mapped_column(Integer, default=0)
    cumulative_reward: Mapped[float] = mapped_column(Float, default=0.0)
    epsilon_value: Mapped[float] = mapped_column(Float, default=0.5)
    linucb_a: Mapped[list] = mapped_column(JSON, default=list)
    linucb_b: Mapped[list] = mapped_column(JSON, default=list)
    ts_alpha: Mapped[float] = mapped_column(Float, default=1.0)
    ts_beta: Mapped[float] = mapped_column(Float, default=1.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RecommenderState(Base):
    __tablename__ = "recommender_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    weights: Mapped[dict] = mapped_column(JSON, default=dict)
    bias: Mapped[float] = mapped_column(Float, default=0.0)
    cumulative_regret: Mapped[float] = mapped_column(Float, default=0.0)
    total_feedback: Mapped[int] = mapped_column(Integer, default=0)
    successful_feedback: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExecutionRun(Base):
    __tablename__ = "execution_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    session_id: Mapped[str] = mapped_column(String(128), index=True)
    executor_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    intent: Mapped[dict] = mapped_column(JSON, default=dict)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    screenshot_paths: Mapped[list] = mapped_column(JSON, default=list)
    failure_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
