"""
name: BERA_BexSwap
cron: 0 10,20 * * *
"""
import math
import os
import random

import web3
from eth_abi import encode
from web3 import Web3, HTTPProvider
from web3.exceptions import ContractLogicError, TransactionNotFound

from common.task import QLTask, LOCAL
from common.util import get_logger, get_session, raise_error

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

BEX_POOL_ADDRESS = Web3.to_checksum_address('0xAB827b1Cc3535A9e549EE387A6E9C3F02F481B49')
BEX_POOL_ABI = [{"inputs": [{"internalType": "uint16", "name": "callpath", "type": "uint16"},
                            {"internalType": "bytes", "name": "cmd", "type": "bytes"}], "name": "userCmd",
                 "outputs": [{"internalType": "bytes", "name": "", "type": "bytes"}], "stateMutability": "payable", "type": "function"}]
BEX_POOL_CONTRACT = BERA.eth.contract(address=BEX_POOL_ADDRESS, abi=BEX_POOL_ABI)

TOKEN_ABI = [{"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf",
              "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"},
             {"inputs": [{"internalType": "address", "name": "spender", "type": "address"},
                         {"internalType": "uint256", "name": "value", "type": "uint256"}], "name": "approve",
              "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
             {"inputs": [{"internalType": "address", "name": "owner", "type": "address"},
                         {"internalType": "address", "name": "spender", "type": "address"}], "name": "allowance",
              "outputs": [{"internalType": "uint256", "name": "result", "type": "uint256"}], "stateMutability": "view",
              "type": "function"}]

HONEY_ADDRESS = Web3.to_checksum_address("0x0E4aaF1351de4c0264C5c7056Ef3777b41BD8e03")
HONEY_CONTRACT = BERA.eth.contract(address=Web3.to_checksum_address(HONEY_ADDRESS), abi=TOKEN_ABI)

HONEY_WBERA_LP_ADDRESS = Web3.to_checksum_address("0xd28d852cbcc68dcec922f6d5c7a8185dbaa104b7")
HONEY_WBERA_LP_CONTRACT = BERA.eth.contract(address=Web3.to_checksum_address(HONEY_WBERA_LP_ADDRESS), abi=TOKEN_ABI)

LP_DEPOSIT_ADDRESS = Web3.to_checksum_address("0xAD57d7d39a487C04a44D3522b910421888Fb9C6d")


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


def approve(logger, account, contract, spender):
    logger.info(f"授权{contract.address} TO {spender}")
    method = contract.functions.approve(Web3.to_checksum_address(spender),
                                        57896044618658097711785492504343953926634992332820282019728792003956564819967)
    gas_price = int(BERA.eth.gas_price * 1.2)
    nonce = BERA.eth.get_transaction_count(account.address)
    tx = method.build_transaction(
        {'from': account.address, 'value': 0, 'gasPrice': gas_price, 'nonce': nonce, 'gas': 2000000}
    )
    signed_tx = BERA.eth.account.sign_transaction(tx, account.key)
    transaction = BERA.eth.send_raw_transaction(signed_tx.raw_transaction)
    logger.info(f'授权交易发送成功: 0x{transaction.hex()}')
    result = confirm_transaction(transaction)
    if not result:
        logger.error(f'授权交易确认失败: 0x{transaction.hex()}')
    else:
        logger.success(f'授权交易确认成功: 0x{transaction.hex()}')
    return result


def swap_honey(logger, account, is_buy, value, base_bera_value):
    if is_buy:
        info = "HONEY TO BERA"
        receive = int(value * base_bera_value * 0.9)
    else:
        info = "BERA TO HONEY"
        receive = int(value / base_bera_value * 0.9)

    logger.info(info)
    params = {
        'poolIdx': 36000,
        'base': HONEY_ADDRESS,
        'quote': '0x0000000000000000000000000000000000000000',
        'isBuy': is_buy,
    }
    method = BEX_SWAP_CONTRACT.functions.multiSwap([params], value, receive)
    gas_price = int(BERA.eth.gas_price * 1.2)
    nonce = BERA.eth.get_transaction_count(account.address)
    tx = method.build_transaction(
        {'from': account.address, 'value': 0 if is_buy else value, 'gasPrice': gas_price, 'nonce': nonce, 'gas': 2000000}
    )
    tx['gas'] = int(BERA.eth.estimate_gas(tx) * 1.1)
    signed_tx = BERA.eth.account.sign_transaction(tx, account.key)
    transaction = BERA.eth.send_raw_transaction(signed_tx.raw_transaction)
    logger.info(f'{info}交易发送成功: 0x{transaction.hex()}')
    result = confirm_transaction(transaction)
    if not result:
        logger.error(f'{info}交易确认失败: 0x{transaction.hex()}')
    else:
        logger.success(f'{info}交易确认成功: 0x{transaction.hex()}')
    return result


def query_pool():
    name = '查询Pool'
    url = 'https://api.goldsky.com/api/public/project_clq1h5ct0g4a201x18tfte5iv/subgraphs/bgt-subgraph/v1000000/gn'
    payload = {"operationName": "GetPoolList", "variables": {"shareAddress": "0xd28d852cbcc68dcec922f6d5c7a8185dbaa104b7"},
               "query": "query GetPoolList($shareAddress: String) {\n  pools(where: {shareAddress_: {address_contains: $shareAddress}}) {\n    id\n    poolIdx\n    base\n    quote\n    timeCreate\n    tvlUsd\n    baseAmount\n    quoteAmount\n    bgtApy\n    template {\n      feeRate\n      __typename\n    }\n    baseInfo {\n      id\n      address\n      symbol\n      name\n      decimals\n      usdValue\n      beraValue\n      __typename\n    }\n    quoteInfo {\n      id\n      address\n      symbol\n      name\n      decimals\n      usdValue\n      beraValue\n      __typename\n    }\n    shareAddress {\n      address\n      __typename\n    }\n    latestPoolDayData {\n      tvlUsd\n      feesUsd\n      volumeUsd\n      __typename\n    }\n    vault {\n      id\n      vaultAddress\n      __typename\n    }\n    __typename\n  }\n}"}
    res = LOCAL.session.post(url, json=payload)
    if res.text.count('pools'):
        return res.json().get('data').get('pools')[0]
    raise_error(name, res)


def d(e):
    # 计算初始 t 值
    t = 18446744073709552e3 * math.sqrt(e)
    n = 0
    # 当 t 超过最大安全整数时，进行缩减
    while t > 9007199254740991:  # Number.MAX_SAFE_INTEGER 在 Python 中是 2**53 - 1
        t /= 65536
        n += 16
    # 取整
    i = round(t)
    # 计算结果
    return i * 2 ** n


class Task(QLTask):
    def task(self, index: int, datas: list[str], proxy: str, logger):
        if len(datas) < 2:
            logger.warning('不存在私钥，不进行Swap')
            return
        private_key = datas[1]

        LOCAL.session = get_session(proxy)
        LOCAL.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        })
        pool = query_pool()
        base_bera_value = float(pool.get('baseInfo').get('beraValue'))
        quote_usd_value = float(pool.get('quoteInfo').get('usdValue'))

        account = web3.Account.from_key(private_key)
        balance = BERA.eth.get_balance(account.address)
        logger.info(f'BERA Balance: {Web3.from_wei(balance, "ether")}')
        if balance < Web3.to_wei(0.005, 'ether'):
            logger.warning('BERA余额低于0.005，不进行Swap')
            return
        token_balance = HONEY_CONTRACT.functions.balanceOf(account.address).call()
        logger.info(f'HONEY Balance: {Web3.from_wei(token_balance, "ether")}')
        is_buy = token_balance > Web3.to_wei(2, "ether")
        try:
            if is_buy:
                allowance_amount = HONEY_CONTRACT.functions.allowance(account.address, BEX_SWAP_ADDRESS).call()
                if token_balance > allowance_amount and not approve(logger, account, HONEY_CONTRACT, BEX_SWAP_ADDRESS):
                    return
                swap_honey(logger, account, is_buy, token_balance, base_bera_value)
            else:
                if balance < Web3.to_wei(0.01, 'ether'):
                    logger.warning('BERA余额低于0.001，不进行BERA TO HONEY')
                    return
                if balance <= Web3.to_wei(0.05, 'ether'):
                    random_value = 0.01
                elif balance <= Web3.to_wei(0.1, 'ether'):
                    random_value = random.uniform(0.01, 0.05)
                elif balance <= Web3.to_wei(0.5, 'ether'):
                    random_value = random.uniform(0.05, 0.25)
                else:
                    random_value = random.uniform(0.1, 0.3)
                random_value_ether = Web3.to_wei(random_value, 'ether')

                if swap_honey(logger, account, is_buy, random_value_ether, base_bera_value):
                    balance = BERA.eth.get_balance(account.address)
                    logger.info(f'BERA Balance: {Web3.from_wei(balance, "ether")}')
                    token_balance = HONEY_CONTRACT.functions.balanceOf(account.address).call()
                    logger.info(f'HONEY Balance: {Web3.from_wei(token_balance, "ether")}')
                    lp_balance = HONEY_WBERA_LP_CONTRACT.functions.balanceOf(account.address).call()
                    logger.info(f'LP Balance: {Web3.from_wei(lp_balance, "ether")}')
                    if lp_balance > 0 and random.randint(1, 5) != 3:
                        return
                    allowance_amount = HONEY_CONTRACT.functions.allowance(account.address, BEX_POOL_ADDRESS).call()
                    if token_balance > allowance_amount and not approve(logger, account, HONEY_CONTRACT, BEX_POOL_ADDRESS):
                        return
                    logger.info(f"添加流动性HONEY_WBERA")
                    bera_value_ether = int(token_balance * base_bera_value / 2)
                    if bera_value_ether >= balance:
                        bera_value_ether = int(balance / 2)
                    min_value = d(quote_usd_value * (1 - (0.75 / 100)))
                    max_value = d(quote_usd_value * (1 + (0.75 / 100)))
                    types = ["uint8", "address", "address", "uint24", "int24", "int24", "uint128", "uint128", "uint128", "uint8",
                             "address"]
                    params = [32, HONEY_ADDRESS, "0x0000000000000000000000000000000000000000", 36000, 0, 0, bera_value_ether, min_value,
                              max_value, 0, HONEY_WBERA_LP_ADDRESS]
                    method = BEX_POOL_CONTRACT.functions.userCmd(128, encode(types, params))
                    gas_price = int(BERA.eth.gas_price * 1.2)
                    nonce = BERA.eth.get_transaction_count(account.address)
                    tx = method.build_transaction(
                        {'from': account.address, 'value': bera_value_ether, 'gasPrice': gas_price, 'nonce': nonce, 'gas': 2000000}
                    )
                    signed_tx = BERA.eth.account.sign_transaction(tx, account.key)
                    transaction = BERA.eth.send_raw_transaction(signed_tx.raw_transaction)
                    logger.info(f'添加流动性交易发送成功: 0x{transaction.hex()}')
                    result = confirm_transaction(transaction)
                    if not result:
                        logger.error(f'添加流动性交易确认失败: 0x{transaction.hex()}')
                    else:
                        logger.success(f'添加流动性交易确认成功: 0x{transaction.hex()}')
                    lp_balance = HONEY_WBERA_LP_CONTRACT.functions.balanceOf(account.address).call()
                    logger.info(f'LP Balance: {Web3.from_wei(lp_balance, "ether")}')
                    if lp_balance > 0:
                        allowance_amount = HONEY_WBERA_LP_CONTRACT.functions.allowance(account.address, LP_DEPOSIT_ADDRESS).call()
                        if lp_balance > allowance_amount and not approve(logger, account, HONEY_WBERA_LP_CONTRACT, LP_DEPOSIT_ADDRESS):
                            return
                        logger.info(f"质押HONEY_WBERA流动性")
                        gas_price = int(BERA.eth.gas_price * 1.2)
                        nonce = BERA.eth.get_transaction_count(account.address)
                        tx = {
                            'from': account.address, 'to': LP_DEPOSIT_ADDRESS, 'value': 0, 'nonce': nonce, 'gas': 2000000,
                            'data': f'0xa694fc3a{Web3.to_hex(lp_balance).replace("0x", "").zfill(64)}',
                            'maxFeePerGas': gas_price, 'maxPriorityFeePerGas': gas_price, 'chainId': BERA.eth.chain_id
                        }
                        signed_tx = BERA.eth.account.sign_transaction(tx, account.key)
                        transaction = BERA.eth.send_raw_transaction(signed_tx.raw_transaction)
                        logger.info(f'质押流动性交易发送成功: 0x{transaction.hex()}')
                        result = confirm_transaction(transaction)
                        if not result:
                            logger.error(f'质押流动性交易确认失败: 0x{transaction.hex()}')
                        else:
                            logger.success(f'质押流动性交易确认成功: 0x{transaction.hex()}')
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
        base_logger.error('GasPrice过高不进行Swap')
