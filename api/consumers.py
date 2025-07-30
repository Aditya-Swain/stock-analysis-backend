import json
import asyncio
import websockets
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from asgiref.sync import sync_to_async
from .models import StockData

class StockConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.symbol = self.scope['url_route']['kwargs']['symbol']
        self.room_group_name = f'stock_{self.symbol}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Start Finnhub WebSocket connection
        await self.start_finnhub_connection()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def start_finnhub_connection(self):
        """Start connection to Finnhub WebSocket"""
        try:
            uri = f"wss://ws.finnhub.io?token={settings.FINNHUB_API_KEY}"
            
            async with websockets.connect(uri) as websocket:
                # Subscribe to symbol
                await websocket.send(json.dumps({
                    'type': 'subscribe',
                    'symbol': self.symbol.upper()
                }))
                
                async for message in websocket:
                    data = json.loads(message)
                    
                    if data.get('type') == 'trade' and data.get('data'):
                        for trade in data['data']:
                            # Save to database
                            await self.save_trade_data(trade)
                            
                            # Send to WebSocket clients
                            await self.channel_layer.group_send(
                                self.room_group_name,
                                {
                                    'type': 'stock_update',
                                    'data': {
                                        'symbol': trade['s'],
                                        'price': trade['p'],
                                        'volume': trade['v'],
                                        'timestamp': trade['t']
                                    }
                                }
                            )
        except Exception as e:
            print(f"Finnhub WebSocket error: {e}")
    
    @sync_to_async
    def save_trade_data(self, trade):
        """Save trade data to database"""
        StockData.objects.create(
            symbol=trade['s'],
            price=trade['p'],
            volume=trade['v']
        )
    
    async def stock_update(self, event):
        """Send stock update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'stock_update',
            'data': event['data']
        }))