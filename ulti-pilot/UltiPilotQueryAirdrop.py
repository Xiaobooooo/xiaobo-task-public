"""
cron: 1 1 1 1 1
new Env('UltiPilot_空投查询')
"""
from web3 import Web3

from common.task import QLTask
from common.util import LOCAL, get_session, write_txt
from UltiPilotExplore import login, up_raise_error

TASK_NAME = 'UltiPilot_空投查询'
FILE_NAME = 'UltiPilotAddress.txt'


def query_airdrop() -> int:
    name = '查询Soul'
    res = LOCAL.session.get(f'https://rewards.ultiverse.io/api/token?wallet={LOCAL.address}')
    if res.text.count('success') and res.json().get('success'):
        airdrop = 0
        for data in res.json().get('data'):
            for details in data.get('details'):
                airdrop += details.get('nftQuantities') + details.get('tokenQuantities')
        return airdrop
    up_raise_error(name, res)


class Task(QLTask):
    def task(self, index: int, datas: list, proxy: str, logger, next_datas: list) -> str or None:
        LOCAL.address = Web3.to_checksum_address(datas[0])
        LOCAL.private_key = datas[1]

        if not hasattr(LOCAL, 'session'):
            LOCAL.session = get_session()
        LOCAL.session.proxies = proxy
        LOCAL.session.headers.update({
            'Host': 'account-api.ultiverse.io',
            'ul-auth-api-key': 'YWktYWdlbnRAZFd4MGFYWmxjbk5s',
            'Origin': 'https://pilot.ultiverse.io',
            'Referer': 'https://pilot.ultiverse.io/'
        })
        if not hasattr(LOCAL, 'token'):
            LOCAL.token = login()
            logger.info(f'登录: 成功')
            LOCAL.session.headers.update({
                'Host': 'pml.ultiverse.io',
                'ul-auth-address': LOCAL.address,
                'ul-auth-token': LOCAL.token
            })

        airdrop = query_airdrop()
        logger.info(f'当前Airdrop: {airdrop}')
        if airdrop > 0:
            write_txt('UP_Airdrop.txt', f'{datas[0]}----{datas[1]}----{airdrop}\n', True)


if __name__ == '__main__':
    Task(TASK_NAME, FILE_NAME).run()
