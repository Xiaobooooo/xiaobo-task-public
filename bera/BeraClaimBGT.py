"""
name: BERA_ClaimBGT
cron: 0 18 1/3 * *
"""
import web3
from web3 import Web3
from web3.exceptions import ContractLogicError

from common.task import QLTask
from BeraBexSwap import BERA, TOKEN_ABI, confirm_transaction

TASK_NAME = 'BERA_ClaimBGT'
FILE_NAME = 'BeraWallet'

BGT_CLAIM1_ADDRESS = Web3.to_checksum_address('0x2E8410239bB4b099EE2d5683e3EF9d6f04E321CC')
BGT_CLAIM2_ADDRESS = Web3.to_checksum_address('0xAD57d7d39a487C04a44D3522b910421888Fb9C6d')
BGT_CLAIM_ABI = [{"type": "function", "name": "getReward", "inputs": [{"name": "account", "type": "address", "internalType": "address"}],
                  "outputs": [{"name": "", "type": "uint256", "internalType": "uint256"}], "stateMutability": "nonpayable"}]
BGT_CLAIM1_CONTRACT = BERA.eth.contract(address=Web3.to_checksum_address(BGT_CLAIM1_ADDRESS), abi=BGT_CLAIM_ABI)
BGT_CLAIM2_CONTRACT = BERA.eth.contract(address=Web3.to_checksum_address(BGT_CLAIM2_ADDRESS), abi=BGT_CLAIM_ABI)

BGT_ADDRESS = Web3.to_checksum_address('0xbDa130737BDd9618301681329bF2e46A016ff9Ad')
BGT_CONTRACT = BERA.eth.contract(address=Web3.to_checksum_address(BGT_ADDRESS), abi=TOKEN_ABI)


class Task(QLTask):
    def task(self, index: int, datas: list[str], proxy: str, logger):
        if len(datas) < 2:
            logger.warning('不存在私钥，不进行Supply')
            return
        private_key = datas[1]
        account = web3.Account.from_key(private_key)
        for contract in [BGT_CLAIM1_CONTRACT, BGT_CLAIM2_CONTRACT]:
            try:
                gas_price = int(BERA.eth.gas_price * 1.2)
                nonce = BERA.eth.get_transaction_count(account.address)
                method = contract.functions.getReward(account.address)
                tx = method.build_transaction(
                    {'from': account.address, 'value': 0, 'gasPrice': gas_price, 'nonce': nonce, 'gas': 2000000}
                )
                signed_tx = BERA.eth.account.sign_transaction(tx, account.key)
                transaction = BERA.eth.send_raw_transaction(signed_tx.raw_transaction)
                logger.info(f'Claim交易发送成功: 0x{transaction.hex()}')
                result = confirm_transaction(transaction)
                if not result:
                    logger.error(f'Claim交易确认失败: 0x{transaction.hex()}')
                else:
                    logger.success(f'Claim交易确认成功: 0x{transaction.hex()}')
            except ContractLogicError as e:
                logger.error(f'合约调用失败: {e}')
                return
            except Exception as e:
                if repr(e).count("insufficient funds"):
                    logger.error("资金不足，可能Gas过高")
                    return
                raise e


if __name__ == '__main__':
    Task(TASK_NAME, FILE_NAME, disable_task_proxy=True).run()
