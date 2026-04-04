from fastapi import FastAPI
from .database import engine
from . import models
from .api import chat

# DB 테이블 생성
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# 위에서 만든 chat 라우터를 등록함
app.include_router(chat.router)

@app.get("/")
def root():
    return {"status": "Saha AI Server is running!"}