import random
from utils.core import logger
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestWebView
import asyncio
from urllib.parse import unquote
from data import config
import urllib.parse
import json
import jwt
class BlumBot:
    def __init__(self, thread, account, session, proxy):
        """
        Initialize the BlumBot with thread id, account name, and optional proxy.
        """
        self.proxy = f"socks5://{proxy}" if proxy is not None else None
        self.thread = thread
        
        if proxy:
            parts = proxy.split(":")
            proxy = {
                "scheme": "socks5",
                "hostname": parts[0] if len(parts) == 2 else parts[1].split('@')[1],
                "port": int(parts[2]) if len(parts) == 3 else int(parts[1]),
                "username": parts[0] if len(parts) == 3 else "",
                "password": parts[1].split('@')[0] if len(parts) == 3 else ""
            }

        self.client = Client(name=account, api_id=config.API_ID, api_hash=config.API_HASH, workdir=config.WORKDIR,
                             proxy=proxy)
        self.session = session
        self.refresh_token = ''
        self.user_id= ''
        self.address = ''

    async def logout(self):
        """
        Logout by closing the aiohttp session.
        """
        await self.session.close()

    async def claim_task(self, user_id,task_id):
        """
        Claim a task given its task dictionary.
        """
        data={"userId": str(user_id),
              "taskId": task_id}
        resp = await self.session.post('https://tonstation.app/farming/api/v1/farming/claim',data=data
                                       ,proxy=self.proxy, ssl=False)
        logger.info(await resp.text())
        resp_json = await resp.json()
        
        logger.debug(f"{self.client.name} | claim_task response: {resp_json}")
        if resp.status ==200:
            return True
        else:
            return False

    async def start_task(self, user_id):
        """
        Start a task given its task dictionary.
        """
        data={
        "userId": str(user_id),
        "taskId": "1"
        }
        resp = await self.session.post('https://tonstation.app/farming/api/v1/farming/start',
                                       proxy=self.proxy, ssl=False)
        logger.info(await resp.text())
        resp_json = await resp.json()

        logger.debug(f"{self.client.name} | start_complete_task response: {resp_json}")

    async def get_tasks(self,user_id):
        """
        Retrieve the list of available tasks.
        """
        resp = await self.session.get('https://tonstation.app/farming/api/v1/farming/{}/running'.format(user_id), proxy=self.proxy, ssl=False)
        resp_json = await resp.json()

        logger.debug(f"{self.client.name} | get_tasks response: {resp_json}")

        # Ensure the response is a list of tasks

        return resp_json



    async def balance(self,address):
        """
        Get the current balance and farming status.
        """
        resp = await self.session.get("https://tonstation.app/balance/api/v1/balance/{}/by-address".format(address), proxy=self.proxy, ssl=False)
        resp_json = await resp.json()
        await asyncio.sleep(1)
    
        data = resp_json.get("data")
        balance_list = data.get("balance")
        if balance_list:  # 检查 balance_list 是否为空
            first_balance_dict = balance_list[0]
            inner_balance = first_balance_dict.get("balance")
            return inner_balance


    async def login(self):
        """
        Login to the game using Telegram mini app authentication.
        """
        try:
            params = dict(urllib.parse.parse_qsl(await self.get_tg_web_data(), keep_blank_values=True)) 
            params['user'] = json.loads(urllib.parse.unquote(params['user']))
            # 构建最终的 payload
            payload = json.dumps({
                "query_id": params['query_id'],
                "user": params['user'],
                "auth_date": params['auth_date'],
                "hash": params['hash'],
            })
            logger.info(payload)
            resp = await self.session.post("https://tonstation.app/userprofile/api/v1/users/auth",
                                           data=payload, proxy=self.proxy, ssl=False)
            logger.info(resp.status)
            logger.info(await resp.text())
            resp_json = await resp.json()

            user_id= params['user'].get("id")
            self.session.headers['Authorization'] = "Bearer " +  resp_json.get("accessToken")
            self.refresh_token =  resp_json.get("refreshToken")
            logger.info( resp_json.get("accessToken"))
            logger.info( jwt.decode(resp_json.get("accessToken"), options={"verify_signature": False}))
            address=  jwt.decode(resp_json.get("accessToken"), options={"verify_signature": False}).get("address")
            self.ddltime=  jwt.decode(resp_json.get("accessToken"), options={"verify_signature": False}).get("exp")
            return user_id,address
        except Exception as e :
            raise e 
    async def refresh(self):
        """
        Refresh the authorization token.
        """
        json_data = {'refreshToken': self.refresh_token}
        resp = await self.session.post("https://tonstation.app/userprofile/api/v1/users/auth/refresh", json=json_data, proxy=self.proxy, ssl=False)
        resp_json = await resp.json()
        self.ddltime= json.loads(jwt.decode(resp_json.get("accessToken"), options={"verify_signature": False})).get("exp")
        self.session.headers['Authorization'] = "Bearer " + resp_json.get('accessToken')
        self.refresh_token = resp_json.get('refreshToken')
    async def get_tg_web_data(self):
        """
        Get the Telegram web data needed for login.
        """
        await self.client.connect()
        # start_command_found = False

        # async for message in self.client.get_chat_history('tonstationgames_bot'):
        #     if (message.text and message.text.startswith('/start')) or (message.caption and message.caption.startswith('/start')):
        #         start_command_found = True
        #         break
        # if not start_command_found:
        #     await self.client.send_message("tonstationgames_bot", "/start ref_xavygoyfrvstgwv7gptymu")#ref_xavygoyfrvstgwv7gptymu
        web_view = await self.client.invoke(
            RequestWebView(
                peer=await self.client.resolve_peer('tonstationgames_bot'),
                bot=await self.client.resolve_peer('tonstationgames_bot'),
                platform='android',
                from_bot_menu=False,
                url='https://tonstation.app/'
            )
        )
        auth_url = web_view.url
        logger.info(auth_url)
        await self.client.disconnect()
        tg_web_data = unquote(
            string=unquote(
                string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split(
                    '&tgWebAppVersion', maxsplit=1
                )[0]
            )
        )
        return tg_web_data
