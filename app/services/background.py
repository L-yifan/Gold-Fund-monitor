# -*- coding: utf-8 -*-
"""
后台任务模块
包含后台定时抓取金价等任务
"""

import time

from app.models.state import lock, price_history
from app.services.gold_fetcher import fetch_gold_price
from app.services.persistence import save_data


def background_fetch_loop():
    """后台持续抓取金价线程，确保即使网页关闭也能记录数据"""
    print("后台抓取线程启动...")
    
    while True:
        try:
            data, _ = fetch_gold_price()
            if data:
                with lock:
                    # 添加到历史记录
                    price_history.append(data)
                # 记录成功后保存数据（内部包含清理逻辑）
                save_data()
            
            # 每 5 秒采集一次（后台不需要太频繁，平衡性能与连续性）
            time.sleep(5)
        except Exception as e:
            print(f"后台抓取异常: {e}")
            time.sleep(30) # 异常后等待较长时间再重试
