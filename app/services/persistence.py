# -*- coding: utf-8 -*-
"""
数据持久化模块
负责数据的保存、加载和清理，包含自动迁移逻辑
"""

import os
import json
import shutil
from datetime import datetime

from app.config import (
    DATA_FILE, OLD_DATA_FILE, DATA_DIR,
    RECORDS_KEEP_DAYS
)
from app.models.state import (
    lock, price_history, manual_records, alert_settings,
    fund_watchlist, fund_holdings, fund_portfolios
)


def _get_today_start_timestamp():
    """获取当天自然日零点的时间戳（本地时区）"""
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
    return today_start.timestamp()


def cleanup_expired_data():
    """清理过期的数据，保持文件精简"""
    # 注意：此函数必须在锁保护下调用，以避免与状态修改的竞态
    
    # 1. 清理历史价格（仅保留当天自然日内的数据）
    # 计算今日零点时间戳
    today_start_ts = _get_today_start_timestamp()
    # 因为 price_history 是有序的，我们可以直接根据时间戳过滤
    while price_history and price_history[0].get('timestamp', 0) < today_start_ts:
        price_history.popleft()
        
    # 2. 清理手动记录 (7天)
    now_ts = datetime.now().timestamp()
    record_threshold = now_ts - (RECORDS_KEEP_DAYS * 86400)
    # 使用原地切片赋值，避免破坏与 state.manual_records 的共享引用
    manual_records[:] = [r for r in manual_records if r.get('timestamp', 0) > record_threshold]


def save_data():
    """将数据保存到 JSON 文件 (原子写入模式)"""
    with lock:
        try:
            # 确保数据目录存在
            os.makedirs(DATA_DIR, exist_ok=True)
            
            # 在保存前执行清理
            cleanup_expired_data()
            
            data = {
                "manual_records": manual_records,
                "price_history": list(price_history),
                "alert_settings": alert_settings,
                "fund_watchlist": fund_watchlist,
                "fund_holdings": fund_holdings,
                "fund_portfolios": fund_portfolios
            }
            
            # 使用临时文件进行原子写入
            tmp_file = DATA_FILE + ".tmp"
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())  # 确保数据写入物理磁盘
            
            # 原子替换原文件
            os.replace(tmp_file, DATA_FILE)
        except Exception as e:
            print(f"保存数据失败: {e}")


def _migrate_old_data_file():
    """
    自动迁移旧版本数据文件到新位置
    从根目录的 data.json 迁移到 data/data.json
    """
    # 如果新路径已存在，无需迁移
    if os.path.exists(DATA_FILE):
        return
    
    # 如果旧路径存在，执行迁移
    if os.path.exists(OLD_DATA_FILE):
        try:
            # 确保目标目录存在
            os.makedirs(DATA_DIR, exist_ok=True)
            # 移动文件
            shutil.move(OLD_DATA_FILE, DATA_FILE)
            print(f"[迁移] 数据文件已从 {OLD_DATA_FILE} 移动到 {DATA_FILE}")
        except Exception as e:
            print(f"[迁移] 数据文件迁移失败: {e}")
            # 迁移失败时尝试复制
            try:
                shutil.copy2(OLD_DATA_FILE, DATA_FILE)
                print(f"[迁移] 数据文件已复制到 {DATA_FILE}（原文件保留）")
            except Exception as e2:
                print(f"[迁移] 数据文件复制也失败: {e2}")


def load_data():
    """从 JSON 文件加载数据"""
    global manual_records, alert_settings, fund_watchlist, fund_holdings, fund_portfolios
    
    # 执行自动迁移检查
    _migrate_old_data_file()
    
    if os.path.exists(DATA_FILE):
        try:
            with lock:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 加载手动记录
                    loaded_records = data.get("manual_records", [])
                    manual_records.clear()
                    manual_records.extend(loaded_records)
                    
                    # 加载历史价格
                    history = data.get("price_history", [])
                    price_history.clear()
                    price_history.extend(history)
                    
                    # 加载预警配置
                    saved_alerts = data.get("alert_settings", {})
                    alert_settings.update(saved_alerts)
                    
                    # 加载自选基金
                    fund_watchlist.clear()
                    fund_watchlist.extend(data.get("fund_watchlist", []))
                    
                    # 加载基金持仓
                    fund_holdings.clear()
                    fund_holdings.extend(data.get("fund_holdings", []))
                    
                    # 加载基金重仓股内容缓存
                    fund_portfolios.clear()
                    fund_portfolios.update(data.get("fund_portfolios", {}))
                    
                print(f"成功加载数据: {len(manual_records)} 条记录, {len(price_history)} 条历史, "
                      f"{len(fund_watchlist)} 个自选基金, {len(fund_holdings)} 条持仓, "
                      f"{len(fund_portfolios)} 个重仓股缓存")
                
                # 加载后立即执行清理，避免跨日数据在首次 save_data() 前可见
                cleanup_expired_data()
            
        except Exception as e:
            print(f"加载数据失败: {e}")
    else:
        print(f"数据文件不存在: {DATA_FILE}，将使用默认空数据")
