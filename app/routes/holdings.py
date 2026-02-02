# -*- coding: utf-8 -*-
"""
持仓相关路由
包含持仓数据获取、添加、删除等
"""

import time
from flask import Blueprint, jsonify, request
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from app.config import (
    HOLDINGS_CACHE_TTL_SECONDS, HOLDINGS_STALE_TTL_SECONDS, MAX_FETCH_WORKERS
)
from app.models.state import lock, fund_holdings, fund_cache, holdings_cache
from app.services.fund_fetcher import (
    fetch_fund_data,
    build_holdings_response,
    refresh_holdings_cache_async
)
from app.services.persistence import save_data


holdings_bp = Blueprint('holdings', __name__)


@holdings_bp.route('/api/holdings', methods=['GET'])
def get_holdings():
    """
    获取持仓数据，并结合实时净值计算盈亏
    """
    fast_mode = request.args.get('fast', '0').lower() in ('1', 'true')
    force_refresh = request.args.get('refresh', 'false').lower() in ('1', 'true')
    now_ts = time.time()

    with lock:
        holdings = list(fund_holdings)
        cached_response = holdings_cache.get("response")
        cached_ts = holdings_cache.get("timestamp", 0)

    if fast_mode and not force_refresh and cached_response:
        if now_ts - cached_ts < HOLDINGS_CACHE_TTL_SECONDS:
            return jsonify(cached_response)
        if now_ts - cached_ts < HOLDINGS_STALE_TTL_SECONDS:
            refresh_holdings_cache_async(holdings)
            stale_response = dict(cached_response)
            stale_response["stale"] = True
            return jsonify(stale_response)
    
    if not holdings:
        response = {
            "success": True,
            "data": [],
            "summary": {"total_cost": 0, "total_value": 0, "total_profit": 0, "total_profit_rate": 0, "count": 0},
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with lock:
            holdings_cache["timestamp"] = now_ts
            holdings_cache["response"] = response
        return jsonify(response)
    
    codes = [h['code'] for h in holdings]

    with ThreadPoolExecutor(max_workers=MAX_FETCH_WORKERS) as executor:
        fund_data_list = list(executor.map(fetch_fund_data, codes))

    with lock:
        cached_map = {code: fund_cache.get(code) for code in codes}
        for i, data in enumerate(fund_data_list):
            if data:
                fund_cache[codes[i]] = data

    response = build_holdings_response(holdings, fund_data_list, cached_map)
    with lock:
        holdings_cache["timestamp"] = now_ts
        holdings_cache["response"] = response

    return jsonify(response)


@holdings_bp.route('/api/holdings', methods=['POST'])
def add_or_update_holding():
    """
    添加或更新持仓记录
    请求体: { code, cost_price, shares, note? }
    """
    req_data = request.get_json()
    code = str(req_data.get('code', '')).strip()
    
    if not code or not code.isdigit() or len(code) != 6:
        return jsonify({"success": False, "message": "无效的基金代码 (需6位数字)"})
    
    try:
        cost_price = float(req_data.get('cost_price', 0))
        shares = float(req_data.get('shares', 0))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "成本价或份额格式无效"})
    
    note = str(req_data.get('note', '')).strip()
    
    if cost_price <= 0 or shares <= 0:
        return jsonify({"success": False, "message": "成本价和份额必须大于0"})
    
    # 尝试获取基金名称
    fund_data = fetch_fund_data(code)
    name = fund_data['name'] if fund_data else f'基金{code}'
    
    with lock:
        # 检查是否已存在
        existing = next((h for h in fund_holdings if h['code'] == code), None)
        if existing:
            # 更新
            existing['cost_price'] = cost_price
            existing['shares'] = shares
            existing['note'] = note
            existing['name'] = name
        else:
            # 新增
            fund_holdings.append({
                'code': code,
                'name': name,
                'cost_price': cost_price,
                'shares': shares,
                'note': note
            })
        # 修改数据后使缓存失效
        holdings_cache["response"] = None
        holdings_cache["timestamp"] = 0
    
    save_data()
    return jsonify({"success": True, "message": "持仓已保存"})


@holdings_bp.route('/api/holdings/<code_to_del>', methods=['DELETE'])
def delete_holding(code_to_del):
    """删除持仓记录"""
    with lock:
        original_len = len(fund_holdings)
        # 使用列表推导式过滤
        to_keep = [h for h in fund_holdings if h['code'] != code_to_del]
        if len(to_keep) < original_len:
            fund_holdings.clear()
            fund_holdings.extend(to_keep)
            # 修改数据后使缓存失效
            holdings_cache["response"] = None
            holdings_cache["timestamp"] = 0
            save_data()
            return jsonify({"success": True, "message": "持仓已删除"})
    
    return jsonify({"success": False, "message": "未找到该持仓"})
