"""
name: BERA_BendSupply
cron: 0 15 * * *
"""
import random

import web3
from web3 import Web3
from web3.exceptions import ContractLogicError

from common.task import QLTask, LOCAL
from common.util import get_logger, get_session, raise_error
from BeraBexSwap import HONEY_CONTRACT, confirm_transaction, BERA, approve, TOKEN_ABI, swap

TASK_NAME = 'BERA_BendSupply'
FILE_NAME = 'BeraWallet'

BEND_ADDRESS = Web3.to_checksum_address('0x30A3039675E5b5cbEA49d9a5eacbc11f9199B86D')

WETH_ADDRESS = Web3.to_checksum_address('0xE28AfD8c634946833e89ee3F122C06d7C537E8A8')
WBTC_ADDRESS = Web3.to_checksum_address('0x2577D24a26f8FA19c1058a8b0106E2c7303454a4')
WETH_CONTRACT = BERA.eth.contract(address=Web3.to_checksum_address(WETH_ADDRESS), abi=TOKEN_ABI)
WBTC_CONTRACT = BERA.eth.contract(address=Web3.to_checksum_address(WBTC_ADDRESS), abi=TOKEN_ABI)


def query_token(address):
    name = '查询Token'
    url = 'https://api.goldsky.com/api/public/project_clq1h5ct0g4a201x18tfte5iv/subgraphs/bgt-subgraph/v1000000/gn'
    payload = {"operationName": "GetTokenInformation", "variables": {"id": address.lower()},
               "query": "query GetTokenInformation($id: String) {\n  tokenInformation(id: $id) {\n    id\n    address\n    symbol\n    name\n    decimals\n    usdValue\n    beraValue\n    __typename\n  }\n}"}
    res = LOCAL.session.post(url, json=payload)
    if res.text.count('tokenInformation'):
        return res.json().get('data').get('tokenInformation')
    raise_error(name, res)


def supply(logger, account, contract, token_amount, code=18):
    if contract.address == WBTC_CONTRACT.address:
        code = 8
    logger.info(f"Supply {contract.address}")
    gas_price = int(BERA.eth.gas_price * 1.2)
    nonce = BERA.eth.get_transaction_count(account.address)
    data = f'0x617ba037{contract.address.replace("0x", "").zfill(64)}{Web3.to_hex(token_amount).replace("0x", "").zfill(64)}{account.address.replace("0x", "").zfill(64)}{Web3.to_hex(code).replace("0x", "").zfill(64)}'
    tx = {
        'from': account.address, 'to': BEND_ADDRESS, 'value': 0, 'nonce': nonce, 'gas': 2000000, 'data': data, 'maxFeePerGas': gas_price,
        'maxPriorityFeePerGas': gas_price, 'chainId': BERA.eth.chain_id
    }
    signed_tx = BERA.eth.account.sign_transaction(tx, account.key)
    transaction = BERA.eth.send_raw_transaction(signed_tx.raw_transaction)
    logger.info(f'Supply交易发送成功: 0x{transaction.hex()}')
    result = confirm_transaction(transaction)
    if not result:
        logger.error(f'Supply交易确认失败: 0x{transaction.hex()}')
    else:
        logger.success(f'Supply交易确认成功: 0x{transaction.hex()}')
    return result


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
        eth_balance = WETH_CONTRACT.functions.balanceOf(account.address).call()
        logger.info(f'WETH Balance: {Web3.from_wei(eth_balance, "ether")}')
        btc_balance = WBTC_CONTRACT.functions.balanceOf(account.address).call()
        logger.info(f'WBTC Balance: {Web3.from_wei(btc_balance, "gwei")}')
        try:
            if token_balance > 0:
                allowance_amount = HONEY_CONTRACT.functions.allowance(account.address, BEND_ADDRESS).call()
                if token_balance > allowance_amount and not approve(logger, account, HONEY_CONTRACT, BEND_ADDRESS):
                    return
                token_amount = int(token_balance / 2)
                supply(logger, account, HONEY_CONTRACT, token_amount)

            if eth_balance > 0 and btc_balance == 0:
                base_contract = WETH_CONTRACT
            elif btc_balance > 0 and eth_balance == 0:
                base_contract = WBTC_CONTRACT
            else:
                base_contract = random.choice([WETH_CONTRACT, WBTC_CONTRACT])
            base_balance = eth_balance if base_contract == WETH_CONTRACT else btc_balance
            base_decimals = 18 if base_contract == WETH_CONTRACT else 8

            LOCAL.session = get_session(proxy)
            LOCAL.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
            })
            token_info = query_token(base_contract.address)
            base_bera_value = float(token_info.get('beraValue'))

            if base_balance == 0:
                if balance <= Web3.to_wei(0.05, 'ether'):
                    random_value = 0.01
                elif balance <= Web3.to_wei(0.5, 'ether'):
                    random_value = random.uniform(0.05, 0.1)
                else:
                    random_value = random.uniform(0.08, 0.2)
                random_value_ether = Web3.to_wei(random_value, 'ether')
                if not swap(logger, account, False, random_value_ether, base_bera_value, base_contract.address, base_decimals):
                    return
                if base_contract == WETH_CONTRACT:
                    base_balance = base_contract.functions.balanceOf(account.address).call()
                    logger.info(f'WETH Balance: {Web3.from_wei(base_balance, "ether")}')
                else:
                    base_balance = base_contract.functions.balanceOf(account.address).call()
                    logger.info(f'WBTC Balance: {Web3.from_wei(base_balance, "gwei")}')

            if base_balance > 0:
                allowance_amount = base_contract.functions.allowance(account.address, BEND_ADDRESS).call()
                if base_balance > allowance_amount and not approve(logger, account, base_contract, BEND_ADDRESS):
                    return
                supply(logger, account, base_contract, base_balance)
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
        Task(TASK_NAME, FILE_NAME, use_ipv6=True).run()
    else:
        base_logger.error('GasPrice过高不进行Supply')
