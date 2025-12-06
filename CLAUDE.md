# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

네이버 블로그 "메르의 블로그"(ranto28)에서 경제/주식/국제정세/사회 카테고리(categoryNo=21) 게시글을 크롤링하여 마크다운 파일로 저장하는 크롤러.

## 명령어

```bash
# 의존성 설치
pip3 install -r requirements.txt

# 전체 크롤링 실행
python3 crawl.py

# 테스트용 제한 실행 (예: 5개만)
python3 crawl.py 5
```

## launchd 스케줄러 설정

매일 10:00에 자동 실행되도록 설정되어 있음:
```bash
# 설치
cp com.merr.crawler.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.merr.crawler.plist

# 수동 실행
launchctl start com.merr.crawler

# 로그 확인
tail -f crawler.log
tail -f crawler_error.log
```

## 아키텍처

- `crawl.py`: 메인 크롤러 (`NaverBlogCrawler` 클래스)
  - PC 버전으로 게시글 목록 수집 → 모바일 버전으로 본문 크롤링
  - `__INITIAL_STATE__` JSON에서 본문/날짜/태그 추출
  - YAML 프론트매터 포함 마크다운 파일 생성
- `config.py`: 설정 (블로그 ID, 저장 경로, 딜레이 등)
- `.last_crawl`: 크롤링 완료된 게시글 ID 기록 (중복 방지)

## 크롤링 흐름

1. **목록 수집** (`get_posts_in_category`): PC 버전 URL에서 `logNo=` 파라미터로 게시글 ID 추출
2. **본문 크롤링** (`crawl_post`): 모바일 버전에서 `og:title`, `publishDate`, `tagNames` 추출
3. **본문 정리** (`_clean_content`): 출처 제거, 빈 줄 정리, "한줄코멘트" → Obsidian 콜아웃 변환
4. **저장** (`save_as_markdown`): YAML 프론트매터 포함 마크다운 생성

## 본문 추출 주요 로직

- `.se-main-container` 내 `.se-module-text` 에서 텍스트 추출
- 순서 있는 리스트(`ol.decimal`)는 번호 유지
- 연합뉴스 링크(`yna.co.kr`) 포함 문단은 인용(`>`) 처리
- Zero-width space(`\u200b`) 제거

## 저장 위치

마크다운 파일: `~/승표의보관소/Web Clipping/메르의 블로그 원문/`
파일명 형식: `YYMMDD_제목.md`
