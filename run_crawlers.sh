#!/bin/bash


# 여기 주석 지우고 자기 프로젝트 파일 경로 적기
# cd /home/dain/Saha_AI_Counselor

source venv/bin/activate

mkdir -p logs

echo "===== 크롤링 시작: $(date) =====" >> logs/crawler_daily.log

# 로그 파일로 기록
python ai/rag/crawler.py >> logs/crawler_daily.log 2>&1
python ai/rag/form_crawler.py >> logs/crawler_daily.log 2>&1
python ai/rag/waste_crawler.py >> logs/crawler_daily.log 2>&1
python ai/rag/bid_crawler.py >> logs/crawler_daily.log 2>&1
python ai/rag/passport_crawler.py >> logs/crawler_daily.log 2>&1


echo "===== 크롤링 종료: $(date) =====" >> logs/crawler_daily.log
echo "" >> logs/crawler_daily.log
