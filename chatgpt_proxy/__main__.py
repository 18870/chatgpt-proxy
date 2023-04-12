import asyncio
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from chatgpt_proxy.proxy import WebChatGPTProxy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()],
)

if __name__ == "__main__":
    PUID = os.environ["PUID"]
    ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", 7800))
    TRUST = os.environ.get("PROXY_TRUST_CLIENT", "False").lower() == "true"

    proxy = WebChatGPTProxy(puid=PUID, access_token=ACCESS_TOKEN, trust=TRUST)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        refresh_puid_task = asyncio.create_task(proxy._refresh_task())
        yield

    app = FastAPI(lifespan=lifespan)
    proxy.attach(app, path="/backend-api")

    uvicorn.run(app, host=HOST, port=PORT)
