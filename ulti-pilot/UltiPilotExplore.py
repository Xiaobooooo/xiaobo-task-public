"""
cron: 0 10,22 * * *
new Env('UltiPilot_探索')
"""
import time

from eth_account.messages import encode_defunct
from web3 import Web3, HTTPProvider

from common.task import QLTask
from common.util import LOCAL, get_session, raise_error

TASK_NAME = 'UltiPilot_探索'
FILE_NAME = 'UltiPilotAddress.txt'

BSC = Web3(HTTPProvider("https://opbnb-mainnet-rpc.bnbchain.org"))


def up_raise_error(name, res):
    raise_error(name, res, msg_key="err")


def login() -> str:
    name = '登录-获取签名'
    payload = {"address": LOCAL.address, "feature": "assets-wallet-login", "chainId": 204}
    res = LOCAL.session.post('https://account-api.ultiverse.io/api/user/signature', json=payload)
    if res.text.count('message'):
        msg = res.json().get('data').get('message')
        message = encode_defunct(text=msg)
        signature = BSC.eth.account.sign_message(message, private_key=LOCAL.private_key).signature.hex()
        name = '登录'
        payload = {"address": LOCAL.address, "signature": signature, "chainId": 204}
        res = LOCAL.session.post('https://account-api.ultiverse.io/api/wallets/signin', json=payload)
        if res.text.count('access_token'):
            return res.json().get('data').get('access_token')
    up_raise_error(name, res)


def query() -> int:
    name = '查询Soul'
    res = LOCAL.session.get('https://pml.ultiverse.io/api/profile')
    if res.text.count('success') and res.json().get('success'):
        soul1 = int(int(res.json().get('data').get('soulInAccount')) / 1000000)
        soul2 = int(int(res.json().get('data').get('soulInWallets')) / 1000000)
        return soul1 + soul2
    up_raise_error(name, res)


def query_explore() -> dict:
    name = '查询探索'
    res = LOCAL.session.get('https://pml.ultiverse.io/api/explore/list?&active=true')
    explore_list = {}
    if res.text.count('success') and res.json().get('success'):
        for data in res.json().get('data'):
            if not data.get('explored'):
                explore_list.update({data.get('worldId'): data.get('soul')})
        return explore_list
    up_raise_error(name, res)


def explore() -> (str, list, int):
    name = '探索'
    while True:
        if len(LOCAL.world_ids) < 1:
            return f'{name}: 没有可以探索的任务', [], -1
        payload = {"worldIds": LOCAL.world_ids, "chainId": 204}
        res = LOCAL.session.post('https://pml.ultiverse.io/api/explore/sign', json=payload)
        if res.text.count('Insufficient soul point'):
            LOCAL.world_ids.pop()
            time.sleep(10)
        elif res.text.count('Request too frequent'):
            time.sleep(10)
        elif res.text.count('Already explored for Terminus'):
            return f'{name}: 今日已经探索过了', [], -1
        else:
            break
    if res.text.count('deadline'):
        data_json = res.json().get('data')
        contract = data_json.get('contract')
        deadline = data_json.get('deadline')
        voyage_id = data_json.get('voyageId')
        destinations = data_json.get('destinations')
        data = data_json.get('data')
        signature = data_json.get('signature')
        nonce = BSC.eth.get_transaction_count(LOCAL.address)

        destinations_hex = hex(224 + (len(destinations) - 1) * 32).replace("0x", "")
        for i in range(64 - len(destinations_hex)):
            destinations_hex = f'0{destinations_hex}'

        voyage_id_hex = hex(voyage_id).replace("0x", "")
        for i in range(64 - len(voyage_id_hex)):
            voyage_id_hex = f'0{voyage_id_hex}'

        destinations_len_hex = hex(len(destinations)).replace("0x", "")
        for i in range(64 - len(destinations_len_hex)):
            destinations_len_hex = f'0{destinations_len_hex}'

        destination_hexs = ''
        for destination in destinations:
            destination_hex = hex(destination).replace("0x", "")
            for i in range(64 - len(destination_hex)):
                destination_hex = f'0{destination_hex}'
            destination_hexs += destination_hex

        data = f'0x75278b5c00000000000000000000000000000000000000000000000000000000{hex(deadline).replace("0x", "")}{voyage_id_hex}00000000000000000000000000000000000000000000000000000000000000a0{data.replace("0x", "")}{destinations_hex}{destinations_len_hex}{destination_hexs}0000000000000000000000000000000000000000000000000000000000000041{signature.replace("0x", "")}00000000000000000000000000000000000000000000000000000000000000'
        tx = {'from': LOCAL.address, 'to': contract, 'nonce': nonce, 'data': data, 'gasPrice': int(BSC.eth.gas_price * 1.2)}
        tx['gas'] = BSC.eth.estimate_gas(tx)
        signed_tx = BSC.eth.account.sign_transaction(tx, LOCAL.private_key)
        transaction = BSC.eth.send_raw_transaction(signed_tx.rawTransaction)
        BSC.eth.wait_for_transaction_receipt(transaction)
        return transaction.hex(), LOCAL.world_ids, voyage_id
    up_raise_error(name, res)


def check() -> str:
    name = '检测浏览'
    for i in range(3):
        try:
            res = LOCAL.session.get(f'https://pml.ultiverse.io/api/explore/check?id={LOCAL.voyage_id}&chainId=204')
            if res.text.count('success'):
                return f"{name}: {'成功' if res.json().get('data').get('success') else '失败'}"
            up_raise_error(name, res)
        except Exception:
            pass
    raise Exception(f'{name}: 请求失败')


class Task(QLTask):
    def task(self, index: int, datas: list, proxy: str, logger, next_datas: list) -> str or None:
        LOCAL.address = BSC.to_checksum_address(datas[0])
        LOCAL.private_key = datas[1]

        if not hasattr(LOCAL, 'session'):
            LOCAL.session = get_session()
        LOCAL.session.proxies = proxy
        LOCAL.session.headers.update({
            'Host': 'account-api.ultiverse.io',
            'ul-auth-api-key': 'YWktYWdlbnRAZFd4MGFYWmxjbk5s',
            'Origin': 'https://pilot.ultiverse.io',
            'Referer': 'https://pilot.ultiverse.io/'
        })
        if not hasattr(LOCAL, 'token'):
            LOCAL.token = login()
            logger.info(f'登录: 成功')
            LOCAL.session.headers.update({
                'Host': 'pml.ultiverse.io',
                'ul-auth-address': LOCAL.address,
                'ul-auth-token': LOCAL.token
            })
        if not hasattr(LOCAL, 'soul'):
            LOCAL.soul = query()
            logger.info(f'当前Soul: {LOCAL.soul}')
        if not hasattr(LOCAL, 'world_ids'):
            my_soul = LOCAL.soul
            LOCAL.world_ids = []
            explore_list = query_explore()
            for world_id, soul in explore_list.items():
                if soul == 0:
                    LOCAL.world_ids.append(world_id)
                else:
                    my_soul -= soul
                    if my_soul >= 0:
                        LOCAL.world_ids.append(world_id)
                    else:
                        break
            if len(LOCAL.world_ids) < 1:
                logger.success(f'没有可以探索的任务')
                return
            logger.info(f'当前探索: {LOCAL.world_ids}')
        if not hasattr(LOCAL, 'voyage_id'):
            result, LOCAL.world_ids, voyage_id = explore()
            if voyage_id == -1:
                logger.info(result)
                return
            LOCAL.voyage_id = voyage_id
            logger.info(f'{LOCAL.world_ids}探索交易Hash: {result}')
            time.sleep(2.33)

        result = check()
        logger.success(result)


if __name__ == '__main__':
    Task(TASK_NAME, FILE_NAME).run()
