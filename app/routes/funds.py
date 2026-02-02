# -*- coding: utf-8 -*-
"""
基金相关路由
包含基金自选列表、基金持仓详情等
"""

import time
from flask import Blueprint, jsonify, request
from concurrent.futures import ThreadPoolExecutor

from app.config import (
    CACHE_TTL_SECONDS, FUND_STALE_TTL_SECONDS, MAX_FETCH_WORKERS
)
from app.models.state import lock, fund_watchlist, fund_cache
from app.services.fund_fetcher import (
    fetch_fund_data,
    fetch_fund_portfolio,
    refresh_fund_cache_async
)
from app.services.persistence import save_data


funds_bp = Blueprint('funds', __name__)


@funds_bp.route('/api/funds', methods=['GET'])
def get_funds():
    """获取所有自选基金的实时数据 (并发优化版)"""
    results = []

    fast_mode = request.args.get('fast', '0').lower() in ('1', 'true')
    current_time = time.time()

    with lock:
        current_watchlist = list(fund_watchlist)

    codes_to_fetch = []
    codes_to_refresh = []
    temp_results = {}

    for code in current_watchlist:
        cache_item = fund_cache.get(code)
        if cache_item and (current_time - cache_item['timestamp'] < CACHE_TTL_SECONDS):
            temp_results[code] = cache_item
        elif fast_mode and cache_item and (current_time - cache_item['timestamp'] < FUND_STALE_TTL_SECONDS):
            # 快速模式：优先返回可接受的过期缓存
            stale_item = dict(cache_item)
            if "(缓存)" not in stale_item.get('source', ''):
                stale_item['source'] = f"{stale_item.get('source', '')}(缓存)"
            temp_results[code] = stale_item
            codes_to_refresh.append(code)
        else:
            codes_to_fetch.append(code)

    # 非快速模式或无可用缓存时：并发抓取
    if codes_to_fetch:
        with ThreadPoolExecutor(max_workers=MAX_FETCH_WORKERS) as executor:
            fetched_data_list = list(executor.map(fetch_fund_data, codes_to_fetch))

        with lock:
            for i, data in enumerate(fetched_data_list):
                code = codes_to_fetch[i]
                if data:
                    fund_cache[code] = data
                    temp_results[code] = data
                else:
                    old_cache = fund_cache.get(code)
                    if old_cache:
                        if "(过期)" not in old_cache.get('source', ''):
                            old_cache['source'] = f"{old_cache.get('source', '')}(过期)"
                        temp_results[code] = old_cache
                    else:
                        temp_results[code] = {
                            "code": code,
                            "name": "加载失败",
                            "price": 0,
                            "change": 0,
                            "time_str": "--",
                            "source": "Error"
                        }

    if fast_mode and codes_to_refresh:
        refresh_fund_cache_async(codes_to_refresh)

    results = [temp_results.get(code) for code in current_watchlist if temp_results.get(code)]

    return jsonify({"success": True, "data": results})


@funds_bp.route('/api/funds/<fund_code>/portfolio')
def get_fund_portfolio(fund_code):
    """获取基金持仓详情"""
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    data = fetch_fund_portfolio(fund_code, force_refresh=force_refresh)
    if data is not None:
        return jsonify({"success": True, "data": data})
    return jsonify({"success": False, "message": "获取持仓失败"})


@funds_bp.route('/api/funds/add', methods=['POST'])
def add_fund():
    """添加自选基金"""
    req_data = request.get_json()
    code = str(req_data.get('code', '')).strip()
    
    if not code or not code.isdigit() or len(code) != 6:
        return jsonify({"success": False, "message": "无效的基金代码 (需6位数字)"})
        
    with lock:
        if code in fund_watchlist:
            return jsonify({"success": False, "message": "该基金已在列表中"})
    
    # 尝试抓取一次以验证代码有效性
    data = fetch_fund_data(code)
    if not data:
        return jsonify({"success": False, "message": "无法获取该基金数据，请确认代码是否正确"})
        
    with lock:
        fund_watchlist.append(code)
        fund_cache[code] = data # 顺便存入缓存
        
    save_data()
    return jsonify({"success": True, "data": data})


@funds_bp.route('/api/funds/<code_to_del>', methods=['DELETE'])
def delete_fund(code_to_del):
    """删除自选基金"""
    with lock:
        if code_to_del in fund_watchlist:
            fund_watchlist.remove(code_to_del)
            # 缓存可以选择不删，反正会自动过期，或者删掉省内存
            if code_to_del in fund_cache:
                del fund_cache[code_to_del]
            save_data()
            return jsonify({"success": True})
            
    return jsonify({"success": False, "message": "未找到该基金"})
