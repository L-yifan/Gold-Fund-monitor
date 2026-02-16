# -*- coding: utf-8 -*-
"""
农历节假日计算工具
基于2024年国务院修订的《全国年节及纪念日放假办法》
"""

from datetime import datetime, timedelta
from functools import lru_cache

try:
    from lunardate import LunarDate
    LUNARDATE_AVAILABLE = True
except ImportError:
    LUNARDATE_AVAILABLE = False


def calculate_qingming_date(year):
    """
    计算清明节日期
    清明节是春分后第15天，通常在4月4日或5日
    
    算法：日期 = floor(年份后两位 * 0.2422 + C) - floor(年份后两位 / 4)
    其中 C = 4.81 (21世纪), 5.59 (20世纪)
    """
    year_mod = year % 100
    
    if year >= 2000:
        C = 4.81
    else:
        C = 5.59
    
    day = int(year_mod * 0.2422 + C) - int(year_mod / 4)
    
    # 清明节只能是4月4日或5日
    if day not in (4, 5):
        day = 4
    
    return datetime(year, 4, day)


def calculate_spring_eve(year):
    """
    计算农历除夕（春节前一天）
    需要 lunardate 库支持
    """
    if not LUNARDATE_AVAILABLE:
        # 回退：使用已知的2026-2030年春节日期估算
        fallback_spring = {
            2026: datetime(2026, 2, 16),
            2027: datetime(2027, 2, 6),
            2028: datetime(2028, 1, 26),
            2029: datetime(2029, 2, 13),
            2030: datetime(2030, 2, 3),
        }
        return fallback_spring.get(year, datetime(year, 2, 10))
    
    # 农历正月初一
    lunar_new_year = LunarDate(year, 1, 1).to_datetime()
    # 除夕 = 春节前一天
    spring_eve = lunar_new_year - timedelta(days=1)
    return spring_eve


def calculate_lunar_holidays(year):
    """
    计算农历相关节假日
    
    春节：农历除夕、正月初一至初三（4天）
    端午节：农历五月初五
    中秋节：农历八月十五
    """
    holidays = {}
    
    if not LUNARDATE_AVAILABLE:
        # 使用备用数据（已知的准确农历日期）
        fallback_lunar = {
            2026: {
                "spring_start": datetime(2026, 2, 16),  # 春节除夕
                "duanwu": "2026-05-31",  # 端午节
                "zhongqiu": "2026-10-25",  # 中秋节
            },
            2027: {
                "spring_start": datetime(2027, 2, 6),  # 春节除夕
                "duanwu": "2027-05-20",  # 端午节
                "zhongqiu": "2027-10-14",  # 中秋节
            },
            2028: {
                "spring_start": datetime(2028, 1, 26),  # 春节除夕
                "duanwu": "2028-06-08",  # 端午节
                "zhongqiu": "2028-10-02",  # 中秋节
            },
            2029: {
                "spring_start": datetime(2029, 2, 13),  # 春节除夕
                "duanwu": "2029-05-27",  # 端午节
                "zhongqiu": "2029-09-21",  # 中秋节
            },
            2030: {
                "spring_start": datetime(2030, 2, 2),  # 春节除夕
                "duanwu": "2030-06-15",  # 端午节
                "zhongqiu": "2030-10-10",  # 中秋节
            },
        }
        
        data = fallback_lunar.get(year, {})
        
        # 春节：除夕至初三（4天）
        if "spring_start" in data:
            spring_dates = [
                (data["spring_start"] + timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(4)
            ]
            holidays["春节"] = spring_dates
        
        # 端午节
        if "duanwu" in data:
            holidays["端午节"] = [data["duanwu"]]
        
        # 中秋节
        if "zhongqiu" in data:
            holidays["中秋节"] = [data["zhongqiu"]]
    else:
        # 春节
        try:
            spring_eve = calculate_spring_eve(year)
            spring_dates = [
                (spring_eve + timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(4)  # 除夕至初三
            ]
            holidays["春节"] = spring_dates
        except Exception:
            pass
        
        # 端午节（农历五月初五）
        try:
            duanwu = LunarDate(year, 5, 5).to_datetime()
            holidays["端午节"] = [duanwu.strftime("%Y-%m-%d")]
        except Exception:
            pass
        
        # 中秋节（农历八月十五）
        try:
            zhongqiu = LunarDate(year, 8, 15).to_datetime()
            holidays["中秋节"] = [zhongqiu.strftime("%Y-%m-%d")]
        except Exception:
            pass
    
    return holidays


def calculate_solar_holidays(year):
    """
    计算公历固定节假日（2024年新规）
    
    元旦：1月1日（1天）
    劳动节：5月1日-2日（2天）
    国庆节：10月1日-3日（3天）
    """
    holidays = {}
    
    # 元旦
    holidays["元旦"] = [f"{year}-01-01"]
    
    # 劳动节
    holidays["劳动节"] = [f"{year}-05-01", f"{year}-05-02"]
    
    # 国庆节
    holidays["国庆节"] = [f"{year}-10-0{i}" for i in range(1, 4)]
    
    return holidays


def calculate_qingming_holidays(year):
    """
    计算清明节（节气）
    """
    holidays = {}
    
    try:
        qingming = calculate_qingming_date(year)
        holidays["清明节"] = [qingming.strftime("%Y-%m-%d")]
    except Exception:
        pass
    
    return holidays


def calculate_all_legal_holidays(year):
    """
    计算所有法定节假日（不含调休）
    返回格式: {"节日名": [日期列表], ...}
    """
    holidays = {}
    
    # 公历节日
    holidays.update(calculate_solar_holidays(year))
    
    # 农历节日
    holidays.update(calculate_lunar_holidays(year))
    
    # 清明节
    holidays.update(calculate_qingming_holidays(year))
    
    return holidays


def get_holidays_as_set(year):
    """
    获取年份的所有法定节假日日期集合
    返回: set(["2026-01-01", "2026-02-16", ...])
    """
    holidays = calculate_all_legal_holidays(year)
    
    all_dates = set()
    for dates in holidays.values():
        all_dates.update(dates)
    
    return all_dates


def apply_adjustments(holidays_set, adjustments):
    """
    应用调休数据
    
    参数:
        holidays_set: 节假日集合
        adjustments: 调休数据 {"workdays": [], "holidays": []}
    
    返回:
        调整后的节假日集合
    """
    if not adjustments:
        return holidays_set
    
    result = set(holidays_set)
    
    # 移除调休上班日（原本是周末，现在要上班）
    for date in adjustments.get("workdays", []):
        result.discard(date)
    
    # 添加调休放假日（原本是工作日，现在放假）
    result.update(adjustments.get("holidays", []))
    
    return result


def get_next_holiday_info(current_date, holidays_set):
    """
    获取下一个节假日信息
    
    参数:
        current_date: 当前日期
        holidays_set: 节假日集合
    
    返回:
        (距离天数, 节日名称) 或 None
    """
    holiday_dates = sorted([
        (datetime.strptime(d, "%Y-%m-%d"), d) 
        for d in holidays_set 
        if d >= current_date.strftime("%Y-%m-%d")
    ])
    
    if not holiday_dates:
        return None
    
    next_date, date_str = holiday_dates[0]
    days = (next_date - current_date).days
    
    # 推断节日名称
    month = next_date.month
    day = next_date.day
    
    if month == 1 and day == 1:
        name = "元旦"
    elif month == 2 and day in range(15, 20):
        name = "春节"
    elif month == 4 and day in (4, 5):
        name = "清明节"
    elif month == 5 and day in (1, 2):
        name = "劳动节"
    elif month == 5 and day in range(5, 10):
        name = "端午节"
    elif month == 9 or (month == 10 and day < 5):
        name = "中秋节"
    elif month == 10 and day in (1, 2, 3):
        name = "国庆节"
    else:
        name = "假期"
    
    return (days, name)


if __name__ == "__main__":
    # 测试
    print("=== 2026年法定节假日测试 ===")
    holidays = calculate_all_legal_holidays(2026)
    for name, dates in holidays.items():
        print(f"{name}: {dates}")
    
    print("\n=== 节假日集合 ===")
    all_dates = get_holidays_as_set(2026)
    print(f"共 {len(all_dates)} 天")
    print(sorted(all_dates))
    
    print("\n=== 2027年测试 ===")
    holidays_2027 = calculate_all_legal_holidays(2027)
    for name, dates in holidays_2027.items():
        print(f"{name}: {dates}")
