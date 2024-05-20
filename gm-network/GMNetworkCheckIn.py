"""
cron: 0 12 * * *
new Env('GM_签到')
"""
from common.task import QLTask
from common.util import LOCAL, raise_error, get_session

TASK_NAME = 'GM_签到'
FILE_NAME = 'GMWallet.txt'


def gm_raise_error(name, res):
    raise_error(name, res, msg_key="error_message")


def check_in() -> str:
    name = '签到'
    url = 'https://api-launchpad.gmnetwork.ai/task/auth/task/'
    payload = {"task_id": "903134427101827116", "category": 200}
    res = LOCAL.session.post(url, json=payload)
    if res.text.count('success') and res.json().get('success'):
        return f'{name}: 成功'
    if res.text.count('The reward has already been claimed'):
        return f'{name}: 今日签到了'
    gm_raise_error(name, res)


class Task(QLTask):
    def task(self, index: int, datas: list, proxy: str, logger, next_datas: list) -> str or None:
        LOCAL.address = datas[0]
        LOCAL.private_key = datas[1]
        LOCAL.token = datas[2]

        if not hasattr(LOCAL, 'session'):
            LOCAL.session = get_session()
            LOCAL.session.headers.update({
                'Host': 'api-launchpad.gmnetwork.ai',
                'ACCESS-TOKEN': LOCAL.token,
                'Origin': 'https://launchpad.gmnetwork.ai'
            })
        LOCAL.session.proxies = proxy

        result = check_in()
        logger.success(result)


if __name__ == '__main__':
    Task(TASK_NAME, FILE_NAME).run()
