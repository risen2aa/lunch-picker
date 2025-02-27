from flask import Flask, render_template, request, jsonify
import random
import json
import os

app = Flask(__name__)

# 식당 데이터
restaurants = [
    {"main_menu": "닭갈비", "name": "구도로식당", "url": "https://naver.me/GvcTy4hQ"},
    {"main_menu": "한식", "name": "금슬", "url": "https://naver.me/GipBM8wO"},
    {"main_menu": "우동", "name": "깡우동", "url": "https://naver.me/5gFlnctz"},
    {"main_menu": "분식", "name": "남촌김밥", "url": "https://naver.me/x4FLKdMg"},
    {"main_menu": "돈가스", "name": "뉴욕돈가스", "url": "https://naver.me/5vcjaG5r"},
    {"main_menu": "순대국", "name": "담소소사골순대육개장", "url": "https://naver.me/GgWaBwsP"},
    {"main_menu": "닭볶음탕", "name": "도리도리", "url": "https://naver.me/5CW26HnJ"},
    {"main_menu": "떡볶이", "name": "동대문엽기떡볶이", "url": "https://naver.me/GubF7z4d"},
    {"main_menu": "부대찌개", "name": "두꺼비부대찌개", "url": "https://naver.me/xf5AbWCn"},
    {"main_menu": "순두부찌개", "name": "두부사랑", "url": "https://naver.me/xdprL5kX"},
    {"main_menu": "한식", "name": "마구아", "url": "https://naver.me/F74V7FRg"},
    {"main_menu": "햄버거", "name": "맘스터치", "url": "https://naver.me/xv31ukoo"},
    {"main_menu": "한식", "name": "명학골", "url": "https://naver.me/FzSZuqJ7"},
    {"main_menu": "중식", "name": "몽샹", "url": "https://naver.me/5MVzfVxq"},
    {"main_menu": "부대찌개", "name": "미가부대찌개(부대천국)", "url": "https://naver.me/IMycTLv8"},
    {"main_menu": "라멘", "name": "미정당", "url": "https://naver.me/Fy2JVcvP"},
    {"main_menu": "일식", "name": "보우야", "url": "https://naver.me/FDnqI8Uh"},
    {"main_menu": "밀면/냉면", "name": "부산가야밀면", "url": "https://naver.me/IDFn99pP"},
    {"main_menu": "샤브샤브", "name": "부엉이샤브 스키야키", "url": "https://naver.me/Fy2F3lSk"},
    {"main_menu": "순두부찌개", "name": "북창동순두부", "url": "https://naver.me/x2j1cBWu"},
    {"main_menu": "쌈밥", "name": "삼겹살과쌈밥_우리동네고기마을", "url": "https://naver.me/FlZXRmNF"},
    {"main_menu": "한식", "name": "성가네 숯불갈비", "url": "https://naver.me/GHvqNNWS"},
    {"main_menu": "감자탕", "name": "수누리감자탕", "url": "https://naver.me/GzEDLOmV"},
    {"main_menu": "쌀국수", "name": "신머이쌀국수", "url": "https://naver.me/FV75CwnY"},
    {"main_menu": "떡볶이", "name": "신전떡볶이", "url": "https://naver.me/5qDZmvDK"},
    {"main_menu": "제육볶음", "name": "연신내", "url": "https://naver.me/xCBDpY8u"},
    {"main_menu": "돈가스", "name": "오늘은수제돈가스", "url": "https://naver.me/GOPeK9Ar"},
    {"main_menu": "중식", "name": "오로지짬뽕", "url": "https://naver.me/FeX2hhFN"},
    {"main_menu": "포케,샌드위치", "name": "우키샌드위치", "url": None},
    {"main_menu": "분식", "name": "일대김밥", "url": "https://naver.me/5chljxqQ"},
    {"main_menu": "분식", "name": "제주분식", "url": "https://naver.me/GEX0nwPZ"},
    {"main_menu": "중식", "name": "중찬미식", "url": "https://naver.me/xprhXOTH"},
    {"main_menu": "마라탕", "name": "진달래 양꼬치 마라탕", "url": "https://naver.me/FjbnpkXQ"},
    {"main_menu": "칼국수", "name": "참만나칼국수", "url": "https://naver.me/53lu38dR"},
    {"main_menu": "닭갈비", "name": "춘천닭갈비막국수", "url": "https://naver.me/5JpUYyAR"},
    {"main_menu": "라멘", "name": "쿠니라멘", "url": "https://naver.me/xmxcITjG"},
    {"main_menu": "순대국/순대볶음", "name": "태평순대", "url": "https://naver.me/FG7xn9wT"},
    {"main_menu": "한식", "name": "푸짐한마을", "url": "https://naver.me/GgWaS5X2"},
    {"main_menu": "피자", "name": "피자스쿨", "url": "https://naver.me/xxYv5Oba"},
    {"main_menu": "중식", "name": "하오하오", "url": "https://naver.me/FN7ZCHbm"},
    {"main_menu": "쌀국수", "name": "하이비엣남_쌀국수", "url": "https://naver.me/52RVh9SW"},
    {"main_menu": "중식", "name": "홍콩반점0410", "url": "https://naver.me/5KbK526x"},
]

REVIEW_FILE = "reviews.json"

def load_reviews():
    if os.path.exists(REVIEW_FILE):
        with open(REVIEW_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_reviews(reviews):
    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=4)

def calculate_average_rating(reviews):
    if not reviews:
        return 0
    total = sum(int(r['rating']) for r in reviews)
    return round(total / len(reviews), 1)

@app.route('/', methods=['GET', 'POST'])
def index():
    pick = None
    reviews = []
    avg_rating = 0
    
    if request.method == 'POST':
        # 추천받기
        if 'preference' in request.form and 'rating' not in request.form:
            preference = request.form.get('preference', '')
            filtered = [r for r in restaurants if preference in r["main_menu"] or not preference] or restaurants
            pick = random.choice(filtered)
            reviews = load_reviews().get(pick['name'], [])
            avg_rating = calculate_average_rating(reviews)
        
        # 리뷰 등록
        elif 'rating' in request.form and 'review' in request.form and 'restaurant' in request.form:
            restaurant = request.form['restaurant']
            rating = request.form['rating']
            review = request.form['review']
            if rating and review:
                reviews_dict = load_reviews()
                if restaurant not in reviews_dict:
                    reviews_dict[restaurant] = []
                reviews_dict[restaurant].append({"rating": rating, "review": review})
                save_reviews(reviews_dict)
            pick = next(r for r in restaurants if r['name'] == restaurant)
            reviews = load_reviews().get(restaurant, [])
            avg_rating = calculate_average_rating(reviews)
    
    return render_template('index.html', pick=pick, reviews=reviews, avg_rating=avg_rating)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)