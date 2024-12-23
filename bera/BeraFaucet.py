"""
cron: 0 10 * * *
new Env('Bera_领水')
"""
import os
import time

import requests

from common.constant import ENV_CAPTCHA_RUN_KEY
from common.task import QLTask, ENV_YES_CAPTCHA_KEY, LOCAL
from common.util import raise_error, get_session, base_logger

TASK_NAME = 'Bera_领水'
FILE_NAME = 'BeraWallet'


def claim() -> str:
    name = '领水'
    url = f'https://bartiofaucet.berachain.com/api/claim?address={LOCAL.address}'
    res = LOCAL.session.post(url, json={"address": LOCAL.address}, headers={'Authorization': 'Bearer ' + LOCAL.captcha})
    if res.text.count('Added'):
        return f'{name}: 成功'
    if res.text.count('You have exceeded the rate limit'):
        return f'{name}: 领取限制时间中'
    if res.text.count('Invalid captcha token'):
        return f'{name}: 无效的验证'
    if res.status_code == 402:
        return f'{name}: 无法领水，ETH主网余额不足0.001 ETH '
    raise_error(name, res)


class Task(QLTask):
    def task(self, index: int, datas: list[str], proxy: str, logger):
        LOCAL.address = datas[0]
        LOCAL.session = get_session(proxy)
        LOCAL.captcha = ''
        result = claim()
        if not result.count('无效的验证'):
            logger.info(result)
            return

        while True:
            if YES_CAPTCHA_KEY:
                payload = {
                    'clientKey': YES_CAPTCHA_KEY,
                    'task': {
                        'type': 'TurnstileTaskProxyless',
                        'websiteURL': 'https://bartio.faucet.berachain.com/',
                        'websiteKey': '0x4AAAAAAARdAuciFArKhVwt'
                    },
                    'softID': 16796
                }
                resp = requests.post('https://api.yescaptcha.com/createTask', json=payload)
                if resp.text.count('ERROR_ZERO_BALANCE') or resp.text.count('ERROR_SETTLEMENT_FAILED'):
                    logger.error('YesCaptcha余额不足')
                    return False
                if resp.text.count('taskId') == 0:
                    logger.error(
                        f"TaskId获取失败，进行重试{resp.json().get('errorDescription') if resp.text.count('errorDescription') else resp.text}"
                    )
                    continue
                task_id = resp.json().get('taskId')
                logger.info(f"TaskId: {task_id}")
                for i in range(30):
                    payload = {'clientKey': YES_CAPTCHA_KEY, 'taskId': task_id}
                    resp = requests.post('https://api.yescaptcha.com/getTaskResult', json=payload)
                    if resp.text.count('token'):
                        LOCAL.captcha = resp.json().get('solution').get('token')
                        logger.success(f"人机验证处理成功")
                        break
                    time.sleep(3)
                if hasattr(LOCAL, 'captcha') and LOCAL.captcha:
                    break
                logger.error(f'人机验证处理失败，进行重试')
            else:
                session = get_session()
                session.headers.update({'Authorization': f'Bearer {CAPTCHA_RUN_KEY}'})

                payload = {
                    "captchaType": "Turnstile",
                    "siteKey": '0x4AAAAAAARdAuciFArKhVwt',
                    "siteReferer": 'https://bartio.faucet.berachain.com/',
                    "developer": "4a6c9794-4159-4588-8686-f80958b6018c"
                }
                resp = session.post('https://api.captcha.run/v2/tasks', json=payload)
                if resp.text.count('taskId') == 0:
                    logger.error(
                        f"TaskId获取失败，进行重试{resp.json().get('reason') if resp.text.count('reason') else resp.text}"
                    )
                    continue
                task_id = resp.json().get('taskId')
                logger.info(f"TaskId: {task_id}")
                for i in range(30):
                    resp = session.get(f'https://api.captcha.run/v2/tasks/{task_id}')
                    if resp.text.count('token'):
                        LOCAL.captcha = resp.json().get('response').get('token')
                        logger.success(f"人机验证处理成功")
                        break
                    time.sleep(3)
                if hasattr(LOCAL, 'captcha') and LOCAL.captcha:
                    break
                logger.error(f'人机验证处理失败，进行重试')

        result = claim()
        logger.success(result)


if __name__ == '__main__':
    CAPTCHA_RUN_KEY, YES_CAPTCHA_KEY = os.getenv(ENV_CAPTCHA_RUN_KEY), os.getenv(ENV_YES_CAPTCHA_KEY)
    if CAPTCHA_RUN_KEY or YES_CAPTCHA_KEY:
        try:
            if YES_CAPTCHA_KEY:
                cap_res = requests.post('https://api.yescaptcha.com/getBalance', json={'clientKey': YES_CAPTCHA_KEY})
            else:
                cap_res = requests.get('https://api.captcha.run/v2/users/self/wallet',
                                       headers={'Authorization': f'Bearer {CAPTCHA_RUN_KEY}'})
            if cap_res.text.count('balance'):
                base_logger.success(
                    f"当前{'YesCaptchaKey' if YES_CAPTCHA_KEY else 'CaptchaRunKey'}: {YES_CAPTCHA_KEY if YES_CAPTCHA_KEY else CAPTCHA_RUN_KEY}   余额: {cap_res.json().get('balance')}")
                Task(TASK_NAME, FILE_NAME, is_delay=False).run()
            else:
                base_logger.error(
                    f"{'YesCaptchaKey' if YES_CAPTCHA_KEY else 'CaptchaRunKey'}余额查询失败: {cap_res.json().get('errorDescription') if cap_res.text.count('errorDescription') else cap_res.text}"
                )
        except:
            base_logger.error(f"{'YesCaptchaKey' if YES_CAPTCHA_KEY else 'CaptchaRunKey'}余额查询失败")
    else:
        base_logger.error(f"请设置CaptchaRunKey变量[{ENV_CAPTCHA_RUN_KEY}]或YesCaptchaKey变量[{ENV_YES_CAPTCHA_KEY}]，程序退出。")
