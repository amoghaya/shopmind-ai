import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.db.models import Product, ProductPricePoint
from backend.schemas.ecommerce import PricePointRead, PriceTrackerRead


class PriceTrackerAgent:
    history_days = 30

    def ensure_price_history(self, db: Session, product: Product) -> None:
        existing = db.query(ProductPricePoint).filter_by(product_id=product.id).count()
        if existing >= self.history_days:
            return

        db.query(ProductPricePoint).filter_by(product_id=product.id).delete()
        points = []
        for day_offset in range(self.history_days, 0, -1):
            observed_on = datetime.utcnow() - timedelta(days=day_offset)
            points.append(
                ProductPricePoint(
                    product_id=product.id,
                    observed_on=observed_on,
                    price=self._fluctuate(product.price, product.id, day_offset),
                )
            )
        points.append(
            ProductPricePoint(
                product_id=product.id,
                observed_on=datetime.utcnow(),
                price=product.price,
            )
        )
        db.add_all(points)
        db.commit()

    def get_product_history(self, db: Session, product_id: int) -> PriceTrackerRead:
        product = db.query(Product).filter_by(id=product_id).one()
        self.ensure_price_history(db, product)
        history = (
            db.query(ProductPricePoint)
            .filter_by(product_id=product_id)
            .order_by(ProductPricePoint.observed_on.asc())
            .all()
        )
        prices = [point.price for point in history]
        current_price = prices[-1]
        avg_price = round(sum(prices) / len(prices), 2)
        drop_percent = round(((avg_price - current_price) / avg_price) * 100, 2) if avg_price else 0.0
        return PriceTrackerRead(
            product_id=product_id,
            current_price=current_price,
            min_price=min(prices),
            max_price=max(prices),
            avg_price=avg_price,
            drop_percent=drop_percent,
            history=[
                PricePointRead(observed_on=point.observed_on, price=point.price)
                for point in history
            ],
        )

    def _fluctuate(self, base_price: float, product_id: int, day_offset: int) -> float:
        rng = random.Random(product_id * 1000 + day_offset)
        roll = rng.random()
        if roll < 0.12:
            factor = rng.uniform(0.76, 0.94)
        elif roll < 0.22:
            factor = rng.uniform(1.02, 1.12)
        else:
            factor = rng.uniform(0.97, 1.03)
        return round(max(1.0, base_price * factor), 2)


price_tracker_agent = PriceTrackerAgent()
