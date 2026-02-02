# -*- coding: utf-8 -*-
"""
金价相关路由
包含首页、金价获取、历史数据、盈利计算等
"""

import time
from flask import Blueprint, render_template, jsonify, request

from app.config import STALE_THRESHOLD_SECONDS
from app.models.state import lock, price_history
from app.services.gold_fetcher import fetch_gold_price
from app.services.calculator import (
    calculate_target_prices,
    calculate_current_profit,
    get_24h_summary
)
from app.services.persistence import save_data


price_bp = Blueprint('price', __name__)


@price_bp.route('/')
def index():
    """首页"""
    return render_template('index.html')


@price_bp.route('/api/price')
def get_price():
    """获取当前金价 (改为从缓存获取，不再实时去抓取，提高响应速度)"""
    with lock:
        if price_history:
            latest = price_history[-1].copy() # 复制一份，避免直接修改缓存
            # 如果缓存数据太老（超过 30 秒），说明后台可能挂了或未运行，尝试实时抓一次
            if time.time() - latest["timestamp"] > STALE_THRESHOLD_SECONDS:
                data, _ = fetch_gold_price()
                if data:
                    price_history.append(data)
                    save_data()
                    latest = data
            
            # 注入 24 小时摘要信息
            summary = get_24h_summary()
            if summary:
                latest.update(summary)
                
            return jsonify({"success": True, "data": latest})
        else:
            # 没历史记录时去抓一次
            data, error_msg = fetch_gold_price()
            if data:
                with lock:
                    price_history.append(data)
                save_data()
                return jsonify({"success": True, "data": data})
            else:
                return jsonify({"success": False, "message": error_msg or "无法初始化基础数据"})
            
    return jsonify({"success": False, "message": "系统错误，无法读取历史记录"})


@price_bp.route('/api/history')
def get_history():
    """获取历史价格数据"""
    with lock:
        history_list = list(price_history)
    return jsonify({"success": True, "data": history_list})


@price_bp.route('/api/calculate', methods=['POST'])
def calculate():
    """计算盈利目标"""
    req_data = request.get_json()
    buy_price = req_data.get('buy_price', 0)
    current_price = req_data.get('current_price', 0)
    
    if buy_price <= 0:
        return jsonify({"success": False, "message": "买入价格必须大于0"})
    
    targets = calculate_target_prices(buy_price)
    current_profit = calculate_current_profit(buy_price, current_price)
    
    return jsonify({
        "success": True,
        "targets": targets,
        "current_profit": current_profit
    })
