"""
name: BERA_BexSwap
cron: 0 10,20 * * *
"""
import os
import random

import web3
from web3 import Web3, HTTPProvider
from web3.exceptions import ContractLogicError, TransactionNotFound

from common.task import QLTask
from common.util import get_logger

TASK_NAME = 'BERA_BexSwap'
FILE_NAME = 'BeraWallet'

RPC_NAME = 'BERA_RPC'
rpc = os.getenv(RPC_NAME)
if not rpc:
    get_logger().info(f"暂未设置熊链RPC环境变量[{RPC_NAME}]")
    rpc = "https://bartio.rpc.berachain.com/"

BERA = Web3(HTTPProvider(rpc))

BEX_SWAP_ADDRESS = Web3.to_checksum_address('0x21e2C0AFd058A89FCf7caf3aEA3cB84Ae977B73D')
BEX_SWAP_ABI = [{"inputs": [{"components": [{"internalType": "uint256", "name": "poolIdx", "type": "uint256"},
                                            {"internalType": "address", "name": "base", "type": "address"},
                                            {"internalType": "address", "name": "quote", "type": "address"},
                                            {"internalType": "bool", "name": "isBuy", "type": "bool"}],
                             "internalType": "struct SwapHelpers.SwapStep[]", "name": "_steps", "type": "tuple[]"},
                            {"internalType": "uint128", "name": "_amount", "type": "uint128"},
                            {"internalType": "uint128", "name": "_minOut", "type": "uint128"}], "name": "multiSwap",
                 "outputs": [{"internalType": "uint128", "name": "out", "type": "uint128"}], "stateMutability": "payable",
                 "type": "function"}]
BEX_SWAP_CONTRACT = BERA.eth.contract(address=BEX_SWAP_ADDRESS, abi=BEX_SWAP_ABI)

TOKEN_ABI = [{"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf",
              "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"},
             {"inputs": [{"internalType": "address", "name": "spender", "type": "address"},
                         {"internalType": "uint256", "name": "value", "type": "uint256"}], "name": "approve",
              "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"}]

HONEY_ADDRESS = Web3.to_checksum_address("0x0E4aaF1351de4c0264C5c7056Ef3777b41BD8e03")
HONEY_CONTRACT = BERA.eth.contract(address=Web3.to_checksum_address(HONEY_ADDRESS), abi=TOKEN_ABI)


def confirm_transaction(transaction):
    while True:
        try:
            receipt = BERA.eth.get_transaction_receipt(transaction)
            return receipt.get('status') == 1
        except TransactionNotFound:
            continue
        except Exception as e:
            raise e
    return False


def approve(account, contract, spender):
    method = contract.functions.approve(Web3.to_checksum_address(spender),
                                        57896044618658097711785492504343953926634992332820282019728792003956564819967)
    gas_price = int(BERA.eth.gas_price * 1.2)
    nonce = BERA.eth.get_transaction_count(account.address)
    tx = method.build_transaction(
        {'from': account.address, 'value': 0, 'gasPrice': gas_price, 'nonce': nonce}
    )
    signed_tx = BERA.eth.account.sign_transaction(tx, account.key)
    return BERA.eth.send_raw_transaction(signed_tx.raw_transaction)


def swap_honey(account, is_buy, value):
    params = {
        'poolIdx': 36000,
        'base': '0x0E4aaF1351de4c0264C5c7056Ef3777b41BD8e03',
        'quote': '0x0000000000000000000000000000000000000000',
        'isBuy': is_buy,
    }
    method = BEX_SWAP_CONTRACT.functions.multiSwap([params], value, 0)
    gas_price = int(BERA.eth.gas_price * 1.2)
    nonce = BERA.eth.get_transaction_count(account.address)
    print( {
        'poolIdx': 36000,
        'base': '0x0E4aaF1351de4c0264C5c7056Ef3777b41BD8e03',
        'quote': '0x0000000000000000000000000000000000000000',
        'isBuy': is_buy,
    })
    print(0 if is_buy else value)
    tx = method.build_transaction(
        {'from': account.address, 'value': 0 if is_buy else value, 'gasPrice': gas_price, 'nonce': nonce}
    )
    tx['gas'] = int(BERA.eth.estimate_gas(tx) * 1.1)
    signed_tx = BERA.eth.account.sign_transaction(tx, account.key)
    return BERA.eth.send_raw_transaction(signed_tx.raw_transaction)


class Task(QLTask):
    def task(self, index: int, datas: list[str], proxy: str, logger):
        if len(datas) < 2:
            logger.warning('不存在私钥，不进行Swap')
            return
        private_key = datas[1]

        account = web3.Account.from_key(private_key)
        balance = BERA.eth.get_balance(account.address)
        logger.info(f'BERA Balance: {Web3.from_wei(balance, "ether")}')
        if balance < Web3.to_wei(0.005, 'ether'):
            logger.warning('BERA余额低于0.005，不进行Swap')
            return
        token_balance = HONEY_CONTRACT.functions.balanceOf(account.address).call()
        logger.info(f'HONEY Balance: {Web3.from_wei(token_balance, "ether")}')
        try:
            if token_balance > Web3.to_wei(2, "ether"):
                logger.info("HONEY TO BERA")
                try:
                    transaction = swap_honey(account, True, token_balance)
                    logger.info(f'Swap交易发送成功: 0x{transaction.hex()}')
                except ContractLogicError as e:
                    if repr(e).count("0x13be252b"):
                        logger.info("授权HONEY")
                        transaction = approve(account, HONEY_CONTRACT, '0x21e2C0AFd058A89FCf7caf3aEA3cB84Ae977B73D')
                        logger.info(f'授权HONEY交易发送成功: 0x{transaction.hex()}')
                        result = confirm_transaction(transaction)
                        if not result:
                            logger.error(f'授权HONEY交易确认失败: 0x{transaction.hex()}')
                            return
                        logger.success(f'授权HONEY交易确认成功: 0x{transaction.hex()}')
                        transaction = swap_honey(account, True, token_balance)
                        logger.info(f'HONEY TO BERA交易发送成功: 0x{transaction.hex()}')
                    else:
                        raise e
            else:
                if balance < Web3.to_wei(0.01, 'ether'):
                    logger.warning('BERA余额低于0.001，不进行BERA TO HONEY')
                    return
                logger.info("BERA TO HONEY")
                if balance <= Web3.to_wei(0.05, 'ether'):
                    random_value = 0.01
                elif balance <= Web3.to_wei(0.1, 'ether'):
                    random_value = random.uniform(0.01, 0.05)
                elif balance <= Web3.to_wei(0.5, 'ether'):
                    random_value = random.uniform(0.05, 0.25)
                else:
                    random_value = random.uniform(0.1, 0.3)
                random_value_ether = Web3.to_wei(random_value, 'ether')
                transaction = swap_honey(account, False, random_value_ether)
                logger.info(f'BERA TO HONEY交易发送成功: 0x{transaction.hex()}')
        except ContractLogicError as e:
            logger.error(f'合约调用失败: {e}')
            return
        except Exception as e:
            if repr(e).count("insufficient funds"):
                logger.error("资金不足，可能Gas过高")
                return
            raise e
        result = confirm_transaction(transaction)
        if result:
            logger.success(f'Swap交易确认成功: 0x{transaction.hex()}')
        else:
            logger.error(f'Swap交易确认失败: 0x{transaction.hex()}')


if __name__ == '__main__':
    gas_price_now = Web3.from_wei(BERA.eth.gas_price, 'gwei')
    base_logger = get_logger()
    base_logger.info("GasPrice: {}".format(gas_price_now))
    if gas_price_now < 250:
        Task(TASK_NAME, FILE_NAME, disable_task_proxy=True, is_delay=False).run()
    else:
        base_logger.error('GasPrice过高不进行Swap')
