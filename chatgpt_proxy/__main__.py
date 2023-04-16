import asyncio
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from pydantic import BaseSettings, Field

from chatgpt_proxy.proxy import WebChatGPTProxy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()],
)


class Settings(BaseSettings):
    cf_clearance: str
    user_agent: str

    access_token: str = None
    host: str = "127.0.0.1"
    port: int = 7800
    trust: bool = Field(default=False, env="proxy_trust_client")

    class Config:
        env_file = '.env'


if __name__ == "__main__":
    env = Settings()
    proxy = WebChatGPTProxy(
        cf_clearance=env.cf_clearance,
        user_agent=env.user_agent,
        access_token=env.access_token,
        trust=env.trust,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        refresh_puid_task = asyncio.create_task(proxy._refresh_task())
        yield

    app = FastAPI(lifespan=lifespan)
    proxy.attach(app, path="/backend-api")

    uvicorn.run(app, host=env.host, port=env.port)
