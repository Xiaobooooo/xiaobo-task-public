"""
name: BERA_Swap
cron: 0 10,20 * * *
"""
import os
import random

import web3
from web3 import Web3, HTTPProvider
from web3.exceptions import ContractLogicError, TransactionNotFound

from common.task import QLTask
from common.util import get_logger

TASK_NAME = 'BERA_Swap'
FILE_NAME = 'BeraWallet'

RPC_NAME = 'BERA_RPC'
rpc = os.getenv(RPC_NAME)
if not rpc:
    get_logger().info(f"暂未设置熊链RPC环境变量[{RPC_NAME}]")
    rpc = "https://bartio.rpc.berachain.com/"

BERA = Web3(HTTPProvider(rpc))

CONTRACT_ADDRESS = Web3.to_checksum_address('0x21e2C0AFd058A89FCf7caf3aEA3cB84Ae977B73D')
ABI = [{"inputs": [{"components": [{"internalType": "uint256", "name": "poolIdx", "type": "uint256"},
                                   {"internalType": "address", "name": "base", "type": "address"},
                                   {"internalType": "address", "name": "quote", "type": "address"},
                                   {"internalType": "bool", "name": "isBuy", "type": "bool"}],
                    "internalType": "struct SwapHelpers.SwapStep[]", "name": "_steps", "type": "tuple[]"},
                   {"internalType": "uint128", "name": "_amount", "type": "uint128"},
                   {"internalType": "uint128", "name": "_minOut", "type": "uint128"}], "name": "multiSwap",
        "outputs": [{"internalType": "uint128", "name": "out", "type": "uint128"}], "stateMutability": "payable", "type": "function"}]
CONTRACT = BERA.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

TOKEN_CONTRACT_ADDRESS = Web3.to_checksum_address("0x0E4aaF1351de4c0264C5c7056Ef3777b41BD8e03")
TOKEN_ABI = [{"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf",
              "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"},
             {"inputs": [{"internalType": "address", "name": "spender", "type": "address"},
                         {"internalType": "uint256", "name": "value", "type": "uint256"}], "name": "approve",
              "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"}]
TOKEN_CONTRACT = BERA.eth.contract(address=Web3.to_checksum_address(TOKEN_CONTRACT_ADDRESS), abi=TOKEN_ABI)


class Task(QLTask):
    def task(self, index: int, datas: list[str], proxy: str, logger):
        if len(datas) == 0:
            logger.warning('不存在私钥，不进行Swap')
            return
        private_key = datas[1]

        account = web3.Account.from_key(private_key)
        nonce = BERA.eth.get_transaction_count(account.address)
        gas_price = int(BERA.eth.gas_price * 1.2)
        balance = BERA.eth.get_balance(account.address)
        logger.info(f'BERA Balance: {Web3.from_wei(balance, "ether")}')
        if balance < Web3.to_wei(0.001, 'ether'):
            logger.warning('BERA余额低于0.001，不进行Swap')
            return
        token_balance = TOKEN_CONTRACT.functions.balanceOf(account.address).call()
        logger.info(f'HONEY Balance: {Web3.from_wei(token_balance, "ether")}')
        try:
            if token_balance > Web3.to_wei(2, "ether"):
                logger.info("HONEY TO BERA")
                params = {
                    'poolIdx': 36000,
                    'base': '0x0E4aaF1351de4c0264C5c7056Ef3777b41BD8e03',
                    'quote': '0x0000000000000000000000000000000000000000',
                    'isBuy': True,
                }
                method = CONTRACT.functions.multiSwap([params], token_balance, 0)
                try:
                    tx = method.build_transaction(
                        {'from': account.address, 'value': 0, 'gasPrice': gas_price, 'nonce': nonce}
                    )
                except ContractLogicError as e:
                    if repr(e).count("0x13be252b"):
                        logger.info("授权HONEY")
                        approve = TOKEN_CONTRACT.functions.approve(Web3.to_checksum_address('0x21e2C0AFd058A89FCf7caf3aEA3cB84Ae977B73D'),
                                                                   57896044618658097711785492504343953926634992332820282019728792003956564819967)
                        tx = approve.build_transaction(
                            {'from': account.address, 'value': 0, 'gasPrice': gas_price, 'nonce': nonce}
                        )
                    else:
                        raise e
            else:
                if balance < Web3.to_wei(0.01, 'ether'):
                    logger.warning('BERA余额低于0.001，不进行ETH TO HONEY')
                    return
                logger.info("BERA TO HONEY")
                if balance <= Web3.to_wei(0.05, 'ether'):
                    random_value = 0.01
                elif balance <= Web3.to_wei(0.1, 'ether'):
                    random_value = random.uniform(0.01, 0.05)
                elif balance <= Web3.to_wei(1, 'ether'):
                    random_value = random.uniform(0.1, 0.5)
                else:
                    random_value = random.uniform(0.1, 0.9)
                random_value_ether = Web3.to_wei(random_value, 'ether')
                params = {
                    'poolIdx': 36000,
                    'base': '0x0E4aaF1351de4c0264C5c7056Ef3777b41BD8e03',
                    'quote': '0x0000000000000000000000000000000000000000',
                    'isBuy': False,
                }
                method = CONTRACT.functions.multiSwap([params], random_value_ether, 0)
                tx = method.build_transaction(
                    {'from': account.address, 'value': random_value_ether, 'nonce': nonce, 'gasPrice': gas_price}
                )
        except ContractLogicError as e:
            logger.error(f'Swap交易检测失败: {e}')
            return
        tx['gas'] = int(BERA.eth.estimate_gas(tx) * 1.2)
        signed_tx = BERA.eth.account.sign_transaction(tx, private_key)
        transaction = BERA.eth.send_raw_transaction(signed_tx.raw_transaction)
        logger.success(f"Swap交易发送成功: 0x{transaction.hex()}")
        while True:
            try:
                receipt = BERA.eth.get_transaction_receipt(transaction)
                if receipt.get('status') == 0:
                    logger.error(f'Swap交易确认失败: 0x{transaction.hex()}')
                if receipt.get('status') == 1:
                    logger.success(f'Swap交易确认成功: 0x{transaction.hex()}')
                break
            except TransactionNotFound:
                continue
            except Exception as e:
                raise e


if __name__ == '__main__':
    Task(TASK_NAME, FILE_NAME).run()
