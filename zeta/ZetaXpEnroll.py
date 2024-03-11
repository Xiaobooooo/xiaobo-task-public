"""
cron: 1 1 1 1 1
new Env('Zeta_XP注册')
"""
import base64
import time
from urllib.parse import parse_qs, unquote

from eth_typing import ChecksumAddress
from tls_client import Session
from web3 import Web3, HTTPProvider
from web3.exceptions import ContractLogicError

from common.task import QLTask
from common.util import log, get_env, get_session, raise_error, LOCAL, clear_local, TaskException

TASK_NAME = 'Zeta_XP注册'
FILE_NAME = 'ZetaWallet.txt'

RPC_NAME = 'ZETA_RPC'
rpc = get_env(RPC_NAME)
if rpc is None or rpc == '':
    rpc = "https://zetachain-evm.blockpi.network/v1/rpc/public"
    log.info(f"暂未设置RPC，默认RPC: {rpc}")

ZETA = Web3(HTTPProvider(rpc))


def send_enroll() -> str:
    nonce = ZETA.eth.get_transaction_count(LOCAL.address)
    if invite_code:
        parsed_dict = parse_qs(base64.b64decode(unquote(invite_code)).decode())
        method = CONTRACT.functions.confirmAndAcceptInvitation(ZETA.to_checksum_address(parsed_dict.get('address')[0]),
                                                               int(parsed_dict.get('expiration')[0]),
                                                               (int(parsed_dict.get('v')[0]), parsed_dict.get('r')[0],
                                                                parsed_dict.get('s')[0]))
        try:
            tx = method.build_transaction({'from': LOCAL.address, 'gasPrice': ZETA.eth.gas_price, 'nonce': nonce})
        except ContractLogicError as e:
            return str(e)
    else:
        gas_price = ZETA.eth.gas_price
        tx = {'from': LOCAL.address, 'to': CONTRACT_ADDRESS, 'data': '0x90c08473', 'nonce': nonce,
              'maxFeePerGas': int(gas_price * 1.2), 'maxPriorityFeePerGas': int(gas_price * 1.1), 'chainId': ZETA.eth.chain_id}
        try:
            tx['gas'] = ZETA.eth.estimate_gas(tx)
        except ContractLogicError as e:
            return str(e)
    signed_tx = ZETA.eth.account.sign_transaction(tx, LOCAL.private_key)
    transaction = ZETA.eth.send_raw_transaction(signed_tx.rawTransaction)
    ZETA.eth.wait_for_transaction_receipt(transaction)
    return transaction.hex()


def enroll() -> bool:
    name = '注册验证'
    res = LOCAL.session.post('https://xp.cl04.zetachain.com/v1/enroll-in-zeta-xp', json={"address": LOCAL.address})
    if res.text.count('isUserVerified'):
        return res.json().get('isUserVerified')
    raise_error(name, res)


def refresh(session: Session, address: ChecksumAddress) -> str:
    name = '刷新任务'
    res = session.get(f'https://xp.cl04.zetachain.com/v1/get-user-has-xp-to-refresh?address={address}')
    if res.text.count('totalAmountEarnedInEpoch'):
        return f'{name}: 成功'
    raise_error(name, res)


def claim_xp(session: Session, task: str, address: ChecksumAddress, private_key: str) -> str:
    name = f'领取XP-{task}'
    signature = ZETA.eth.account.sign_typed_data(private_key, {'name': "Hub/XP", 'version': "1", 'chainId': '7000'},
                                                 {'Message': [{'name': "content", 'type': "string"}]}, {'content': "Claim XP"})
    payload = {"address": address, "task": task, "signedMessage": signature.signature.hex()}
    while True:
        res = session.post('https://xp.cl04.zetachain.com/v1/xp/claim-task', json=payload)
        if res.text.count('Please wait a few seconds before trying again.'):
            time.sleep(3)
        else:
            break

    if res.text.count('totalXp') or res.text.count('XP refreshed successfully'):
        return f'{name}: 成功'
    if res.text.count('Task already claimed'):
        return f'{name}: 任务已完成'
    raise_error(name, res)


class Task(QLTask):
    @clear_local
    def task(self, index: int, datas: list, proxy: str, logger, next_datas: list) -> str or None:
        LOCAL.address = ZETA.to_checksum_address(datas[0])
        LOCAL.private_key = datas[1]
        if not hasattr(LOCAL, 'session'):
            LOCAL.session = get_session()
            LOCAL.session.headers.update({
                'sec-ch-ua-platform': '"Windows"',
                'Origin': 'https://hub.zetachain.com',
            })
        LOCAL.session.proxies = proxy
        result = send_enroll()
        if result.startswith('0x'):
            logger.info(f'注册交易Hash: {result}   10S后进行注册')
            time.sleep(10)
        else:
            logger.info(f'注册发送失败: {result}')

        result = enroll()
        if result:
            result = refresh(LOCAL.session, LOCAL.address)
            logger.info(result)
            result = claim_xp(LOCAL.session, "WALLET_VERIFY", LOCAL.address, LOCAL.private_key)
            logger.info(result)
            result = claim_xp(LOCAL.session, "WALLET_VERIFY_BY_INVITE", LOCAL.address, LOCAL.private_key)
            logger.info(result)
        else:
            raise TaskException("注册", "注册认证失败")


if __name__ == '__main__':
    INVITE_CODE_NAME = 'ZETA_INVITE_CODE'
    invite_code = get_env(INVITE_CODE_NAME)
    if not invite_code:
        log.info("暂未设置邀请码INVITE_CODE")

    ABI = [{"inputs": [{"internalType": "address", "name": "inviter", "type": "address"},
                       {"internalType": "uint256", "name": "expiration", "type": "uint256"},
                       {"components": [{"internalType": "uint8", "name": "v", "type": "uint8"},
                                       {"internalType": "bytes32", "name": "r", "type": "bytes32"},
                                       {"internalType": "bytes32", "name": "s", "type": "bytes32"}],
                        "internalType": "struct InvitationManager.Signature", "name": "signature", "type": "tuple"}],
            "name": "confirmAndAcceptInvitation", "outputs": [], "type": "function"}]

    CONTRACT_ADDRESS = ZETA.to_checksum_address('0x3C85e0cA1001F085A3e58d55A0D76E2E8B0A33f9')
    CONTRACT = ZETA.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)
    Task(TASK_NAME, FILE_NAME).run()
