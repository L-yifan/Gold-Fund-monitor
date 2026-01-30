# -*- coding: utf-8 -*-
"""
国内金价实时监控系统 - 后端服务
数据来源：新浪财经 (上海黄金交易所 Au99.99)
"""

from flask import Flask, render_template, jsonify, request
import requests
import re
import time
from datetime import datetime
from collections import deque
import threading

app = Flask(__name__)

# ==================== 配置 ====================
# 数据源列表（按优先级排序）
DATA_SOURCES = [
    {
        "name": "东方财富",
        "type": "eastmoney",
        "enabled": True,
        "timeout": 5
    },
    {
        "name": "新浪财经",
        "type": "sina",
        "enabled": True,
        "timeout": 5
    },
    {
        "name": "金十数据",
        "type": "jin10",
        "enabled": False,  # 暂不可用
        "timeout": 5
    }
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}

# 存储历史价格数据 (最多保存 720 条，约 1 小时的数据，5秒一条)
MAX_HISTORY_SIZE = 720
price_history = deque(maxlen=MAX_HISTORY_SIZE)

# 用户手动记录的价格快照
manual_records = []

# 线程锁
lock = threading.Lock()


# ==================== 数据获取实现 ====================
def fetch_from_eastmoney(source_config):
    """
    从东方财富获取 Au99.99 实时价格
    """
    try:
        url = "https://push2.eastmoney.com/api/qt/stock/get?secid=118.AU9999&fields=f43,f44,f45,f46,f60,f170"
        response = requests.get(url, headers=HEADERS, timeout=source_config.get('timeout', 5))
        data = response.json()
        
        if data.get('data'):
            d = data['data']
            # 东方财富价格单位是分，需要除以100
            current_price = d.get('f43', 0) / 100
            
            if current_price <= 0:
                return None

            open_price = d.get('f46', 0) / 100
            high_price = d.get('f44', 0) / 100
            low_price = d.get('f45', 0) / 100
            yesterday_close = d.get('f60', 0) / 100
            change_percent = d.get('f170', 0) / 100
            
            change = current_price - yesterday_close
            
            now = datetime.now()
            
            return {
                "price": round(current_price, 2),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "yesterday_close": round(yesterday_close, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "timestamp": now.timestamp(),
                "time_str": now.strftime("%H:%M:%S"),
                "source": source_config['name']
            }
    except Exception as e:
        print(f"[{source_config['name']}] 获取失败: {e}")
    return None


def fetch_from_sina(source_config):
    """
    从新浪财经获取 Au99.99 实时价格
    """
    try:
        url = "https://hq.sinajs.cn/list=gds_au9999"
        headers = {
            "Referer": "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=source_config.get('timeout', 5))
        
        # 处理编码
        content_type = response.headers.get('Content-Type', '').lower()
        if 'charset' in content_type:
             response.encoding = content_type.split('charset=')[-1]
        else:
             response.encoding = 'gbk' # 默认GBK

        text = response.text
        
        match = re.search(r'"([^"]+)"', text)
        if not match:
            return None
        
        data_str = match.group(1)
        parts = data_str.split(',')
        
        if len(parts) < 8:
            return None
        
        current_price = float(parts[1]) if parts[1] else 0
        
        if current_price <= 0:
            return None

        yesterday_close = float(parts[2]) if parts[2] else current_price
        open_price = float(parts[3]) if parts[3] else current_price
        high_price = float(parts[4]) if parts[4] else current_price
        low_price = float(parts[5]) if parts[5] else current_price
            
        change = current_price - yesterday_close
        change_percent = (change / yesterday_close * 100) if yesterday_close else 0
        
        now = datetime.now()
        
        return {
            "price": round(current_price, 2),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "yesterday_close": round(yesterday_close, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "timestamp": now.timestamp(),
            "time_str": now.strftime("%H:%M:%S"),
            "source": source_config['name']
        }
    except Exception as e:
        print(f"[{source_config['name']}] 获取失败: {e}")
    return None

# 数据源处理函数映射
SOURCE_HANDLERS = {
    "eastmoney": fetch_from_eastmoney,
    "sina": fetch_from_sina
    # "jin10": fetch_from_jin10 # 待实现
}

def fetch_gold_price():
    """
    从配置的数据源列表中循环获取价格
    """
    for source in DATA_SOURCES:
        if not source.get('enabled', False):
            continue
            
        handler = SOURCE_HANDLERS.get(source['type'])
        if not handler:
            print(f"未找到类型为 {source['type']} 的处理函数")
            continue
            
        # 尝试获取数据
        data = handler(source)
        if data:
            return data
            
    print("所有可用数据源均获取失败")
    return None


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


# ==================== 路由 ====================
@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/price')
def get_price():
    """获取当前金价"""
    data = fetch_gold_price()
    if data:
        # 添加到历史记录
        with lock:
            price_history.append({
                "price": data["price"],
                "timestamp": data["timestamp"],
                "time_str": data["time_str"]
            })
        return jsonify({"success": True, "data": data})
    else:
        return jsonify({"success": False, "message": "获取数据失败"})


@app.route('/api/history')
def get_history():
    """获取历史价格数据"""
    with lock:
        history_list = list(price_history)
    return jsonify({"success": True, "data": history_list})


@app.route('/api/calculate', methods=['POST'])
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


@app.route('/api/record', methods=['POST'])
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
    
    return jsonify({"success": True, "record": record})


@app.route('/api/records')
def get_records():
    """获取所有手动记录"""
    with lock:
        records = list(manual_records)
    return jsonify({"success": True, "data": records})


@app.route('/api/records/clear', methods=['POST'])
def clear_records():
    """清空手动记录"""
    with lock:
        manual_records.clear()
    return jsonify({"success": True})


# ==================== 启动 ====================
if __name__ == '__main__':
    print("=" * 50)
    print("  国内金价实时监控系统")
    print("  数据来源: 上海黄金交易所 Au99.99")
    print("  访问地址: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
