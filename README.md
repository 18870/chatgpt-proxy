# ChatGPT-Proxy
Python version of OpenAI's ChatGPT web API proxy  
Python alternative to [ChatGPT-Proxy-V4](https://github.com/acheong08/ChatGPT-Proxy-V4)  
Use cookie `_puid` to bypass Cloudflare browser check  

## Requirements
- ChatGPT plus account
- Access to chat.openai.com

## Install
`pip install chatgpt-proxy`

## Usage
### Run as a service
Set these environment variables:
- `PUID`: Preset cookie `_puid`
- `ACCESS_TOKEN`: (Optional) For automatic refresh of `_puid`, obtains from [here](https://chat.openai.com/api/auth/session)
- `PROXY_TRUST_CLIENT`: (Optional) Trust requests from any client.  
    When set to `True`, any requests without an access_token will be given the above access_token.  
    Default to `False`, which will only use for refresh puid.
- `HOST`: (Optional) Listen on host, default to `127.0.0.1`
- `PORT`: (Optional) Listen on port, default to `7800`

Or create a `.env` file with your environment variables at where you want to run the proxy:
```ini
puid=YOUR_PUID
access_token=YOUR_ACCESS_TOKEN
proxy_trust_client=False
host=127.0.0.1
port=7800
```

Note that environment variables will override the values in `.env` file.

Then run: `python -m chatgpt_proxy`
The proxy will be avaliable at `http://host:port/backend-api/`

### Integrate into your FastAPI app
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

class `WebChatGPTProxy`:
- `puid`: Preset cookie `_puid`
- `access_token`: (Optional), for automatic refresh of `_puid`
- `trust`: Trust requests from any client.
    When set to True, any requests without an access_token will be given the above access_token.
    Default to False, which will only use for refresh puid.


## Credits
- ChatGPT-Proxy-V4
https://github.com/acheong08/ChatGPT-Proxy-V4
- Implement reverse proxy in FastAPI
https://github.com/tiangolo/fastapi/discussions/7382#discussioncomment-5136454

## License
This work is licensed under the [GNU Affero General Public License v3.0](/LICENSE) or later, with the "CHATGPT-PROXY" exception.

> **"CHATGPT-PROXY" EXCEPTION TO THE AGPL**
>
> As a special exception, using this work in the following ways does not cause your program to be covered by the AGPL:
> 1. Bundling the unaltered code or binary of this work in your program; or
> 2. Interacting with this work through the provided inter-process communication interface, such as the HTTP API.