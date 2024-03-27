"""
cron: 0 0 1,15 * *
new Env('Qna3_领取')
"""
import time

from web3 import Web3, HTTPProvider

from common.task import QLTask
from common.util import LOCAL, get_session
from Qna3CheckIn import FILE_NAME, CONTRACT_ADDRESS, qna3_raise_error, login

TASK_NAME = 'Qna3_领取'

BSC = Web3(HTTPProvider("https://bsc-dataseed2.defibit.io"))


def claim_all():
    name = '获取领取数据'
    res = LOCAL.session.post('https://api.qna3.ai/api/v2/my/claim-all', json={})
    if res.text.count('signature'):
        amount = res.json().get('data').get("amount")
        history_id = res.json().get('data').get("history_id")
        nonce = res.json().get('data').get("signature").get("nonce")
        signature = res.json().get('data').get("signature").get("signature")
        return amount, history_id, nonce, signature
    if res.text.count('statusCode') and res.json().get("statusCode") == 200:
        return None, None, None, None
    qna3_raise_error(name, res)


def send_claim() -> str:
    transaction_data = f'0x624f82f5{format(LOCAL.amount, "0>64x")}{format(LOCAL.nonce, "0>64x")}00000000000000000000000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000000000041{LOCAL.signature[2:]}00000000000000000000000000000000000000000000000000000000000000'
    gas_price = int(BSC.eth.gas_price * 1.1)
    nonce = BSC.eth.get_transaction_count(LOCAL.address)
    tx = {'from': LOCAL.address, 'to': CONTRACT_ADDRESS, 'data': transaction_data, 'gasPrice': gas_price, 'nonce': nonce}
    tx['gas'] = BSC.eth.estimate_gas(tx)
    signed_tx = BSC.eth.account.sign_transaction(tx, LOCAL.private_key)
    transaction = BSC.eth.send_raw_transaction(signed_tx.rawTransaction)
    BSC.eth.wait_for_transaction_receipt(transaction)
    return transaction.hex()


def claim() -> str:
    name = '领取'
    payload = {"hash": LOCAL.hash}
    res = LOCAL.session.put(f'https://api.qna3.ai/api/v2/my/claim/{LOCAL.history_id}', json=payload)
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
        if not hasattr(LOCAL, 'history_id'):
            LOCAL.amount, LOCAL.history_id, LOCAL.nonce, LOCAL.signature = claim_all()
        if not hasattr(LOCAL, 'history_id') or not LOCAL.history_id:
            logger.info(f'领取: 暂无可领取积分')
            return
        LOCAL.hash = send_claim()
        logger.info(f'领取交易Hash: {LOCAL.hash}')
        time.sleep(3)
        result = claim()
        logger.info(result)
        time.sleep(2)


if __name__ == '__main__':
    Task(TASK_NAME, FILE_NAME).run()
