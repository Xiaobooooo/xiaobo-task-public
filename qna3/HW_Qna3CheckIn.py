"""
cron: 0 10 * * *
new Env('Qna3_签到')
"""
import sys
import time

from eth_account.messages import encode_defunct
from eth_typing import ChecksumAddress
from requests import Session, Response
from web3 import Web3, HTTPProvider

from common.task import QLTask
from common.util import LOCAL, log, get_env, raise_error, get_session

TASK_NAME = 'Qna3_签到'
FILE_NAME = 'Qna3Wallet.txt'

CONTRACT_ADDRESS = Web3.to_checksum_address('0xb342e7d33b806544609370271a8d074313b7bc30')


def qna3_raise_error(name: str, res: Response):
    raise_error(name, res, msg_key="errors/0/message")


def login(session: Session, bsc: Web3, address: ChecksumAddress, private_key: str) -> str:
    name = '登录'
    msg = 'AI + DYOR = Ultimate Answer to Unlock Web3 Universe'
    signature = bsc.eth.account.sign_message(encode_defunct(text=msg), private_key=private_key).signature.hex()
    payload = {'wallet_address': address, 'signature': signature}
    res = session.post('https://api.qna3.ai/api/v2/auth/login?via=wallet', json=payload)
    if res.text.count('accessToken'):
        return res.json().get('data').get("accessToken")
    qna3_raise_error(name, res)


def query_check_in() -> str:
    name = '查询'
    res = LOCAL.session.post('https://api.qna3.ai/api/v2/graphql', json={
        "query": "query loadUserDetail($cursored: CursoredRequestInput!) {\n  userDetail {\n    checkInStatus {\n      checkInDays\n      todayCount\n      checked\n    }\n    credit\n    creditHistories(cursored: $cursored) {\n      cursorInfo {\n        endCursor\n        hasNextPage\n      }\n      items {\n        claimed\n        extra\n        id\n        score\n        signDay\n        signInId\n        txHash\n        typ\n      }\n      total\n    }\n    invitation {\n      code\n      inviteeCount\n      leftCount\n    }\n    origin {\n      email\n      id\n      internalAddress\n      userWalletAddress\n    }\n    voteHistoryOfCurrentActivity {\n      created_at\n      query\n    }\n    ambassadorProgram {\n      bonus\n      claimed\n      family {\n        checkedInUsers\n        totalUsers\n      }\n    }\n  }\n}",
        "variables": {"cursored": {"after": "", "first": 20}}})
    if res.text.count('checkInStatus'):
        return res.json().get('data').get("userDetail").get("checkInStatus").get("checked")
    qna3_raise_error(name, res)


def send_check_in() -> str:
    gas_price = int(BSC.eth.gas_price * 1.1)
    nonce = BSC.eth.get_transaction_count(LOCAL.address)
    method = CONTRACT.functions.checkIn(1)
    tx = method.build_transaction({'gasPrice': gas_price, 'nonce': nonce})
    tx['gas'] = BSC.eth.estimate_gas(tx)
    signed_tx = BSC.eth.account.sign_transaction(tx, LOCAL.private_key)
    transaction = BSC.eth.send_raw_transaction(signed_tx.rawTransaction)
    BSC.eth.wait_for_transaction_receipt(transaction)
    return transaction.hex()


def check_in() -> str:
    name = '签到'
    payload = {"hash": LOCAL.hash, "via": VIA}
    res = LOCAL.session.post('https://api.qna3.ai/api/v2/my/check-in', json=payload)
    if res.text.count('statusCode') and res.json().get("statusCode") == 200:
        return f'{name}: 成功'
    qna3_raise_error(name, res)


class Task(QLTask):
    def task(self, index: int, datas: list, proxy: str, logger, next_datas: list) -> str or None:
        LOCAL.address = BSC.to_checksum_address(datas[0])
        LOCAL.private_key = datas[1]

        if not hasattr(LOCAL, 'session'):
            LOCAL.session = get_session()
        LOCAL.session.proxies = proxy
        if not hasattr(LOCAL, 'token'):
            LOCAL.token = login(LOCAL.session, BSC, LOCAL.address, LOCAL.private_key)
            logger.info(f'登录: 成功')
            LOCAL.session.headers.update({'Authorization': f'Bearer {LOCAL.token}'})
        if query_check_in():
            logger.info(f'签到: 今日已签到')
            return
        LOCAL.hash = send_check_in()
        logger.info(f'签到交易Hash: {LOCAL.hash}')
        time.sleep(3)
        result = check_in()
        logger.info(result)
        time.sleep(2)


if __name__ == '__main__':
    RPC_NAME = 'QNA3_RPC'
    ABI = [{"inputs": [{"name": "param_uint256_1", "type": "uint256"}], "name": "checkIn", "outputs": [], "type": "function"},
           {"inputs": [{"name": "activityIndex", "type": "uint256"}, {"name": "id", "type": "uint256"},
                       {"name": "credit", "type": "uint32"}], "name": "vote", "outputs": [], "type": "function"}]

    RPC = get_env(RPC_NAME)
    if RPC is None or RPC == '':
        RPC = "https://opbnb-mainnet-rpc.bnbchain.org"
        log.info(f"暂未设置RPC，默认opBNB RPC: {RPC}")
    BSC = Web3(HTTPProvider(RPC))
    CHAIN_ID = BSC.eth.chain_id
    CONTRACT = BSC.eth.contract(CONTRACT_ADDRESS, abi=ABI)

    if CHAIN_ID == 56:
        VIA = 'bnb'
    elif CHAIN_ID == 204:
        VIA = 'opbnb'
    else:
        log.error("链ID获取失败，请检查RPC")
        sys.exit()
    Task(TASK_NAME, FILE_NAME).run()
