#!/usr/bin/env python3
"""
메르의 블로그 크롤러
- 대상: https://blog.naver.com/ranto28
- 카테고리: 경제/주식/국제정세/사회 (categoryNo=21)
- PC 버전으로 목록 수집, 모바일 버전으로 본문 크롤링
"""
import os
import re
import time
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup

import config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 대상 카테고리 (하드코딩 - 블로그 구조 확인 완료)
TARGET_CATEGORY = {
    'name': '경제/주식/국제정세/사회',
    'no': '21'
}


class NaverBlogCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        self.crawled_posts = self._load_crawled_posts()
        self.crawl_state = self._load_crawl_state()  # 마지막 크롤링 위치
        self.crawl_results = []  # 크롤링 결과 저장 (로그용)

    def _load_crawled_posts(self) -> set:
        """이미 크롤링된 게시글 ID 목록 로드"""
        if os.path.exists(config.CRAWLED_POSTS_FILE):
            with open(config.CRAWLED_POSTS_FILE, 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f if line.strip())
        return set()

    def _load_crawl_state(self) -> dict:
        """마지막 크롤링 위치 로드 (페이지 번호, 마지막 게시글 ID)"""
        if os.path.exists(config.CRAWL_STATE_FILE):
            with open(config.CRAWL_STATE_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    parts = content.split(',')
                    if len(parts) >= 2:
                        return {
                            'last_page': int(parts[0]),
                            'last_post_id': parts[1]
                        }
        return {'last_page': 1, 'last_post_id': None}

    def _save_crawl_state(self, page: int, post_id: str):
        """마지막 크롤링 위치 저장"""
        with open(config.CRAWL_STATE_FILE, 'w', encoding='utf-8') as f:
            f.write(f"{page},{post_id}")
        self.crawl_state = {'last_page': page, 'last_post_id': post_id}

    def _save_crawled_post(self, post_id: str):
        """크롤링된 게시글 ID 저장"""
        with open(config.CRAWLED_POSTS_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{post_id}\n")
        self.crawled_posts.add(post_id)

    def _save_crawl_log(self):
        """크롤링 로그를 md 파일로 저장"""
        if not self.crawl_results:
            return

        os.makedirs(config.LOG_DIR, exist_ok=True)

        today = datetime.now().strftime('%Y-%m-%d')
        log_filename = f"crawl_log_{today}.md"
        log_filepath = os.path.join(config.LOG_DIR, log_filename)

        # 첫 번째와 마지막 크롤링 결과
        first_post = self.crawl_results[0]
        last_post = self.crawl_results[-1]

        log_content = f"""---
date: {today}
total_crawled: {len(self.crawl_results)}
---

# 크롤링 로그 - {today}

## 요약
- **크롤링 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **총 크롤링 수**: {len(self.crawl_results)}개

## 첫 번째 글
- **제목**: {first_post['title']}
- **날짜**: {first_post['date']}

## 마지막 글
- **제목**: {last_post['title']}
- **날짜**: {last_post['date']}

## 전체 목록
| 순번 | 제목 | 날짜 |
|------|------|------|
"""
        for i, post in enumerate(self.crawl_results, 1):
            # 제목에서 파이프 문자 이스케이프
            safe_title = post['title'].replace('|', '\\|')
            log_content += f"| {i} | {safe_title} | {post['date']} |\n"

        # 기존 로그 파일이 있으면 append, 없으면 새로 생성
        if os.path.exists(log_filepath):
            with open(log_filepath, 'a', encoding='utf-8') as f:
                f.write(f"\n\n---\n\n# 추가 크롤링 - {datetime.now().strftime('%H:%M:%S')}\n\n")
                f.write(f"- **크롤링 수**: {len(self.crawl_results)}개\n")
                f.write(f"- **첫 번째 글**: {first_post['title']} ({first_post['date']})\n")
                f.write(f"- **마지막 글**: {last_post['title']} ({last_post['date']})\n")
        else:
            with open(log_filepath, 'w', encoding='utf-8') as f:
                f.write(log_content)

        logger.info(f"크롤링 로그 저장: {log_filepath}")

    def _fetch_page(self, url: str, use_pc_agent: bool = False) -> BeautifulSoup | None:
        """페이지 요청 및 파싱"""
        try:
            headers = self.session.headers.copy()
            if use_pc_agent:
                headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'lxml')
        except requests.RequestException as e:
            logger.error(f"페이지 요청 실패: {url} - {e}")
            return None

    def _fetch_raw(self, url: str) -> str | None:
        """페이지 원본 텍스트 가져오기"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"페이지 요청 실패: {url} - {e}")
            return None

    def get_posts_in_category(self, limit: int = None, batch_size: int = None, start_page: int = None, stop_on_crawled: bool = False) -> tuple[list[str], int, bool]:
        """대상 카테고리의 게시글 ID 수집 (PC 버전 사용)

        저장된 마지막 페이지부터 시작하여 새 게시글을 수집합니다.

        Args:
            limit: 새 게시글 수집 개수 제한 (지정 시 새 게시글 n개 발견하면 즉시 중단)
            batch_size: 배치 크기 (지정 시 새 게시글 batch_size개 발견하면 즉시 중단)
            start_page: 시작 페이지 (지정하지 않으면 저장된 마지막 페이지 사용)
            stop_on_crawled: True면 이미 크롤링된 게시글을 만나면 즉시 중단 (일일 자동화용)

        Returns:
            (새 게시글 ID 목록, 마지막으로 탐색한 페이지 번호, 전체 완료 여부)
            - 전체 완료 = True: 더 이상 페이지가 없음 (빈 페이지 발견)
            - 전체 완료 = False: batch_size 도달로 중단 또는 stop_on_crawled로 중단 (계속 진행 필요할 수 있음)
        """
        new_posts = []  # 새 게시글만 수집

        # 시작 페이지 결정: 인자 > 저장된 상태 > 1
        if start_page is not None:
            page = start_page
        else:
            page = self.crawl_state.get('last_page', 1)

        if page > 1:
            logger.info(f"저장된 위치에서 재개: 페이지 {page}부터 시작")

        # limit이 있으면 limit 사용, 없으면 batch_size 사용
        target_count = limit if limit else batch_size
        last_page = page
        is_complete = False  # 전체 완료 여부

        # 연속으로 새 게시글이 없는 페이지 수 카운트 (조기 종료 방지)
        consecutive_no_new = 0
        MAX_CONSECUTIVE_NO_NEW = 10  # 연속 10페이지 동안 새 게시글 없으면 계속 진행하되 경고

        while True:
            url = f"https://blog.naver.com/PostList.naver?blogId={config.BLOG_ID}&categoryNo={TARGET_CATEGORY['no']}&currentPage={page}"
            soup = self._fetch_page(url, use_pc_agent=True)

            if not soup:
                is_complete = True  # 페이지 로드 실패 = 끝
                break

            # 글 목록에서 게시글 ID 추출
            # aPostBaseInfo 배열에서 추출 (가장 신뢰할 수 있는 방법)
            # 형식: aPostBaseInfo[1] = "게시글ID|...|페이지|카테고리|..."
            page_posts = []
            seen_in_page = set()
            html_str = str(soup)

            # 방법 1: aPostBaseInfo에서 카테고리 21 게시글 추출
            for match in re.finditer(r'aPostBaseInfo\[\d+\]\s*=\s*"(\d+)\|[^"]*\|' + TARGET_CATEGORY['no'] + r'\|', html_str):
                post_id = match.group(1)
                if post_id not in seen_in_page:
                    seen_in_page.add(post_id)
                    page_posts.append(post_id)

            # 방법 2: PostView.naver 패턴 (폴백)
            if not page_posts:
                for match in re.finditer(rf'PostView\.naver\?blogId={config.BLOG_ID}&logNo=(\d+)', html_str):
                    post_id = match.group(1)
                    if post_id not in seen_in_page:
                        seen_in_page.add(post_id)
                        page_posts.append(post_id)

            if not page_posts:
                is_complete = True  # 더 이상 게시글 없음 = 끝
                break

            # 페이지 내 새 게시글 수 카운트
            new_in_page = 0

            # 페이지 내 게시글 처리
            for post_id in page_posts:
                # 이미 크롤링된 게시글 처리
                if post_id in self.crawled_posts:
                    if stop_on_crawled:
                        # 일일 자동화 모드: 이미 크롤링된 게시글을 만나면 즉시 중단
                        logger.info(f"페이지 {page}: 이미 크롤링된 게시글 발견 (ID: {post_id}), 수집 중단")
                        # stop_on_crawled 모드에서는 is_complete=False로 반환 (다음 실행 시 같은 동작)
                        return new_posts, last_page, False
                    else:
                        # 초기 크롤링 모드: 건너뛰고 계속 진행
                        continue

                # 새 게시글 추가 (중복 체크)
                if post_id not in new_posts:
                    new_posts.append(post_id)
                    new_in_page += 1

                    # target_count에 도달하면 즉시 반환 (계속 진행 필요)
                    if target_count and len(new_posts) >= target_count:
                        logger.info(f"페이지 {page}: 새 게시글 {target_count}개 발견, 배치 중단")
                        return new_posts, page, False  # is_complete=False

            # 이 페이지에서 새 게시글이 있었는지 체크
            if new_in_page > 0:
                consecutive_no_new = 0
            else:
                consecutive_no_new += 1
                if consecutive_no_new >= MAX_CONSECUTIVE_NO_NEW:
                    logger.warning(f"페이지 {page}: 연속 {MAX_CONSECUTIVE_NO_NEW}페이지 동안 새 게시글 없음, 계속 진행...")
                    consecutive_no_new = 0  # 리셋하고 계속 진행

            logger.info(f"페이지 {page}: {len(page_posts)}개 게시글 확인 (새 게시글 누적: {len(new_posts)}개)")

            last_page = page
            page += 1
            time.sleep(config.REQUEST_DELAY)

        logger.info(f"총 {len(new_posts)}개 새 게시글 발견")
        return new_posts, last_page, is_complete

    def _clean_content(self, content: str) -> str:
        """본문 정리: 출처 제거, 줄바꿈 정리, 한줄코멘트 콜아웃 처리"""
        # 1. '© *, 출처 *' 패턴 제거
        content = re.sub(r'©[^,]*,\s*출처[^\n]*', '', content)

        # 2. 빈 줄만 있는 경우 (​ 같은 특수문자) 제거
        content = re.sub(r'\n\s*\u200b\s*\n', '\n', content)
        content = re.sub(r'^\s*\u200b\s*$', '', content, flags=re.MULTILINE)

        # 3. '한줄 코멘트' 부분을 콜아웃으로 변환 (빈 줄 정규화 전에 처리해야 함)
        # 패턴: "한줄코멘트", "한줄 코멘트", "한 줄 코멘트" 등 띄어쓰기 무관
        # 중요: 글 중간에 여러 번 등장할 수 있으므로, 맨 마지막 것만 콜아웃으로 처리
        lines = content.split('\n')

        # 한줄코멘트 패턴 (띄어쓰기 무관)
        comment_pattern = re.compile(r'^한\s*줄\s*코멘트\.?\s*', re.IGNORECASE)

        # 마지막 한줄코멘트 위치 찾기
        last_comment_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if comment_pattern.match(stripped):
                last_comment_idx = i

        # 마지막 한줄코멘트가 있으면 그 부분만 콜아웃으로 처리
        if last_comment_idx >= 0:
            result_lines = lines[:last_comment_idx]
            comment_lines = []
            after_comment_lines = []  # 빈줄 두 줄 이상 이후의 내용

            # 한줄코멘트 이후 내용 처리
            remaining_lines = lines[last_comment_idx:]
            consecutive_empty = 0
            found_separator = False  # 빈줄 두 줄 이상 발견 여부

            for line in remaining_lines:
                stripped = line.strip()

                if found_separator:
                    # 빈줄 두 줄 이상 이후의 내용은 별도 저장
                    if stripped:
                        after_comment_lines.append(stripped)
                else:
                    if not stripped:
                        consecutive_empty += 1
                        if consecutive_empty >= 2:
                            found_separator = True
                    else:
                        consecutive_empty = 0
                        if comment_pattern.match(stripped):
                            # "한줄코멘트." 또는 "한 줄 코멘트." 제거하고 나머지 내용만
                            comment_text = comment_pattern.sub('', stripped)
                            if comment_text:
                                comment_lines.append(comment_text)
                        else:
                            comment_lines.append(stripped)

            # 콜아웃 형식으로 변환
            if comment_lines:
                content = '\n'.join(result_lines).rstrip()
                comment_content = ' '.join(comment_lines)
                content += f"\n\n> [!note] 한줄코멘트\n> {comment_content}"

                # 빈줄 두 줄 이상 이후의 내용 추가
                if after_comment_lines:
                    content += "\n\n" + '\n\n'.join(after_comment_lines)
            else:
                content = '\n'.join(result_lines)

        # 4. 연속된 빈 줄을 1줄로 통일 (한줄코멘트 처리 후에 적용)
        content = re.sub(r'\n{3,}', '\n\n', content)

        return content.strip()

    def _extract_content_from_html(self, soup: BeautifulSoup) -> str:
        """HTML에서 본문 추출 - 구조를 유지하면서 추출"""
        main = soup.select_one('.se-main-container')
        if not main:
            return None

        paragraphs = []
        embedded_links = []  # 삽입된 링크 URL 저장

        # .se-component를 순회하여 텍스트와 테이블을 순서대로 처리
        for component in main.select('.se-component'):
            classes = component.get('class', [])

            # 테이블 컴포넌트 처리
            if 'se-table' in classes:
                table_md = self._extract_table(component)
                if table_md:
                    paragraphs.append(table_md)
            else:
                # 기존 텍스트 모듈 처리
                for module in component.select('.se-module'):
                    mod_classes = module.get('class', [])

                    if 'se-module-text' in mod_classes:
                        module_text = self._extract_text_module(module, embedded_links)
                        if module_text:
                            paragraphs.append(module_text)

                    elif 'se-module-image' in mod_classes:
                        # 이미지 모듈은 출처 텍스트만 추출 (나중에 제거됨)
                        caption = module.select_one('.se-caption, .se-text-paragraph')
                        if caption:
                            text = caption.get_text(strip=True)
                            if text and '출처' in text:
                                # 출처는 나중에 _clean_content에서 제거됨
                                pass

        content = '\n\n'.join(paragraphs)
        return content

    def _extract_table(self, component) -> str:
        """테이블 컴포넌트에서 마크다운 테이블 추출"""
        table = component.select_one('table.se-table-content')
        if not table:
            return None

        rows = table.select('tr.se-tr')
        if not rows:
            return None

        # 각 행에서 셀 추출
        table_data = []
        max_cols = 0

        for row in rows:
            cells = row.select('td.se-cell')
            row_data = []
            for cell in cells:
                # 셀 내 텍스트 추출 (여러 줄이면 공백으로 연결)
                text = cell.get_text(separator=' ').replace('\u200b', '').strip()
                # 셀 내 줄바꿈을 공백으로 변환
                text = re.sub(r'\s+', ' ', text)
                row_data.append(text)
            if row_data:  # 빈 행 제외
                table_data.append(row_data)
                max_cols = max(max_cols, len(row_data))

        if not table_data:
            return None

        # 마크다운 테이블 생성
        md_lines = []

        # 첫 행이 제목 행인지 확인 (단일 셀에 [] 포함이면 캡션)
        start_idx = 0
        if len(table_data) > 0:
            first_row = table_data[0]
            # 제목/캡션 행 처리 (예: "[미분양주택 추이]" 또는 "(단위 : 호)")
            if len(first_row) == 1:
                text = first_row[0]
                if text.startswith('[') or text.startswith('('):
                    md_lines.append(text)
                    start_idx = 1
                    # 두 번째 행도 단위 행인지 확인
                    if len(table_data) > 1 and len(table_data[1]) == 1:
                        text2 = table_data[1][0]
                        if text2.startswith('('):
                            md_lines.append(text2)
                            start_idx = 2

        # 실제 테이블 데이터
        actual_data = table_data[start_idx:]
        if not actual_data:
            return '\n'.join(md_lines) if md_lines else None

        # 열 수 통일
        actual_max_cols = max(len(row) for row in actual_data) if actual_data else 0
        if actual_max_cols == 0:
            return '\n'.join(md_lines) if md_lines else None

        # 헤더 행
        header = actual_data[0]
        # 빈 셀 패딩
        while len(header) < actual_max_cols:
            header.append('')
        md_lines.append('| ' + ' | '.join(header) + ' |')

        # 구분선
        md_lines.append('| ' + ' | '.join(['---'] * actual_max_cols) + ' |')

        # 데이터 행
        for row in actual_data[1:]:
            # 빈 셀 패딩
            while len(row) < actual_max_cols:
                row.append('')
            md_lines.append('| ' + ' | '.join(row) + ' |')

        return '\n'.join(md_lines)

    def _is_quotable_link(self, href: str) -> bool:
        """인용 처리해야 할 링크인지 확인 (언론사 + 본인 블로그)"""
        if not href:
            return False
        # 본인 블로그 링크
        if 'blog.naver.com/ranto28' in href or 'm.blog.naver.com/ranto28' in href:
            return True
        # 언론사 링크 (주요 언론사 도메인)
        news_domains = [
            'yna.co.kr', 'yonhap',  # 연합뉴스
            'chosun.com', 'donga.com', 'joongang.co.kr', 'hani.co.kr',  # 종합지
            'khan.co.kr', 'kmib.co.kr', 'mk.co.kr', 'mt.co.kr',  # 종합지/경제지
            'hankyung.com', 'sedaily.com', 'edaily.co.kr',  # 경제지
            'news.kbs.co.kr', 'news.sbs.co.kr', 'news.jtbc.co.kr',  # 방송사
            'news.mbc.co.kr', 'ytn.co.kr', 'newsis.com',  # 방송사/통신사
            'news1.kr', 'asiae.co.kr', 'newspim.com',  # 통신사/전문지
            'biz.chosun.com', 'news.einfomax.co.kr',  # 전문지
            'reuters.com', 'bloomberg.com', 'wsj.com',  # 외신
            'ft.com', 'nytimes.com', 'cnbc.com',  # 외신
        ]
        return any(domain in href for domain in news_domains)

    def _extract_text_module(self, module, embedded_links: list) -> str:
        """텍스트 모듈에서 본문 추출 - ol/li 번호 유지, 삽입 링크 인용 처리"""
        lines = []

        for elem in module.children:
            if not hasattr(elem, 'name'):
                continue

            # ol (순서 있는 리스트) 처리
            if elem.name == 'ol':
                list_class = elem.get('class', [])
                # decimal 타입 리스트 확인
                if any('decimal' in c for c in list_class):
                    for i, li in enumerate(elem.select('li'), 1):
                        text = li.get_text(strip=True)
                        # Zero-width space 제거
                        text = text.replace('\u200b', '').strip()
                        if text:
                            lines.append(f"{i}. {text}")

            # p (문단) 처리
            elif elem.name == 'p':
                # 여러 span 요소 사이의 공백을 보존하기 위해 separator=' ' 사용
                text = elem.get_text(separator='')
                # Zero-width space 제거
                text = text.replace('\u200b', '').strip()
                # 연속된 공백을 하나로 정리
                text = re.sub(r' {2,}', ' ', text)

                if text and len(text) > 1:
                    # 인용 처리할 링크가 있는 문단인지 확인
                    has_quotable_link = False
                    for link in elem.select('a.se-link'):
                        href = link.get('href', '')
                        if self._is_quotable_link(href):
                            has_quotable_link = True
                            break

                    # 인용 처리할 링크가 있는 문단은 인용 처리
                    if has_quotable_link:
                        lines.append(f"> {text}")
                    else:
                        lines.append(text)
                else:
                    # 빈 문단은 빈 줄로 추가 (한줄코멘트 분리에 필요)
                    lines.append('')

        # 결과 텍스트 생성 - 인용 줄 연속 시 빈줄 제거
        result = self._merge_consecutive_quotes(lines)

        return result

    def _merge_consecutive_quotes(self, lines: list) -> str:
        """연속된 인용 줄을 하나의 인용 블록으로 합침"""
        if not lines:
            return ''

        result_parts = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith('> '):
                # 연속된 인용 줄 수집
                quote_lines = [line]
                j = i + 1
                while j < len(lines) and lines[j].startswith('> '):
                    quote_lines.append(lines[j])
                    j += 1
                # 인용 줄들을 줄바꿈만으로 연결 (빈줄 없이)
                result_parts.append('\n'.join(quote_lines))
                i = j
            else:
                result_parts.append(line)
                i += 1

        # 일반 문단 사이는 빈줄로 구분
        return '\n\n'.join(result_parts)

    def crawl_post(self, post_id: str) -> dict | None:
        """개별 게시글 크롤링 (모바일 버전 사용)"""
        url = f"https://m.blog.naver.com/{config.BLOG_ID}/{post_id}"
        raw_html = self._fetch_raw(url)

        if not raw_html:
            return None

        soup = BeautifulSoup(raw_html, 'lxml')

        # 제목 추출 (og:title 메타 태그에서)
        title = None
        og_title = soup.select_one('meta[property="og:title"]')
        if og_title:
            title = og_title.get('content', '').strip()
            # " : 네이버 블로그" 제거
            if ' : 네이버 블로그' in title:
                title = title.replace(' : 네이버 블로그', '')

        if not title:
            title = f'제목없음_{post_id}'

        # 날짜 추출 - blog_date 클래스에서 (예: "2025. 12. 6. 0:10")
        date_str = None
        blog_date = soup.select_one('.blog_date')
        if blog_date:
            date_text = blog_date.get_text(strip=True)
            # "2025. 12. 6. 0:10" -> "2025.12.06" 형식으로 변환
            date_match = re.search(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})', date_text)
            if date_match:
                year, month, day = date_match.groups()
                date_str = f"{year}.{month.zfill(2)}.{day.zfill(2)}"

        # 대체: __INITIAL_STATE__ JSON에서 시도
        if not date_str:
            date_match = re.search(r'"publishDate"\s*:\s*"([^"]+)"', raw_html)
            if date_match:
                date_str = date_match.group(1)

        if not date_str:
            date_str = datetime.now().strftime('%Y.%m.%d')

        # 태그 추출 - tagNames 필드에서
        tags = []
        tag_match = re.search(r'tagNames[^:]*:[^"]*"([^"]*)"', raw_html)
        if tag_match:
            tag_str = tag_match.group(1)
            # 빈 문자열이나 백슬래시만 있는 경우 스킵
            if tag_str and tag_str.strip() and tag_str not in ['', '\\']:
                # \uXXXX 패턴을 직접 변환
                def decode_unicode_escape(s):
                    result = []
                    i = 0
                    while i < len(s):
                        if s[i:i+2] == '\\u' and i+6 <= len(s):
                            try:
                                code = int(s[i+2:i+6], 16)
                                result.append(chr(code))
                                i += 6
                                continue
                            except:
                                pass
                        result.append(s[i])
                        i += 1
                    return ''.join(result)

                tag_str = decode_unicode_escape(tag_str)
                # 태그 분리 및 정리 (남은 백슬래시 제거)
                tag_str = tag_str.replace('\\', '')
                tags = [t.strip() for t in tag_str.split(',') if t.strip()]

        # 본문 추출 - 구조를 유지하면서 추출
        content = self._extract_content_from_html(soup)

        # 대체 방법: 이전 방식으로 시도
        if not content:
            for selector in ['.se-main-container', '#postViewArea', '.post_ct']:
                elem = soup.select_one(selector)
                if elem:
                    for tag in elem.select('script, style, iframe, img, video, figure'):
                        tag.decompose()
                    content = elem.get_text(separator='\n', strip=True)
                    if content:
                        break

        if not content:
            logger.warning(f"게시글 {post_id}: 본문 추출 실패")
            return None

        # 본문 정리
        content = self._clean_content(content)

        return {
            'id': post_id,
            'title': title,
            'date': date_str,
            'tags': tags,
            'content': content,
            'url': url,
        }

    def save_as_markdown(self, post: dict):
        """게시글을 마크다운 파일로 저장"""
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)

        # 날짜 정규화 (YYMMDD 형식)
        date_str = post['date']
        date_normalized = re.sub(r'[./\s]', '', date_str)
        date_normalized = re.sub(r'[^\d]', '', date_normalized)

        # YYMMDD 형식으로 맞추기
        if len(date_normalized) >= 8:
            # YYYYMMDD -> YYMMDD
            date_normalized = date_normalized[2:8]
        elif len(date_normalized) == 6:
            pass  # 이미 YYMMDD
        else:
            date_normalized = datetime.now().strftime('%y%m%d')

        # 파일명 안전하게 만들기
        safe_title = re.sub(r'[<>:"/\\|?*\n\r]', '', post['title'])
        safe_title = safe_title.strip()[:50]

        filename = f"{date_normalized}_{safe_title}.md"
        filepath = os.path.join(config.OUTPUT_DIR, filename)

        # YAML 프론트매터 생성 (tags는 항상 포함, 비어있어도 유지)
        if post['tags']:
            tag_list = ', '.join(post['tags'])
            yaml_tags = f"tags: [{tag_list}]"
        else:
            yaml_tags = "tags: []"

        md_content = f"""---
{yaml_tags}
date: {post['date']}
url: {post['url']}
---

# {post['title']}

{post['content']}
"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(f"저장됨: {filename}")
        return filepath

    def _process_batch(self, post_ids: list, batch_num: int, total_batches: int) -> int:
        """배치 단위로 게시글 크롤링 및 저장

        Args:
            post_ids: 크롤링할 게시글 ID 목록
            batch_num: 현재 배치 번호
            total_batches: 전체 배치 수

        Returns:
            성공한 크롤링 수
        """
        success_count = 0
        batch_results = []

        for i, post_id in enumerate(post_ids, 1):
            logger.info(f"[배치 {batch_num}/{total_batches}] [{i}/{len(post_ids)}] 게시글 {post_id} 크롤링 중...")

            time.sleep(config.REQUEST_DELAY)

            post = self.crawl_post(post_id)
            if post:
                self.save_as_markdown(post)
                self._save_crawled_post(post_id)
                success_count += 1
                batch_results.append({
                    'title': post['title'],
                    'date': post['date']
                })

        # 배치 결과를 전체 결과에 추가
        self.crawl_results.extend(batch_results)

        # 배치 완료 후 즉시 로그 저장 (중간 오류 대비)
        if batch_results:
            self._save_crawl_log()
            logger.info(f"배치 {batch_num} 완료: {success_count}개 저장, 로그 갱신됨")

        return success_count

    def run(self, limit: int = None, initial_crawl: bool = False):
        """크롤러 실행

        Args:
            limit: 크롤링할 최대 게시글 수 (지정 시 새 게시글 n개 발견하면 즉시 중단)
            initial_crawl: True면 초기 크롤링 모드 (이미 크롤링된 게시글 건너뛰고 끝까지 진행)
                          False면 일일 자동화 모드 (최신글부터, 이미 크롤링된 게시글 만나면 중단)
        """
        # 초기 크롤링 여부 자동 판단: crawl_state에 저장된 페이지가 1보다 크면 초기 크롤링 재개
        if self.crawl_state.get('last_page', 1) > 1:
            initial_crawl = True

        mode_name = "초기 크롤링" if initial_crawl else "일일 자동화"
        logger.info(f"=== 메르의 블로그 크롤러 시작 ({mode_name} 모드) ===")
        logger.info(f"대상 카테고리: {TARGET_CATEGORY['name']}")
        logger.info(f"저장 경로: {config.OUTPUT_DIR}")
        logger.info(f"이미 크롤링된 게시글: {len(self.crawled_posts)}개")
        if initial_crawl and self.crawl_state.get('last_page', 1) > 1:
            logger.info(f"마지막 크롤링 위치: 페이지 {self.crawl_state['last_page']}")

        # 크롤링 결과 초기화
        self.crawl_results = []
        total_success = 0

        if limit:
            # limit 모드: 첫 페이지부터 지정된 개수만 수집하고 처리
            new_posts, last_page, _ = self.get_posts_in_category(limit=limit, start_page=1, stop_on_crawled=True)

            if not new_posts:
                logger.info("새로운 게시글이 없습니다.")
                return

            logger.info(f"테스트 모드: {len(new_posts)}개 크롤링")
            total_success = self._process_batch(new_posts, 1, 1)
        elif initial_crawl:
            # 초기 크롤링 모드: 저장된 위치부터 끝까지 진행 (이미 크롤링된 게시글 건너뛰기)
            batch_size = config.BATCH_SIZE
            batch_num = 0
            current_page = None  # 첫 배치는 저장된 위치에서 시작

            while True:
                batch_num += 1
                logger.info(f"\n=== 배치 {batch_num} 시작: 새 게시글 최대 {batch_size}개 수집 중... ===")

                # 배치 크기만큼만 새 게시글 수집 (이미 크롤링된 게시글 건너뛰기)
                new_posts, last_page, is_complete = self.get_posts_in_category(
                    batch_size=batch_size, start_page=current_page, stop_on_crawled=False
                )

                # is_complete=True면 전체 완료 (더 이상 페이지 없음 = 빈 페이지 발견)
                if is_complete:
                    if new_posts:
                        # 마지막 배치 처리
                        logger.info(f"배치 {batch_num}: 마지막 배치, 새 게시글 {len(new_posts)}개 처리")
                        batch_success = self._process_batch(new_posts, batch_num, -1)
                        total_success += batch_success
                    logger.info("모든 페이지 크롤링 완료.")
                    # 초기 크롤링 완료 시 상태 초기화
                    self._save_crawl_state(1, "")
                    break

                if not new_posts:
                    # is_complete=False인데 new_posts가 비어있음 = 현재 페이지 범위에서 새 게시글 없음
                    # 다음 페이지로 계속 진행
                    logger.info(f"페이지 {last_page}: 새 게시글 없음, 다음 페이지로 계속...")
                    current_page = last_page + 1
                    continue

                logger.info(f"배치 {batch_num}: 새 게시글 {len(new_posts)}개 처리 시작")

                # 즉시 파일 생성
                batch_success = self._process_batch(new_posts, batch_num, -1)
                total_success += batch_success

                # 마지막 게시글 ID와 페이지 저장
                self._save_crawl_state(last_page, new_posts[-1])
                logger.info(f"크롤링 상태 저장: 페이지 {last_page}")

                # 다음 배치는 마지막 페이지의 다음 페이지부터 시작
                current_page = last_page + 1
        else:
            # 일일 자동화 모드: 첫 페이지부터 시작, 이미 크롤링된 게시글 만나면 중단
            logger.info("최신글부터 수집 시작...")
            new_posts, last_page, _ = self.get_posts_in_category(
                start_page=1, stop_on_crawled=True
            )

            if not new_posts:
                logger.info("새로운 게시글이 없습니다.")
                return

            logger.info(f"새 게시글 {len(new_posts)}개 발견, 크롤링 시작")
            total_success = self._process_batch(new_posts, 1, 1)

        logger.info(f"\n=== 완료: {total_success}개 새 게시글 저장 ===")


if __name__ == '__main__':
    import sys
    crawler = NaverBlogCrawler()

    # 커맨드라인 인자로 limit 지정 가능
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    crawler.run(limit=limit)
