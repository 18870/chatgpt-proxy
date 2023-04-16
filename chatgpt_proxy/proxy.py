import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse, urlunparse, ParseResult

import httpx
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import StreamingResponse


logger = logging.getLogger(__name__)


class ReverseProxy:
    ALL_METHODS = [
        "GET",
        "POST",
        "HEAD",
        "PUT",
        "DELETE",
        "OPTIONS",
        "PATCH",
        "TRACE",
        "CONNECT",
    ]

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)
        _url = urlparse(base_url)
        self._domain = _url.netloc
        self._origin = urlunparse(
            ParseResult(
                scheme=_url.scheme,
                netloc=_url.netloc,
                path="",
                params="",
                query="",
                fragment="",
            )
        )

    async def _prepare_cookies(self, request: Request):
        return request.cookies.copy()

    async def _prepare_headers(self, request: Request):
        # Note that all header keys are lowercased
        headers = dict(request.headers)

        # cookie in headers have higher priority
        # so remove it here and let cookies parameter take effect
        headers.pop("cookie", None)

        # preset header
        headers["host"] = self._domain
        headers["origin"] = self._origin
        headers["referer"] = self.base_url
        return headers

    async def proxy(self, request: Request, path: str):
        # https://github.com/tiangolo/fastapi/discussions/7382#discussioncomment-5136454
        rp_resp = await self._send_request(
            path=path,
            query=request.url.query.encode("utf-8"),
            method=request.method,
            headers=await self._prepare_headers(request),
            cookies=await self._prepare_cookies(request),
            content=request.stream(),
        )

        # Handle Set-Cookie headers
        headers = rp_resp.headers.copy()
        headers.pop("set-cookie", None)

        resp = StreamingResponse(
            rp_resp.aiter_raw(),
            status_code=rp_resp.status_code,
            headers=headers,
        )

        for key, value in rp_resp.cookies.items():
            resp.set_cookie(key=key, value=value)
        return resp

    async def _send_request(self, path: str, query: bytes, **kwargs) -> httpx.Response:
        url = httpx.URL(path=path, query=query)
        rp_req = self.client.build_request(url=url, **kwargs)
        rp_resp = await self.client.send(rp_req, stream=True)
        return rp_resp

    def attach(self, app: FastAPI, path: str, **kwargs) -> None:
        path = path.rstrip("/")
        app.add_api_route(
            path + "/{path:path}",
            self.proxy,
            methods=self.ALL_METHODS,
            description=f"Reverse proxy of {self.base_url}",
            **kwargs,
        )


class WebChatGPTProxy(ReverseProxy):
    def __init__(
        self, cf_clearance: str, user_agent: str, access_token: Optional[str] = None, trust: bool = False
    ) -> None:
        """
        :param puid: from `_puid` cookie
        :param access_token: from openai `access_token`
                             obtained from here https://chat.openai.com/api/auth/session
                             Used to refresh puid
        :param trust: Trust requests from any client.
                      When set to True, any requests without an access_token will be given the above access_token.
                      Default to False, which will only use for refresh puid.
        """
        super().__init__(base_url="https://chat.openai.com/backend-api/")
        self.cf_clearance = cf_clearance
        self.ua = user_agent
        self.access_token = access_token
        self.trust = trust
        self._app: Optional[FastAPI] = None
        self._path: Optional[str] = None

    async def _prepare_cookies(self, request: Request):
        cookies = await super()._prepare_cookies(request)
        cookies.setdefault("cf_clearance", self.cf_clearance)
        return cookies

    async def _prepare_headers(self, request: Request):
        headers = await super()._prepare_headers(request)
        headers["origin"] = "https://chat.openai.com"
        headers["referer"] = "https://chat.openai.com/chat"
        headers["user-agent"] = self.ua
        if self.trust and self.access_token:
            headers.setdefault("authorization", f"Bearer {self.access_token}")
        return headers

    async def _refresh_puid(self) -> None:
        """
        Send requests to /models through reverse proxy (current FastAPI app) to get a new puid
        
        Use to see if you pass cloudflare
        """
        if self._app is None:
            logger.info("Not attached to any FastAPI app, skip")
        async with httpx.AsyncClient(
            app=self._app, base_url=f"https://chat.openai.com{self._path}"
        ) as client:
            resp = await client.get(
                "/models", headers={"authorization": f"Bearer {self.access_token}"}
            )
            puid = resp.cookies.get("_puid")
            if puid:
                logger.info(f"puid: {puid}")
                self.puid = puid
            else:
                logger.error("Failed to get puid")
                logger.error(f"Cookies: {resp.cookies}")
                logger.error(f"Response: \n{resp.text}")

    async def _refresh_task(self) -> None:
        if self.access_token is None:
            logger.info("access_token not found, skip")
            return

        try:
            await self._refresh_puid()
        except Exception as e:
            logger.exception(e)
            # await asyncio.sleep(60 * 60)
            # continue
        # await asyncio.sleep(60 * 60 * 6)

    def attach(self, app: FastAPI, path: str) -> None:
        super().attach(app=app, path=path, include_in_schema=self.trust)
        self._app = app
        self._path = path
