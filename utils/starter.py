from asyncio import sleep
from random import uniform
import time 
from datetime import datetime, timedelta, timezone
import aiohttp
from aiocfscrape import CloudflareScraper
from .agents import generate_random_user_agent
import math
from data import config
from utils.blum import BlumBot
from utils.core import logger
from utils.helper import format_duration
import asyncio
headers = {
  'accept': '*/*',
  'accept-encoding': 'gzip, deflate, br, zstd',
  'accept-language': 'zh,zh-CN;q=0.9,en-US;q=0.8,en;q=0.7',
  'connection': 'keep-alive',
  'content-type': 'application/json',
  'host': 'tonstation.app',
  'origin': 'https://tonstation.app',
  'referer': 'https://tonstation.app/app/',
  'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Android WebView";v="126"',
  'sec-ch-ua-mobile': '?1',
  'sec-ch-ua-platform': '"Android"',
  'sec-fetch-dest': 'empty',
  'sec-fetch-mode': 'cors',
  'sec-fetch-site': 'same-origin',
  'user-agent': 'Mozilla/5.0 (Linux; Android 14; 2304FPN6DC Build/UKQ1.230804.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/126.0.6478.134 Mobile Safari/537.36',
  'x-requested-with': 'app.nicegram'
}

async def start(thread: int, account: str, proxy: [str, None]):
    while True:
        async with CloudflareScraper(headers=headers,timeout=aiohttp.ClientTimeout(total=60)) as session:
            try:
                blum = BlumBot(account=account, thread=thread, session=session, proxy=proxy)
                await sleep(uniform(*config.DELAYS['ACCOUNT']))
                user_id,address= await blum.login()

                while True:
                    try:
                        balance = await blum.balance(address)
                        logger.success(f"{account} | Balance:{balance}")
                        try:
                            task_info = await blum.get_tasks(user_id)
                            logger.info(task_info)
                            if "data" in task_info and task_info["data"]:
                                if task_info.get("data")[0]["isClaimed"]:
                                    await blum.claim_task(user_id,task_info["data"][0]["_id"])
                                    await sleep(10)
                                    await blum.start_task(user_id)
                                    sleep_time = 8*60*60
                                        
                                else:
                                    end_time=task_info.get("data")[0]["timeEnd"]
                                    
                                    farm_end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                                    logger.info(farm_end_time)
                                    remaining_time = farm_end_time - datetime.now(timezone.utc)
                                    if farm_end_time > datetime.now(timezone.utc):
                                        sleep_time=math.ceil(remaining_time.total_seconds())
                                    else:
                                        sleep_time= 0 
                                        await blum.claim_task(user_id,task_info["data"][0]["_id"])
                                        await blum.start_task(user_id=user_id)
                            else:
                                await blum.start_task(user_id)
                                sleep_time = 8*60*60

                            if time.time()-1000>blum.ddltime:
                                await blum.refresh()

                        except Exception as e:
                            logger.error(f"{account} | Error in farming management: {e}")
                        logger.info(sleep_time)
                        await sleep(sleep_time)  
                    except Exception as e:
                        logger.error(f"{account} | Error: {e}")
            except Exception as outer_e:
                logger.error(f"{account} | Session error: {outer_e}")
            finally:
                logger.info(f"{account} | Reconnecting, 61 s")


async def stats():
    logger.success("Analytics disabled")
