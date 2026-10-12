# -*- coding: utf-8 -*-
"""
프랑 커피 프랜차이즈 자료 수집기 (2024~2025)
설치: pip install requests beautifulsoup4 pandas openpyxl
실행: python coffee_franchise_2024_2025.py

수집:
- 커피 카테고리 페이지의 브랜드/가맹본부/표시된 가맹점 수/폐점률/창업비용
- 각 브랜드 상세 페이지의 2024·2025 폐점률 추이와 연초·연말 가맹점 수(표에 존재할 때)
- 상세 페이지의 지역별 연평균 매출(페이지에 존재할 때)
- 서울 25개 구별 가맹/직영점 수, 창업혜택 등 사이트에서 제공하지 않는 항목은 별도 공란 시트로 생성

주의:
카테고리 표는 '2025'로 표시된 최신 페이지 데이터이며, 상세 페이지의 연도별 표에서
2024/2025 행을 각각 찾아 저장합니다. 서울 지역 매출은 '서울' 시도 단위이지 25개 구 단위가 아닙니다.
"""

import os
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://franc-kr.pages.dev"
CATEGORY_URL = BASE_URL + "/category/%EC%BB%A4%ED%94%BC/"
OUT_DIR = "coffee_data_2024_2025"
YEARS = (2024, 2025)
DELAY_SECONDS = 0.25
MAX_BRANDS = None  # 테스트는 5, 전체 수집은 None

os.makedirs(OUT_DIR, exist_ok=True)
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
})


def fetch_soup(url):
    response = SESSION.get(url, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, "html.parser")


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def number(value, as_float=False):
    if value is None:
        return ""
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(value).replace(",", ""))
    if not match:
        return ""
    try:
        return float(match.group()) if as_float else int(float(match.group()))
    except ValueError:
        return ""


def get_brand_list():
    soup = fetch_soup(CATEGORY_URL)
    table = soup.select_one("#cat-table") or soup.find("table")
    if table is None:
        raise RuntimeError("브랜드 표를 찾지 못했습니다. 사이트 HTML 구조가 변경되었을 수 있습니다.")

    records = []
    for tr in table.select("tbody tr"):
        link = tr.find("a", href=True)
        cells = [clean(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
        name = clean(tr.get("data-name")) or (clean(link.get_text(" ", strip=True)) if link else "")
        if not name:
            continue

        records.append({
            "브랜드": name,
            "가맹본부": cells[1] if len(cells) > 1 else "",
            "전국가맹점수_카테고리표시": number(tr.get("data-frcs")),
            "폐점률_pct_카테고리표시": number(tr.get("data-rate"), as_float=True),
            "창업비용_원자료_만원": clean(tr.get("data-cost")),
            "브랜드페이지": urljoin(BASE_URL, link["href"]) if link else "",
            "카테고리자료출처": CATEGORY_URL,
            "페이지표시연도": 2025
        })

    if not records:
        raise RuntimeError("브랜드 행을 읽지 못했습니다.")
    df = pd.DataFrame(records).drop_duplicates(subset=["브랜드", "브랜드페이지"])
    df["_sort"] = pd.to_numeric(df["전국가맹점수_카테고리표시"], errors="coerce")
    df = df.sort_values("_sort", ascending=False, na_position="last").drop(columns="_sort")
    return df.reset_index(drop=True)


def parse_year_trend(soup, year):