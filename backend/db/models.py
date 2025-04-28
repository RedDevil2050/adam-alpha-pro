from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Float, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Optional, List, Dict, Any
import datetime

from .base import Base

class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    watchlists = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSetting", back_populates="user", uselist=False, cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")


class Portfolio(Base):
    """Portfolio model containing user's investment portfolios"""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    
    # Renamed metadata to extra_metadata to avoid conflict
    extra_metadata = Column(JSON, nullable=True)  # Store additional portfolio metadata


class Holding(Base):
    """Model for individual holdings within portfolios"""
    __tablename__ = "holdings"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    symbol = Column(String, nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    purchase_price = Column(Float, nullable=False)
    purchase_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")
    transactions = relationship("Transaction", back_populates="holding", cascade="all, delete-orphan")


class Transaction(Base):
    """Model for individual buy/sell transactions"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    holding_id = Column(Integer, ForeignKey("holdings.id"))
    transaction_type = Column(String, nullable=False)  # "BUY" or "SELL"
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    transaction_date = Column(DateTime, server_default=func.now())
    fees = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    
    # Relationships
    holding = relationship("Holding", back_populates="transactions")


class Watchlist(Base):
    """Model for user watchlists"""
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="watchlists")
    symbols = relationship("WatchlistSymbol", back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistSymbol(Base):
    """Model for symbols in a watchlist"""
    __tablename__ = "watchlist_symbols"
    
    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey("watchlists.id"))
    symbol = Column(String, nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)
    
    # Relationships
    watchlist = relationship("Watchlist", back_populates="symbols")


class UserSetting(Base):
    """Model for user settings and preferences"""
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    theme = Column(String, default="light")
    notification_preferences = Column(JSON, nullable=True)
    default_portfolio_id = Column(Integer, nullable=True)
    default_watchlist_id = Column(Integer, nullable=True)
    ui_preferences = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="settings")


class Alert(Base):
    """Model for stock alerts"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String, nullable=False, index=True)
    alert_type = Column(String, nullable=False)  # "price", "volume", "technical", etc.
    condition = Column(String, nullable=False)  # ">", "<", "=", etc.
    target_value = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    is_recurring = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_triggered = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="alerts")