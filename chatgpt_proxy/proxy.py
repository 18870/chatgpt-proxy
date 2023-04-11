import asyncio
import logging
from http.cookies import SimpleCookie
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import StreamingResponse


logger = logging.getLogger(__name__)


def parse_set_cookie(headers: httpx.Headers) -> SimpleCookie:
    cookies = SimpleCookie()
    for key, value in headers.raw:
        if key.lower() == b'set-cookie':
            cookies.load(value.decode("utf-8"))
    return cookies


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
        self.domain = _url.netloc

    async def _prepare_cookies(self, request: Request):
        return request.cookies.copy()

    async def _prepare_headers(self, request: Request):
        # Note that all header keys are lowercased
        headers = dict(request.headers)

        # cookie in headers have higher priority
        # so remove it here and let cookies parameter take effect
        headers.pop("cookie", None)

        # preset header
        headers["host"] = self.domain
        headers["origin"] = self.base_url
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
        cookies = parse_set_cookie(rp_resp.headers)
        headers = rp_resp.headers.copy()
        headers.pop("set-cookie", None)

        resp = StreamingResponse(
            rp_resp.aiter_raw(),
            status_code=rp_resp.status_code,
            headers=headers,
        )

        for key, morsel in cookies.items():
            resp.set_cookie(
                key,
                morsel.value,
                max_age=morsel.get("max-age", None),
                expires=morsel.get("expires", None),
                path=morsel.get("path", "/"),
                domain=morsel.get("domain", None),
                secure=morsel.get("secure", False),
                httponly=morsel.get("httponly", False),
                samesite=morsel.get("samesite", 'lax'),
            )
        return resp

    async def _send_request(self, path: str, query: bytes, **kwargs) -> httpx.Response:
        url = httpx.URL(path=path, query=query)
        rp_req = self.client.build_request(url=url, **kwargs)
        rp_resp = await self.client.send(rp_req, stream=True)
        return rp_resp

    def attach(self, app: FastAPI, path: str) -> None:
        path = path.rstrip("/")
        app.add_api_route(
            path + "/{path:path}",
            self.proxy,
            methods=self.ALL_METHODS,
            description=f"Reverse proxy of {self.base_url}",
        )


class WebChatGPTProxy(ReverseProxy):
    def __init__(
        self, puid: str, access_token: Optional[str] = None, trust: bool = False
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
        self.puid = puid
        self.access_token = access_token
        self.trust = trust
        self._app: Optional[FastAPI] = None
        self._path: Optional[str] = None

    async def _prepare_cookies(self, request: Request):
        cookies = await super()._prepare_cookies(request)
        cookies.setdefault("_puid", self.puid)
        return cookies

    async def _prepare_headers(self, request: Request):
        headers = await super()._prepare_headers(request)
        headers["origin"] = "https://chat.openai.com"
        headers["referer"] = "https://chat.openai.com/chat"
        headers[
            "user-agent"
        ] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.54"
        if self.trust and self.access_token:
            headers.setdefault("authorization", f"Bearer {self.access_token}")
        return headers

    async def _refresh_puid(self) -> None:
        """
        Send requests to /models through reverse proxy (current FastAPI app) to get a new puid
        """
        if self._app is None:
            logger.info("Not attached to any FastAPI app, skip refresh")
        async with httpx.AsyncClient(
            app=self._app, base_url=f"http://app{self._path}"
        ) as client:
            resp = await client.get(
                "/models", headers={"authorization": f"Bearer {self.access_token}"}
            )
            cookies = parse_set_cookie(resp.headers)
            puid = cookies.get("_puid")
            if puid:
                logger.info(f"puid: {puid.value}")
                self.puid = puid.value
            else:
                logger.info("puid not found")

    async def _refresh_task(self) -> None:
        if self.access_token is None:
            logger.info("access_token not found, skip refresh")
            return
        while True:
            try:
                await self._refresh_puid()
            except Exception as e:
                logger.exception(e)
                await asyncio.sleep(60 * 60)
                continue
            await asyncio.sleep(60 * 60 * 6)

    def attach(self, app: FastAPI, path: str) -> None:
        super().attach(app=app, path=path)
        self._app = app
        self._path = path


