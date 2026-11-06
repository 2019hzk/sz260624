from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from atguigu.app.router import hello
from atguigu.app.router import chat
from atguigu.common.settings import get_settings

app = FastAPI(description="FastAPI实例")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]

)

app.include_router(hello.router)
app.include_router(chat.router)
