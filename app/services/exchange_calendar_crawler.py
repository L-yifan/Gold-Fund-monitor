# -*- coding: utf-8 -*-
"""
交易所交易日历爬虫模块
从上海证券交易所官网获取A股交易日历
"""

import re
import time
import json
import os
import requests
from datetime import datetime, timedelta

from app.config import (
    EXCHANGE_CALENDAR_URL,
    EXCHANGE_CALENDAR_FILE,
    EXCHANGE_CALENDAR_CACHE_DIR
)


class ExchangeCalendarCrawler:
    """交易所交易日历爬虫"""
    
    def __init__(self):
        self.url = EXCHANGE_CALENDAR_URL
        self.cache_file = EXCHANGE_CALENDAR_FILE
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        cache_dir = os.path.dirname(self.cache_file)
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def _load_cache(self):
        """从文件加载缓存"""
        if not os.path.exists(self.cache_file):
            return None
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[交易所日历] 加载缓存失败: {e}")
            return None
    
    def _save_cache(self, data):
        """保存到文件"""
        try:
            temp_file = self.cache_file + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, self.cache_file)
            return True
        except Exception as e:
            print(f"[交易所日历] 保存缓存失败: {e}")
            return False
    
    def _fetch_page(self):
        """获取上交所页面内容"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            response = requests.get(self.url, headers=headers, timeout=10)
            
            # 使用 latin1 解码，然后再用正确的编码替换
            # 这种方法可以处理各种编码的网页
            content = response.content
            text = response.text
            
            # 检查是否有乱码，如果有尝试修复
            try:
                # 尝试用 gbk 解码二进制内容
                text = content.decode('gbk')
            except:
                pass
            
            return text
            
        except Exception as e:
            print(f"[交易所日历] 获取页面失败: {e}")
            return None
    
    def _parse_date_range(self, text, year=2026):
        """解析日期范围文本，返回日期列表"""
        dates = []
        
        # 匹配格式：X月X日（星期X）至X月X日（星期X）
        pattern = r'(\d{1,2})月(\d{1,2})日[^\d至]*至[^\d]*(\d{1,2})月(\d{1,2})日'
        match = re.search(pattern, text)
        
        if match:
            start_month = int(match.group(1))
            start_day = int(match.group(2))
            end_month = int(match.group(3))
            end_day = int(match.group(4))
            
            try:
                start_date = datetime(year, start_month, start_day)
                end_date = datetime(year, end_month, end_day)
                
                current = start_date
                while current <= end_date:
                    dates.append(current.strftime("%Y-%m-%d"))
                    current += timedelta(days=1)
            except Exception as e:
                print(f"[交易所日历] 日期解析错误: {e}")
        
        return dates
    
    def _find_first_trading_day(self, text, year=2026):
        """从文本中找到首个交易日"""
        # 匹配格式：X月X日（星期X）起照常开市
        pattern = r'(\d{1,2})月(\d{1,2})日[^\d]*起照常开市'
        match = re.search(pattern, text)
        
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            return f"{year}-{month:02d}-{day:02d}"
        
        return None
    
    def parse_year_from_content(self, content, year=2026):
        """解析页面内容，提取指定年份的休市安排"""
        holidays = {}
        first_trading_days = {}
        
        # 使用正则直接搜索内容
        # 先找到包含年份的区块
        # 格式类似：<td>2月15日（星期日）至2月23日（星期一）休市，2月24日（星期二）起照常开市</td>
        
        # 匹配所有包含日期范围的行
        # 格式：X月X日（周X）至X月X日（周X）休市，X月X日（周X）起照常开市
        holiday_names = ['元旦', '春节', '清明节', '劳动节', '端午节', '中秋节', '国庆节']
        
        # 直接在内容中搜索
        for holiday_name in holiday_names:
            # 查找包含该节假日名称的行
            pattern = rf'{holiday_name}：?([^至]+至[^休]+)休市([^开]+)?开市?'
            match = re.search(pattern, content)
            
            if match:
                date_range_text = match.group(1) + '至' + match.group(2) if match.group(2) else match.group(1)
                
                # 解析日期范围
                dates = self._parse_date_range(date_range_text, year)
                if dates:
                    holidays[holiday_name] = dates
                
                # 查找首个交易日
                full_text = match.group(0)
                first_day = self._find_first_trading_day(full_text, year)
                if first_day:
                    first_trading_days[holiday_name] = first_day
        
        # 备用方案：直接在整个内容中搜索日期范围模式
        if not holidays:
            # 匹配所有类似 "2月15日...至2月23日休市" 的模式
            pattern = r'(\d{1,2})月(\d{1,2})日[^\d至]*至[^\d]*(\d{1,2})日[^\d]*休市'
            for match in re.finditer(pattern, content):
                try:
                    start_month = int(match.group(1))
                    start_day = int(match.group(2))
                    end_month = int(match.group(3))
                    
                    # 简单判断是哪个节日
                    if start_month == 1:
                        name = '元旦'
                    elif start_month == 2 and start_day >= 14:
                        name = '春节'
                    elif start_month == 4:
                        name = '清明节'
                    elif start_month == 5:
                        name = '劳动节'
                    elif start_month == 6:
                        name = '端午节'
                    elif start_month == 9:
                        name = '中秋节'
                    elif start_month == 10:
                        name = '国庆节'
                    else:
                        continue
                    
                    if name not in holidays:
                        # 解析日期
                        dates = self._parse_date_range(match.group(0), year)
                        if dates:
                            holidays[name] = dates
                except:
                    continue
        
        if not holidays:
            print(f"[交易所日历] 未能解析出任何节假日")
            return None
        
        # 生成所有休市日期
        all_dates = set()
        for dates in holidays.values():
            all_dates.update(dates)
        
        return {
            "year": year,
            "holidays": holidays,
            "first_trading_days": first_trading_days,
            "all_holiday_dates": sorted(all_dates)
        }
    
    def crawl_year(self, year=None):
        """爬取指定年份的交易日历"""
        if year is None:
            year = datetime.now().year
        
        # 尝试获取页面
        content = self._fetch_page()
        if not content:
            print(f"[交易所日历] 爬取失败，使用缓存数据")
            return self._load_from_cache(year)
        
        # 解析内容
        result = self.parse_year_from_content(content, year)
        if not result:
            return self._load_from_cache(year)
        
        # 更新缓存
        self._update_cache(result)
        
        return result
    
    def _load_from_cache(self, year):
        """从缓存加载"""
        cache = self._load_cache()
        if not cache:
            return None
        
        calendars = cache.get("calendars", {})
        if str(year) in calendars:
            return calendars[str(year)]
        
        # 尝试找最近的年份
        for y in range(year, year - 3, -1):
            if str(y) in calendars:
                print(f"[交易所日历] 使用缓存的 {y} 年数据")
                return calendars[str(y)]
        
        return None
    
    def _update_cache(self, new_data):
        """更新缓存"""
        year = new_data.get("year")
        
        cache = self._load_cache() or {
            "metadata": {
                "version": "3.0",
                "source": "sse_crawler",
                "url": self.url,
                "last_updated": datetime.now().isoformat()
            },
            "calendars": {}
        }
        
        cache["calendars"][str(year)] = new_data
        cache["metadata"]["last_updated"] = datetime.now().isoformat()
        
        self._save_cache(cache)
        print(f"[交易所日历] 已更新 {year} 年数据，共 {len(new_data.get('all_holiday_dates', []))} 天休市")
    
    def get_holidays(self, year=None):
        """获取指定年份的休市日期集合"""
        data = self.crawl_year(year)
        if data:
            return set(data.get("all_holiday_dates", []))
        return set()
    
    def get_first_trading_day(self, holiday_name, year=None):
        """获取指定节假日后的首个交易日"""
        data = self.crawl_year(year)
        if data:
            return data.get("first_trading_days", {}).get(holiday_name)
        return None


# 全局爬虫实例
_crawler = None


def get_crawler():
    """获取爬虫单例"""
    global _crawler
    if _crawler is None:
        _crawler = ExchangeCalendarCrawler()
    return _crawler


def fetch_exchange_holidays(year=None):
    """获取交易所休市日期（快捷函数）"""
    return get_crawler().get_holidays(year)


if __name__ == "__main__":
    # 测试
    print("=== 测试交易所日历爬虫 ===")
    crawler = ExchangeCalendarCrawler()
    
    # 爬取2026年数据
    result = crawler.crawl_year(2026)
    
    if result:
        print(f"\n年份: {result['year']}")
        print(f"\n节假日明细:")
        for name, dates in result.get("holidays", {}).items():
            print(f"  {name}: {dates}")
        
        print(f"\n所有休市日期 ({len(result['all_holiday_dates'])}天):")
        print(result["all_holiday_dates"])
        
        print(f"\n首个交易日:")
        for name, date in result.get("first_trading_days", {}).items():
            print(f"  {name}后: {date}")
    else:
        print("获取失败")
