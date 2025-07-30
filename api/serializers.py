from rest_framework import serializers
from .models import Trade

class TradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trade
        fields = [
            'id',
            'user',
            'stock_symbol',
            'action',
            'quantity',
            'price_per_share',
            'date',
            'notes',
        ]
        read_only_fields = ['user']
