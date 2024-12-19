"""
name: Hemi_Swap
cron: 0 10,20 * * *
"""
import os
import random
import time

import web3
from web3 import Web3, HTTPProvider
from web3.exceptions import ContractLogicError

from common.task import QLTask
from common.util import get_logger

TASK_NAME = 'Hemi_Swap'
FILE_NAME = 'HemiWallet.txt'

RPC_NAME = 'HEMI_RPC'
rpc = os.getenv(RPC_NAME)
if not rpc:
    get_logger().info(f"暂未设置熊链RPC环境变量[{RPC_NAME}]")
    rpc = "https://testnet.rpc.hemi.network/rpc"

HEMI = Web3(HTTPProvider(rpc))

CONTRACT_ADDRESS = Web3.to_checksum_address('0xA18019E62f266C2E17e33398448e4105324e0d0F')
ABI = [{"inputs": [{"internalType": "bytes", "name": "commands", "type": "bytes"},
                   {"internalType": "bytes[]", "name": "inputs", "type": "bytes[]"},
                   {"internalType": "uint256", "name": "deadline", "type": "uint256"}], "name": "execute", "outputs": [],
        "stateMutability": "payable", "type": "function"}]
CONTRACT = HEMI.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

TOKEN_CONTRACT_ADDRESS = Web3.to_checksum_address("0xec46E0EFB2EA8152da0327a5Eb3FF9a43956F13e")
TOKEN_ABI = [{"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf",
              "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"},
             {"inputs": [{"internalType": "address", "name": "spender", "type": "address"},
                         {"internalType": "uint256", "name": "value", "type": "uint256"}], "name": "approve",
              "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"}]
TOKEN_CONTRACT = HEMI.eth.contract(address=Web3.to_checksum_address(TOKEN_CONTRACT_ADDRESS), abi=TOKEN_ABI)


class Task(QLTask):
    def task(self, index: int, datas: list[str], proxy: str, logger):
        private_key = datas[1]
        account = web3.Account.from_key(private_key)
        gas_price = int(HEMI.eth.gas_price * 1.2)
        nonce = HEMI.eth.get_transaction_count(account.address)
        # balance = TOKEN_CONTRACT.functions.balanceOf(account.address).call()
        try:
            # if balance > Web3.to_wei(30_000, "ether"):
            #     hex_value = Web3.to_hex(balance)
            #     execute = CONTRACT.functions.execute("0x0a000c00", (
            #         f"0x0000000000000000000000000000000000000000000000000000000000000002{hex_value.zfill(64)}",
            #         f"0x0000000000000000000000000000000000000000000000000000000000000001{hex_value.zfill(64)}000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002b0c8afd1b58aa2a5bad2414b861d8a7ff898edc3a000bb8ec46e0efb2ea8152da0327a5eb3ff9a43956f13e000000000000000000000000000000000000000000"
            #     ), int(time.time() + 120))
            #     tx = execute.build_transaction(
            #         {'from': account.address, 'value': 0, 'gasPrice': gas_price, 'nonce': nonce}
            #     )
            # else:
            #     random_value = random.uniform(0.00001, 0.001)
            #     hex_value = Web3.to_hex(Web3.to_wei(random_value, "ether"))
            #     execute = CONTRACT.functions.execute("0x0b00", (
            #     Web3.to_bytes(text=f"0x0000000000000000000000000000000000000000000000000000000000000002{hex_value.zfill(64)}"),
            #     Web3.to_bytes(
            #         text=f"0x0000000000000000000000000000000000000000000000000000000000000001{hex_value.zfill(64)}000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002b0c8afd1b58aa2a5bad2414b861d8a7ff898edc3a000bb8ec46e0efb2ea8152da0327a5eb3ff9a43956f13e000000000000000000000000000000000000000000")),
            #                                          int(time.time() + 120))
            #     tx = execute.build_transaction(
            #         {'from': account.address, 'value': Web3.to_wei(random_value, 'ether'), 'gasPrice': gas_price, 'nonce': nonce}
            #     )
            execute = CONTRACT.functions.execute("0x0b00", (
                "0x000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000005af3107a4000",
                "0x000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000005af3107a4000000000000000000000000000000000000000000000000000457fd60a0614bb5400000000000000000000000000000000000000000000000000000000000000a00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002b0c8afd1b58aa2a5bad2414b861d8a7ff898edc3a000bb8ec46e0efb2ea8152da0327a5eb3ff9a43956f13e000000000000000000000000000000000000000000"
            ), int(time.time() + 120))
            tx = execute.build_transaction(
                {'from': account.address, 'value': Web3.to_wei(0.0001, 'ether'), 'gasPrice': gas_price, 'nonce': nonce}
            )
        except ContractLogicError as e:
            logger.error(f'Swap交易检测失败: {e}')
            return

        signed_tx = HEMI.eth.account.sign_transaction(tx, private_key)
        transaction = HEMI.eth.send_raw_transaction(signed_tx.raw_transaction)
        logger.success(f"Swap交易发送成功: 0x{transaction.hex()}")
        # receipt = HEMI.eth.get_transaction_receipt(transaction)
        # if receipt.get('status') == 0:
        #     logger.error(f'Swap交易确认失败: 0x{transaction.hex()}')
        # if receipt.get('status') == 1:
        #     logger.success(f'Swap交易确认成功: 0x{transaction.hex()}')


if __name__ == '__main__':
    Task(TASK_NAME, FILE_NAME, disable_task_proxy=True).run()
