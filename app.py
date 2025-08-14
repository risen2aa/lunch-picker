import os
import sys
import io
import random
import time
import json
import re
import asyncio
from pathlib import Path
from mimetypes import guess_type
from PIL import Image
from flask import Flask, render_template, request, Response, abort
from jinja2 import DictLoader
import aiofiles
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# 환경 변수 로드 및 앱 설정
load_dotenv()
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 요청 전체 5MB 제한

# 템플릿
TEMPLATES = {
    'base.html': r'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}명학역 맛집 추천 | {{ brand.name }}{% endblock %}</title>
  <meta name="description" content="{% block meta_description %}명학역 맛집 추천 리스트 | 실제 방문수, 별점, 카테고리 필터 제공{% endblock %}">
  <link rel="canonical" href="{{ canonical or request.url }}">
  <meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{% block og_title %}명학역 맛집 추천{% endblock %}">
  <meta property="og:description" content="{% block og_description %}도보 거리/가격대/별점 기반 추천{% endblock %}">
  <meta property="og:url" content="{{ canonical or request.url }}">
  <meta property="og:image" content="{{ og_image or url_for('static', filename='cover.jpg', _external=True) }}">
  <style>
    body{font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif; margin:0; background:#fafafa;}
    .container{max-width:1100px; margin:0 auto; padding:16px;}
    header{display:flex; align-items:center; gap:12px; padding:12px 0;}
    header img{height:36px}
    .grid{display:grid; grid-template-columns:280px 1fr; gap:20px;}
    @media (max-width: 768px) {
      .grid{grid-template-columns:1fr;}
      .list{max-height:50vh;}
      .photos{grid-template-columns:repeat(auto-fill,minmax(120px,1fr));}
      .btn{padding:10px 14px; font-size:16px; touch-action:manipulation;}
    }
    .card{background:#fff; border:1px solid #eee; border-radius:12px; padding:16px;}
    .list{list-style:none; margin:0; padding:0; max-height:70vh; overflow:auto;}
    .list li{padding:10px 8px; border-bottom:1px solid #f1f1f1;}
    .list a{color:#222; text-decoration:none; display:block}
    .badge{display:inline-block; padding:2px 8px; background:#eef; border-radius:999px; font-size:12px; margin-left:6px}
    .brand-box{background:#f7fbff; border:1px solid #e2efff;}
    .footer{color:#666; font-size:14px; padding:24px 0; text-align:center}
    form{margin:0}
    input,select,textarea,button{font:inherit}
    .btn{padding:8px 12px; border-radius:8px; border:1px solid #ddd; background:#fff; cursor:pointer}
    .btn-primary{background:#2b6cb0; color:#fff; border-color:#2b6cb0}
    .muted{color:#666}
    .photos{display:grid; grid-template-columns:repeat(auto-fill,minmax(140px,1fr)); gap:10px}
    .photos img{width:100%; height:110px; object-fit:cover; border-radius:8px; border:1px solid #eee}
    .reviews{display:flex; flex-direction:column; gap:10px}
    .review{border:1px solid #eee; border-radius:8px; padding:10px}
    .pill{display:inline-block; padding:2px 8px; border-radius:999px; background:#f4f4f4; font-size:12px}
    .error{color:#d32f2f; font-size:14px; margin-top:8px}
    .search-bar{display:flex; gap:8px; margin-bottom:12px}
    .search-bar input{width:100%; padding:8px; border:1px solid #ddd; border-radius:8px}
  </style>
  {% block head_extra %}{% endblock %}
</head>
<body>
  <div class="container">
    <header>
      <img src="{{ url_for('static', filename='logo.png') }}" alt="{{ brand.name }}">
      <div>
        <div><strong>{{ brand.name }}</strong></div>
        <div class="muted" style="font-size:14px">{{ brand.slogan }}</div>
      </div>
    </header>
    <div class="grid">
      <aside>
        <div class="card brand-box">
          <h3>🎓 {{ brand.name }}</h3>
          <p class="muted">사회복지사·보육교사·한국어교원·사서 등 자격, 온라인으로 취득</p>
          <a class="btn btn-primary" href="{{ brand.url }}" target="_blank" rel="nofollow noopener">공식 사이트</a>
        </div>
        <div class="card">
          <h3>명학역 맛집 리스트</h3>
          <form class="search-bar" method="get" action="{{ url_for('search') }}">
            <input type="text" name="q" placeholder="식당 이름/메뉴 검색" aria-label="식당 검색">
            <button class="btn btn-primary" type="submit">검색</button>
          </form>
          <ul class="list">
            {% for r in restaurants %}
              <li>
                <a href="{{ url_for('place', slug=slugify(r['name'], r['main_menu'])) }}">{{ r['name'] }}<span class="badge">{{ r['main_menu'] }}</span></a>
              </li>
            {% endfor %}
          </ul>
        </div>
      </aside>
      <main>
        {% block content %}{% endblock %}
      </main>
    </div>
    <div class="footer">© 2025 {{ brand.name }} · <a href="{{ url_for('sitemap') }}">sitemap</a></div>
  </div>
</body>
</html>''',

    'index.html': r'''{% extends 'base.html' %}
{% block title %}명학역 맛집 추천 40곳 | {{ brand.name }}{% endblock %}
{% block meta_description %}명학역 맛집 추천 리스트: 한식, 중식, 분식, 라멘 등 40곳. 실제 방문수/별점 기반 추천.{% endblock %}
{% block og_title %}명학역 맛집 추천 40곳{% endblock %}
{% block og_description %}도보 거리/가격대/별점/방문수 기반 추천{% endblock %}
{% block head_extra %}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "ItemList",
  "name": "명학역 맛집 추천",
  "itemListElement": [
    {% for r in restaurants %}{"@type":"ListItem","position": {{ loop.index }},"url":"{{ url_for('place', slug=slugify(r['name'], r['main_menu']), _external=True) }}"}{% if not loop.last %},{% endif %}{% endfor %}
  ]
}
</script>
{% endblock %}
{% block content %}
  <div class="card">
    <h1>명학역 맛집 추천</h1>
    <p class="muted">명학역 직장인 점심/저녁을 위한 선별 리스트입니다. 카테고리로 골라보세요.</p>
    <form method="post" style="display:flex; gap:8px; align-items:center; flex-wrap:wrap">
      <label>카테고리
        <select name="preference">
          <option value="">전체</option>
          {% for c in categories %}
            <option value="{{ c }}">{{ c }}</option>
          {% endfor %}
        </select>
      </label>
      <button class="btn btn-primary" type="submit">랜덤 추천</button>
    </form>
  </div>
  {% if message %}
  <div class="card" style="margin-top:12px; background:#f6ffed; border-color:#b7eb8f">{{ message }}</div>
  {% endif %}
  {% if error %}
  <div class="card error" style="margin-top:12px">{{ error }}</div>
  {% endif %}
  {% if pick %}
    <div class="card" style="margin-top:12px">
      <h2>{{ pick.name }} <span class="badge">{{ pick.main_menu }}</span></h2>
      {% if reason %}<p class="muted">{{ reason }}</p>{% endif %}
      <p>평균 별점: <strong>{{ avg_rating }}</strong> / 5 · 방문수: <span class="pill">{{ visits.get(pick.name, 0) }}</span></p>
      <p>
        {% if pick.url %}<a class="btn" href="{{ pick.url }}" target="_blank" rel="noopener">네이버 지도 보기</a>{% endif %}
        <a class="btn btn-primary" href="{{ url_for('place', slug=slugify(pick['name'], pick['main_menu'])) }}">상세 페이지</a>
      </p>
      <h3>사진</h3>
      <div class="photos">
        {% for i in range(photos|length) %}
          <img src="{{ url_for('image', restaurant=pick.name, idx=i+1) }}" alt="{{ pick.name }} 사진 {{ i+1 }}">
        {% else %}
          <div class="muted">사진이 아직 없습니다.</div>
        {% endfor %}
      </div>
      <form method="post" enctype="multipart/form-data" style="margin-top:10px">
        <input type="hidden" name="restaurant" value="{{ pick.name }}">
        <input type="hidden" name="photo_upload" value="1">
        <input type="file" name="photo" accept="image/*">
        <button class="btn" type="submit">사진 업로드</button>
      </form>
      <h3>리뷰</h3>
      <div class="reviews">
        {% for r in reviews %}
          <div class="review">
            <div>⭐ {{ r.rating }} · <span class="muted">{{ r.username }}</span></div>
            <div>{{ r.review }}</div>
            <form method="post" style="margin-top:6px">
              <input type="hidden" name="restaurant" value="{{ pick.name }}">
              <button class="btn" name="delete_review" value="{{ loop.index0 }}">리뷰 삭제</button>
            </form>
          </div>
        {% else %}
          <div class="muted">아직 리뷰가 없습니다.</div>
        {% endfor %}
      </div>
      <form method="post" style="margin-top:10px; display:grid; gap:6px; max-width:420px">
        <input type="hidden" name="restaurant" value="{{ pick.name }}">
        <label>별점
          <select name="rating">
            <option value="5">5</option>
            <option value="4">4</option>
            <option value="3">3</option>
            <option value="2">2</option>
            <option value="1">1</option>
          </select>
        </label>
        <label>이름 <input name="username" placeholder="익명" maxlength="50"></label>
        <label>리뷰 <textarea name="review" rows="3" placeholder="맛은 어떤가요?" maxlength="500"></textarea></label>
        <button class="btn btn-primary" type="submit">리뷰 등록</button>
      </form>
      <form method="post" style="margin-top:10px">
        <input type="hidden" name="restaurant" value="{{ pick.name }}">
        <button class="btn" name="visit" value="1">방문 체크</button>
      </form>
    </div>
  {% endif %}
{% endblock %}
''',

    'place.html': r'''{% extends 'base.html' %}
{% block title %}{{ pick.name }} {{ pick.main_menu }} - 명학역 맛집 | {{ brand.name }}{% endblock %}
{% block meta_description %}{{ pick.name }} ({{ pick.main_menu }}), 명학역 맛집 상세: 평균 별점 {{ avg_rating }}, 방문수 {{ visits }}, 사진/리뷰 보기{% endblock %}
{% block og_title %}{{ pick.name }} - 명학역 {{ pick.main_menu }}{% endblock %}
{% block og_description %}평균 별점 {{ avg_rating }}, 실제 리뷰와 사진 제공{% endblock %}
{% set canonical = url_for('place', slug=slugify(pick.name, pick.main_menu), _external=True) %}
{% block head_extra %}
<script type="application/ld+json">
{
  "@context":"https://schema.org",
  "@type":"Restaurant",
  "name":"{{ pick.name }}",
  "servesCuisine":"{{ pick.main_menu }}",
  "address":{"@type":"PostalAddress","addressLocality":"안양시"},
  "areaServed":"명학역",
  "url":"{{ canonical }}",
  "image": [
    {% for i in range(photos|length) %}"{{ url_for('image', restaurant=pick.name, idx=i+1, _external=True) }}"{% if not loop.last %},{% endif %}{% endfor %}
  ],
  "aggregateRating":{ "@type":"AggregateRating", "ratingValue":"{{ avg_rating }}", "reviewCount":"{{ reviews|length }}" }
}
</script>
{% endblock %}
{% block content %}
  <div class="card">
    <a class="btn" href="{{ url_for('index') }}">← 리스트로</a>
    <h1 style="margin-top:10px">{{ pick.name }} <span class="badge">{{ pick.main_menu }}</span></h1>
    <p class="muted">명학역 주변 맛집. 간혹 ‘명학엿’으로도 검색합니다.</p>
    <p>평균 별점: <strong>{{ avg_rating }}</strong> / 5 · 방문수: <span class="pill">{{ visits }}</span></p>
    <p>
      {% if pick.url %}<a class="btn" href="{{ pick.url }}" target="_blank" rel="noopener">네이버 지도</a>{% endif %}
    </p>
    <h3>사진</h3>
    <div class="photos">
      {% for i in range(photos|length) %}
        <img src="{{ url_for('image', restaurant=pick.name, idx=i+1) }}" alt="{{ pick.name }} 사진 {{ i+1 }}">
      {% else %}
        <div class="muted">사진이 아직 없습니다.</div>
      {% endfor %}
    </div>
    <form method="post" action="{{ url_for('index') }}" enctype="multipart/form-data" style="margin-top:10px">
      <input type="hidden" name="restaurant" value="{{ pick.name }}">
      <input type="hidden" name="photo_upload" value="1">
      <input type="file" name="photo" accept="image/*">
      <button class="btn" type="submit">사진 업로드</button>
    </form>
    <h3>리뷰</h3>
    <div class="reviews">
      {% for r in reviews %}
        <div class="review">
          <div>⭐ {{ r.rating }} · <span class="muted">{{ r.username }}</span></div>
          <div>{{ r.review }}</div>
          <form method="post" action="{{ url_for('index') }}" style="margin-top:6px">
            <input type="hidden" name="restaurant" value="{{ pick.name }}">
            <button class="btn" name="delete_review" value="{{ loop.index0 }}">리뷰 삭제</button>
          </form>
        </div>
      {% else %}
        <div class="muted">아직 리뷰가 없습니다.</div>
      {% endfor %}
    </div>
    <form method="post" action="{{ url_for('index') }}" style="margin-top:10px; display:grid; gap:6px; max-width:420px">
      <input type="hidden" name="restaurant" value="{{ pick.name }}">
      <label>별점
        <select name="rating">
          <option value="5">5</option>
          <option value="4">4</option>
          <option value="3">3</option>
          <option value="2">2</option>
          <option value="1">1</option>
        </select>
      </label>
      <label>이름 <input name="username" placeholder="익명" maxlength="50"></label>
      <label>리뷰 <textarea name="review" rows="3" placeholder="맛은 어떤가요?" maxlength="500"></textarea></label>
      <button class="btn btn-primary" type="submit">리뷰 등록</button>
    </form>
    <form method="post" action="{{ url_for('index') }}" style="margin-top:10px">
      <input type="hidden" name="restaurant" value="{{ pick.name }}">
      <button class="btn" name="visit" value="1">방문 체크</button>
    </form>
  </div>
{% endblock %}
'''
}

# Jinja 로더
app.jinja_loader = DictLoader(TEMPLATES)

# 데이터 로드
DATA_PATH = 'restaurants.json'

async def load_restaurants():
    if not os.path.exists(DATA_PATH):
        async with aiofiles.open(DATA_PATH, 'w', encoding='utf-8') as f:
            await f.write(json.dumps([
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
            ], ensure_ascii=False))
    async with aiofiles.open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.loads(await f.read())
    return sorted(data, key=lambda x: x['name'])

restaurants = asyncio.run(load_restaurants())
CATEGORIES = sorted({r['main_menu'] for r in restaurants})

# 브랜드 정보
BRAND = {
    "name": "중앙사이버평생교육원",
    "url": "https://example.com",
    "slogan": "일과 학위를 함께! 자격·학위 100% 온라인",
}

# 유틸
IMAGE_DIR = Path('images')
IMAGE_DIR.mkdir(exist_ok=True)
MAX_PHOTOS_PER_RESTAURANT = 10

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def slugify(name: str, menu: str) -> str:
    base = f"{name}-{menu}-명학역"
    s = re.sub(r'[^가-힣a-zA-Z0-9\- ]', '', base).strip().replace(' ', '-')
    return s

app.jinja_env.globals['slugify'] = slugify

def sanitize_input(text: str) -> str:
    return re.sub(r'[<>"\']', '', (text or '')[:500]).strip()

def safe_filename_component(text: str) -> str:
    return re.sub(r'[^가-힣a-zA-Z0-9_-]+', '', text or '').strip()[:80]

CACHE_TTL = 60
_reviews_cache = {}
_photos_cache = {}
_visits_cache = {}

def _get_cached(bucket: dict, key: str):
    item = bucket.get(key)
    if item and (time.time() - item["ts"] <= CACHE_TTL):
        return item["data"]
    return None

def _set_cached(bucket: dict, key: str, data):
    bucket[key] = {"ts": time.time(), "data": data}
    return data

# Firestore 스토리지 레이어
cred = credentials.Certificate(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'credentials/service-account.json'))
firebase_admin.initialize_app(cred)
db = firestore.client()

class FirestoreStorage:
    async def get_reviews(self, name):
        try:
            doc_ref = db.collection('reviews').document(name)
            doc = await doc_ref.get()
            return doc.to_dict().get('reviews', []) if doc.exists else []
        except Exception as e:
            print(f"[ERROR] Firestore get_reviews failed: {e}", file=sys.stderr)
            return []

    async def save_reviews(self, name, reviews):
        try:
            await db.collection('reviews').document(name).set({'reviews': reviews})
        except Exception as e:
            print(f"[ERROR] Firestore save_reviews failed: {e}", file=sys.stderr)

    async def get_photos(self, name):
        try:
            doc_ref = db.collection('photos').document(name)
            doc = await doc_ref.get()
            return doc.to_dict().get('photos', []) if doc.exists else []
        except Exception as e:
            print(f"[ERROR] Firestore get_photos failed: {e}", file=sys.stderr)
            return []

    async def save_photos(self, name, photos):
        try:
            ref = db.collection('photos').document(name)
            if photos:
                await ref.set({'photos': photos})
            else:
                await ref.delete()
        except Exception as e:
            print(f"[ERROR] Firestore save_photos failed: {e}", file=sys.stderr)

    async def get_visits(self, name):
        try:
            doc_ref = db.collection('visits').document(name)
            doc = await doc_ref.get()
            return int(doc.to_dict().get('count', 0)) if doc.exists else 0
        except Exception as e:
            print(f"[ERROR] Firestore get_visits failed: {e}", file=sys.stderr)
            return 0

    async def increment_visits(self, name):
        try:
            doc_ref = db.collection('visits').document(name)
            doc = await doc_ref.get()
            current = doc.to_dict().get('count', 0) if doc.exists else 0
            await doc_ref.set({'count': current + 1})
            return current + 1
        except Exception as e:
            print(f"[ERROR] Firestore increment_visits failed: {e}", file=sys.stderr)
            return await self.get_visits(name)

storage = FirestoreStorage()

# 캐시 래퍼
async def get_reviews(name: str):
    cached = _get_cached(_reviews_cache, name)
    if cached is not None:
        return cached
    data = await storage.get_reviews(name)
    return _set_cached(_reviews_cache, name, data)

async def save_reviews(name: str, review_list: list):
    await storage.save_reviews(name, review_list)
    _set_cached(_reviews_cache, name, review_list)

async def get_photos(name: str):
    cached = _get_cached(_photos_cache, name)
    if cached is not None:
        return cached
    data = await storage.get_photos(name)
    return _set_cached(_photos_cache, name, data)

async def save_photos(name: str, photo_list: list):
    await storage.save_photos(name, photo_list)
    _set_cached(_photos_cache, name, photo_list)

async def get_visits(name: str) -> int:
    cached = _get_cached(_visits_cache, name)
    if cached is not None:
        return cached
    v = await storage.get_visits(name)
    return _set_cached(_visits_cache, name, v)

async def increment_visits(name: str) -> int:
    v = await storage.increment_visits(name)
    _set_cached(_visits_cache, name, v)
    return v

def calculate_average_rating(reviews: list) -> float:
    if not reviews:
        return 0.0
    total = sum(int((r or {}).get('rating', 0)) for r in reviews)
    return round(total / len(reviews), 1)

# POST 처리 함수
async def handle_index_post(form, files):
    pick = None
    reviews = []
    avg_rating = 0
    photos = []
    message = None
    error = None
    reason = None
    visits_for_pick = 0

    try:
        # 1) 랜덤 추천
        if 'preference' in form and all(k not in form for k in ['rating', 'photo_upload', 'delete_review', 'visit']) and 'restaurant' not in form:
            preference = form.get('preference', '')
            filtered = [r for r in restaurants if preference in r["main_menu"] or not preference] or restaurants
            pick = random.choice(filtered)
            reviews = await get_reviews(pick['name'])
            avg = calculate_average_rating(reviews)
            reason = f"최근 별점 {avg}/5를 받은 인기 식당!" if avg > 0 else "무작위로 추천된 맛집!"

        # 2) 리뷰 등록
        elif {'rating', 'review', 'restaurant'} <= set(form.keys()):
            restaurant = form['restaurant']
            pick = next((r for r in restaurants if r['name'] == restaurant), None)
            if not pick:
                raise ValueError("식당을 찾을 수 없습니다")
            rating = form['rating']
            review = sanitize_input(form['review'])
            username = sanitize_input(form.get('username', '익명'))
            if not rating.isdigit() or int(rating) not in range(1, 6):
                raise ValueError("유효하지 않은 별점입니다")
            if not review:
                raise ValueError("리뷰를 입력해주세요")
            review_list = list(await get_reviews(restaurant))
            review_list.append({"rating": rating, "review": review, "username": username})
            await save_reviews(restaurant, review_list)
            message = "리뷰가 등록되었습니다!"

        # 3) 사진 업로드
        elif 'photo_upload' in form and 'restaurant' in form:
            restaurant = form['restaurant']
            pick = next((r for r in restaurants if r['name'] == restaurant), None)
            if not pick:
                raise ValueError("식당을 찾을 수 없습니다")
            if 'photo' not in files:
                raise ValueError("사진을 선택해주세요")
            file = files['photo']
            if not file or not allowed_file(file.filename):
                raise ValueError("허용되지 않는 파일 형식입니다 (png, jpg, jpeg, gif, webp)")
            file_content = file.read()
            if len(file_content) > app.config['MAX_CONTENT_LENGTH']:
                raise ValueError("파일 크기가 너무 큽니다 (단일 파일 최대 5MB)")
            photo_list = list(await get_photos(restaurant))
            if len(photo_list) >= MAX_PHOTOS_PER_RESTAURANT:
                raise ValueError(f"최대 {MAX_PHOTOS_PER_RESTAURANT}개의 사진만 업로드 가능합니다")
            img = Image.open(io.BytesIO(file_content))
            img = img.convert('RGB')
            img.thumbnail((1024, 1024))
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85)
            file_content = output.getvalue()
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
            safe_restaurant = safe_filename_component(restaurant)
            filename = f"{safe_restaurant}_{len(photo_list)+1}.{ext}"
            photo_path = IMAGE_DIR / filename
            async with aiofiles.open(photo_path, 'wb') as f:
                await f.write(file_content)
            photo_list.append(str(photo_path))
            await save_photos(restaurant, photo_list)
            message = "사진이 업로드되었습니다!"

        # 4) 리뷰 삭제
        elif 'delete_review' in form and 'restaurant' in form:
            restaurant = form['restaurant']
            idx = int(form['delete_review'])
            pick = next((r for r in restaurants if r['name'] == restaurant), None)
            if not pick:
                raise ValueError("식당을 찾을 수 없습니다")
            review_list = list(await get_reviews(restaurant))
            if not (0 <= idx < len(review_list)):
                raise ValueError("유효하지 않은 리뷰 인덱스입니다")
            del review_list[idx]
            await save_reviews(restaurant, review_list)
            message = "리뷰가 삭제되었습니다!"

        # 5) 방문 체크
        elif 'visit' in form and 'restaurant' in form:
            restaurant = form['restaurant']
            pick = next((r for r in restaurants if r['name'] == restaurant), None)
            if not pick:
                raise ValueError("식당을 찾을 수 없습니다")
            visits_for_pick = await increment_visits(restaurant)
            message = "방문 체크 완료!"

        # 6) 특정 식당 미리보기
        elif 'restaurant' in form and all(k not in form for k in ['rating', 'photo_upload', 'delete_review', 'visit']):
            restaurant = form['restaurant']
            pick = next((r for r in restaurants if r['name'] == restaurant), None)
            if not pick:
                raise ValueError("식당을 찾을 수 없습니다")
            reviews = await get_reviews(pick['name'])
            avg = calculate_average_rating(reviews)
            reason = f"최근 별점 {avg}/5를 받은 인기 식당!" if avg > 0 else "무작위로 추천된 맛집!"

    except ValueError as e:
        error = str(e)
    except FileNotFoundError:
        error = "파일 시스템 오류가 발생했습니다."
    except Exception as e:
        error = "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        print(f"[ERROR] {e}", file=sys.stderr)

    if pick:
        reviews = reviews or await get_reviews(pick['name'])
        avg_rating = calculate_average_rating(reviews)
        photos = await get_photos(pick['name'])
        visits_for_pick = visits_for_pick or await get_visits(pick['name'])

    return pick, reviews, avg_rating, photos, message, error, reason, visits_for_pick

# 라우트
@app.route('/', methods=['GET', 'POST'])
async def index():
    pick = None
    reviews = []
    avg_rating = 0
    photos = []
    message = None
    error = None
    reason = None
    visits_for_pick = 0

    if request.method == 'POST':
        pick, reviews, avg_rating, photos, message, error, reason, visits_for_pick = await handle_index_post(request.form, request.files)

    return render_template('index.html',
                           restaurants=restaurants,
                           categories=CATEGORIES,
                           brand=BRAND,
                           pick=pick,
                           reviews=reviews,
                           avg_rating=avg_rating,
                           photos=photos,
                           visits={pick['name']: visits_for_pick} if pick else {},
                           message=message,
                           error=error,
                           reason=reason)

@app.route('/place/<slug>')
async def place(slug):
    pick = None
    for r in restaurants:
        if slug == slugify(r['name'], r['main_menu']):
            pick = r
            break
    if not pick:
        return abort(404)

    reviews = await get_reviews(pick['name'])
    photos = await get_photos(pick['name'])
    visits = await get_visits(pick['name'])
    avg = calculate_average_rating(reviews)

    return render_template('place.html',
                           restaurants=restaurants,
                           brand=BRAND,
                           pick=pick,
                           reviews=reviews,
                           photos=photos,
                           avg_rating=avg,
                           visits=visits)

@app.route('/image/<path:restaurant>/<int:idx>')
async def image(restaurant, idx):
    try:
        photos = await get_photos(restaurant)
        if not (1 <= idx <= len(photos)):
            return abort(404)
        photo_path = photos[idx-1]
        mime = guess_type(photo_path)[0] or 'application/octet-stream'
        async with aiofiles.open(photo_path, 'rb') as f:
            data = await f.read()
        return Response(data, mimetype=mime)
    except FileNotFoundError:
        return abort(404)
    except Exception as e:
        print(f"[ERROR] Image serve failed: {e}", file=sys.stderr)
        return abort(404)

@app.route('/search')
async def search():
    query = (request.args.get('q') or '').strip().lower().replace(' ', '')
    if not query:
        return render_template('index.html',
                              restaurants=restaurants,
                              categories=CATEGORIES,
                              brand=BRAND,
                              message="검색어를 입력해주세요")

    filtered = [
        r for r in restaurants
        if query in r['name'].lower().replace(' ', '') or query in r['main_menu'].lower().replace(' ', '')
    ]
    return render_template('index.html',
                          restaurants=filtered,
                          categories=CATEGORIES,
                          brand=BRAND,
                          message=f"'{query}' 검색 결과: {len(filtered)}개 식당")

@app.route('/sitemap.xml')
def sitemap():
    urls = [request.url_root.rstrip('/') + '/'] + [
        request.url_root.rstrip('/') + '/place/' + slugify(r['name'], r['main_menu'])
        for r in restaurants
    ]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml.append(f"<url><loc>{u}</loc></url>")
    xml.append('</urlset>')
    return Response('\n'.join(xml), mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    content = f"""User-agent: *
Allow: /
Sitemap: {request.url_root.rstrip('/')}/sitemap.xml
"""
    return Response(content, mimetype='text/plain')

@app.route('/healthz')
def healthz():
    return {'ok': True, 'storage': 'FirestoreStorage'}

# 앱 실행
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
