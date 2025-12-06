"""
메르의 블로그 크롤러 설정
"""
import os

# 블로그 정보
BLOG_ID = "ranto28"
BLOG_NAME = "메르의 블로그"

# 크롤링 대상 카테고리 (정확한 이름은 실제 블로그에서 확인 필요)
TARGET_CATEGORIES = [
    "경제",
    "주식",
    "국제정세",
    "사회",
]

# 저장 경로 (한글 경로 지원)
OUTPUT_DIR = os.path.expanduser("~/승표의보관소/Web Clipping/메르의 블로그 원문")

# 크롤링 기록 파일
CRAWLED_POSTS_FILE = os.path.join(os.path.dirname(__file__), ".last_crawl")

# 요청 설정
REQUEST_DELAY = 1.0  # 요청 간 딜레이 (초) - 서버 부하 방지
USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"

# URL 패턴
MOBILE_BASE_URL = "https://m.blog.naver.com"
CATEGORY_LIST_URL = f"{MOBILE_BASE_URL}/PostList.naver"
POST_URL_FORMAT = f"{MOBILE_BASE_URL}/{BLOG_ID}/{{post_id}}"
