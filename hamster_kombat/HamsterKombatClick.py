"""
cron: 0/10 * * * *
new Env('仓鼠快打_点击')
"""
import random
import time

from requests import Response

from common.task import QLTask
from common.util import LOCAL, raise_error, get_session

TASK_NAME = '仓鼠快打_点击'
FILE_NAME = 'HamsterKombatToken.txt'


def hk_raise_error(name: str, res: Response, **kwargs):
    raise_error(name, res, msg_key='error_code', **kwargs)


def sync():
    name = '同步信息'
    res = LOCAL.session.post('https://api.hamsterkombatgame.io/clicker/sync')
    if res.text.count('clickerUser'):
        return res.json().get('clickerUser')
    hk_raise_error(name, res)


def click(available_taps: int) -> str:
    name = '点击'
    url = 'https://api.hamsterkombatgame.io/clicker/tap'
    count = available_taps - random.randint(int(available_taps / 2), available_taps)
    payload = {"count": count, "availableTaps": available_taps, "timestamp": int(time.time())}
    res = LOCAL.session.post(url, json=payload)
    if res.text.count('clickerUser'):
        return f'{name}: 成功 - 余额: {res.json().get("clickerUser").get("balanceCoins")}'
    raise_error(name, res)


def buy_boost(boost_id: str) -> str:
    name = '升级最大分数'
    url = 'https://api.hamsterkombatgame.io/clicker/buy-boost'
    payload = {"boostId": boost_id, "timestamp": int(time.time())}
    res = LOCAL.session.post(url, json=payload)
    if res.text.count('clickerUser'):
        return f'{name}: 成功'
    if res.text.count('INSUFFICIENT_FUNDS'):
        return f'{name}: 余额不足'
    raise_error(name, res)


class Task(QLTask):
    def task(self, index: int, datas: list, proxy: str, logger, next_datas: list) -> str or None:
        LOCAL.id = datas[0]
        LOCAL.token = datas[1]

        if not hasattr(LOCAL, 'session'):
            LOCAL.session = get_session()
        LOCAL.session.proxies = proxy
        LOCAL.session.headers.update({
            'Host': 'api.hamsterkombatgame.io',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Origin': 'https://hamsterkombatgame.io',
            'Authorization': f'Bearer {LOCAL.token}'
        })

        info = sync()
        available_taps = info.get('availableTaps')
        result = click(available_taps)
        logger.success(result)


if __name__ == '__main__':
    Task(TASK_NAME, FILE_NAME).run()
