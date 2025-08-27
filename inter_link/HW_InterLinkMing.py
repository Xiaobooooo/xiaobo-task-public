"""
cron: 15 0/4 * * *
new Env('领克_挖矿')
"""
import base64
import hashlib
import hmac
import time

from common.task import QLTask, LOCAL
from common.util import get_session, raise_error

TASK_NAME = '领克_挖矿'
FILE_NAME = 'InterLinkToken.txt'

key = '02094d8004f1ada81e29badb75d347264cb1f360c51b43db8e4e98dfd4610b7a'.encode()


def get_signature(method: str, url: str, payload: str = None):
    x_date = int(time.time() * 1000)
    x_content_hash = base64.b64encode(hashlib.sha256(payload.encode()).digest()) if payload else None
    data = f'{method};{url};{x_date};prod.interlinklabs.ai{f";{x_content_hash}" if x_content_hash else ""}'
    x_signature = base64.b64encode(hmac.new(key, data.encode(), hashlib.sha256).digest())
    headers = {'x-date': f'{x_date}', 'x-signature': x_signature}
    if x_content_hash:
        headers['x-content-hash'] = x_content_hash
    return headers


def get_headers(token: str) -> dict:
    return {'User-Agent': 'okhttp/4.12.0', 'authorization': f'Bearer {token}'}


def mining():
    name = '挖矿'
    headers = get_signature('GET', '/api/v1/token/claim-airdrop')
    res = LOCAL.session.post('https://prod.interlinklabs.ai/api/v1/token/claim-airdrop', headers=headers)
    if res.text.count('statusCode') and res.json().get('statusCode') == 200:
        return f'{name}: 成功'
    if res.text.count('TOKEN_CLAIM_TOO_EARLY'):
        return f'{name}: 时间未到'
    return raise_error(name, res)


class Task(QLTask):
    def __init__(self, task_name: str, file_name: str):
        super().__init__(task_name, file_name)
        self.saves = []

    def task(self, index: int, datas: list[str], proxy: str, logger):
        email, uid, password, token = datas

        LOCAL.session = get_session(proxy)
        LOCAL.session.headers.update(get_headers(token))

        result = mining()
        logger.info(result)


if __name__ == '__main__':
    Task(TASK_NAME, FILE_NAME).run()
