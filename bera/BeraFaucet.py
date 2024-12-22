"""
cron: 0 10 * * *
new Env('Bera_领水')
"""
import os
import time

import requests

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
            payload = {
                'clientKey': CAPTCHA_KEY,
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
            task_id = resp.json()['taskId']
            logger.info(f"TaskId: {task_id}")
            for i in range(30):
                payload = {'clientKey': CAPTCHA_KEY, 'taskId': task_id}
                resp = requests.post('https://api.yescaptcha.com/getTaskResult', json=payload)
                if resp.text.count('token'):
                    LOCAL.captcha = resp.json().get('solution').get('token')
                    logger.success(f"人机验证处理成功")
                    break
                time.sleep(3)
            if hasattr(LOCAL, 'captcha') and LOCAL.captcha:
                break
            logger.error(f'人机验证处理失败，进行重试')

        result = claim()
        logger.success(result)


if __name__ == '__main__':
    CAPTCHA_KEY = os.getenv(ENV_YES_CAPTCHA_KEY)
    if not CAPTCHA_KEY:
        base_logger.error(f"未设置YesCaptchaKey环境变量，不运行此任务。")
    else:
        try:
            cap_res = requests.post('https://api.yescaptcha.com/getBalance', json={'clientKey': CAPTCHA_KEY})
            if cap_res.text.count('balance'):
                base_logger.success(f"当前YesCaptchaKey: {CAPTCHA_KEY}   余额: {cap_res.json().get('balance')}")
                Task(TASK_NAME, FILE_NAME).run()
            else:
                base_logger.error(
                    f"YesCaptcha余额查询失败: {cap_res.json().get('errorDescription') if cap_res.text.count('errorDescription') else cap_res.text}"
                )
        except:
            base_logger.error(f"YesCaptcha余额查询失败")
