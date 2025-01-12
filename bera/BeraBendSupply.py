"""
name: BERA_BendSupply
cron: 0 12,22 * * *
"""
import web3
from web3 import Web3
from web3.exceptions import ContractLogicError

from common.task import QLTask
from common.util import get_logger
from BeraBexSwap import HONEY_CONTRACT, confirm_transaction, BERA, approve

TASK_NAME = 'BERA_BexSwap'
FILE_NAME = 'BeraWallet'

BEND_ADDRESS = Web3.to_checksum_address('0x30A3039675E5b5cbEA49d9a5eacbc11f9199B86D')


class Task(QLTask):
    def task(self, index: int, datas: list[str], proxy: str, logger):
        if len(datas) < 2:
            logger.warning('不存在私钥，不进行Supply')
            return
        private_key = datas[1]
        account = web3.Account.from_key(private_key)
        balance = BERA.eth.get_balance(account.address)
        logger.info(f'BERA Balance: {Web3.from_wei(balance, "ether")}')
        if balance < Web3.to_wei(0.005, 'ether'):
            logger.warning('BERA余额低于0.005，不进行Supply')
            return
        token_balance = HONEY_CONTRACT.functions.balanceOf(account.address).call()
        logger.info(f'HONEY Balance: {Web3.from_wei(token_balance, "ether")}')
        if token_balance == 0:
            logger.warning('无HONEY余额，不进行Supply')
            return
        try:
            allowance_amount = HONEY_CONTRACT.functions.allowance(account.address, BEND_ADDRESS).call()
            if token_balance > allowance_amount and not approve(logger, account, HONEY_CONTRACT, BEND_ADDRESS):
                return
            logger.info(f"Supply HONEY")
            gas_price = int(BERA.eth.gas_price * 1.2)
            nonce = BERA.eth.get_transaction_count(account.address)
            token_amount = int(token_balance / 2)
            data = f'0x617ba037{HONEY_CONTRACT.address.replace("0x", "").zfill(64)}{Web3.to_hex(token_amount).replace("0x", "").zfill(64)}{account.address.replace("0x", "").zfill(64)}0000000000000000000000000000000000000000000000000000000000000012'
            tx = {
                'from': account.address, 'to': BEND_ADDRESS, 'value': 0, 'nonce': nonce, 'gas': 2000000, 'data': data,
                'maxFeePerGas': gas_price, 'maxPriorityFeePerGas': gas_price, 'chainId': BERA.eth.chain_id
            }
            signed_tx = BERA.eth.account.sign_transaction(tx, account.key)
            transaction = BERA.eth.send_raw_transaction(signed_tx.raw_transaction)
            logger.info(f'Supply HONEY交易发送成功: 0x{transaction.hex()}')
            result = confirm_transaction(transaction)
            if not result:
                logger.error(f'Supply HONEY交易确认失败: 0x{transaction.hex()}')
            else:
                logger.success(f'Supply HONEY交易确认成功: 0x{transaction.hex()}')
        except ContractLogicError as e:
            logger.error(f'合约调用失败: {e}')
            return
        except Exception as e:
            if repr(e).count("insufficient funds"):
                logger.error("资金不足，可能Gas过高")
                return
            raise e


if __name__ == '__main__':
    gas_price_now = Web3.from_wei(BERA.eth.gas_price, 'gwei')
    base_logger = get_logger()
    base_logger.info("GasPrice: {}".format(gas_price_now))
    if gas_price_now < 250:
        Task(TASK_NAME, FILE_NAME, disable_task_proxy=True).run()
    else:
        base_logger.error('GasPrice过高不进行Swap')
