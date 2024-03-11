"""
cron: 0 10 * * *
new Env('Web3Go_签到')
"""
import json
from datetime import datetime

import requests
import web3
from eth_account.messages import encode_defunct
from eth_typing import ChecksumAddress
from tls_client import Session
from web3 import Web3

from common.task import QLTask
from common.util import LOCAL, clear_local, get_session, raise_error

TASK_NAME = 'Web3Go_签到'
FILE_NAME = 'Web3GoWallet.txt'


def up_raise_error(name, res):
    raise_error(name, res, msg_key="err")


def login(session: Session, address: ChecksumAddress, private_key: str) -> str:
    name = '获取nonce'
    res = requests.post('https://reiki.web3go.xyz/api/account/web3/web3_nonce', json={'address': address})
    if res.text.count('nonce'):
        name = '登录'
        nonce = res.json().get('nonce')
        challenge = f'reiki.web3go.xyz wants you to sign in with your Ethereum account:\n{address}\n\nWelcome to Web3Go! Click to sign in and accept the Web3Go Terms of Service. This request will not trigger any blockchain transaction or cost any gas fees. Your authentication status will reset after 7 days. Wallet address: {address} Nonce: {nonce}\n\nURI: https://reiki.web3go.xyz\nVersion: 1\nChain ID: 56\nNonce: {address}\nIssued At: {datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"}'
        message = encode_defunct(text=challenge)
        signature = web3.Account.sign_message(message, private_key=private_key).signature.hex()
        payload = {'address': address, 'nonce': nonce, 'challenge': json.dumps({'msg': challenge}), 'signature': signature}
        res = session.post('https://reiki.web3go.xyz/api/account/web3/web3_challenge', json=payload)
        if res.text.count('token'):
            return res.json().get('extra').get('token')
    raise_error(name, res)


def check_in() -> str:
    name = '签到'
    date = datetime.now().strftime("%Y-%m-%d")
    res = LOCAL.session.put(f'https://reiki.web3go.xyz/api/checkin?day={date}')
    if res.text == 'true':
        return f'{name}: 成功'
    raise_error(name, res)


class Task(QLTask):
    @clear_local
    def task(self, index: int, datas: list, proxy: str, logger, next_datas: list) -> str or None:
        address = Web3.to_checksum_address(datas[0])
        private_key = datas[1]

        if not hasattr(LOCAL, 'session'):
            LOCAL.session = get_session()
        LOCAL.session.proxies = proxy
        if not hasattr(LOCAL, 'token'):
            LOCAL.token = login(LOCAL.session, address, private_key)
            logger.info('登录: 成功')
            LOCAL.session.headers.update({'Authorization': f'Bearer {LOCAL.token}'})
        result = check_in()
        logger.info(result)


if __name__ == '__main__':
    Task(TASK_NAME, FILE_NAME).run()
