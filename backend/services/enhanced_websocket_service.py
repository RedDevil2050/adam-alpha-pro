"""
Enhanced WebSocket Service for Real-Time Data Streaming
=======================================================

Provides real-time data streaming to frontend with intelligent data aggregation,
compression, and client-specific subscriptions.
"""

import asyncio
import json
import time
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import websockets
from websockets.server import WebSocketServerProtocol
from loguru import logger

from ..data_pipeline.enhanced_pipeline import PipelineData, enhanced_pipeline

class MessageType(Enum):
    """WebSocket message types"""
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    DATA_UPDATE = "data_update"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"
    HEARTBEAT = "heartbeat"

@dataclass
class ClientSubscription:
    """Client subscription details"""
    client_id: str
    symbols: Set[str]
    data_types: Set[str]
    last_update: float
    connection: WebSocketServerProtocol

@dataclass
class WebSocketMessage:
    """Standardized WebSocket message"""
    type: MessageType
    data: Dict[str, Any]
    timestamp: float
    client_id: Optional[str] = None

class DataAggregator:
    """Aggregate and optimize data for streaming"""
    
    def __init__(self):
        self.data_buffer: Dict[str, PipelineData] = {}
        self.last_broadcast: Dict[str, float] = {}
        self.aggregation_window = 1.0  # 1 second aggregation window
    
    def add_data(self, data: PipelineData):
        """Add data to aggregation buffer"""
        self.data_buffer[data.symbol] = data
    
    def get_aggregated_data(self) -> Dict[str, Any]:
        """Get aggregated data for broadcast"""
        current_time = time.time()
        updates = {}
        
        for symbol, data in self.data_buffer.items():
            # Check if enough time has passed since last broadcast
            if symbol not in self.last_broadcast or \
               current_time - self.last_broadcast[symbol] >= self.aggregation_window:
                
                updates[symbol] = {
                    "symbol": symbol,
                    "price": data.processed_data.get("price") if data.processed_data else None,
                    "change": data.processed_data.get("change") if data.processed_data else None,
                    "change_percent": data.processed_data.get("change_percent") if data.processed_data else None,
                    "volume": data.processed_data.get("volume") if data.processed_data else None,
                    "validation_score": data.validation_score,
                    "trend": data.enrichment_data.get("trend") if data.enrichment_data else None,
                    "volatility": data.enrichment_data.get("volatility") if data.enrichment_data else None,
                    "source": data.source,
                    "timestamp": data.timestamp.isoformat() if data.timestamp else None
                }
                
                self.last_broadcast[symbol] = current_time
        
        return updates
    
    def clear_buffer(self):
        """Clear aggregation buffer"""
        self.data_buffer.clear()

class ConnectionManager:
    """Manage WebSocket connections and subscriptions"""
    
    def __init__(self):
        self.connections: Dict[str, ClientSubscription] = {}
        self.symbol_subscribers: Dict[str, Set[str]] = {}  # symbol -> client_ids
        self.connection_count = 0
    
    def add_connection(self, websocket: WebSocketServerProtocol) -> str:
        """Add new WebSocket connection"""
        client_id = f"client_{int(time.time())}_{self.connection_count}"
        self.connection_count += 1
        
        subscription = ClientSubscription(
            client_id=client_id,
            symbols=set(),
            data_types={"price", "volume", "change"},
            last_update=time.time(),
            connection=websocket
        )
        
        self.connections[client_id] = subscription
        logger.info(f"📱 New WebSocket connection: {client_id}")
        return client_id
    
    def remove_connection(self, client_id: str):
        """Remove WebSocket connection"""
        if client_id in self.connections:
            subscription = self.connections[client_id]
            
            # Remove from symbol subscriptions
            for symbol in subscription.symbols:
                if symbol in self.symbol_subscribers:
                    self.symbol_subscribers[symbol].discard(client_id)
                    if not self.symbol_subscribers[symbol]:
                        del self.symbol_subscribers[symbol]
            
            del self.connections[client_id]
            logger.info(f"📱 WebSocket connection removed: {client_id}")
    
    def subscribe_to_symbols(self, client_id: str, symbols: List[str]):
        """Subscribe client to symbols"""
        if client_id not in self.connections:
            return
        
        subscription = self.connections[client_id]
        
        for symbol in symbols:
            subscription.symbols.add(symbol)
            
            if symbol not in self.symbol_subscribers:
                self.symbol_subscribers[symbol] = set()
            
            self.symbol_subscribers[symbol].add(client_id)
        
        logger.info(f"📝 Client {client_id} subscribed to symbols: {symbols}")
    
    def unsubscribe_from_symbols(self, client_id: str, symbols: List[str]):
        """Unsubscribe client from symbols"""
        if client_id not in self.connections:
            return
        
        subscription = self.connections[client_id]
        
        for symbol in symbols:
            subscription.symbols.discard(symbol)
            
            if symbol in self.symbol_subscribers:
                self.symbol_subscribers[symbol].discard(client_id)
                if not self.symbol_subscribers[symbol]:
                    del self.symbol_subscribers[symbol]
        
        logger.info(f"📝 Client {client_id} unsubscribed from symbols: {symbols}")
    
    def get_subscribers_for_symbol(self, symbol: str) -> List[ClientSubscription]:
        """Get all subscribers for a symbol"""
        if symbol not in self.symbol_subscribers:
            return []
        
        subscribers = []
        for client_id in self.symbol_subscribers[symbol]:
            if client_id in self.connections:
                subscribers.append(self.connections[client_id])
        
        return subscribers
    
    def get_all_connections(self) -> List[ClientSubscription]:
        """Get all active connections"""
        return list(self.connections.values())

class EnhancedWebSocketService:
    """Enhanced WebSocket service with real-time data streaming"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.connection_manager = ConnectionManager()
        self.data_aggregator = DataAggregator()
        self.server = None
        self.is_running = False
        
        # Subscribe to pipeline data updates
        enhanced_pipeline.subscribe(self._handle_pipeline_data)
        
        logger.info(f"🌐 Enhanced WebSocket Service initialized on {host}:{port}")
    
    async def start_server(self):
        """Start the WebSocket server"""
        try:
            self.server = await websockets.serve(
                self._handle_client_connection,
                self.host,
                self.port
            )
            
            self.is_running = True
            logger.success(f"🚀 WebSocket server started on ws://{self.host}:{self.port}")
            
            # Start background tasks
            asyncio.create_task(self._background_data_broadcaster())
            asyncio.create_task(self._heartbeat_monitor())
            
        except Exception as e:
            logger.error(f"❌ Failed to start WebSocket server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.is_running = False
            logger.info("🔴 WebSocket server stopped")
    
    async def _handle_client_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new client connection"""
        client_id = self.connection_manager.add_connection(websocket)
        
        try:
            # Send initial connection message
            await self._send_message(websocket, WebSocketMessage(
                type=MessageType.SYSTEM_STATUS,
                data={
                    "status": "connected",
                    "client_id": client_id,
                    "available_symbols": list(enhanced_pipeline.processed_data_cache.keys())
                },
                timestamp=time.time()
            ))
            
            # Handle incoming messages
            async for message in websocket:
                await self._handle_client_message(client_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"📱 Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"❌ Error handling client {client_id}: {e}")
        finally:
            self.connection_manager.remove_connection(client_id)
    
    async def _handle_client_message(self, client_id: str, message: str):
        """Handle incoming client message"""
        try:
            data = json.loads(message)
            message_type = MessageType(data.get("type"))
            
            if message_type == MessageType.SUBSCRIBE:
                symbols = data.get("symbols", [])
                self.connection_manager.subscribe_to_symbols(client_id, symbols)
                
                # Send immediate data for subscribed symbols
                await self._send_initial_data(client_id, symbols)
                
            elif message_type == MessageType.UNSUBSCRIBE:
                symbols = data.get("symbols", [])
                self.connection_manager.unsubscribe_from_symbols(client_id, symbols)
                
            elif message_type == MessageType.HEARTBEAT:
                # Respond to heartbeat
                subscription = self.connection_manager.connections.get(client_id)
                if subscription:
                    await self._send_message(subscription.connection, WebSocketMessage(
                        type=MessageType.HEARTBEAT,
                        data={"status": "alive"},
                        timestamp=time.time(),
                        client_id=client_id
                    ))
                
        except Exception as e:
            logger.error(f"❌ Error handling message from {client_id}: {e}")
    
    async def _send_initial_data(self, client_id: str, symbols: List[str]):
        """Send initial data for newly subscribed symbols"""
        subscription = self.connection_manager.connections.get(client_id)
        if not subscription:
            return
        
        initial_data = {}
        for symbol in symbols:
            pipeline_data = enhanced_pipeline.get_latest_data(symbol)
            if pipeline_data:
                initial_data[symbol] = {
                    "symbol": symbol,
                    "price": pipeline_data.processed_data.get("price") if pipeline_data.processed_data else None,
                    "change": pipeline_data.processed_data.get("change") if pipeline_data.processed_data else None,
                    "volume": pipeline_data.processed_data.get("volume") if pipeline_data.processed_data else None,
                    "source": pipeline_data.source,
                    "timestamp": pipeline_data.timestamp.isoformat() if pipeline_data.timestamp else None
                }
        
        if initial_data:
            await self._send_message(subscription.connection, WebSocketMessage(
                type=MessageType.DATA_UPDATE,
                data={"initial": True, "updates": initial_data},
                timestamp=time.time(),
                client_id=client_id
            ))
    
    async def _handle_pipeline_data(self, data: PipelineData):
        """Handle new data from pipeline"""
        self.data_aggregator.add_data(data)
    
    async def _background_data_broadcaster(self):
        """Background task to broadcast aggregated data"""
        while self.is_running:
            try:
                # Get aggregated data
                updates = self.data_aggregator.get_aggregated_data()
                
                if updates:
                    # Broadcast to relevant subscribers
                    await self._broadcast_updates(updates)
                
                await asyncio.sleep(1)  # 1-second broadcast cycle
                
            except Exception as e:
                logger.error(f"❌ Background broadcast error: {e}")
                await asyncio.sleep(5)
    
    async def _broadcast_updates(self, updates: Dict[str, Any]):
        """Broadcast updates to subscribed clients"""
        for symbol, update_data in updates.items():
            subscribers = self.connection_manager.get_subscribers_for_symbol(symbol)
            
            for subscription in subscribers:
                try:
                    await self._send_message(subscription.connection, WebSocketMessage(
                        type=MessageType.DATA_UPDATE,
                        data={"symbol": symbol, "update": update_data},
                        timestamp=time.time(),
                        client_id=subscription.client_id
                    ))
                    
                    subscription.last_update = time.time()
                    
                except Exception as e:
                    logger.error(f"❌ Failed to send update to {subscription.client_id}: {e}")
    
    async def _send_message(self, websocket: WebSocketServerProtocol, message: WebSocketMessage):
        """Send message to WebSocket client"""
        try:
            message_data = {
                "type": message.type.value,
                "data": message.data,
                "timestamp": message.timestamp
            }
            
            if message.client_id:
                message_data["client_id"] = message.client_id
            
            await websocket.send(json.dumps(message_data))
            
        except Exception as e:
            logger.error(f"❌ Failed to send WebSocket message: {e}")
    
    async def _heartbeat_monitor(self):
        """Monitor client connections with heartbeat"""
        while self.is_running:
            try:
                current_time = time.time()
                
                # Check for stale connections
                stale_connections = []
                for client_id, subscription in self.connection_manager.connections.items():
                    if current_time - subscription.last_update > 300:  # 5 minutes timeout
                        stale_connections.append(client_id)
                
                # Remove stale connections
                for client_id in stale_connections:
                    self.connection_manager.remove_connection(client_id)
                    logger.warning(f"⚠️ Removed stale connection: {client_id}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"❌ Heartbeat monitor error: {e}")
                await asyncio.sleep(60)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        connections = self.connection_manager.get_all_connections()
        
        return {
            "total_connections": len(connections),
            "total_subscriptions": sum(len(conn.symbols) for conn in connections),
            "unique_symbols": len(self.connection_manager.symbol_subscribers),
            "server_status": "running" if self.is_running else "stopped"
        }

# Global WebSocket service instance
websocket_service = EnhancedWebSocketService()
