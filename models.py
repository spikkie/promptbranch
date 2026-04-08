# Saving to PostgreSQL using SQLAlchemy
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)

# from database import Base
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    otp_enabled = Column(Boolean, default=False)
    otp_secret = Column(String, nullable=True)


class Receipt(Base):
    __tablename__ = "receipts"
    id = Column(Integer, primary_key=True, index=True)
    uri = Column(String, index=True)
    type = Column(String, index=True)
    is_receipt = Column(Boolean, default=False)
    file_name = Column(String, index=True)
    shop_name = Column(String)
    shop_address = Column(String)
    scan_datetime = Column(DateTime)
    receipt_datetime = Column(DateTime)
    receipt_number = Column(String)
    subtotal = Column(Float)
    total = Column(Float)
    payment_method = Column(String)
    items = relationship(
        "ReceiptItem", back_populates="receipt", cascade="all, delete-orphan"
    )


class ReceiptItem(Base):
    __tablename__ = "receipt_items"
    id = Column(Integer, primary_key=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id"))
    description = Column(String)
    currency = Column(String)
    quantity = Column(Integer)
    unit_price = Column(Float)
    total_price = Column(Float)
    receipt = relationship("Receipt", back_populates="items")
