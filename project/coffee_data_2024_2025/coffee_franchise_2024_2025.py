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
    """'연도 | 폐점률 | 연초→연말' 형태의 표에서 연도별 수치를 추출."""
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header = clean(rows[0].get_text(" ", strip=True))
        if "폐점률" not in header or "연도" not in header:
            continue

        for tr in rows[1:]:
            cells = [clean(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            if number(cells[0]) != year:
                continue

            rate = number(cells[1].replace("%", ""), as_float=True)
            start_count, end_count = "", ""
            if len(cells) >= 3:
                nums = re.findall(r"\d[\d,]*", cells[2])
                if len(nums) >= 2:
                    start_count = number(nums[0])
                    end_count = number(nums[1])
            return start_count, end_count, rate
    return "", "", ""


def parse_regional_sales(soup, brand, url):
    records = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header = clean(rows[0].get_text(" ", strip=True))
        if "연평균매출" not in header or "지역" not in header:
            continue

        for tr in rows[1:]:
            cells = [clean(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
            if len(cells) < 3:
                continue
            records.append({
                "브랜드": brand,
                "지역": cells[0],
                "가맹점수_지역단위": number(cells[1]),
                "연평균매출_만원_원자료": cells[2],
                "면적당매출_원자료": cells[3] if len(cells) > 3 else "",
                "페이지표시연도": 2025,
                "자료출처": url
            })
    return records


def parse_brand_page(brand, url):
    soup = fetch_soup(url)
    yearly_records = []

    for year in YEARS:
        start_count, end_count, closure_rate = parse_year_trend(soup, year)
        record = {
            "브랜드": brand,
            "연도": year,
            "연초가맹점수": start_count,
            "연말가맹점수": end_count,
            "폐점률_pct": closure_rate,
            "신규개점수": "",
            "계약종료수": "",
            "계약해지수": "",
            "전국연평균매출_만원_원자료": "",
            "서울연말가맹점수_시도단위": "",
            "서울연평균매출_만원_원자료": "",
            "브랜드페이지": url,
            "자료출처": url
        }

        # 현재 페이지가 2025 팩트시트일 때, 2025 요약값을 보충
        if year == 2025:
            page_text = clean(soup.get_text(" ", strip=True))
            m_end = re.search(r"연말\s*가맹점\s*([\d,]+)\s*개", page_text)
            m_new = re.search(r"신규\s*([\d,]+)", page_text)
            m_contract_end = re.search(r"종료\s*([\d,]+)", page_text)
            m_cancel = re.search(r"해지\s*([\d,]+)", page_text)
            if m_end:
                record["연말가맹점수"] = number(m_end.group(1))
            if m_new:
                record["신규개점수"] = number(m_new.group(1))
            if m_contract_end:
                record["계약종료수"] = number(m_contract_end.group(1))
            if m_cancel:
                record["계약해지수"] = number(m_cancel.group(1))

        yearly_records.append(record)

    # 상세 페이지의 매출 표는 대체로 2025 팩트시트 표시값이므로 2025 행에 기록
    regional = parse_regional_sales(soup, brand, url)
    for item in regional:
        if item["지역"] == "전체":
            for record in yearly_records:
                if record["연도"] == 2025:
                    record["전국연평균매출_만원_원자료"] = item["연평균매출_만원_원자료"]
        elif item["지역"] == "서울":
            for record in yearly_records:
                if record["연도"] == 2025:
                    record["서울연말가맹점수_시도단위"] = item["가맹점수_지역단위"]
                    record["서울연평균매출_만원_원자료"] = item["연평균매출_만원_원자료"]

    return yearly_records, regional


def make_missing_fields(brand_df):
    rows = []
    for brand in brand_df["브랜드"]:
        rows.append({
            "브랜드": brand,
            "2024_서울25개구_가맹점수": "",
            "2024_서울25개구_직영점수": "",
            "2025_서울25개구_가맹점수": "",
            "2025_서울25개구_직영점수": "",
            "2024_전국직영점수": "",
            "2025_전국직영점수": "",
            "2024_월평균매출": "",
            "2025_월평균매출": "",
            "2024_창업혜택": "",
            "2025_창업혜택": "",
            "비고": "이 사이트에서 확인되지 않은 항목은 추정하지 않고 공란 처리"
        })
    return pd.DataFrame(rows)


def main():
    print("커피 프랜차이즈 2024~2025 수집을 시작합니다.")
    brand_df = get_brand_list()
    print(f"카테고리 페이지에서 브랜드 {len(brand_df)}개 확인")

    limit = len(brand_df) if MAX_BRANDS is None else min(MAX_BRANDS, len(brand_df))
    yearly_all, regional_all = [], []

    for i, row in brand_df.head(limit).iterrows():
        brand, url = row["브랜드"], row["브랜드페이지"]
        if not url:
            continue
        print(f"[{i + 1}/{limit}] {brand}")
        try:
            yearly, regional = parse_brand_page(brand, url)
            yearly_all.extend(yearly)
            regional_all.extend(regional)
        except Exception as exc:
            print("  수집 오류:", exc)
            for year in YEARS:
                yearly_all.append({
                    "브랜드": brand, "연도": year,
                    "수집오류": str(exc), "브랜드페이지": url,
                    "자료출처": url
                })
        time.sleep(DELAY_SECONDS)

    yearly_df = pd.DataFrame(yearly_all)
    regional_df = pd.DataFrame(regional_all)
    missing_df = make_missing_fields(brand_df)

    top5 = brand_df.head(5).copy()
    top5.insert(0, "순위", range(1, len(top5) + 1))

    brand_df.to_csv(os.path.join(OUT_DIR, "brand_list_2025.csv"), index=False, encoding="utf-8-sig")
    yearly_df.to_csv(os.path.join(OUT_DIR, "yearly_2024_2025.csv"), index=False, encoding="utf-8-sig")
    regional_df.to_csv(os.path.join(OUT_DIR, "region_sales_2025.csv"), index=False, encoding="utf-8-sig")
    missing_df.to_csv(os.path.join(OUT_DIR, "missing_fields.csv"), index=False, encoding="utf-8-sig")

    excel_path = os.path.join(OUT_DIR, "coffee_franchise_2024_2025.xlsx")
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        top5.to_excel(writer, sheet_name="상위5개_2025표시", index=False)
        brand_df.to_excel(writer, sheet_name="브랜드전체_2025표시", index=False)
        yearly_df.to_excel(writer, sheet_name="연도별_2024_2025", index=False)
        regional_df.to_excel(writer, sheet_name="지역별매출_2025표시", index=False)
        missing_df.to_excel(writer, sheet_name="사이트미제공항목", index=False)

    print("\n완료!")
    print("Excel 파일:", os.path.abspath(excel_path))
    print("CSV 폴더:", os.path.abspath(OUT_DIR))
    print("서울 25개 구별 가맹/직영 수와 창업혜택은 사이트에 없으면 공란으로 남깁니다.")


if __name__ == "__main__":
    main()
