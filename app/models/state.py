# -*- coding: utf-8 -*-
"""
全局状态管理模块
包含所有共享的全局变量、缓存、锁等
"""

import threading
from collections import deque
from app.config import MAX_HISTORY_SIZE


# ==================== 线程锁 ====================
# 使用 RLock 以支持在持有锁的情况下调用其他需要锁的函数
lock = threading.RLock()

# ==================== 金价历史数据 ====================
# 存储历史价格数据 (最多保存 MAX_HISTORY_SIZE 条)
price_history = deque(maxlen=MAX_HISTORY_SIZE)

# ==================== 手动记录 ====================
# 用户手动记录的价格快照
manual_records = []

# ==================== 预警设置 ====================
alert_settings = {
    "high": 0,
    "low": 0,
    "enabled": False,
    "trading_events_enabled": True
}

# ==================== 基金相关状态 ====================
# 基金自选列表 (存储基金代码)
fund_watchlist = []

# 基金重仓股配置缓存 (持久化缓存，用于存储股票构成和权重)
# 结构: { "code": { "timestamp": float, "report_period": str, "holdings_info": {stock_code: {name, weight}} } }
fund_portfolios = {}

# 基金数据缓存 (内存缓存，不持久化详情，只持久化代码列表)
fund_cache = {}

# 基金持仓数据 (存储在 data.json 中)
# 结构: [{code, name, cost_price, shares, note}, ...]
fund_holdings = []

# ==================== 持仓数据缓存 ====================
# 内存缓存，用于加速基金估值页刷新
holdings_cache = {
    "timestamp": 0,
    "response": None
}

# ==================== 后台刷新标记 ====================
fund_refreshing = False
holdings_refreshing = False
