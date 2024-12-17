from flask import Flask, render_template, request
import requests
from math import radians, cos, sin, asin, sqrt, tan, log, floor
from datetime import datetime

app = Flask(__name__)

# 서울 공공데이터 API 키
SEOUL_API_KEY = "4c55544e4d64757338327343434443"
# 기상청 단기예보 API 키
KMA_API_KEY = "Xj3ry4CURRC968uAlAUQTw"


def haversine(lon1, lat1, lon2, lat2):
    """
    Haversine 공식을 이용해 두 지점 간의 거리(km)를 계산하는 함수.
    지구를 구 형태로 가정하고 위도, 경도를 이용해 두 좌표 사이의 직선 거리를 반환한다.
    """
    # 모든 각도를 radian으로 변환
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # 경도차, 위도차
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    # 하버사인 공식 적용
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    # 지구 반지름(km)을 곱해 거리 반환
    km = 6371 * c
    return km


def convert_lat_lon_to_grid(lat, lon):
    """
    위도, 경도를 기상청 격자(nx, ny) 좌표로 변환하는 함수.
    기상청 단기예보 API에서 날씨 조회 시 격자좌표 사용이 필요하여 변환한다.
    """
    # 기상청 단기예보 격자 설정값
    RE = 6371.00877  # 지구 반경(km)
    GRID = 5.0  # 격자 간격(km)
    SLAT1 = 30.0  # 표준위도1
    SLAT2 = 60.0  # 표준위도2
    OLON = 126.0  # 기준점 경도
    OLAT = 38.0  # 기준점 위도
    XO = 210 / GRID  # 기준점 X좌표
    YO = 675 / GRID  # 기준점 Y좌표

    # 수학적 계산을 위한 변환
    DEGRAD = 3.14159265359 / 180.0
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = tan(3.14159265359 / 4.0 + slat2 / 2.0) / tan(3.14159265359 / 4.0 + slat1 / 2.0)
    sn = log(cos(slat1) / cos(slat2)) / log(sn)
    sf = tan(3.14159265359 / 4.0 + slat1 / 2.0)
    sf = (sf ** sn) * (cos(slat1) / sn)
    re = RE / GRID
    ro = tan(3.14159265359 / 4.0 + olat / 2.0)
    ro = re * sf / (ro ** sn)
    ra = tan(3.14159265359 / 4.0 + (lat * DEGRAD) / 2.0)
    ra = re * sf / (ra ** sn)
    theta = lon * DEGRAD - olon
    if theta > 3.14159265359:
        theta -= 2.0 * 3.14159265359
    if theta < -3.14159265359:
        theta += 2.0 * 3.14159265359
    theta *= sn

    x = floor(ra * sin(theta) + XO + 0.5)
    y = floor(ro - ra * cos(theta) + YO + 0.5)
    return x, y


def get_weather_data(lat, lon):
    """
    위도, 경도를 입력받아 해당 지역의 기상청 초단기예보 날씨 데이터를 조회하는 함수.
    SKY: 하늘 상태 (1: 맑음, 3: 구름많음, 4: 흐림 등)
    PTY: 강수 형태 (0: 없음, 1: 비, 2: 비+눈, 3: 눈 등)
    """
    # 위도, 경도를 기상청 격자로 변환
    nx, ny = convert_lat_lon_to_grid(lat, lon)
    now = datetime.now()
    base_date = now.strftime("%Y%m%d")
    base_time = "1200"  # 기준 시간(예: 12시 발표 기준)

    # 기상청 초단기예보 API 엔드포인트 및 파라미터 설정
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst"
    params = {
        "serviceKey": KMA_API_KEY,
        "numOfRows": 100,
        "pageNo": 1,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # JSON 응답 구조 확인 후 날씨 정보 추출
        if "response" in data and "body" in data["response"] and "items" in data["response"]["body"]:
            weather_items = data["response"]["body"]["items"]["item"]
            sky_condition = next((item["fcstValue"] for item in weather_items if item["category"] == "SKY"), None)
            rain_type = next((item["fcstValue"] for item in weather_items if item["category"] == "PTY"), None)
            return {"sky_condition": sky_condition, "rain_type": rain_type}
        else:
            return {"sky_condition": None, "rain_type": None}
    except:
        # API 호출 실패 시 None 반환
        return {"sky_condition": None, "rain_type": None}


def get_parks_data():
    """
    서울시 공원 정보 데이터를 조회하는 함수.
    API를 통해 서울시의 공원 목록과 정보(JSON)를 가져온다.
    """
    # 서울시 공원정보 API 엔드포인트
    url = f"http://openAPI.seoul.go.kr:8088/{SEOUL_API_KEY}/json/SearchParkInfoService/1/1000/"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # 공원 정보 리스트 반환
        parks = data.get("SearchParkInfoService", {}).get("row", [])
        return parks
    except:
        print("Failed to fetch park data.")
        return []


def recommend_parks(user_preferences):
    """
    사용자 선호도(햇빛선호, 편의시설, 산책로, 사용자 위치)를 바탕으로
    점수를 매긴 후 상위 5개 공원을 추천하는 함수.
    """
    sunlight_pref = user_preferences.get("sunlight")
    amenities_prefs = user_preferences.get("amenities", [])
    trails_prefs = user_preferences.get("trails", [])
    user_lat = user_preferences.get("user_lat")
    user_lon = user_preferences.get("user_lon")

    # 사용자 위치 정보가 없으면 빈 리스트 반환
    if not user_lat or not user_lon:
        return []

    # 서울시 공원 정보 불러오기
    parks = get_parks_data()
    recommended_parks = []

    for park in parks:
        # 공원 좌표(위도, 경도) 파싱
        try:
            park_lat = float(park.get("LATITUDE", 0) or 0.0)
            park_lon = float(park.get("LONGITUDE", 0) or 0.0)
        except ValueError:
            park_lat, park_lon = 0.0, 0.0

        # 공원 날씨 정보 조회
        weather = get_weather_data(park_lat, park_lon)
        sky_condition = weather.get("sky_condition")

        score = 0
        # 햇빛 상태에 따른 선호도 반영
        # SKY=1: 맑음, 사용자 선호(많이 받고 싶음)일 경우 점수 증가
        if sky_condition == "1":
            sunlight_condition_str = "햇빛 많음"
            if sunlight_pref == "많이 받고 싶음":
                score += 3
        else:
            sunlight_condition_str = "그늘 선호 가능"

        # 공원 주요시설 정보
        main_equip = park.get("MAIN_EQUIP", "") or ""
        park_description = park.get("P_LIST_CONTENT", "") or ""

        # 편의시설 정보 체크(벤치, 화장실, 놀이터 등)
        has_bench = "벤치 있음" if "벤치" in main_equip else "벤치 정보 없음"
        has_toilet = "화장실 있음" if "화장실" in main_equip else "화장실 정보 없음"
        has_playground = "놀이터 있음" if "놀이터" in main_equip else "놀이터 정보 없음"

        # 산책로 정보 체크 (주요시설 또는 설명에서 산책로 키워드 탐색)
        has_trail = "산책로 있음" if "산책로" in main_equip or "산책로" in park_description else "산책로 정보 없음"

        # 사용자 요청한 편의시설 및 산책로 반영
        for amenity in amenities_prefs:
            # 예: 사용자 wants "벤치" -> main_equip에 "벤치"가 있으면 점수 추가
            if amenity in main_equip:
                score += 1

        for trail in trails_prefs:
            # 예: 사용자 wants "산책로" -> 공원에 "산책로" 있으면 점수 추가
            if trail in main_equip or trail in park_description:
                score += 1

        # 거리 계산 (사용자 위치와 공원간 거리)
        distance = haversine(float(user_lon), float(user_lat), park_lon, park_lat)
        # 거리가 멀어질수록 점수가 낮아지도록 가중치 적용
        distance_weight = 0.5
        final_score = score - (distance * distance_weight)

        # 공원 조건 딕셔너리: 렌더링 시 UI에 표시할 수 있다.
        park_conditions = {
            "햇빛 상태": sunlight_condition_str,
            "편의시설": [has_bench, has_toilet, has_playground],
            "산책로": has_trail
        }

        recommended_parks.append({
            "name": park.get("P_PARK", "알 수 없음"),
            "image": park.get("P_IMG"),
            "score": final_score,
            "distance": distance,
            "conditions": park_conditions
        })

    # 점수 기준으로 정렬 후 상위 5개 반환
    recommended_parks.sort(key=lambda x: x["score"], reverse=True)
    return recommended_parks[:5]


@app.route("/")
def home():
    """
    검색 페이지 렌더링.
    사용자가 공원 조건을 입력할 수 있는 페이지를 보여준다.
    """
    return render_template("search.html")


@app.route("/results")
def get_parks():
    """
    사용자가 입력한 선호도(햇빛, 편의시설, 산책로, 위치)를 기반으로
    추천 공원 리스트를 생성하고 결과 페이지를 렌더링한다.
    """
    sunlight = request.args.get("sunlight", "")
    amenities = request.args.getlist("amenities")
    trails = request.args.getlist("trails")
    user_lat = request.args.get("user_lat")
    user_lon = request.args.get("user_lon")

    # 사용자 선호도 딕셔너리
    user_preferences = {
        "sunlight": sunlight,
        "amenities": amenities,
        "trails": trails,
        "user_lat": user_lat,
        "user_lon": user_lon
    }

    # 추천 공원 목록 가져오기
    recommended = recommend_parks(user_preferences)

    # 결과 렌더링 (결과 페이지에 추천 공원 정보 및 사용자 선호도 표시)
    return render_template("result.html",
                           parks=recommended,
                           user_preferences=user_preferences)


if __name__ == '__main__':
    # Flask 앱 실행: 호스트 및 포트 설정, 디버그 모드
    app.run(host='0.0.0.0', port=8081, debug=True)
