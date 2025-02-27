from flask import Flask, render_template, request, jsonify, send_from_directory
import random
import os
import base64
import firebase_admin
from firebase_admin import credentials, firestore
import json
from google.oauth2 import service_account

app = Flask(__name__)

# Firebase 초기화 (환경 변수에서 키 로드)
cred_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON', '{"type": "service_account", ...}')  # 로컬은 JSON 파일로 대체
cred_dict = json.loads(cred_json)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)
db = firestore.client()

restaurants = sorted([
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
], key=lambda x: x['name'])

def load_reviews():
    reviews_ref = db.collection('reviews').get()
    reviews = {}
    for doc in reviews_ref:
        restaurant = doc.id
        reviews[restaurant] = doc.to_dict().get('reviews', [])
    return reviews

def save_reviews(reviews):
    for restaurant, review_list in reviews.items():
        db.collection('reviews').document(restaurant).set({'reviews': review_list})

def load_photos():
    photos_ref = db.collection('photos').get()
    photos = {}
    for doc in photos_ref:
        restaurant = doc.id
        photos[restaurant] = doc.to_dict().get('photos', [])
    return photos

def save_photos(photos):
    for restaurant, photo_list in photos.items():
        db.collection('photos').document(restaurant).set({'photos': photo_list})

def calculate_average_rating(reviews):
    if not reviews:
        return 0
    total = sum(int(r['rating']) for r in reviews)
    return round(total / len(reviews), 1)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    pick = None
    reviews = []
    avg_rating = 0
    photos = []
    message = None
    
    if request.method == 'POST':
        try:
            if 'preference' in request.form and 'rating' not in request.form and 'photo_upload' not in request.form and 'delete_photo' not in request.form and 'delete_review' not in request.form:
                preference = request.form.get('preference', '')
                filtered = [r for r in restaurants if preference in r["main_menu"] or not preference] or restaurants
                pick = random.choice(filtered)
            
            elif 'rating' in request.form and 'review' in request.form and 'restaurant' in request.form:
                restaurant = request.form['restaurant']
                rating = request.form['rating']
                review = request.form['review']
                username = request.form.get('username', '익명')
                pick = next(r for r in restaurants if r['name'] == restaurant)
                if rating and review:
                    reviews_dict = load_reviews()
                    if restaurant not in reviews_dict:
                        reviews_dict[restaurant] = []
                    reviews_dict[restaurant].append({"rating": rating, "review": review, "username": username})
                    save_reviews(reviews_dict)
                    message = "리뷰가 등록되었습니다!"
            
            elif 'photo_upload' in request.form and 'restaurant' in request.form:
                restaurant = request.form['restaurant']
                pick = next(r for r in restaurants if r['name'] == restaurant)
                if 'photo' in request.files:
                    file = request.files['photo']
                    if file and allowed_file(file.filename):
                        photo_data = base64.b64encode(file.read()).decode('utf-8')
                        photos_dict = load_photos()
                        if restaurant not in photos_dict:
                            photos_dict[restaurant] = []
                        photos_dict[restaurant].append(photo_data)
                        save_photos(photos_dict)
                        message = "사진이 업로드되었습니다!"
            
            elif 'delete_photo' in request.form and 'restaurant' in request.form:
                restaurant = request.form['restaurant']
                photo_index = int(request.form['delete_photo'])
                pick = next(r for r in restaurants if r['name'] == restaurant)
                photos_dict = load_photos()
                if restaurant in photos_dict and 0 <= photo_index < len(photos_dict[restaurant]):
                    del photos_dict[restaurant][photo_index]
                    if not photos_dict[restaurant]:
                        db.collection('photos').document(restaurant).delete()  # 빈 리스트면 문서 삭제
                    else:
                        save_photos(photos_dict)
                    message = "사진이 삭제되었습니다!"
            
            elif 'delete_review' in request.form and 'restaurant' in request.form:
                restaurant = request.form['restaurant']
                review_index = int(request.form['delete_review'])
                pick = next(r for r in restaurants if r['name'] == restaurant)
                reviews_dict = load_reviews()
                if restaurant in reviews_dict and 0 <= review_index < len(reviews_dict[restaurant]):
                    del reviews_dict[restaurant][review_index]
                    if not reviews_dict[restaurant]:
                        del reviews_dict[restaurant]
                    save_reviews(reviews_dict)
                    message = "리뷰가 삭제되었습니다!"
            
            elif 'restaurant' in request.form and 'rating' not in request.form and 'photo_upload' not in request.form and 'delete_photo' not in request.form and 'delete_review' not in request.form:
                restaurant = request.form['restaurant']
                pick = next(r for r in restaurants if r['name'] == restaurant)
        except Exception as e:
            message = f"오류 발생: {str(e)}"
    
    if pick:
        reviews = load_reviews().get(pick['name'], [])
        avg_rating = calculate_average_rating(reviews)
        photos = load_photos().get(pick['name'], [])
    
    return render_template('index.html', restaurants=restaurants, pick=pick, reviews=reviews, avg_rating=avg_rating, photos=photos, message=message)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)