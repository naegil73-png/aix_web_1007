import requests
import pandas as pd
import json
import os
from urllib.parse import unquote

# ==========================================
# 1. API 설정
# ==========================================

SERVICE_KEY = "yH3oOa54IPvHVoSEUZ7YQPGXyj%2F3hs45bv4lOpijqdIC%2BROJDo%2BAkU7qVixOZpXThikQll1vQon0qDwjJDoHxw%3D%3D"

# 공공데이터포털 1번 API의 실제 요청주소를 입력
API_URL = "https://apis.data.go.kr/1130000/FftcBrandFrcsStatsService/getBrandFrcsStats"

SERVICE_KEY = unquote(SERVICE_KEY)

OUTPUT_FILE = "1번_지역별_가맹점_평균매출.xlsx"

# 상세 명세에서 확인한 필수 요청변수를 입력
EXTRA_PARAMS = {
    # 예:
    # "실제변수명": "실제값"
}

# ==========================================
# 2. API 데이터 추출 함수
# ==========================================

def find_records(data):

    if isinstance(data, dict):

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

        if data and all(isinstance(x, dict) for x in data):
            return data

        for item in data:

            result = find_records(item)

            if result:
                return result

    return []


# ==========================================
# 3. 서울·경기 자료 수집
# ==========================================

if API_URL.startswith("여기에_"):
    raise SystemExit(
        "공공데이터포털에서 실제 요청주소를 확인해 입력하세요."
    )

all_data = []

for page in range(1, 10001):

    params = {
    "serviceKey": SERVICE_KEY,
    "pageNo": 1,
    "numOfRows": 100,
    "resultType": "json",
    "yr": 2024
}

    response = requests.get(
        API_URL,
        params=params,
        timeout=30
    )

    print("페이지:", page)
    print("HTTP 상태:", response.status_code)

    response.raise_for_status()

    try:
        data = response.json()

    except ValueError:
        print(response.text[:2000])
        break

    print(json.dumps(
        data,
        ensure_ascii=False
    )[:500])

    records = find_records(data)

    if not records:
        print("추가 데이터가 없습니다.")
        break

    all_data.extend(records)

    if len(records) < 100:
        break


# ==========================================
# 4. 지역 필터링 및 엑셀 저장
# ==========================================

if all_data:

    df = pd.json_normalize(all_data)

    print("전체 수집:", len(df), "건")
    print("컬럼:", df.columns.tolist())

    # 실제 지역 컬럼을 확인한 뒤 필터링해야 합니다.
    df.to_excel(OUTPUT_FILE, index=False)

    print("저장 완료:", os.path.abspath(OUTPUT_FILE))

else:
    print("수집된 자료가 없습니다.")