"""
name: Hemi_CreateCapsule
cron: 0 12 * * 3,6
"""
import web3
from web3 import Web3
from web3.exceptions import ContractLogicError

from common.task import QLTask, LOCAL
from common.util import get_session, raise_error, get_random_str
from HemiSwap import HEMI

TASK_NAME = 'Hemi_CreateCapsule'
FILE_NAME = 'HemiWallet.txt'

CONTRACT_ADDRESS = Web3.to_checksum_address('0x1E8db2Fc15Bf1207784763219e00e98D0BA82362')
ABI = [{"stateMutability": "payable", "type": "function", "inputs": [
    {"name": "packageContent_", "internalType": "struct PostOfficeStorage.CapsuleContent", "type": "tuple",
     "components": [{"name": "tokenData", "internalType": "bytes[]", "type": "bytes[]"},
                    {"name": "tokenURI", "internalType": "string", "type": "string"}]},
    {"name": "securityInfo_", "internalType": "struct PostOfficeStorage.SecurityInfo", "type": "tuple",
     "components": [{"name": "passwordHash", "internalType": "bytes32", "type": "bytes32"},
                    {"name": "unlockTimestamp", "internalType": "uint64", "type": "uint64"},
                    {"name": "keyAddress", "internalType": "address", "type": "address"},
                    {"name": "keyId", "internalType": "uint256", "type": "uint256"}]},
    {"name": "receiver_", "internalType": "address", "type": "address"}], "name": "shipPackage",
        "outputs": [{"name": "", "internalType": "uint256", "type": "uint256"}]}]
CONTRACT = HEMI.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)


def get_token_url():
    name = "获取TokenUrl"
    res = LOCAL.session.post("https://app.capsulelabs.xyz/api/create-metadata", json={"name": get_random_str()})
    if res.text.count('tokenURI'):
        return res.json().get('tokenURI')
    raise_error(name, res)


class Task(QLTask):
    def task(self, index: int, datas: list[str], proxy: str, logger):
        private_key = datas[1]
        LOCAL.session = get_session(proxy)

        token_url = get_token_url()
        account = web3.Account.from_key(private_key)
        gas_price = HEMI.eth.gas_price
        nonce = HEMI.eth.get_transaction_count(account.address)
        try:
            execute = CONTRACT.functions.shipPackage([[], token_url],
                                                     ["0x0000000000000000000000000000000000000000000000000000000000000000", 0,
                                                      Web3.to_checksum_address("0x0000000000000000000000000000000000000000"), 0],
                                                     account.address)
            tx = execute.build_transaction(
                {'from': account.address, 'value': Web3.to_wei(0.001, 'ether'), 'gasPrice': int(gas_price * 1.1), 'nonce': nonce}
            )
        except ContractLogicError as e:
            logger.error(f'Create交易检测失败: {e}')
            return
        signed_tx = HEMI.eth.account.sign_transaction(tx, private_key)
        transaction = HEMI.eth.send_raw_transaction(signed_tx.raw_transaction)
        logger.success(f"Create交易发送成功: 0x{transaction.hex()}")
        # receipt = HEMI.eth.get_transaction_receipt(transaction)
        # if receipt.get('status') == 0:
        #     logger.error(f'Create交易确认失败: 0x{transaction.hex()}')
        # if receipt.get('status') == 1:
        #     logger.success(f'Create交易确认成功: 0x{transaction.hex()}')


if __name__ == '__main__':
    Task(TASK_NAME, FILE_NAME).run()
