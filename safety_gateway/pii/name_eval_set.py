"""Eval-only full names. Not used as a production lookup.

50 大姓（內政部戶政開放資料 112 年姓氏排名）× 20 常見名字
（內政部《全國姓名統計分析》新聞稿：家豪／淑芬、承恩／品妍等）= 1000。
"""

from __future__ import annotations

# https://data.gov.tw ／ 內政部「各年齡層前十大姓人口數」112 年 ranking
MOI_TOP_SURNAMES: tuple[str, ...] = tuple(
    "陳林黃張李王吳劉蔡楊許鄭謝洪郭邱曾廖賴徐周葉蘇莊江呂何蕭羅高潘簡朱鍾游彭詹施胡沈余盧梁趙顏柯翁魏孫戴"
)

# 內政部常見名＋各世代熱門名（男／女各 10）
MOI_COMMON_GIVENS: tuple[str, ...] = (
    "家豪",
    "志明",
    "建宏",
    "承恩",
    "宥廷",
    "品睿",
    "恩碩",
    "承翰",
    "宇翔",
    "冠廷",
    "淑芬",
    "淑惠",
    "美玲",
    "品妍",
    "子晴",
    "詠晴",
    "采潔",
    "沛恩",
    "子涵",
    "品妤",
)

TOP_1000_FULL_NAMES: tuple[str, ...] = tuple(
    f"{surname}{given}" for surname in MOI_TOP_SURNAMES for given in MOI_COMMON_GIVENS
)

assert len(MOI_TOP_SURNAMES) == 50
assert len(MOI_COMMON_GIVENS) == 20
assert len(TOP_1000_FULL_NAMES) == 1000
assert len(set(TOP_1000_FULL_NAMES)) == 1000
