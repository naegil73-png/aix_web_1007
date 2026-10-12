import requests
import pandas as pd
import os
from urllib.parse import unquote

# ==========================================
# 1. API 설정
# ==========================================

SERVICE_KEY = "yH3oOa54IPvHVoSEUZ7YQPGXyj%2F3hs45bv4lOpijqdIC%2BROJDo%2BAkU7qVixOZpXThikQll1vQon0qDwjJDoHxw%3D%3D"

# URL 인코딩된 인증키라면 디코딩
SERVICE_KEY = unquote(SERVICE_KEY)

URL = (
    "https://apis.data.go.kr/"
    "1130000/FftcBrandFrcsStatsService/getBrandFrcsStats"
)

NUM_OF_ROWS = 100

# ==========================================
# 2. 응답 데이터 찾기
# ==========================================

def find_value(data, target_key):

    if isinstance(data, dict):

        if target_key in data:
            return data[target_key]

        for value in data.values():
            result = find_value(value, target_key)

            if result is not None:
                return result

    elif isinstance(data, list):

        for item in data:
            result = find_value(item, target_key)

            if result is not None:
                return result

    return None


def find_records(data):

    if isinstance(data, dict):

        # 데이터 목록을 담는 주요 항목 확인
        for key in ["items", "item", "data", "list", "result"]:

            if key in data:
                result = find_records(data[key])

                if result:
                    return result

        for value in data.values():

            result = find_records(value)

            if result:
                return result

    elif isinstance(data, list):

        if data and all(isinstance(item, dict) for item in data):
            return data

        for item in data:

            result = find_records(item)

            if result:
                return result

    return []


# ==========================================
# 3. 연도별 모든 페이지 조회
# ==========================================

all_data = []

for year in [2024, 2025]:

    print("\n" + "=" * 50)
    print(f"{year}년 데이터 수집 시작")
    print("=" * 50)

    page_no = 1
    year_data = []
    total_count = None

    while True:

        params = {
            "serviceKey": SERVICE_KEY,
            "pageNo": page_no,
            "numOfRows": NUM_OF_ROWS,
            "resultType": "json",
            "yr": year
        }

        try:

            response = requests.get(
                URL,
                params=params,
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

        except Exception as e:

            print(f"{year}년 {page_no}페이지 조회 오류:", e)
            break

        result_code = find_value(data, "resultCode")
        result_msg = find_value(data, "resultMsg")

        if result_code is not None and str(result_code) != "00":

            print("API 오류 코드:", result_code)
            print("API 오류 메시지:", result_msg)
            break

        records = find_records(data)

        if not records:
            print(f"{page_no}페이지에 데이터가 없습니다.")
            break

        # 전체 데이터 수 확인
        count_value = find_value(data, "totalCount")

        if count_value is not None:

            try:
                total_count = int(count_value)
            except (ValueError, TypeError):
                pass

        # 조회 연도 추가
        for record in records:
            record["조회연도"] = year

        year_data.extend(records)

        print(
            f"{year}년 {page_no}페이지: "
            f"{len(records)}건 수집 / "
            f"누적 {len(year_data)}건"
        )

        # 전체 건수를 확인했다면 수집 완료 여부 확인
        if total_count is not None:

            if len(year_data) >= total_count:
                break

        # 전체 건수를 모르는 경우 마지막 페이지인지 확인
        elif len(records) < NUM_OF_ROWS:
            break

        page_no += 1

        # 무한 반복 방지
        if page_no > 10000:
            print("페이지 제한에 도달했습니다.")
            break

    print(f"{year}년 최종 수집 건수: {len(year_data)}건")

    all_data.extend(year_data)


# ==========================================
# 4. 엑셀 파일 생성
# ==========================================

if not all_data:

    print("\n수집된 데이터가 없습니다.")
    raise SystemExit

df = pd.json_normalize(all_data)

print("\n전체 수집 건수:", len(df))

# ==========================================
# 5. 커피 관련 브랜드 후보 분류
# ==========================================

# 업종명, 브랜드명, 회사명에 커피 관련 단어가 있는지 확인
search_columns = [
    col for col in [
        "indutyLclasNm",
        "indutyMlsfcNm",
        "brandNm",
        "corpNm"
    ]
    if col in df.columns
]

if search_columns:

    search_text = (
        df[search_columns]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
    )

    coffee_mask = search_text.str.contains(
        r"커피|카페|coffee|cafe",
        case=False,
        regex=True
    )

    coffee_candidates = df[coffee_mask].copy()

else:
    coffee_candidates = pd.DataFrame()


# ==========================================
# 6. 업종별 건수 집계
# ==========================================

if "indutyMlsfcNm" in df.columns:

    industry_summary = (
        df.groupby(
            ["조회연도", "indutyLclasNm", "indutyMlsfcNm"],
            dropna=False
        )
        .size()
        .reset_index(name="브랜드자료건수")
    )

else:
    industry_summary = pd.DataFrame()


# ==========================================
# 7. 엑셀 저장
# ==========================================

output_file = os.path.abspath(
    "프랜차이즈_전체자료_2024_2025.xlsx"
)

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:

    # 전체 브랜드 자료
    df.to_excel(
        writer,
        sheet_name="전체자료",
        index=False
    )

    # 커피 관련 단어가 포함된 브랜드 후보
    coffee_candidates.to_excel(
        writer,
        sheet_name="커피브랜드_후보",
        index=False
    )

    # 업종별 자료 건수
    industry_summary.to_excel(
        writer,
        sheet_name="업종별건수",
        index=False
    )

print("\n" + "=" * 50)
print("엑셀 저장 완료!")
print("=" * 50)

print("파일 위치:", output_file)
print("전체 자료:", len(df), "건")
print("커피 관련 후보:", len(coffee_candidates), "건")

print("\n전체 자료 미리보기")
print(df.head(10).to_string(index=False))

print("\n업종별 자료 건수")
print(industry_summary.to_string(index=False))