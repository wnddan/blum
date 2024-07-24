from asyncio import sleep
from random import uniform
from time import time
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

async def start(thread: int, account: str, proxy: [str, None]):
    while True:
        async with CloudflareScraper(headers={'User-Agent': generate_random_user_agent(device_type='android',
                                                                                       browser_type='chrome')},
                                     timeout=aiohttp.ClientTimeout(total=60)) as session:
            try:
                blum = BlumBot(account=account, thread=thread, session=session, proxy=proxy)
                await sleep(uniform(*config.DELAYS['ACCOUNT']))
                await blum.login()
                
                exit()
                while True:
                    try:
                        balance = await blum.balance()
                        logger.success(f"{account} | Balance:{balance}")

                        try:
                            task_info = await blum.get_tasks()
                            if task_info !=[]:
                                if task_info.get("data")!=[]:
                                    if task_info.get("data")[0]["isClaimed"]:
                                        blum.claim_task(task_info.get("data")[0]["_id"])
                                        await sleep(10)
                                        blum.start_task()
                                        sleep_time = 8*60*60
                                        
                                    else:
                                        end_time=task_info.get("data")[0]["timeEnd"]
                                        farm_end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                                        remaining_time = farm_end_time - datetime.now(timezone.utc)
                                        sleep_time=math.ceil(remaining_time.total_seconds())
                                else:
                                    blum.start_task()
                                    sleep_time = 8*60*60
                                            
                            else:
                                blum.start_task()
                                sleep_time = 8*60*60

                            if time.time()-1000>blum.ddltime:
                                await blum.refresh()

                        except Exception as e:
                            logger.error(f"{account} | Error in farming management: {e}")

                        await asyncio.sleep(delay=sleep_time)  
                    except Exception as e:
                        logger.error(f"{account} | Error: {e}")
            except Exception as outer_e:
                logger.error(f"{account} | Session error: {outer_e}")
            finally:
                logger.info(f"{account} | Reconnecting, 61 s")


async def stats():
    logger.success("Analytics disabled")
