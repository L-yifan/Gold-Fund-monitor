# -*- coding: utf-8 -*-
"""
金价数据抓取模块
包含多数据源抓取实现和熔断机制
"""

import re
import time
import json
import requests
from datetime import datetime

from app.config import (
    DATA_SOURCES, HEADERS, MAX_FAIL_COUNT, MUTE_DURATION
)


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


def fetch_from_tencent(source_config):
    """
    从腾讯财经获取 Au99.99 实时价格
    """
    try:
        url = "http://qt.gtimg.cn/q=s_shau9999"
        response = requests.get(url, headers=HEADERS, timeout=source_config.get('timeout', 3))
        text = response.text
        
        # 格式: v_s_shau9999="1~黄金Au9999~shau9999~550.45~0.12~0.02~...~";
        match = re.search(r'"([^"]+)"', text)
        if not match:
            return None
            
        parts = match.group(1).split('~')
        if len(parts) < 6:
            return None
            
        current_price = float(parts[3])
        change = float(parts[4])
        change_percent = float(parts[5])
        
        # 腾讯简版不含最高最低，尝试使用全版以获取更全数据
        full_url = "http://qt.gtimg.cn/q=shau9999"
        full_res = requests.get(full_url, headers=HEADERS, timeout=2)
        full_match = re.search(r'"([^"]+)"', full_res.text)
        
        open_price = current_price
        high_price = current_price
        low_price = current_price
        yesterday_close = current_price - change
        
        if full_match:
            f_parts = full_match.group(1).split('~')
            if len(f_parts) > 34:
                yesterday_close = float(f_parts[4])
                open_price = float(f_parts[5])
                high_price = float(f_parts[33])
                low_price = float(f_parts[34])

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


def fetch_from_netease(source_config):
    """
    从网易财经获取 Au99.99 实时价格
    """
    try:
        # 网易接口，118AU9999 是 SGE Au99.99 的代码
        url = "http://api.money.126.net/data/feed/118AU9999,money.api"
        response = requests.get(url, headers=HEADERS, timeout=source_config.get('timeout', 3))
        
        # 网易返回的是 _ntes_quote_callback({...});
        text = response.text
        match = re.search(r'\((.*)\)', text)
        if not match:
            return None
            
        data = json.loads(match.group(1))
        d = data.get('118AU9999')
        if not d:
            return None
            
        current_price = d.get('price', 0)
        if current_price <= 0:
            return None
            
        open_price = d.get('open', current_price)
        high_price = d.get('high', current_price)
        low_price = d.get('low', current_price)
        yesterday_close = d.get('yestclose', current_price)
        change = d.get('updown', 0)
        change_percent = d.get('percent', 0) * 100
        
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
    "sina": fetch_from_sina,
    "tencent": fetch_from_tencent,
    "netease": fetch_from_netease
}


def fetch_gold_price():
    """
    从配置的数据源列表中循环获取价格，包含熔断机制
    
    返回:
        (data, error_msg): 成功时 data 为价格数据字典，error_msg 为 None
                          失败时 data 为 None，error_msg 为错误信息
    """
    now_ts = time.time()
    enabled_sources = [s for s in DATA_SOURCES if s.get('enabled', False)]
    
    if not enabled_sources:
        return None, "没有启用的数据源"
        
    muted_count = 0
    for source in enabled_sources:
        # 检查是否处于熔断期
        if source.get('mute_until', 0) > now_ts:
            muted_count += 1
            continue
            
        handler = SOURCE_HANDLERS.get(source['type'])
        if not handler:
            continue
            
        # 尝试获取数据
        data = handler(source)
        if data:
            # 成功获取，重置失败计数
            source['fail_count'] = 0
            source['mute_until'] = 0
            return data, None
        else:
            # 失败处理：增加计数并检查是否触发熔断
            source['fail_count'] = source.get('fail_count', 0) + 1
            if source['fail_count'] >= MAX_FAIL_COUNT:
                print(f"!!! [熔断] {source['name']} 连续失败 {MAX_FAIL_COUNT} 次，进入 {MUTE_DURATION}s 冷却期")
                source['mute_until'] = now_ts + MUTE_DURATION
                source['fail_count'] = 0 # 触发后重置，等待冷却后重新开始
            
    if muted_count == len(enabled_sources):
        return None, "所有数据源均处于熔断冷却期，请稍后再试"
        
    return None, "所有可用数据源均获取失败，请检查网络或稍后重试"
