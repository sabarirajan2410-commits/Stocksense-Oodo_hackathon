from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="Warehouse Staff") # or "Inventory Manager"

class Warehouse(Base):
    __tablename__ = "warehouses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    location_code = Column(String, unique=True, nullable=False)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, default="General")
    uom = Column(String, default="Units") # Unit of Measure
    min_reorder_level = Column(Float, default=10.0)

class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    quantity = Column(Float, default=0.0)

    product = relationship("Product")
    warehouse = relationship("Warehouse")

class StockMove(Base):
    __tablename__ = "stock_moves"
    id = Column(Integer, primary_key=True, index=True)
    doc_type = Column(String, nullable=False) # Receipt, Delivery, Internal, Adjustment
    status = Column(String, default="Draft") # Draft, Waiting, Ready, Done, Canceled
    product_id = Column(Integer, ForeignKey("products.id"))
    src_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    dest_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    quantity = Column(Float, nullable=False)
    partner = Column(String, nullable=True) # Vendor or Customer
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product")
    src_warehouse = relationship("Warehouse", foreign_keys=[src_warehouse_id])
    dest_warehouse = relationship("Warehouse", foreign_keys=[dest_warehouse_id])