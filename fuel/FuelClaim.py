"""
cron: 0 10 * * *
new Env('Fuel_领水')
"""
import time

import requests

from common.task import QLTask, ENV_YES_CAPTCHA_KEY
from common.util import LOCAL, raise_error, get_session, get_env, log

TASK_NAME = 'Fuel_领水'
FILE_NAME = 'FuelWallet.txt'


def dispense() -> str:
    name = '领水'
    url = 'https://faucet-beta-5.fuel.network/dispense'
    payload = {"address": LOCAL.address, "captcha": LOCAL.captcha}
    res = LOCAL.session.post(url, json=payload)
    if res.text.count('status') and res.json().get('status') == 'Success':
        return f'{name}: 成功'
    if res.text.count('Account has already received assets today'):
        return f'{name}: 今日已经领取过了'
    raise_error(name, res, msg_key='error')


class Task(QLTask):
    def task(self, index: int, datas: list, proxy: str, logger, next_datas: list) -> str or None:
        LOCAL.address = datas[0]
        while True:
            payload = {
                'clientKey': CAPTCHA_KEY,
                'task': {
                    'type': 'NoCaptchaTaskProxyless',
                    'websiteURL': 'https://faucet-beta-5.fuel.network/',
                    'websiteKey': '6Ld3cEwfAAAAAMd4QTs7aO85LyKGdgj0bFsdBfre'
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
                if resp.text.count('gRecaptchaResponse'):
                    LOCAL.captcha = resp.json().get('solution').get('gRecaptchaResponse')
                    logger.info(f"人机验证处理成功")
                    break
                time.sleep(3)
            if hasattr(LOCAL, 'captcha') and LOCAL.captcha:
                break
            logger.error(f'人机验证处理失败，进行重试')

        if not hasattr(LOCAL, 'session'):
            LOCAL.session = get_session()
        LOCAL.session.proxies = proxy
        result = dispense()
        logger.info(result)
        return


if __name__ == '__main__':
    CAPTCHA_KEY = get_env(ENV_YES_CAPTCHA_KEY)
    if not CAPTCHA_KEY:
        log.info(f"未设置YesCaptchaKey环境变量，不运行此任务。")
    else:
        try:
            res = requests.post('https://api.yescaptcha.com/getBalance', json={'clientKey': CAPTCHA_KEY})
            if res.text.count('balance'):
                log.info(f"当前YesCaptchaKey: {CAPTCHA_KEY}   余额: {res.json().get('balance')}")
                Task(TASK_NAME, FILE_NAME).run()
            else:
                log.info(
                    f"YesCaptcha余额查询失败: {res.json().get('errorDescription') if res.text.count('errorDescription') else res.text}"
                )
        except:
            log.info(f"YesCaptcha余额查询失败")
