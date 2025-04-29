from typing import Dict, List, Any
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pandas as pd
from datetime import datetime

Base = declarative_base()


class MarketData(Base):
    __tablename__ = "market_data"
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    timestamp = Column(DateTime)
    price = Column(Float)
    volume = Column(Float)


class DatabaseService:
    def __init__(self, connection_string: str = "sqlite:///market_data.db"):
        self.engine = create_engine(connection_string)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save_market_data(self, data: Dict[str, float]):
        session = self.Session()
        try:
            market_data = MarketData(
                symbol=data["symbol"],
                timestamp=datetime.fromtimestamp(data["timestamp"]),
                price=data["price"],
                volume=data["volume"],
            )
            session.add(market_data)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_historical_data(self, symbol: str, start_date: datetime) -> pd.DataFrame:
        query = f"""
        SELECT timestamp, price, volume 
        FROM market_data 
        WHERE symbol = '{symbol}' 
        AND timestamp >= '{start_date}'
        """
        return pd.read_sql(query, self.engine)
