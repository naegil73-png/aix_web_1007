# -*- coding: utf-8 -*-
"""
프랑 커피 브랜드: 서울·경기 기초자치단체 매장 검색 + 2024~2025 월별 형식 정리

설치:
    pip install requests beautifulsoup4 pandas openpyxl

실행:
    python coffee_seoul_gyeonggi_monthly.py

선택 기능:
- 카카오 로컬 API 키가 있으면 상위 5개 브랜드의 매장을 서울 25개 구 + 경기 시·군 단위로 검색합니다.
- 카카오 검색 결과는 주소 기반 매장 후보 목록입니다. 가맹점/직영점 구분을 보장하지 않습니다.
- 프랑의 공개 자료가 연간값이면 월별 실적을 만들어내지 않습니다. 월별 시트에는 연간 원자료를 표시하고,
  연평균 매출이 있을 때만 12로 나눈 '월평균 환산값'을 별도 열에 기록합니다.
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
KAKAO_API_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
KAKAO_API_KEY = os.getenv("KAKAO_REST_API_KEY")  # 환경변수 권장
OUT_DIR = "coffee_seoul_gyeonggi_monthly"
TOP_N = 5
YEARS = [2024, 2025]
MONTHS = list(range(1, 13))
DELAY = 0.2

SEOUL_DISTRICTS = [
    "강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구",
    "금천구", "노원구", "도봉구", "동대문구", "동작구", "마포구",
    "서대문구", "서초구", "성동구", "성북구", "송파구", "양천구",
    "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구"
]

# 경기도 기초자치단체(시·군). 주소 검색에서 사용할 대표 명칭
GYEONGGI_MUNICIPALITIES = [
    "수원시", "용인시", "고양시", "화성시", "성남시", "부천시", "남양주시",
    "안산시", "평택시", "안양시", "시흥시", "파주시", "김포시", "의정부시",
    "광주시", "하남시", "광명시", "군포시", "양주시", "오산시", "이천시",
    "안성시", "구리시", "의왕시", "포천시", "양평군", "여주시", "동두천시",
    "과천시", "가평군", "연천군"
]

os.makedirs(OUT_DIR, exist_ok=True)
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
})


def fetch_soup(url):
    r = session.get(url, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return BeautifulSoup(r.text, "html.parser")


def clean(v):
    return re.sub(r"\s+", " ", str(v or "")).strip()


def to_num(v, floating=False):
    if v is None:
        return None
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(v).replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group()) if floating else int(float(m.group()))
    except ValueError:
        return None


def get_brand_list():
    soup = fetch_soup(CATEGORY_URL)
    table = soup.select_one("#cat-table") or soup.find("table")
    if table is None:
        raise RuntimeError("브랜드 표를 찾지 못했습니다. 사이트의 HTML 구조가 바뀌었을 수 있습니다.")

    rows = []
    for tr in table.select("tbody tr"):
        a = tr.find("a", href=True)
        brand = clean(tr.get("data-name")) or (clean(a.get_text(" ", strip=True)) if a else "")
        if not brand:
            continue
        rows.append({
            "브랜드": brand,
            "전국가맹점수_사이트표시": to_num(tr.get("data-frcs")),
            "폐점률_pct_사이트표시": to_num(tr.get("data-rate"), True),
            "창업비용_원자료_만원": clean(tr.get("data-cost")),
            "상세페이지": urljoin(BASE_URL, a["href"]) if a else "",
            "목록출처": CATEGORY_URL,
            "목록표시기준연도": 2025
        })
    if not rows:
        raise RuntimeError("브랜드 목록을 찾지 못했습니다.")
    df = pd.DataFrame(rows).drop_duplicates(subset=["브랜드", "상세페이지"])
    df["_sort"] = pd.to_numeric(df["전국가맹점수_사이트표시"], errors="coerce")
    return df.sort_values("_sort", ascending=False, na_position="last").drop(columns="_sort").reset_index(drop=True)


def parse_annual_detail(brand, url):
    """상세 페이지에서 연도별 가맹점 추이와 지역별 연평균매출을 가능한 범위에서 읽음."""
    soup = fetch_soup(url)
    text = clean(soup.get_text(" ", strip=True))
    annual = []

    # 연도 추이 표: 예) 2024 | 24.1% | 79→63
    trend_rows = {}
    for table in soup.find_all("table"):
        trs = table.find_all("tr")
        if not trs:
            continue
        header = clean(trs[0].get_text(" ", strip=True))
        if "폐점률" not in header or "연도" not in header:
            continue
        for tr in trs[1:]:
            cells = [clean(x.get_text(" ", strip=True)) for x in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            year = to_num(cells[0])
            if year in YEARS:
                count_pair = re.findall(r"\d[\d,]*", cells[2]) if len(cells) > 2 else []
                start_count = to_num(count_pair[0]) if len(count_pair) >= 1 else None
                end_count = to_num(count_pair[1]) if len(count_pair) >= 2 else None
                trend_rows[int(year)] = {
                    "연초가맹점수": start_count,
                    "연말가맹점수": end_count,
                    "폐점률_pct": to_num(cells[1], True)
                }

    # 2025 상세 요약값(문구가 있을 경우)
    summary_2025 = {}
    patterns = {
        "연말가맹점수": r"연말\s*가맹점\s*([\d,]+)\s*개",
        "신규개점수": r"신규\s*([\d,]+)",
        "계약종료수": r"계약종료\s*([\d,]+)",
        "계약해지수": r"해지\s*([\d,]+)"
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if m:
            summary_2025[key] = to_num(m.group(1))

    # 지역별 연평균매출 표(시·도 단위)
    regional = []
    for table in soup.find_all("table"):
        trs = table.find_all("tr")
        if not trs:
            continue
        header = clean(trs[0].get_text(" ", strip=True))
        if "연평균매출" not in header or "지역" not in header:
            continue
        for tr in trs[1:]:
            cells = [clean(x.get_text(" ", strip=True)) for x in tr.find_all(["td", "th"])]
            if len(cells) < 3:
                continue
            regional.append({
                "브랜드": brand,
                "지역_시도": cells[0],
                "가맹점수": to_num(cells[1]),
                "연평균매출_만원_원자료": cells[2],
                "면적당매출_원자료": cells[3] if len(cells) > 3 else "",
                "자료기준": "사이트 상세 페이지 표시값; 기본적으로 연간 자료",
                "출처": url
            })

    for year in YEARS:
        row = {
            "브랜드": brand,
            "연도": year,
            "연초가맹점수": None,
            "연말가맹점수": None,
            "폐점률_pct": None,
            "신규개점수": None,
            "계약종료수": None,
            "계약해지수": None,
            "상세페이지": url
        }
        row.update(trend_rows.get(year, {}))
        if year == 2025:
            row.update(summary_2025)
        annual.append(row)

    return annual, regional


def make_monthly_rows(annual_df, regional_df):
    """
    월별 24행/브랜드 생성.
    연도별 가맹점 수·폐점률은 월별 실적이 아니므로 월마다 복제하지 않고 연간값 열에만 둠.
    연평균 매출 범위의 양 끝값을 /12 해 월평균 범위로 환산(추정 월별 실적이 아님).
    """
    regional_lookup = {}
    for _, r in regional_df.iterrows():
        regional_lookup[(r["브랜드"], r["지역_시도"])] = r.get("연평균매출_만원_원자료", "")

    rows = []
    for _, annual in annual_df.iterrows():
        brand = annual["브랜드"]
        year = int(annual["연도"])
        # 사이트의 지역 매출 표는 시도 단위. 서울·경기만 월평균 환산값을 준비.
        for province in ["서울", "경기"]:
            raw_sales = regional_lookup.get((brand, province), "")
            nums = [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*(?:\.\d+)?", str(raw_sales))]
            monthly_range = ""
            if nums:
                if len(nums) >= 2:
                    monthly_range = f"{nums[0] / 12:.1f}~{nums[1] / 12:.1f} 만원/월 (연평균÷12 환산)"
                else:
                    monthly_range = f"{nums[0] / 12:.1f} 만원/월 (연평균÷12 환산)"
            for month in MONTHS:
                rows.append({
                    "브랜드": brand,
                    "연도": year,
                    "월": month,
                    "지역_시도": province,
                    "월별실적자료": "사이트에 월별 실적 없음",
                    "월평균매출_환산값": monthly_range if year == 2025 else "",
                    "연초가맹점수_연간자료": annual.get("연초가맹점수"),
                    "연말가맹점수_연간자료": annual.get("연말가맹점수"),
                    "폐점률_pct_연간자료": annual.get("폐점률_pct"),
                    "신규개점수_연간자료": annual.get("신규개점수"),
                    "계약종료수_연간자료": annual.get("계약종료수"),
                    "계약해지수_연간자료": annual.get("계약해지수"),
                    "주의": "연간값은 월별 값이 아님. 월별 실제 매출/개점/폐점 데이터로 해석하지 말 것."
                })
    return pd.DataFrame(rows)


def kakao_search(query):
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    all_places, seen = [], set()
    for page in range(1, 4):
        r = session.get(KAKAO_API_URL, headers=headers,
                        params={"query": query, "page": page, "size": 15}, timeout=20)
        r.raise_for_status()
        data = r.json()
        for p in data.get("documents", []):
            pid = p.get("id")
            if pid and pid not in seen:
                seen.add(pid)
                all_places.append(p)
        if data.get("meta", {}).get("is_end", True):
            break
        time.sleep(0.15)
    return all_places


def collect_local_stores(top_brands):
    """
    서울 구 + 경기 시·군 단위 매장 후보를 검색.
    지도 API의 결과는 가맹/직영 소유 구분을 제공하지 않으므로 '검색 매장 후보'로만 표기.
    """
    if not KAKAO_API_KEY:
        print("카카오 API 키가 없어 기초자치단체 매장 검색은 건너뜁니다.")
        print("Windows PowerShell 예: $env:KAKAO_REST_API_KEY='발급키'")
        return pd.DataFrame(), pd.DataFrame()

    areas = [(f"서울특별시 {d}", "서울", d) for d in SEOUL_DISTRICTS]
    areas += [(f"경기도 {m}", "경기", m) for m in GYEONGGI_MUNICIPALITIES]
    summary, detail = [], []

    for _, brand_row in top_brands.iterrows():
        brand = brand_row["브랜드"]
        search_brand = re.sub(r"\([^)]*\)", "", brand).strip()
        for query_area, province, municipality in areas:
            query = f"{query_area} {search_brand}"
            print("매장 검색:", query)
            try:
                places = kakao_search(query)
                matched = []
                for p in places:
                    address = p.get("road_address_name") or p.get("address_name") or ""
                    # 주소가 검색 지역과 일치하는지 확인
                    area_word = municipality
                    if province == "서울":
                        ok = ("서울" in address and area_word in address)
                    else:
                        ok = ("경기" in address and area_word in address)
                    if not ok:
                        continue
                    matched.append(p)
                    detail.append({
                        "브랜드검색어": brand,
                        "시도": province,
                        "기초자치단체": municipality,
                        "매장명": p.get("place_name", ""),
                        "주소": address,
                        "전화번호": p.get("phone", ""),
                        "카카오장소ID": p.get("id", ""),
                        "카카오URL": p.get("place_url", ""),
                        "분류": "검색 후보; 가맹/직영 구분 미확인",
                        "검색어": query
                    })
                summary.append({
                    "브랜드": brand,
                    "시도": province,
                    "기초자치단체": municipality,
                    "검색결과매장후보수": len(matched),
                    "API결과한도주의": "45개 반환 시 추가 확인 필요" if len(places) >= 45 else "",
                    "가맹점수": "",
                    "직영점수": "",
                    "검색어": query
                })
            except Exception as e:
                summary.append({
                    "브랜드": brand, "시도": province, "기초자치단체": municipality,
                    "검색결과매장후보수": None, "API결과한도주의": str(e),
                    "가맹점수": "", "직영점수": "", "검색어": query
                })
            time.sleep(DELAY)
    return pd.DataFrame(summary), pd.DataFrame(detail)


def main():
    print("1) 프랑 커피 브랜드 목록 수집")
    brands = get_brand_list()
    top = brands.head(TOP_N).copy()
    top.insert(0, "순위", range(1, len(top) + 1))
    print(top[["순위", "브랜드", "전국가맹점수_사이트표시", "폐점률_pct_사이트표시"]].to_string(index=False))

    annual_rows, regional_rows = [], []
    for i, row in top.iterrows():
        brand, url = row["브랜드"], row["상세페이지"]
        if not url:
            continue
        print(f"2) 상세 페이지 수집 {i+1}/{len(top)}: {brand}")
        try:
            a, r = parse_annual_detail(brand, url)
            annual_rows.extend(a)
            regional_rows.extend(r)
        except Exception as e:
            print("상세 페이지 오류:", brand, e)
        time.sleep(DELAY)

    annual_df = pd.DataFrame(annual_rows)
    regional_df = pd.DataFrame(regional_rows)
    monthly_df = make_monthly_rows(annual_df, regional_df)

    print("3) 서울·경기 기초자치단체 매장 검색")
    local_summary_df, local_detail_df = collect_local_stores(top)

    # 저장
    top.to_csv(os.path.join(OUT_DIR, "top5_brands.csv"), index=False, encoding="utf-8-sig")
    annual_df.to_csv(os.path.join(OUT_DIR, "annual_2024_2025.csv"), index=False, encoding="utf-8-sig")
    regional_df.to_csv(os.path.join(OUT_DIR, "regional_annual_sales.csv"), index=False, encoding="utf-8-sig")
    monthly_df.to_csv(os.path.join(OUT_DIR, "monthly_format_2024_2025.csv"), index=False, encoding="utf-8-sig")
    local_summary_df.to_csv(os.path.join(OUT_DIR, "seoul_gyeonggi_municipality_counts.csv"), index=False, encoding="utf-8-sig")
    local_detail_df.to_csv(os.path.join(OUT_DIR, "seoul_gyeonggi_store_candidates.csv"), index=False, encoding="utf-8-sig")

    excel = os.path.join(OUT_DIR, "coffee_seoul_gyeonggi_monthly.xlsx")
    with pd.ExcelWriter(excel, engine="openpyxl") as writer:
        top.to_excel(writer, sheet_name="상위5개브랜드", index=False)
        annual_df.to_excel(writer, sheet_name="연간원자료_2024_2025", index=False)
        monthly_df.to_excel(writer, sheet_name="월별형식_주의필독", index=False)
        regional_df.to_excel(writer, sheet_name="시도별연평균매출", index=False)
        local_summary_df.to_excel(writer, sheet_name="서울경기_기초자치단체", index=False)
        local_detail_df.to_excel(writer, sheet_name="매장검색후보목록", index=False)

    print("\n완료:", os.path.abspath(excel))
    print("중요: 서울·경기 시·군·구 매장 검색은 카카오 검색 후보입니다. 가맹/직영 확정 집계가 아닙니다.")
    print("중요: 월별 시트는 월별 형식으로 펼친 것이며, 사이트가 공개하지 않은 월별 실적을 생성하지 않습니다.")


if __name__ == "__main__":
    main()
