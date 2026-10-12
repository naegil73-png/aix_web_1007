import os
import re
import time
import requests
import pandas as pd

from bs4 import BeautifulSoup


# ============================================================
# 1. 기본 설정
# ============================================================

# 커피 프랜차이즈 공개 자료
SOURCE_URL = (
    "https://franc-kr.pages.dev/category/%EC%BB%A4%ED%94%BC/"
)

# 카카오 로컬 API
KAKAO_API_URL = (
    "https://dapi.kakao.com/v2/local/search/keyword.json"
)

# ------------------------------------------------------------
# 카카오 REST API 키
#
# 방법 1:
# 아래에 직접 입력
#
# KAKAO_API_KEY = "여기에_카카오_REST_API_키"
#
# 방법 2:
# Windows 환경변수 사용
# ------------------------------------------------------------

KAKAO_API_KEY = os.getenv("KAKAO_REST_API_KEY")


# ============================================================
# 2. 서울 25개 구
# ============================================================

SEOUL_DISTRICTS = [
    "강남구",
    "강동구",
    "강북구",
    "강서구",
    "관악구",
    "광진구",
    "구로구",
    "금천구",
    "노원구",
    "도봉구",
    "동대문구",
    "동작구",
    "마포구",
    "서대문구",
    "서초구",
    "성동구",
    "성북구",
    "송파구",
    "양천구",
    "영등포구",
    "용산구",
    "은평구",
    "종로구",
    "중구",
    "중랑구"
]


# ============================================================
# 3. 저장 폴더
# ============================================================

OUTPUT_DIR = "coffee_data"

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# 4. 웹 접속 설정
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    )
}


# ============================================================
# 5. 웹페이지 가져오기
# ============================================================

def get_html(url):

    print("\n웹페이지 접속 중...")

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    # 한글 깨짐 방지
    response.encoding = response.apparent_encoding

    print("웹페이지 접속 성공")

    return response.text


# ============================================================
# 6. 숫자 변환 함수
# ============================================================

def to_int(value):

    if value is None:
        return None

    text = str(value)

    text = text.replace(",", "")
    text = text.replace("개", "")
    text = text.strip()

    try:
        return int(text)

    except:
        return None


def to_float(value):

    if value is None:
        return None

    text = str(value)

    text = text.replace("%", "")
    text = text.replace(",", "")
    text = text.strip()

    try:
        return float(text)

    except:
        return None


# ============================================================
# 7. 커피 프랜차이즈 브랜드 수집
# ============================================================

def collect_brand_data():

    print("\n")
    print("=" * 60)
    print("[1단계] 커피 프랜차이즈 브랜드 수집")
    print("=" * 60)

    # 웹페이지 가져오기
    html = get_html(SOURCE_URL)

    # BeautifulSoup으로 HTML 분석
    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # 실제 페이지의 브랜드 행
    rows = soup.select(
        "#cat-table tbody tr"
    )

    print(
        f"발견한 브랜드 수: {len(rows)}개"
    )

    if not rows:

        raise ValueError(
            "브랜드 데이터를 찾지 못했습니다."
        )


    data = []


    # --------------------------------------------------------
    # 각 브랜드 처리
    # --------------------------------------------------------

    for row in rows:

        # 실제 HTML의 data-name
        brand = row.get(
            "data-name",
            ""
        ).strip()


        # 가맹점 수
        frcs = row.get(
            "data-frcs",
            ""
        ).strip()


        # 폐점률
        rate = row.get(
            "data-rate",
            ""
        ).strip()


        # 창업비용
        cost = row.get(
            "data-cost",
            ""
        ).strip()


        # 브랜드명이 없으면 건너뜀
        if not brand:
            continue


        # 숫자 변환
        frcs_number = to_int(frcs)

        rate_number = to_float(rate)


        # 데이터 저장
        data.append({

            "브랜드": brand,

            "전국가맹점수": frcs_number,

            "폐점률": rate_number,

            "창업비용_만원": cost,

            # 나중에 추가할 항목
            "서울가맹점수": "",

            "서울직영점수": "",

            "전국직영점수": "",

            "월평균매출": "",

            "폐점수": "",

            "창업혜택": "",

            "기준연도": "2025",

            "자료출처": SOURCE_URL

        })


    # DataFrame 생성
    df = pd.DataFrame(data)


    # --------------------------------------------------------
    # 가맹점 수 기준으로 정렬
    # --------------------------------------------------------

    df = df.sort_values(
        by="전국가맹점수",
        ascending=False
    )


    # --------------------------------------------------------
    # 상위 5개
    # --------------------------------------------------------

    top5 = df.head(5).copy()


    # 순위 추가
    top5.insert(
        0,
        "순위",
        range(
            1,
            len(top5) + 1
        )
    )


    # --------------------------------------------------------
    # CSV 저장
    # --------------------------------------------------------

    csv_path = os.path.join(
        OUTPUT_DIR,
        "brand_top5.csv"
    )

    top5.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig"
    )


    # --------------------------------------------------------
    # 화면 출력
    # --------------------------------------------------------

    print("\n")
    print("=" * 60)
    print("커피 프랜차이즈 상위 5개")
    print("=" * 60)


    print(
        top5[
            [
                "순위",
                "브랜드",
                "전국가맹점수",
                "폐점률",
                "창업비용_만원"
            ]
        ].to_string(
            index=False
        )
    )


    print("\n상위 5개 저장 완료:")
    print(csv_path)


    return top5


# ============================================================
# 8. 카카오 API 매장 검색
# ============================================================

def search_kakao_places(query):

    # API 키 확인
    if not KAKAO_API_KEY:

        raise ValueError(
            "카카오 REST API 키가 없습니다."
        )


    headers = {

        "Authorization":
            f"KakaoAK {KAKAO_API_KEY}"

    }


    places = []

    seen_ids = set()


    # 카카오 API는 한 페이지 최대 15개
    # 최대 3페이지까지 검색
    for page in range(1, 4):

        params = {

            "query": query,

            "page": page,

            "size": 15

        }


        response = requests.get(

            KAKAO_API_URL,

            headers=headers,

            params=params,

            timeout=20

        )


        response.raise_for_status()


        result = response.json()


        documents = result.get(
            "documents",
            []
        )


        # 검색 결과 저장
        for place in documents:

            place_id = place.get(
                "id"
            )


            # 중복 제거
            if place_id in seen_ids:
                continue


            seen_ids.add(
                place_id
            )


            places.append(
                place
            )


        # 마지막 페이지인지 확인
        meta = result.get(
            "meta",
            {}
        )


        if meta.get(
            "is_end",
            True
        ):

            break


        time.sleep(0.2)


    return places


# ============================================================
# 9. 서울 25개 구별 매장 검색
# ============================================================

def collect_seoul_store_counts(top5):

    print("\n")
    print("=" * 60)
    print("[2단계] 서울 25개 구별 매장 검색")
    print("=" * 60)


    # API 키가 없는 경우
    if not KAKAO_API_KEY:

        print(
            "\n카카오 REST API 키가 없습니다."
        )

        print(
            "서울 구별 매장 검색은 건너뜁니다."
        )

        print(
            "상위 5개 브랜드 자료는 정상적으로 저장되었습니다."
        )

        return pd.DataFrame()


    results = []


    # 상위 5개 브랜드
    for _, row in top5.iterrows():

        brand = str(
            row["브랜드"]
        )


        # ----------------------------------------------------
        # 검색어 정리
        # ----------------------------------------------------

        # 괄호 안 영문명 제거
        search_brand = re.sub(
            r"\([^)]*\)",
            "",
            brand
        ).strip()


        print("\n")
        print("-" * 50)
        print(
            f"브랜드: {search_brand}"
        )
        print("-" * 50)


        # ----------------------------------------------------
        # 서울 25개 구 검색
        # ----------------------------------------------------

        for district in SEOUL_DISTRICTS:

            query = (
                f"서울 {district} "
                f"{search_brand}"
            )


            print(
                f"{district} 검색 중..."
            )


            try:

                places = search_kakao_places(
                    query
                )


                # 해당 구에 있는 매장만 추출
                district_places = []


                for place in places:

                    road_address = place.get(
                        "road_address_name",
                        ""
                    )

                    address = place.get(
                        "address_name",
                        ""
                    )


                    # 도로명주소 또는 지번주소
                    full_address = (
                        road_address
                        or address
                    )


                    # 서울 + 해당 구 확인
                    if (
                        "서울" in full_address
                        and district in full_address
                    ):

                        district_places.append(
                            place
                        )


                # 매장명
                store_names = []

                for place in district_places:

                    store_names.append(
                        place.get(
                            "place_name",
                            ""
                        )
                    )


                # 결과 저장
                results.append({

                    "브랜드": brand,

                    "구": district,

                    "검색어": query,

                    "검색매장수":
                        len(
                            district_places
                        ),

                    # 카카오 검색만으로는
                    # 가맹/직영 구분 불가능
                    "가맹점수": "",

                    "직영점수": "",

                    "매장목록":
                        " / ".join(
                            store_names
                        ),

                    "검색한도확인":
                        (
                            "확인필요"
                            if len(places) >= 45
                            else "정상"
                        ),

                    "자료출처":
                        "카카오 로컬 API"

                })


            except Exception as error:

                print(
                    f"오류 발생: {error}"
                )


                results.append({

                    "브랜드": brand,

                    "구": district,

                    "검색어": query,

                    "검색매장수": "",

                    "가맹점수": "",

                    "직영점수": "",

                    "매장목록": "",

                    "검색한도확인":
                        "오류",

                    "자료출처":
                        "카카오 로컬 API"

                })


            # API 호출 간격
            time.sleep(0.3)


    # DataFrame
    store_df = pd.DataFrame(
        results
    )


    # --------------------------------------------------------
    # CSV 저장
    # --------------------------------------------------------

    csv_path = os.path.join(
        OUTPUT_DIR,
        "seoul_25district_stores.csv"
    )


    store_df.to_csv(

        csv_path,

        index=False,

        encoding="utf-8-sig"

    )


    print("\n")
    print(
        "서울 25개 구 검색 완료"
    )

    print(
        f"저장 위치: {csv_path}"
    )


    return store_df


# ============================================================
# 10. 수동 입력용 데이터 생성
# ============================================================

def create_manual_data(top5):

    print("\n")
    print("=" * 60)
    print("[3단계] 추가 자료 입력용 파일 생성")
    print("=" * 60)


    manual_data = []


    for _, row in top5.iterrows():

        manual_data.append({

            "브랜드":
                row["브랜드"],

            "기준연도":
                "2025",

            "전국가맹점수":
                row["전국가맹점수"],

            "전국직영점수":
                "",

            "서울가맹점수":
                "",

            "서울직영점수":
                "",

            "연평균매출":
                "",

            "월평균매출":
                "",

            "신규개점수":
                "",

            "계약해지수":
                "",

            "계약종료수":
                "",

            "폐점수":
                "",

            "창업비용":
                row["창업비용_만원"],

            "창업혜택":
                "",

            "창업혜택_출처":
                "",

            "정보공개서_출처":
                ""

        })


    manual_df = pd.DataFrame(
        manual_data
    )


    # CSV
    csv_path = os.path.join(
        OUTPUT_DIR,
        "additional_data_template.csv"
    )


    manual_df.to_csv(

        csv_path,

        index=False,

        encoding="utf-8-sig"

    )


    print(
        "추가 입력용 파일 생성:"
    )

    print(csv_path)


    return manual_df


# ============================================================
# 11. Excel 통합 파일 만들기
# ============================================================

def create_excel(
    top5,
    store_df,
    manual_df
):

    print("\n")
    print("=" * 60)
    print("[4단계] Excel 파일 생성")
    print("=" * 60)


    excel_path = os.path.join(
        OUTPUT_DIR,
        "coffee_franchise_analysis.xlsx"
    )


    with pd.ExcelWriter(
        excel_path,
        engine="openpyxl"
    ) as writer:


        # ----------------------------------------------------
        # Sheet 1
        # 상위 5개
        # ----------------------------------------------------

        top5.to_excel(

            writer,

            sheet_name="상위5개브랜드",

            index=False

        )


        # ----------------------------------------------------
        # Sheet 2
        # 서울 25개 구
        # ----------------------------------------------------

        if not store_df.empty:

            store_df.to_excel(

                writer,

                sheet_name="서울25개구",

                index=False

            )


        # ----------------------------------------------------
        # Sheet 3
        # 추가 입력
        # ----------------------------------------------------

        manual_df.to_excel(

            writer,

            sheet_name="추가입력",

            index=False

        )


    print(
        f"Excel 저장 완료: {excel_path}"
    )


# ============================================================
# 12. 프로그램 실행
# ============================================================

def main():

    print("\n")
    print("=" * 60)
    print("커피 프랜차이즈 자료 수집 프로그램")
    print("=" * 60)


    try:

        # ----------------------------------------------------
        # 1. 상위 5개 브랜드
        # ----------------------------------------------------

        top5 = collect_brand_data()


        # ----------------------------------------------------
        # 2. 서울 25개 구
        # ----------------------------------------------------

        store_df = collect_seoul_store_counts(
            top5
        )


        # ----------------------------------------------------
        # 3. 추가 입력용 자료
        # ----------------------------------------------------

        manual_df = create_manual_data(
            top5
        )


        # ----------------------------------------------------
        # 4. Excel 통합
        # ----------------------------------------------------

        create_excel(

            top5,

            store_df,

            manual_df

        )


        # ----------------------------------------------------
        # 완료
        # ----------------------------------------------------

        print("\n")
        print("=" * 60)
        print("모든 작업이 완료되었습니다.")
        print("=" * 60)

        print(
            f"\n저장 폴더:"
        )

        print(
            os.path.abspath(
                OUTPUT_DIR
            )
        )


    except Exception as error:

        print("\n")
        print("=" * 60)
        print("프로그램 실행 중 오류가 발생했습니다.")
        print("=" * 60)

        print(
            type(error).__name__
        )

        print(
            error
        )


# ============================================================
# 프로그램 시작
# ============================================================

if __name__ == "__main__":

    main()