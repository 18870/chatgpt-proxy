import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Header
from pydantic import BaseModel, BaseSettings, Field

from chatgpt_proxy.proxy import WebChatGPTProxy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    cf_clearance: str = None
    user_agent: str = ""
    puid: str = None

    access_token: str = None
    host: str = "127.0.0.1"
    port: int = 7800
    trust: bool = Field(default=False, env="proxy_trust_client")
    mod_access_token: str = None

    class Config:
        env_file = '.env'


if __name__ == "__main__":
    env = Settings()
    proxy = WebChatGPTProxy(
        cf_clearance=env.cf_clearance,
        user_agent=env.user_agent,
        puid=env.puid,
        access_token=env.access_token,
        trust=env.trust,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        asyncio.create_task(proxy._refresh_task())
        yield

    app = FastAPI(lifespan=lifespan)
    proxy.attach(app, path="/backend-api")

    if env.mod_access_token:
        logger.info("Mod access token found, enable /moderation/* endpoint")

        class Info(BaseModel):
            cf_clearance: str = None
            access_token: str = None
            user_agent: str = None

        @app.post("/moderation/update_info", status_code=200)
        async def update_info(
            info: Info,
            authorization: str = Header(...),
            user_agent: str = Header(...),
        ):
            if authorization != env.mod_access_token:
                logger.error("Invalid authorization")
                return {"message": "invalid authorization"}

            if info.access_token:
                logger.info("New access token found")
                proxy.access_token = info.access_token
            if info.cf_clearance:
                logger.info(f"New cf_clearance: {info.cf_clearance}")
                proxy.cf_clearance = info.cf_clearance
            proxy.user_agent = info.user_agent or user_agent

            if await proxy.check_cf():
                logger.info("New info is valid")
                return {"message": "ok"}
            else:
                logger.error("Failed to validate new info")
                return {"message": "failed"}

        @app.get("/moderation/status", status_code=200)
        async def status(authorization: str = Header(...)):
            if authorization != env.mod_access_token:
                logger.error("Invalid authorization")
                return {"message": "invalid authorization"}

            return {"message": "ok", "status": proxy.valid_state}

    uvicorn.run(app, host=env.host, port=env.port)
