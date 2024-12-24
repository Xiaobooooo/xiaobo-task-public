"""
cron: 0 10 * * *
new Env('Bera_注册域名')
"""
import os
import time

import requests
import web3
from eth_utils import keccak
from web3 import Web3, HTTPProvider
from web3.exceptions import ContractLogicError

from common.constant import ENV_CAPTCHA_RUN_KEY
from common.task import QLTask, ENV_YES_CAPTCHA_KEY, LOCAL
from common.util import raise_error, get_session, base_logger, get_logger, get_random_str

TASK_NAME = 'Bera_注册域名'
FILE_NAME = 'BeraWallet'

RPC_NAME = 'BERA_RPC'
rpc = os.getenv(RPC_NAME)
if not rpc:
    get_logger().info(f"暂未设置熊链RPC环境变量[{RPC_NAME}]")
    rpc = "https://bartio.rpc.berachain.com/"

BERA = Web3(HTTPProvider(rpc))

CONTRACT_ADDRESS = Web3.to_checksum_address('0xccc13A84eC34f3b1FbEF193557a68F9af2173Ab9')
ABI = [{"inputs": [{"components": [{"internalType": "string", "name": "name", "type": "string"},
                                   {"internalType": "address", "name": "owner", "type": "address"},
                                   {"internalType": "uint256", "name": "duration", "type": "uint256"},
                                   {"internalType": "address", "name": "resolver", "type": "address"},
                                   {"internalType": "bytes[]", "name": "data", "type": "bytes[]"},
                                   {"internalType": "bool", "name": "reverseRecord", "type": "bool"},
                                   {"internalType": "address", "name": "referrer", "type": "address"}],
                    "internalType": "struct RegistrarController.RegisterRequest", "name": "request", "type": "tuple"}],
        "name": "register", "outputs": [], "stateMutability": "payable", "type": "function"},
       {"inputs": [{"internalType": "bytes32", "name": "node", "type": "bytes32"},
                   {"internalType": "address", "name": "a", "type": "address"}], "name": "setAddr", "outputs": [],
        "stateMutability": "nonpayable", "type": "function"}]
CONTRACT = BERA.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)


def name_hash(domain):
    labels = domain.split('.')
    current_hash = bytes(32)  # 初始哈希为全零
    # 反向遍历标签
    for label in reversed(labels):
        current_hash = keccak(current_hash + keccak(label.encode('utf-8')))
    return current_hash


class Task(QLTask):
    def task(self, index: int, datas: list[str], proxy: str, logger):
        LOCAL.address = datas[0]
        if len(datas) <2:
            return
        private_key = datas[1]
        account = web3.Account.from_key(private_key)

        balance = BERA.eth.get_balance(account.address)
        if balance != Web3.to_wei(3, 'ether') and balance != Web3.to_wei(2, 'ether'):
            return

        domain = get_random_str()
        gas_price = int(BERA.eth.gas_price * 1.1)
        nonce = BERA.eth.get_transaction_count(account.address)
        resolver = '0x34Bb7CC576FA4B5f31f984a65dDB7Ff78b8Ecbe0'
        referrer = '0xb0AD0756C00A7ccBB1edb86eB69971591353b888'
        data = CONTRACT.encode_abi('setAddr', [name_hash(f'{domain}.bera'), account.address])
        try:
            register = CONTRACT.functions.register((domain, account.address, 31536000, resolver, [data], True, referrer))
            tx = register.build_transaction(
                {'from': account.address, 'value': Web3.to_wei(1, 'ether'), 'gasPrice': gas_price, 'nonce': nonce}
            )
        except ContractLogicError as e:
            logger.error(f'Register交易检测失败: {e}')
            return
        signed_tx = BERA.eth.account.sign_transaction(tx, private_key)
        transaction = BERA.eth.send_raw_transaction(signed_tx.raw_transaction)
        logger.success(f"Register交易发送成功: 0x{transaction.hex()}")


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
