# -*- coding: utf-8 -*-
"""
app.services 包初始化
"""

from app.services.gold_fetcher import fetch_gold_price
from app.services.fund_fetcher import (
    fetch_fund_data,
    fetch_fund_portfolio,
    refresh_fund_cache_async,
    refresh_holdings_cache_async,
    build_holdings_response
)
from app.services.calculator import (
    calculate_target_prices,
    calculate_current_profit,
    get_24h_summary
)
from app.services.persistence import save_data, load_data
from app.services.background import background_fetch_loop

__all__ = [
    'fetch_gold_price',
    'fetch_fund_data',
    'fetch_fund_portfolio',
    'refresh_fund_cache_async',
    'refresh_holdings_cache_async',
    'build_holdings_response',
    'calculate_target_prices',
    'calculate_current_profit',
    'get_24h_summary',
    'save_data',
    'load_data',
    'background_fetch_loop'
]
