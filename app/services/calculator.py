# -*- coding: utf-8 -*-
"""
计算工具模块
包含盈利计算、收益率计算、24小时统计等
"""

from app.models.state import lock, price_history


def calculate_target_prices(buy_price, fee_rate=0.005):
    """
    计算多个盈利目标的卖出价格
    
    公式: 目标卖出价 = 买入价 × (1 + 利润率) / (1 - 手续费率)
    
    参数:
        buy_price: 买入价格
        fee_rate: 卖出手续费率 (默认 0.5%)
    
    返回:
        多个盈利目标对应的卖出价格列表
    """
    targets = [5, 10, 15, 20, 30]  # 盈利目标百分比
    results = []
    
    for target in targets:
        profit_rate = target / 100
        # 目标卖出价 = 买入价 × (1 + 利润率) / (1 - 手续费率)
        sell_price = buy_price * (1 + profit_rate) / (1 - fee_rate)
        results.append({
            "target_percent": target,
            "sell_price": round(sell_price, 2),
            "profit_amount": round(buy_price * profit_rate, 2),
            "actual_multiplier": round(sell_price / buy_price, 4)
        })
    
    return results


def calculate_current_profit(buy_price, current_price, fee_rate=0.005):
    """
    计算当前价格卖出后的实际收益率 (扣除手续费)
    
    公式: 实际收益率 = (当前价 × (1 - 手续费率) - 买入价) / 买入价 × 100%
    """
    if buy_price <= 0:
        return 0
    
    actual_receive = current_price * (1 - fee_rate)
    profit_rate = (actual_receive - buy_price) / buy_price * 100
    return round(profit_rate, 2)


def get_24h_summary():
    """计算过去 24 小时的统计数据"""
    with lock:
        if not price_history:
            return None
        
        prices = [p['price'] for p in price_history]
        high = max(prices)
        low = min(prices)
        avg = sum(prices) / len(prices)
        volatility = high - low
        
        return {
            "high_24h": round(high, 2),
            "low_24h": round(low, 2),
            "avg_24h": round(avg, 2),
            "volatility": round(volatility, 2),
            "count": len(prices)
        }
