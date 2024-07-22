"""
cron: 0 10 * * *
new Env('MetaMask_Mint')
"""
from common.task import QLTask
from common.util import LOCAL, raise_error, get_session, write_txt

TASK_NAME = 'MetaMask_Mint'
FILE_NAME = 'MetaMaskWallet.txt'


def task() -> str:
    name = 'MINT'
    url = 'https://public-api.phosphor.xyz/v1/purchase-intents'
    payload = {"buyer": {"eth_address": LOCAL.username}, "listing_id": "dd63cae2-8a51-4bc6-a4e0-bf1c82367593",
               "provider": "ORGANIZATION", "quantity": 1}
    res = LOCAL.session.post(url, json=payload)
    if res.text.count('Your items will be minted to your eth address'):
        write_txt('MetaMaskMint成功', LOCAL.username, True)
        return f'{name}: 成功'
    raise_error(name, res)


class Task(QLTask):
    def task(self, index: int, datas: list, proxy: str, logger, next_datas: list) -> str or None:
        LOCAL.username = datas[0]

        if not hasattr(LOCAL, 'session'):
            LOCAL.session = get_session()
        LOCAL.session.proxies = proxy
        result = task()
        logger.info(result)


if __name__ == '__main__':
    Task(TASK_NAME, FILE_NAME).run()
