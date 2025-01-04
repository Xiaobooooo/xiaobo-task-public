"""
name: Hemi_Swap
cron: 0 10,20 * * *
"""
import os
import random
import time

import web3
from eth_account.messages import encode_typed_data
from web3 import Web3, HTTPProvider
from web3.exceptions import ContractLogicError

from common.task import QLTask
from common.util import get_logger

TASK_NAME = 'Hemi_Swap'
FILE_NAME = 'HemiWallet.txt'

RPC_NAME = 'HEMI_RPC'
rpc = os.getenv(RPC_NAME)
if not rpc:
    get_logger().info(f"暂未设置Hemi链RPC环境变量[{RPC_NAME}]")
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

WETH_ADDRESS = Web3.to_checksum_address("0x0C8aFD1b58aa2A5bAd2414B861D8A7fF898eDC3A")


class Task(QLTask):
    def task(self, index: int, datas: list[str], proxy: str, logger):
        private_key = datas[1]
        account = web3.Account.from_key(private_key)
        gas_price = int(HEMI.eth.gas_price * 1.5)
        nonce = HEMI.eth.get_transaction_count(account.address)

        balance = HEMI.eth.get_balance(account.address)
        logger.info(f'ETH Balance: {Web3.from_wei(balance, "ether")}')
        if balance < Web3.to_wei(0.005, 'ether'):
            logger.warning('ETH余额低于0.005，不进行Swap')
            return
        token_balance = TOKEN_CONTRACT.functions.balanceOf(account.address).call()
        logger.info(f'HDAI Balance: {Web3.from_wei(token_balance, "ether")}')
        try:
            if token_balance > Web3.to_wei(50000, "ether"):
                logger.info("HDAI TO ETH")
                hex_value = Web3.to_hex(token_balance).replace('0x', '')
                timestamp = int(time.time() + 60 * 60 * 24 * 365)
                sig_deadline = int(time.time() + 60 * 60 * 24 * 180)
                sign_nonce = random.randint(6666, 888888888)
                message = encode_typed_data(full_message={"types": {
                    "PermitSingle": [{"name": "details", "type": "PermitDetails"}, {"name": "spender", "type": "address"},
                                     {"name": "sigDeadline", "type": "uint256"}],
                    "PermitDetails": [{"name": "token", "type": "address"}, {"name": "amount", "type": "uint160"},
                                      {"name": "expiration", "type": "uint48"}, {"name": "nonce", "type": "uint48"}],
                    "EIP712Domain": [{"name": "name", "type": "string"}, {"name": "chainId", "type": "uint256"},
                                     {"name": "verifyingContract", "type": "address"}]},
                    "domain": {"name": "Permit2", "chainId": "743111",
                               "verifyingContract": "0xb952578f3520ee8ea45b7914994dcf4702cee578"},
                    "primaryType": "PermitSingle", "message": {
                        "details": {"token": "0xec46e0efb2ea8152da0327a5eb3ff9a43956f13e",
                                    "amount": "1461501637330902918203684832716283019655932542975", "expiration": timestamp,
                                    "nonce": sign_nonce}, "spender": "0xa18019e62f266c2e17e33398448e4105324e0d0f",
                        "sigDeadline": sig_deadline}})
                signature = HEMI.eth.account.sign_message(message, private_key)
                bytes_1 = f"0x{TOKEN_CONTRACT_ADDRESS.lower().replace('0x', '').zfill(64)}000000000000000000000000ffffffffffffffffffffffffffffffffffffffff{Web3.to_hex(timestamp).replace('0x', '').zfill(64)}{Web3.to_hex(sign_nonce).replace('0x', '').zfill(64)}000000000000000000000000a18019e62f266c2e17e33398448e4105324e0d0f{Web3.to_hex(sig_deadline).replace('0x', '').zfill(64)}00000000000000000000000000000000000000000000000000000000000000e00000000000000000000000000000000000000000000000000000000000000041{signature.signature.hex()}00000000000000000000000000000000000000000000000000000000000000"
                bytes_2 = f"0x0000000000000000000000000000000000000000000000000000000000000002{hex_value.zfill(64)}{'0'.zfill(64)}00000000000000000000000000000000000000000000000000000000000000a00000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000002b{TOKEN_CONTRACT_ADDRESS.lower().replace('0x', '')}002710{WETH_ADDRESS.lower().replace('0x', '')}000000000000000000000000000000000000000000"
                bytes_3 = f"0x0000000000000000000000000000000000000000000000000000000000000001{'0'.zfill(64)}"
                execute = CONTRACT.functions.execute("0x0a000c", (bytes_1, bytes_2, bytes_3), int(time.time() + 600))
                try:
                    tx = execute.build_transaction(
                        {'from': account.address, 'value': 0, 'gasPrice': gas_price, 'nonce': nonce}
                    )
                except ContractLogicError as e:
                    if repr(e).count("TRANSFER_FROM_FAILED"):
                        logger.info("授权HDAI")
                        approve = TOKEN_CONTRACT.functions.approve(Web3.to_checksum_address('0xb952578f3520ee8ea45b7914994dcf4702cee578'),
                                                                   Web3.to_wei(999999999999999999999999999999999999999, 'ether'))
                        tx = approve.build_transaction(
                            {'from': account.address, 'value': 0, 'gasPrice': gas_price, 'nonce': nonce}
                        )
                    elif repr(e).count("0x756688fe") or repr(e).count("0x815e1d64"):
                        bytes_1 = f"0x0000000000000000000000000000000000000000000000000000000000000002{hex_value.zfill(64)}{'0'.zfill(64)}00000000000000000000000000000000000000000000000000000000000000a00000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000002b{TOKEN_CONTRACT_ADDRESS.lower().replace('0x', '')}000bb8{WETH_ADDRESS.lower().replace('0x', '')}000000000000000000000000000000000000000000"
                        bytes_2 = f"0x0000000000000000000000000000000000000000000000000000000000000001{'0'.zfill(64)}"
                        execute = CONTRACT.functions.execute("0x000c", (bytes_1, bytes_2), int(time.time() + 600))
                        tx = execute.build_transaction(
                            {'from': account.address, 'value': 0, 'gasPrice': gas_price, 'nonce': nonce}
                        )
                    else:
                        raise e
            else:
                logger.info("ETH TO HDAI")
                if balance <= Web3.to_wei(0.005, 'ether'):
                    random_value = random.uniform(0.0001, 0.001)
                elif balance <= Web3.to_wei(0.01, 'ether'):
                    random_value = random.uniform(0.001, 0.005)
                elif balance <= Web3.to_wei(0.05, 'ether'):
                    random_value = random.uniform(0.005, 0.02)
                elif balance <= Web3.to_wei(0.1, 'ether'):
                    random_value = random.uniform(0.01, 0.03)
                else:
                    random_value = random.uniform(0.01, 0.05)
                hex_value = Web3.to_hex(Web3.to_wei(random_value, "ether")).replace('0x', '')
                bytes_1 = f"0x0000000000000000000000000000000000000000000000000000000000000002{hex_value.zfill(64)}"
                bytes_2 = f"0x0000000000000000000000000000000000000000000000000000000000000001{hex_value.zfill(64)}{'0'.zfill(64)}00000000000000000000000000000000000000000000000000000000000000a00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002b{WETH_ADDRESS.lower().replace('0x', '')}000bb8{TOKEN_CONTRACT_ADDRESS.lower().replace('0x', '')}000000000000000000000000000000000000000000"
                execute = CONTRACT.functions.execute("0x0b00", (bytes_1, bytes_2), int(time.time() + 600))
                tx = execute.build_transaction(
                    {'from': account.address, 'value': Web3.to_wei(random_value, 'ether'), 'nonce': nonce, 'gasPrice': gas_price}
                )
        except ContractLogicError as e:
            logger.error(f'Swap交易检测失败: {e}')
            return
        tx['gas'] = int(HEMI.eth.estimate_gas(tx) * 1.3)
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
