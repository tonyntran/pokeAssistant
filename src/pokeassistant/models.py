from datetime import datetime, date as date_type

from sqlalchemy import Column, Integer, Text, Float, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship


def dollars_to_cents(value) -> int | None:
    """Convert a dollar amount to cents (integer).
    Accepts float, int, string, or None. Returns None if input is None.
    """
    if value is None:
        return None
    return round(float(value) * 100)


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    product_id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    category = Column(Text)
    group_name = Column(Text)
    url = Column(Text)
    image_url = Column(Text)            # NEW
    card_number = Column(Text)           # NEW
    product_type = Column(Text)          # NEW: "card" or "sealed"
    rarity = Column(Text)               # NEW
    release_date = Column(Date)          # NEW
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    # order_by ensures deterministic ordering for [-1] access in API layer.
    price_snapshots = relationship("PriceSnapshot", back_populates="product",
                                    order_by="PriceSnapshot.timestamp")
    sale_records = relationship("SaleRecord", back_populates="product",
                                order_by="SaleRecord.sale_date")
    graded_prices = relationship("GradedPrice", back_populates="product",
                                  order_by="GradedPrice.timestamp")
    population_reports = relationship("PopulationReport", back_populates="product",
                                      order_by="PopulationReport.timestamp")

    def __repr__(self):
        return f"<Product(id={self.product_id}, name='{self.name}', type='{self.product_type}')>"


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    source = Column(Text, nullable=False)
    low_price_cents = Column(Integer)
    market_price_cents = Column(Integer)
    high_price_cents = Column(Integer)
    listing_count = Column(Integer)
    __table_args__ = (UniqueConstraint("product_id", "timestamp", "source"),)

    product = relationship("Product", back_populates="price_snapshots")

    def __repr__(self):
        return f"<PriceSnapshot(product_id={self.product_id}, market={self.market_price_cents}, ts={self.timestamp})>"


class SaleRecord(Base):
    __tablename__ = "sale_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    sale_date = Column(Date, nullable=False)
    condition = Column(Text)
    variant = Column(Text)
    price_cents = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    source = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("product_id", "sale_date", "condition", "variant", "price_cents"),)

    product = relationship("Product", back_populates="sale_records")

    def __repr__(self):
        return f"<SaleRecord(product_id={self.product_id}, price={self.price_cents}, date={self.sale_date})>"


class TrendDataPoint(Base):
    __tablename__ = "trend_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(Text, nullable=False)
    date = Column(Date, nullable=False)
    interest = Column(Integer, nullable=False)
    source = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("keyword", "date"),)

    def __repr__(self):
        return f"<TrendDataPoint(keyword='{self.keyword}', date={self.date}, interest={self.interest})>"


class GradedPrice(Base):
    __tablename__ = "graded_prices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"))
    card_name = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    ungraded_cents = Column(Integer)
    grade_7_cents = Column(Integer)
    grade_8_cents = Column(Integer)
    grade_9_cents = Column(Integer)
    grade_9_5_cents = Column(Integer)
    psa_10_cents = Column(Integer)
    bgs_10_cents = Column(Integer)
    cgc_10_cents = Column(Integer)
    sgc_10_cents = Column(Integer)
    pricecharting_url = Column(Text)
    __table_args__ = (UniqueConstraint("card_name", "timestamp", "source"),)

    product = relationship("Product", back_populates="graded_prices")

    def __repr__(self):
        return f"<GradedPrice(card='{self.card_name}', psa10={self.psa_10_cents})>"


class PopulationReport(Base):
    __tablename__ = "population_reports"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"))
    card_name = Column(Text, nullable=False)
    gemrate_id = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    total_population = Column(Integer, nullable=False)
    psa_10 = Column(Integer)
    psa_9 = Column(Integer)
    psa_8 = Column(Integer)
    bgs_10 = Column(Integer)
    bgs_9_5 = Column(Integer)
    cgc_10 = Column(Integer)
    cgc_9_5 = Column(Integer)
    gem_rate = Column(Float)
    __table_args__ = (UniqueConstraint("gemrate_id", "timestamp"),)

    product = relationship("Product", back_populates="population_reports")

    def __repr__(self):
        return f"<PopulationReport(card='{self.card_name}', total={self.total_population})>"
