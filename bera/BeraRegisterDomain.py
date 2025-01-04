"""
cron: 1 1 1 1 1
new Env('Bera_注册域名')
"""
import os

import requests
import web3
from eth_utils import keccak
from web3 import Web3, HTTPProvider
from web3.exceptions import ContractLogicError

from common.constant import ENV_CAPTCHA_RUN_KEY
from common.task import QLTask, ENV_YES_CAPTCHA_KEY, LOCAL
from common.util import base_logger, get_logger, get_random_str, get_session, raise_error

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


def query_domain(address):
    name = '查询域名'
    url = 'https://api.goldsky.com/api/public/project_clz85ah0rn3jq01uodu4sdogx/subgraphs/beranames-bartio-prod-berachain-bartio/1/gn'
    payload = {"operationName": "getMints",
               "variables": {"first": 10, "offset": 0, "owner": address.lower(), "filterValue": ""},
               "query": "query getMints($first: Int!, $offset: Int!, $owner: String!, $filterValue: String!) {\n  nameRegistereds(\n    first: $first\n    skip: $offset\n    orderBy: timestamp_\n    orderDirection: desc\n    where: {owner: $owner, name_contains: $filterValue}\n  ) {\n    name\n    label\n    id\n    expires\n    owner\n    timestamp_\n    __typename\n  }\n  transfers(where: {owner: $owner}) {\n    owner\n    __typename\n  }\n}"}
    res = LOCAL.session.post(url, json=payload)
    if res.text.count('nameRegistereds'):
        return res.json().get('data').get('nameRegistereds')
    raise_error(name, res)


class Task(QLTask):
    def task(self, index: int, datas: list[str], proxy: str, logger):
        LOCAL.address = datas[0]
        if len(datas) < 2:
            return
        private_key = datas[1]
        account = web3.Account.from_key(private_key)

        balance = BERA.eth.get_balance(account.address)
        if balance <= Web3.to_wei(1, 'ether'):
            logger.error("余额不足，无注册域名")
            return

        LOCAL.session = get_session(proxy)
        LOCAL.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        })
        domains = query_domain(account.address)
        if len(domains) > 0:
            logger.info("已注册域名，跳过")
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
    Task(TASK_NAME, FILE_NAME, use_ipv6=True, is_delay=False).run()
