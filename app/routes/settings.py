# -*- coding: utf-8 -*-
"""
设置和记录相关路由
包含预警设置、手动记录等
"""

from flask import Blueprint, jsonify, request
from datetime import datetime

from app.models.state import lock, alert_settings, manual_records
from app.services.persistence import save_data


settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """获取或更新预警设置"""
    if request.method == 'POST':
        req_data = request.get_json()
        with lock:
            alert_settings["high"] = float(req_data.get('high', 0))
            alert_settings["low"] = float(req_data.get('low', 0))
            alert_settings["enabled"] = bool(req_data.get('enabled', False))
            alert_settings["trading_events_enabled"] = bool(req_data.get('trading_events_enabled', True))
        save_data()
        return jsonify({"success": True, "settings": alert_settings})
    
    return jsonify({"success": True, "settings": alert_settings})


@settings_bp.route('/api/record', methods=['POST'])
def add_record():
    """添加手动记录"""
    req_data = request.get_json()
    record = {
        "price": req_data.get('price'),
        "buy_price": req_data.get('buy_price'),
        "profit": req_data.get('profit'),
        "timestamp": datetime.now().timestamp(),
        "time_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "note": req_data.get('note', '')
    }
    
    with lock:
        manual_records.append(record)
    
    save_data()
    return jsonify({"success": True, "record": record})


@settings_bp.route('/api/records')
def get_records():
    """获取所有手动记录"""
    with lock:
        records = list(manual_records)
    return jsonify({"success": True, "data": records})


@settings_bp.route('/api/records/clear', methods=['POST'])
def clear_records():
    """清空手动记录"""
    with lock:
        manual_records.clear()
    save_data()
    return jsonify({"success": True})
