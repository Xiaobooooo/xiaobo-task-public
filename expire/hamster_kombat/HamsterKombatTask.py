"""
cron: 0 10,22 * * *
new Env('仓鼠快打_任务')
"""
import random
import time

from common.task import QLTask
from common.util import LOCAL, get_session, get_env, log
from HamsterKombatClick import hk_raise_error

TASK_NAME = '仓鼠快打_任务'
FILE_NAME = 'HamsterKombatToken.txt'

UPGRADE_MAX_LEVEL_NAME = 'HK_UPGRADE_MAX_LEVEL'
upgrade_max_level = get_env(UPGRADE_MAX_LEVEL_NAME)
if not upgrade_max_level:
    log.info(f"暂未设置仓鼠快打最大升级变量[{UPGRADE_MAX_LEVEL_NAME}]，设置默认等级5")
    upgrade_max_level = 6
else:
    upgrade_max_level = int(upgrade_max_level) + 1


def query_task():
    name = f'查询任务'
    res = LOCAL.session.post('https://api.hamsterkombatgame.io/clicker/list-tasks')
    if res.text.count('tasks'):
        return res.json().get('tasks')
    hk_raise_error(name, res)


def completed_task(task_id: str):
    name = f'完成任务[{task_id}]'
    res = LOCAL.session.post('https://api.hamsterkombatgame.io/clicker/check-task', json={"taskId": task_id})
    if res.text.count('clickerUser'):
        return f"{name}: {'成功' if res.json().get('task').get('isCompleted') else '失败'}"
    hk_raise_error(name, res)


def query_upgrades():
    name = f'查询升级'
    res = LOCAL.session.post('https://api.hamsterkombatgame.io/clicker/upgrades-for-buy')
    if res.text.count('upgradesForBuy'):
        return res.json().get('upgradesForBuy')
    hk_raise_error(name, res)


def buy_upgrade(upgrade_id: str):
    name = f'升级[{upgrade_id}]'
    payload = {"upgradeId": upgrade_id, "timestamp": int(time.time() * 1000)}
    res = LOCAL.session.post('https://api.hamsterkombatgame.io/clicker/buy-upgrade', json=payload)
    if res.text.count('clickerUser'):
        return f"{name}: 成功"
    if res.text.count('UPGRADE_NOT_AVAILABLE'):
        return f"{name}: 前置条件不足"
    if res.text.count('UPGRADE_COOLDOWN'):
        return f"{name}: 升级冷却中"
    if res.text.count('INSUFFICIENT_FUNDS'):
        return f"{name}: 余额不足"
    hk_raise_error(name, res)


def select_exchange(exchange_id: str = "hamster"):
    name = '选择交易所'
    payload = {"exchangeId": exchange_id}
    res = LOCAL.session.post('https://api.hamsterkombatgame.io/clicker/select-exchange', json=payload)
    if res.text.count('clickerUser'):
        return f'{name}: 成功'
    hk_raise_error(name, res)


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
        tasks = query_task()
        for task in tasks:
            task_id = task.get('id')
            is_completed = task.get('isCompleted')
            if not is_completed and task_id != 'invite_friends':
                if task_id == 'select_exchange':
                    exchange_ids = ['binance', 'okx', 'crypto_com', 'bybit', 'bingx', 'htx', 'kucoin', 'gate_io', 'mexc',
                                    'bitget']
                    select_exchange(exchange_ids[random.randint(0, len(exchange_ids) - 1)])
                result = completed_task(task_id)
                if result.count('成功'):
                    logger.success(result)
                else:
                    logger.warning(result)

        upgrades = query_upgrades()
        for upgrade in upgrades:
            if not upgrade.get('isAvailable') or upgrade.get('isExpired'):
                continue
            level = upgrade_max_level
            if upgrade.get('maxLevel') and upgrade.get('maxLevel') < level:
                level = upgrade.get('maxLevel')
            count = level - upgrade.get('level')
            while count > 0:
                result = buy_upgrade(upgrade.get('id'))
                logger.info(result)
                if result.count('前置条件不足') or result.count('升级冷却中') or result.count('余额不足'):
                    break
                else:
                    count -= 1




if __name__ == '__main__':
    Task(TASK_NAME, FILE_NAME).run()
