import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from atguigu.app.router import hello
from atguigu.app.router import chat
from atguigu.app.router import admin
from atguigu.app.router import realtime
from atguigu.app.workers.ai import AIWorker
from atguigu.app.workers.realtime import RealtimeWorker
from atguigu.common.settings import get_settings


async def lifespan(_: FastAPI):
    asyncio.create_task(AIWorker().start())
    asyncio.create_task(RealtimeWorker().start())

    yield


app = FastAPI(description="FastAPI实例", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]

)

app.include_router(hello.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(realtime.router)
