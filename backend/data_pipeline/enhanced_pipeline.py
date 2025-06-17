"""
Enhanced Data Pipeline for Zion Market Analysis Platform
=========================================================

Provides seamless data flow from collection to distribution with validation,
processing, and enrichment capabilities.
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
from loguru import logger

from backend.agents.core.base_agent import AgentResult, AgentCategory, agent_registry

class PipelineStage(Enum):
    """Data pipeline stages"""
    INGESTION = "ingestion"
    PROCESSING = "processing"
    VALIDATION = "validation"
    ENRICHMENT = "enrichment"
    DISTRIBUTION = "distribution"

@dataclass
class PipelineData:
    """Standardized data structure for pipeline"""
    data_id: str
    source: str
    symbol: str
    raw_data: Dict[str, Any]
    processed_data: Dict[str, Any] = None
    validation_score: float = 0.0
    enrichment_data: Dict[str, Any] = None
    timestamp: datetime = None
    pipeline_stage: PipelineStage = PipelineStage.INGESTION

class DataProcessor:
    """Base class for data processing components"""
    
    def __init__(self, processor_id: str):
        self.processor_id = processor_id
    
    async def process(self, data: PipelineData) -> PipelineData:
        """Process data - to be implemented by subclasses"""
        raise NotImplementedError

class PriceNormalizer(DataProcessor):
    """Normalize price data from different sources"""
    
    def __init__(self):
        super().__init__("price_normalizer")
    
    async def process(self, data: PipelineData) -> PipelineData:
        """Normalize price data format"""
        try:
            raw_data = data.raw_data
            
            # Extract price information from various formats
            price = self._extract_price(raw_data)
            volume = self._extract_volume(raw_data)
            change = self._extract_change(raw_data)
            
            # Create standardized format
            processed_data = {
                "symbol": data.symbol,
                "price": price,
                "volume": volume,
                "change": change,
                "change_percent": self._calculate_change_percent(price, change),
                "timestamp": datetime.now().isoformat(),
                "source": data.source
            }
            
            data.processed_data = processed_data
            data.pipeline_stage = PipelineStage.PROCESSING
            
            logger.debug(f"✅ Normalized price data for {data.symbol}: ₹{price}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Price normalization failed for {data.symbol}: {e}")
            return data
    
    def _extract_price(self, raw_data: Dict[str, Any]) -> Optional[float]:
        """Extract price from raw data"""
        price_fields = ["price", "current_price", "ltp", "last_price", "close"]
        
        for field in price_fields:
            if field in raw_data and raw_data[field] is not None:
                try:
                    return float(raw_data[field])
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _extract_volume(self, raw_data: Dict[str, Any]) -> Optional[int]:
        """Extract volume from raw data"""
        volume_fields = ["volume", "traded_volume", "total_volume"]
        
        for field in volume_fields:
            if field in raw_data and raw_data[field] is not None:
                try:
                    return int(raw_data[field])
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _extract_change(self, raw_data: Dict[str, Any]) -> Optional[float]:
        """Extract price change from raw data"""
        change_fields = ["change", "price_change", "day_change"]
        
        for field in change_fields:
            if field in raw_data and raw_data[field] is not None:
                try:
                    return float(raw_data[field])
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _calculate_change_percent(self, price: Optional[float], change: Optional[float]) -> Optional[float]:
        """Calculate percentage change"""
        if price and change and price > 0:
            previous_price = price - change
            if previous_price > 0:
                return (change / previous_price) * 100
        return None

class DataValidator:
    """Validate data quality and consistency"""
    
    def __init__(self):
        self.validation_rules = {
            "price_range": (0.01, 100000),  # Reasonable price range
            "volume_range": (0, 10000000000),  # Reasonable volume range
            "change_percent_range": (-50, 50)  # Reasonable daily change range
        }
    
    async def validate(self, data: PipelineData) -> PipelineData:
        """Validate data quality"""
        try:
            if not data.processed_data:
                data.validation_score = 0.0
                return data
            
            score = 0.0
            total_checks = 0
            
            # Validate price
            price = data.processed_data.get("price")
            if price is not None:
                total_checks += 1
                if self.validation_rules["price_range"][0] <= price <= self.validation_rules["price_range"][1]:
                    score += 1
            
            # Validate volume
            volume = data.processed_data.get("volume")
            if volume is not None:
                total_checks += 1
                if self.validation_rules["volume_range"][0] <= volume <= self.validation_rules["volume_range"][1]:
                    score += 1
            
            # Validate change percent
            change_percent = data.processed_data.get("change_percent")
            if change_percent is not None:
                total_checks += 1
                if self.validation_rules["change_percent_range"][0] <= change_percent <= self.validation_rules["change_percent_range"][1]:
                    score += 1
            
            # Calculate validation score
            data.validation_score = score / max(total_checks, 1)
            data.pipeline_stage = PipelineStage.VALIDATION
            
            logger.debug(f"✅ Validated data for {data.symbol}: score {data.validation_score:.2f}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Data validation failed for {data.symbol}: {e}")
            data.validation_score = 0.0
            return data

class DataEnricher:
    """Enrich data with additional information"""
    
    async def enrich(self, data: PipelineData) -> PipelineData:
        """Enrich data with additional context"""
        try:
            enrichment_data = {}
            
            # Add market session information
            enrichment_data["market_session"] = self._get_market_session()
            
            # Add trend indicators (if price history available)
            enrichment_data["trend"] = self._calculate_trend(data)
            
            # Add volatility indicator
            enrichment_data["volatility"] = self._calculate_volatility(data)
            
            data.enrichment_data = enrichment_data
            data.pipeline_stage = PipelineStage.ENRICHMENT
            
            logger.debug(f"✅ Enriched data for {data.symbol}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Data enrichment failed for {data.symbol}: {e}")
            return data
    
    def _get_market_session(self) -> str:
        """Determine current market session"""
        now = datetime.now()
        hour = now.hour
        
        if 9 <= hour < 15:
            return "market_open"
        elif 15 <= hour < 16:
            return "closing_session"
        else:
            return "market_closed"
    
    def _calculate_trend(self, data: PipelineData) -> str:
        """Calculate basic trend from change data"""
        if data.processed_data and "change" in data.processed_data:
            change = data.processed_data["change"]
            if change > 0:
                return "bullish"
            elif change < 0:
                return "bearish"
        return "neutral"
    
    def _calculate_volatility(self, data: PipelineData) -> str:
        """Calculate basic volatility indicator"""
        if data.processed_data and "change_percent" in data.processed_data:
            change_percent = abs(data.processed_data["change_percent"] or 0)
            if change_percent > 5:
                return "high"
            elif change_percent > 2:
                return "medium"
        return "low"

class EnhancedDataPipeline:
    """Enhanced data pipeline with processing, validation, and enrichment"""
    
    def __init__(self):
        self.price_normalizer = PriceNormalizer()
        self.data_validator = DataValidator()
        self.data_enricher = DataEnricher()
        self.subscribers: List[Callable] = []
        self.processed_data_cache: Dict[str, PipelineData] = {}
        
        logger.info("🔄 Enhanced Data Pipeline initialized")
    
    async def process_agent_result(self, result: AgentResult) -> Optional[PipelineData]:
        """Process agent result through the pipeline"""
        try:
            if not result.success or not result.data:
                return None
            
            # Create pipeline data from agent result
            pipeline_data = PipelineData(
                data_id=f"{result.agent_id}_{result.task_id}",
                source=result.agent_id,
                symbol=self._extract_symbol(result),
                raw_data=result.data,
                timestamp=result.timestamp or datetime.now()
            )
            
            # Process through pipeline stages
            pipeline_data = await self.price_normalizer.process(pipeline_data)
            pipeline_data = await self.data_validator.validate(pipeline_data)
            pipeline_data = await self.data_enricher.enrich(pipeline_data)
            
            # Set final stage
            pipeline_data.pipeline_stage = PipelineStage.DISTRIBUTION
            
            # Cache processed data
            self.processed_data_cache[pipeline_data.symbol] = pipeline_data
            
            # Notify subscribers
            await self._notify_subscribers(pipeline_data)
            
            logger.success(f"✅ Pipeline processed data for {pipeline_data.symbol}")
            return pipeline_data
            
        except Exception as e:
            logger.error(f"❌ Pipeline processing failed: {e}")
            return None
    
    def _extract_symbol(self, result: AgentResult) -> str:
        """Extract symbol from agent result"""
        # Try to extract symbol from task_id or data
        if "symbol" in result.data:
            return result.data["symbol"]
        
        # Extract from task_id if it contains symbol
        if "_" in result.task_id:
            parts = result.task_id.split("_")
            for part in parts:
                if part.isupper() and len(part) <= 10:  # Likely a symbol
                    return part
        
        return "UNKNOWN"
    
    async def _notify_subscribers(self, data: PipelineData):
        """Notify all subscribers of new processed data"""
        for subscriber in self.subscribers:
            try:
                await subscriber(data)
            except Exception as e:
                logger.error(f"❌ Subscriber notification failed: {e}")
    
    def subscribe(self, callback: Callable):
        """Subscribe to processed data updates"""
        self.subscribers.append(callback)
        logger.info(f"📝 New subscriber added to data pipeline")
    
    def get_latest_data(self, symbol: str) -> Optional[PipelineData]:
        """Get latest processed data for symbol"""
        return self.processed_data_cache.get(symbol)
    
    def get_all_latest_data(self) -> Dict[str, PipelineData]:
        """Get all latest processed data"""
        return self.processed_data_cache.copy()
    
    async def start_real_time_processing(self):
        """Start real-time data processing"""
        logger.info("🚀 Starting real-time data processing pipeline")
        
        while True:
            try:
                # Process any pending agent results
                # This would be connected to the agent results queue
                await asyncio.sleep(1)  # 1-second processing cycle
                
            except Exception as e:
                logger.error(f"❌ Real-time processing error: {e}")
                await asyncio.sleep(5)

# Global pipeline instance
enhanced_pipeline = EnhancedDataPipeline()
