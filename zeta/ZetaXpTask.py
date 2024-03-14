"""
cron: 0 10 * * 5
new Env('Zeta_交互')
"""
import random
import time

from eth_typing import ChecksumAddress
from web3 import Web3
from web3.exceptions import ContractLogicError

from common.task import QLTask
from common.util import get_session, LOCAL
from ZetaXpEnroll import ZETA, claim_xp, refresh, FILE_NAME

TASK_NAME = 'Zeta_交互'

ABI = [{"constant": False, "inputs": [{"internalType": "address", "name": "recipient", "type": "address"},
                                      {"internalType": "uint256", "name": "amount", "type": "uint256"}],
        "name": "transfer", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "payable": False, "stateMutability": "nonpayable", "type": "function"},
       {"constant": True, "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "payable": False, "stateMutability": "view", "type": "function"}]


def send_zeta(address: ChecksumAddress, private_key: str) -> str:
    nonce = ZETA.eth.get_transaction_count(address)
    gas_price = ZETA.eth.gas_price
    tx = {'from': address, 'to': address, 'value': Web3.to_wei(0.01, 'ether'), 'nonce': nonce, 'chainId': ZETA.eth.chain_id,
          'maxFeePerGas': int(gas_price * 1.2), 'maxPriorityFeePerGas': int(gas_price * 1.1)}
    tx['gas'] = ZETA.eth.estimate_gas(tx)
    signed_tx = ZETA.eth.account.sign_transaction(tx, private_key)
    transaction = ZETA.eth.send_raw_transaction(signed_tx.rawTransaction)
    ZETA.eth.wait_for_transaction_receipt(transaction)
    return transaction.hex()


def send_eth(address: ChecksumAddress, private_key: str) -> str:
    contract_address = ZETA.to_checksum_address('0xd97B1de3619ed2c6BEb3860147E30cA8A7dC9891')
    return transfer_token(address, private_key, contract_address)


def send_btc(address: ChecksumAddress, private_key: str) -> str:
    contract_address = ZETA.to_checksum_address('0x13A0c5930C028511Dc02665E7285134B6d11A5f4')
    return transfer_token(address, private_key, contract_address)


def send_bnb(address: ChecksumAddress, private_key: str) -> str:
    contract_address = ZETA.to_checksum_address('0x48f80608B672DC30DC7e3dbBd0343c5F02C738Eb')
    return transfer_token(address, private_key, contract_address)


def transfer_token(address: ChecksumAddress, private_key: str, contract_address: str) -> str:
    contract_address = Web3.to_checksum_address(contract_address)
    contract = ZETA.eth.contract(address=contract_address, abi=ABI)
    nonce = ZETA.eth.get_transaction_count(address)
    try:
        transfer = contract.functions.transfer(address, 0)
        tx = transfer.build_transaction({'from': address, 'gasPrice': ZETA.eth.gas_price, 'nonce': nonce})
    except ContractLogicError as e:
        return str(e)
    signed_tx = ZETA.eth.account.sign_transaction(tx, private_key)
    transaction = ZETA.eth.send_raw_transaction(signed_tx.rawTransaction)
    ZETA.eth.wait_for_transaction_receipt(transaction)
    return transaction.hex()


def mint_st_zeta(address: ChecksumAddress, private_key: str) -> str:
    nonce = ZETA.eth.get_transaction_count(address)
    gas_price = ZETA.eth.gas_price
    tx = {'from': address, 'to': Web3.to_checksum_address('0xcf1A40eFf1A4d4c56DC4042A1aE93013d13C3217'),
          'value': Web3.to_wei(random.randint(1, 100) / 1e11, 'ether'), 'nonce': nonce,
          'data': '0xf340fa01000000000000000000000000d72c1695b0249e94abd83ac920f3cf25d6dd225e',
          'chainId': ZETA.eth.chain_id, 'maxFeePerGas': int(gas_price * 1.2), 'maxPriorityFeePerGas': int(gas_price * 1.1)}
    tx['gas'] = ZETA.eth.estimate_gas(tx)
    signed_tx = ZETA.eth.account.sign_transaction(tx, private_key)
    transaction = ZETA.eth.send_raw_transaction(signed_tx.rawTransaction)
    ZETA.eth.wait_for_transaction_receipt(transaction)
    return transaction.hex()


def stake_zeta(address: ChecksumAddress, private_key: str) -> str:
    nonce = ZETA.eth.get_transaction_count(address)
    gas_price = ZETA.eth.gas_price
    tx = {'from': address, 'to': Web3.to_checksum_address('0x45334a5B0a01cE6C260f2B570EC941C680EA62c0'),
          'value': Web3.to_wei(random.randint(1, 100) / 1e8, 'ether'), 'nonce': nonce, 'chainId': ZETA.eth.chain_id,
          'data': '0x5bcb2fc6', 'maxFeePerGas': int(gas_price * 1.2), 'maxPriorityFeePerGas': int(gas_price * 1.1)}
    tx['gas'] = ZETA.eth.estimate_gas(tx)
    signed_tx = ZETA.eth.account.sign_transaction(tx, private_key)
    transaction = ZETA.eth.send_raw_transaction(signed_tx.rawTransaction)
    ZETA.eth.wait_for_transaction_receipt(transaction)
    return transaction.hex()


class Task(QLTask):
    def task(self, index: int, datas: list, proxy: str, logger, next_datas: list) -> str or None:
        address = ZETA.to_checksum_address(datas[0])
        private_key = datas[1]
        if not hasattr(LOCAL, 'session'):
            LOCAL.session = get_session()
            LOCAL.session.headers.update({
                'sec-ch-ua-platform': '"Windows"',
                'Origin': 'https://hub.zetachain.com',
            })
        LOCAL.session.proxies = proxy
        if not hasattr(LOCAL, 'zeta_tx'):
            LOCAL.zeta_tx = send_zeta(address, private_key)
            logger.info(f'转账ZETA交易Hash: {LOCAL.zeta_tx}')
        if not hasattr(LOCAL, 'eth_tx'):
            LOCAL.eth_tx = send_eth(address, private_key)
            logger.info(f'转账ETH交易Hash: {LOCAL.eth_tx}')
        if not hasattr(LOCAL, 'btc_tx'):
            LOCAL.btc_tx = send_btc(address, private_key)
            logger.info(f'转账BTC交易Hash: {LOCAL.btc_tx}')
        if not hasattr(LOCAL, 'bnb_tx'):
            LOCAL.bnb_tx = send_bnb(address, private_key)
            logger.info(f'转账BNB交易Hash: {LOCAL.bnb_tx}')
        if not hasattr(LOCAL, 'mint_tx'):
            LOCAL.mint_tx = mint_st_zeta(address, private_key)
            logger.info(f'Mint stZeta交易Hash: {LOCAL.mint_tx}')
        if not hasattr(LOCAL, 'stake_tx'):
            LOCAL.stake_tx = stake_zeta(address, private_key)
            logger.info(f'Stake Zeta交易Hash: {LOCAL.stake_tx}')

        delay = random.randint(5, 10)
        logger.info(f'{delay}S后刷新任务')
        time.sleep(delay)

        result = refresh(LOCAL.session, address)
        logger.info(result)

        delay = random.randint(3, 5)
        logger.info(f'{delay}S后领取XP')
        time.sleep(delay)

        result = claim_xp(LOCAL.session, 'SEND_ZETA', address, private_key)
        logger.info(result)
        result = claim_xp(LOCAL.session, 'RECEIVE_ZETA', address, private_key)
        logger.info(result)
        result = claim_xp(LOCAL.session, 'RECEIVE_ETH', address, private_key)
        logger.info(result)
        result = claim_xp(LOCAL.session, 'RECEIVE_BTC', address, private_key)
        logger.info(result)
        result = claim_xp(LOCAL.session, 'RECEIVE_BNB', address, private_key)
        logger.info(result)
        result = claim_xp(LOCAL.session, 'ACCUMULATED_FINANCE_DEPOSIT', address, private_key)
        logger.info(result)
        result = claim_xp(LOCAL.session, 'ZETA_EARN_STAKE', address, private_key)
        logger.info(result)


if __name__ == '__main__':
    Task(TASK_NAME, FILE_NAME).run()
