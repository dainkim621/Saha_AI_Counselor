# app/main.py
from fastapi import FastAPI
from .database import engine, Base
from . import models  # 👈 이 줄이 있어야 models.py의 설정을 읽어옵니다.

# 서버가 켜질 때 DB에 접속해서 테이블이 없으면 생성하는 명령어
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Server Running", "db": "Check completed"}