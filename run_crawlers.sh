#!/bin/bash

# 프로젝트 폴더 주소로 이동
cd /home/dookong/SwProject/Saha_AI_Counselor

# 2. 가상환경 활성화
source venv/bin/activate

# 3. 로그 폴더 생성
mkdir -p logs

echo "===== 크롤링 시작: $(date) =====" >> logs/crawler_daily.log

# 4. 방금 동기화한 최신 크롤러 4개 순차 실행 및 로그 기록
python ai/rag/crawler.py >> logs/crawler_daily.log 2>&1
python ai/rag/form_crawler.py >> logs/crawler_daily.log 2>&1
python ai/rag/waste_crawler.py >> logs/crawler_daily.log 2>&1
python ai/rag/bid_crawler.py >> logs/crawler_daily.log 2>&1

echo "===== 크롤링 종료: $(date) =====" >> logs/crawler_daily.log
echo "" >> logs/crawler_daily.log

echo "===== 델타 동기화 시작: $(date) =====" >> logs/crawler_daily.log
python -m ai.rag.preprocessing.run_delta_pipeline >> logs/crawler_daily.log 2>&1
echo "===== 델타 동기화 종료: $(date) =====" >> logs/crawler_daily.log
echo "" >> logs/crawler_daily.log
