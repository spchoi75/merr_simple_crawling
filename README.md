# 메르의 블로그 크롤러

네이버 블로그 "메르의 블로그"에서 경제/주식/국제정세/사회 카테고리 게시글을 크롤링하여 마크다운 파일로 저장합니다.

## 설치

```bash
pip3 install -r requirements.txt
```

## 사용법

### 수동 실행

```bash
# 전체 크롤링
python3 crawl.py

# 테스트용 (5개만)
python3 crawl.py 5
```

### 자동 실행 (스케줄러)

매일 **오전 10시**, **오후 1시**에 자동 실행됩니다.

```bash
# 스케줄러 설치
cp com.merr.crawler.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.merr.crawler.plist

# 스케줄러 제거
launchctl unload ~/Library/LaunchAgents/com.merr.crawler.plist

# 수동으로 즉시 실행
launchctl start com.merr.crawler

# 등록 확인
launchctl list | grep merr
```

### 로그 확인

```bash
tail -f crawler.log        # 실행 로그
tail -f crawler_error.log  # 에러 로그
```

## 저장 위치

```
~/승표의보관소/Web Clipping/메르의 블로그 원문/
```

파일명 형식: `YYMMDD_제목.md`

## 중복 방지

`.last_crawl` 파일에 크롤링된 게시글 ID가 기록되어 중복 크롤링을 방지합니다.
