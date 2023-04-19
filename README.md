# ChatGPT-Proxy
Python version of OpenAI's ChatGPT web API proxy  
Python alternative of [ChatGPT-Proxy-V4](https://github.com/acheong08/ChatGPT-Proxy-V4)  
Use cookie `cf_clearance` to pass Cloudflare browser check  

**`_puid` no longer works**

## Requirements
- Access to chat.openai.com

## Install
`pip install chatgpt-proxy`

## Usage

For how to get a usable `cf_clearance` cookie, checkout issue [#1](https://github.com/18870/chatgpt-proxy/issues/1) (Chinese only sorry)

### Run as a service
Set these environment variables:
- `CF_CLEARANCE`: (Optional) Cookie `cf_clearance`
- `USER_AGENT`: (Optional) User-agent of your browser when you get the cookie `cf_clearance`
- `ACCESS_TOKEN`: (Optional) Obtains from [here](https://chat.openai.com/api/auth/session)
- `PUID`: (Optional) Cookie `_puid`, still needed to start a conversation for plus account (?)
    When set a plus account's access_token, this can be automatically refresh
- `PROXY_TRUST_CLIENT`: (Optional) Trust requests from any client.  
    When set to `True`, any requests without an access_token will be given the above access_token.  
    Default to `False`, which will only use for refresh puid.
- `HOST`: (Optional) Listen on host, default to `127.0.0.1`
- `PORT`: (Optional) Listen on port, default to `7800`
- `MOD_ACCESS_TOKEN`: (Optional) Update info like cf_clearance through http request 
    requires you set this access_token in `Authorization` Header 

Or create a `.env` file with your environment variables at where you want to run the proxy:
```ini
cf_clearance=YOUR_CF_CLEARANCE
user_agent=YOUR_USER_AGENT
access_token=YOUR_ACCESS_TOKEN
puid=ANY_VALID_PUID
proxy_trust_client=False
host=127.0.0.1
port=7800
mod_access_token=YOUR_MOD_ACCESS_TOKEN
```

Note that environment variables will override the values in `.env` file.

Then run: `python -m chatgpt_proxy`  

#### Success
If you see this in console:
`2023-01-01 00:00:00,000 - chatgpt_proxy.proxy - INFO - puid: user-xxxxxx`
You are ready to go

The proxy is avaliable at `http://host:port/backend-api/`

### Integrate into your FastAPI app
Check out [\_\_main__.py](./chatgpt_proxy/__main__.py)
```python
from chatgpt_proxy import WebChatGPTProxy
proxy = WebChatGPTProxy(cf_clearance=CF_CLEARANCE, user_agent=USER_AGENT, access_token=ACCESS_TOKEN, trust=False)
app = FastAPI()
proxy.attach(app, path="/backend-api")
```

class `WebChatGPTProxy`:
- `cf_clearance`: Cookie `cf_clearance`
- `user_agent`: User-agent of your browser when you get the cookie `cf_clearance`
- `access_token`: (Optional)
- `puid`: (Optional)
- `trust`: (Optional) Trust requests from any client.
    When set to True, any requests without an access_token will be given the above access_token.
    Default to False, which will only use for refresh puid.

### Behind a http proxy
**You need to use the same ip address you used to get the cookie `cf_clearance`**

Set `HTTP_PROXY` and `HTTPS_PROXY` or `ALL_PROXY` environment variables.   
This **cannot be set** in `.env` file becauce `httpx` (the package we used to send request) reads from environment variables only. See also [httpx#Proxies](https://www.python-httpx.org/environment_variables/#http_proxy-https_proxy-all_proxy).

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