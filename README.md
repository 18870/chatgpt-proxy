# ChatGPT-Proxy
Python version of OpenAI's ChatGPT web API proxy  
Python alternative to [ChatGPT-Proxy-V4](https://github.com/acheong08/ChatGPT-Proxy-V4)  
Use cookie `_puid` to bypass Cloudflare browser check  

# Requirements
- ChatGPT plus account
- Access to chat.openai.com

# Install
`pip install chatgpt-proxy`

# Usage
## Run as a service
Set these environment variables:
- `PUID`: Preset cookie `_puid`
- `ACCESS_TOKEN`: (Optional) For automatic refresh of `_puid`, obtains from [here](https://chat.openai.com/api/auth/session)
- `HOST`: (Optional) Listen on host, default to `127.0.0.1`
- `PORT`: (Optional) Listen on port, default to `7800`

Run: `python -m chatgpt_proxy`

## Integrate into your FastAPI app
Check out [\_\_main__.py](./chatgpt_proxy/__main__.py)
```python
from chatgpt_proxy import WebChatGPTProxy
proxy = WebChatGPTProxy(puid=PUID, access_token=ACCESS_TOKEN, trust=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # add this to start refresh puid task
    refresh_puid_task = asyncio.create_task(proxy._refresh_task())
    yield

app = FastAPI(lifespan=lifespan)
proxy.attach(app, path="/backend-api")
```

`WebChatGPTProxy`:
- `puid`: Preset cookie `_puid`
- `access_token`: (Optional), for automatic refresh of `_puid`
- `trust`: Trust requests from anyclient.
    When set to True, any requests without an access_token will be given the above access_token.
    Default to False, which will only use for refresh puid.


# Credits
- ChatGPT-Proxy-V4
https://github.com/acheong08/ChatGPT-Proxy-V4
- Implement reverse proxy in FastAPI
https://github.com/tiangolo/fastapi/discussions/7382#discussioncomment-5136454