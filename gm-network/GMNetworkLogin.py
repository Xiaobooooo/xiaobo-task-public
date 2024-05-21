"""
cron: 0 8 * * *
new Env('GM_登录')
"""
import time

import requests
import web3
from eth_account.messages import encode_defunct

from common.task import QLTask, ENV_YES_CAPTCHA_KEY
from common.util import LOCAL, get_session, get_env, log, write_txt
from GMNetworkCheckIn import gm_raise_error

TASK_NAME = 'GM_登录'
FILE_NAME = 'GMWallet.txt'


def login() -> str:
    name = '登录'
    timestamp = int(time.time())
    message = encode_defunct(
        text=f'Welcome to GM Launchpad.\nPlease sign this message to login GM Launchpad.\n\nTimestamp: {timestamp}'
    )
    signature = web3.Account.sign_message(message, LOCAL.private_key).signature.hex()
    payload = {"address": LOCAL.address, "message": "Welcome to GM Launchpad.\nPlease sign this message to login GM Launchpad.",
               "timestamp": timestamp, "signature": signature.replace('0x', ''), "login_type": 100}
    url = 'https://api-launchpad.gmnetwork.ai/user/login/'
    res = LOCAL.session.post(url, json=payload, headers={'Cf-Turnstile-Resp': LOCAL.captcha},
                             proxy='http://user-xiaobo233:qwer1234@pr.roxlabs.cn:4600')
    if res.text.count('access_token') and res.json().get('result').get('access_token'):
        return res.json().get('result').get('access_token')
    gm_raise_error(name, res)


class Task(QLTask):
    def __init__(self, task_name: str, file_name: str):
        super().__init__(task_name, file_name)
        self.save_list = []

    def task(self, index: int, datas: list, proxy: str, logger, next_datas: list) -> str or None:
        LOCAL.address = datas[0]
        LOCAL.private_key = datas[1]

        while True:
            payload = {
                'clientKey': CAPTCHA_KEY,
                'task': {
                    'type': 'TurnstileTaskProxyless',
                    'websiteURL': 'https://launchpad.gmnetwork.ai/',
                    'websiteKey': '0x4AAAAAAAaAdLjFNjUZZwWZ'
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

        if not hasattr(LOCAL, 'session'):
            LOCAL.session = get_session()
            LOCAL.session.headers.update({
                'Host': 'api-launchpad.gmnetwork.ai',
                'Origin': 'https://launchpad.gmnetwork.ai'
            })
        LOCAL.session.proxies = proxy

        token = login()
        logger.success('登录: 成功')
        self.save_list.append(f'{datas[0]}----{datas[1]}----{token}')

    def save(self):
        write_txt('GMWalletToken', '\n'.join(self.save_list))


if __name__ == '__main__':
    CAPTCHA_KEY = get_env(ENV_YES_CAPTCHA_KEY)
    if not CAPTCHA_KEY:
        log.error(f"未设置YesCaptchaKey环境变量，不运行此任务。")
    else:
        try:
            captcha_res = requests.post('https://api.yescaptcha.com/getBalance', json={'clientKey': CAPTCHA_KEY})
            if captcha_res.text.count('balance'):
                log.success(f"当前YesCaptchaKey: {CAPTCHA_KEY}   余额: {captcha_res.json().get('balance')}")
                Task(TASK_NAME, FILE_NAME).run()
            else:
                log.error(
                    f"YesCaptcha余额查询失败: {captcha_res.json().get('errorDescription') if captcha_res.text.count('errorDescription') else captcha_res.text}"
                )
        except:
            log.error(f"YesCaptcha余额查询失败")
