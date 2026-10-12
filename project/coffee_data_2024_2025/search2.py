import requests
import pandas as pd

from bs4 import BeautifulSoup
from itertools import product


# ========================================
# 1. 기본 설정
# ========================================

URL = "https://franc-kr.pages.dev/category/%EC%BB%A4%ED%94%BC/"

START_YEAR = 2024
END_YEAR = 2025

TOP_N = 5

OUTPUT_FILE = "coffee_franchise_data.xlsx"


# 서울 25개 구
SEOUL_GU = [
    "종로구", "중구", "용산구", "성동구", "광진구",
    "동대문구", "중랑구", "성북구", "강북구", "도봉구",
    "노원구", "은평구", "서대문구", "마포구", "양천구",
    "강서구", "구로구", "금천구", "영등포구", "동작구",
    "관악구", "서초구", "강남구", "송파구", "강동구"
]


# 경기도 시·군
GYEONGGI_SIGUN = [
    "수원시", "용인시", "고양시", "화성시", "성남시",
    "부천시", "남양주시", "안산시", "평택시", "안양시",
    "시흥시", "파주시", "김포시", "의정부시", "광주시",
    "하남시", "광명시", "군포시", "양주시", "오산시",
    "이천시", "안성시", "구리시", "의왕시", "포천시",
    "양평군", "여주시", "동두천시", "과천시", "가평군",
    "연천군"
]


# ========================================
# 2. 프랑 사이트에서 브랜드 목록 수집
# ========================================

def collect_brands():

    print("1. 커피 브랜드 목록 수집 시작")

    response = requests.get(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    rows = soup.select("#cat-table tbody tr")

    if not rows:
        raise ValueError(
            "브랜드 목록을 찾지 못했습니다. "
            "사이트의 HTML 구조가 변경되었는지 확인하세요."
        )

    data = []

    for row in rows:

        name = row.get("data-name")
        store_count = row.get("data-frcs")
        closing_rate = row.get("data-rate")
        opening_cost = row.get("data-cost")

        if not name:
            continue

        data.append({
            "브랜드": name,
            "전국가맹점수_사이트표시": store_count,
            "폐점률_pct_사이트표시": closing_rate,
            "개업비_원자료": opening_cost
        })

    df = pd.DataFrame(data)

    # 가맹점 수를 숫자로 변환
    df["전국가맹점수_사이트표시"] = pd.to_numeric(
        df["전국가맹점수_사이트표시"],
        errors="coerce"
    )

    # 가맹점 수 기준 내림차순 정렬
    df = df.sort_values(
        "전국가맹점수_사이트표시",
        ascending=False
    )

    # 상위 5개 브랜드
    df = df.head(TOP_N).reset_index(drop=True)

    df.insert(0, "순위", range(1, len(df) + 1))

    print(df.to_string(index=False))

    return df


# ========================================
# 3. 연간 원자료 테이블 생성
# ========================================

def make_annual_data(brands):

    print("\n2. 연간 자료 구조 생성")

    records = []

    for _, brand in brands.iterrows():

        for year in range(START_YEAR, END_YEAR + 1):

            records.append({

                "연도": year,

                # 연간 자료에는 월을 임의로 지정하지 않음
                "월": None,

                "브랜드": brand["브랜드"],

                "시도": None,

                "시군구": None,

                "규모(범위)": None,

                "개업비": brand["개업비_원자료"],

                # 별도 가맹비 자료를 확보하기 전에는 공란
                "가맹점비": None,

                # 실제 연도별 매출 원자료가 확보되면 입력
                "매출": None,

                # 사이트에 표시된 전국 가맹점 수
                "가맹점수": brand[
                    "전국가맹점수_사이트표시"
                ],

                # 폐점률과 폐점수는 서로 다른 값
                "폐점수": None,

                "폐점률_pct_사이트표시": brand[
                    "폐점률_pct_사이트표시"
                ],

                "자료유형": "사이트 표시 자료",

                "비고": (
                    "사이트 표시 수치의 기준 연도를 "
                    "확인한 뒤 연도별 자료로 확정할 것"
                )

            })

    return pd.DataFrame(records)


# ========================================
# 4. 월별 분석용 빈 테이블 생성
# ========================================

def make_monthly_template(brands):

    print("\n3. 월별 분석용 자료 구조 생성")

    records = []

    regions = []

    # 서울
    for gu in SEOUL_GU:

        regions.append({
            "시도": "서울",
            "시군구": gu
        })

    # 경기
    for sigun in GYEONGGI_SIGUN:

        regions.append({
            "시도": "경기",
            "시군구": sigun
        })

    # 브랜드 × 연도 × 월 × 지역
    for _, brand in brands.iterrows():

        for year in range(START_YEAR, END_YEAR + 1):

            for month in range(1, 13):

                for region in regions:

                    records.append({

                        "연도": year,

                        "월": month,

                        "브랜드": brand["브랜드"],

                        "시도": region["시도"],

                        "시군구": region["시군구"],

                        "규모(범위)": None,

                        "개업비": None,

                        "가맹점비": None,

                        "매출": None,

                        "가맹점수": None,

                        "폐점수": None,

                        "자료상태": "월별 원자료 미확보"

                    })

    return pd.DataFrame(records)


# ========================================
# 5. 브랜드 기본정보 테이블 생성
# ========================================

def make_brand_summary(brands):

    result = brands.copy()

    result["개업비"] = result["개업비_원자료"]

    result["가맹점비"] = None

    result["규모(범위)"] = None

    result["자료 출처"] = "프랑 커피 카테고리"

    result["확인 사항"] = (
        "개업비의 구성, 기준 연도, 면적 및 가맹비 별도 여부 확인 필요"
    )

    return result


# ========================================
# 6. Excel 파일 저장
# ========================================

def save_excel(
    brands,
    annual_data,
    monthly_template,
    brand_summary
):

    with pd.ExcelWriter(
        OUTPUT_FILE,
        engine="openpyxl"
    ) as writer:

        brands.to_excel(
            writer,
            sheet_name="상위5개브랜드",
            index=False
        )

        annual_data.to_excel(
            writer,
            sheet_name="연간원자료",
            index=False
        )

        monthly_template.to_excel(
            writer,
            sheet_name="월별분석용",
            index=False
        )

        brand_summary.to_excel(
            writer,
            sheet_name="브랜드기본정보",
            index=False
        )

    print("\n================================")
    print("수집 및 파일 생성 완료")
    print("================================")

    print(f"파일 이름: {OUTPUT_FILE}")

    print(f"브랜드 수: {len(brands)}")

    print(f"연간 자료 행 수: {len(annual_data):,}")

    print(
        "월별 분석용 행 수: "
        f"{len(monthly_template):,}"
    )

    print(
        "\n주의: 월별분석용 시트는 입력 구조입니다. "
        "실제 월별 실적이 수집된 것은 아닙니다."
    )


# ========================================
# 7. 프로그램 실행
# ========================================

def main():

    # 브랜드 수집
    brands = collect_brands()

    # 연간 원자료 구조
    annual_data = make_annual_data(brands)

    # 월별 분석용 빈 자료
    monthly_template = make_monthly_template(brands)

    # 브랜드 기본정보
    brand_summary = make_brand_summary(brands)

    # Excel 저장
    save_excel(
        brands,
        annual_data,
        monthly_template,
        brand_summary
    )


if __name__ == "__main__":
    main()