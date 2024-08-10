"""
cron: 0 10,22 * * *
new Env('仓鼠快打_每日奖励')
"""
import base64
import random
import time
import uuid

from common.task import QLTask
from common.util import LOCAL, raise_error, get_session
from HamsterKombatClick import hk_raise_error

TASK_NAME = '仓鼠快打_每日奖励'
FILE_NAME = 'HamsterKombatToken.txt'


def star() -> dict | str:
    name = '开始游戏'
    res = LOCAL.session.post('https://api.hamsterkombatgame.io/clicker/start-keys-minigame')
    if res.text.count('clickerUser'):
        return res.json().get('clickerUser')
    if res.text.count('KEYS-MINIGAME_WAITING'):
        return f'{name}: 未到游戏时间'
    hk_raise_error(name, res)


def claim_key(uid: str) -> str:
    name = '领取每日钥匙'
    game_sleep_time = random.randint(10, 25)
    time.sleep(game_sleep_time)
    cipher = f"0{game_sleep_time}{random.randint(10000000000, 99999999999)}"[:10]
    url = 'https://api.hamsterkombatgame.io/clicker/claim-daily-keys-minigame'
    payload = {"cipher": base64.b64encode(f'{cipher}|{uid}'.encode()).decode()}
    res = LOCAL.session.post(url, json=payload)
    if res.text.count('clickerUser'):
        return f'{name}: 成功'
    if res.text.count('DAILY_KEYS_MINI_GAME_DOUBLE_CLAIMED'):
        return f'{name}: 今日已经领取过了'
    raise_error(name, res)


def query_daily_cipher() -> dict:
    name = '查询每日密码'
    url = 'https://api.hamsterkombatgame.io/clicker/config'
    res = LOCAL.session.post(url)
    if res.text.count('dailyCipher'):
        return res.json()
    raise_error(name, res)


def claim_daily_cipher(cipher: str) -> str:
    name = '领取每日密码奖励'
    url = 'https://api.hamsterkombatgame.io/clicker/claim-daily-cipher'
    payload = {'cipher': base64.b64decode(cipher[:3] + cipher[4:]).decode('utf-8')}
    res = LOCAL.session.post(url, json=payload)
    if res.text.count('clickerUser'):
        return f'{name}: 成功'
    if res.text.count('DAILY_CIPHER_DOUBLE_CLAIMED'):
        return f'{name}: 今日已经领取过了'
    raise_error(name, res)


def claim_daily_combo() -> str:
    name = '领取每日升级奖励'
    url = 'https://api.hamsterkombatgame.io/clicker/claim-daily-combo'
    res = LOCAL.session.post(url, json={})
    if res.text.count('clickerUser'):
        return f'{name}: 成功'
    if res.text.count('CLAIMED'):
        return f'{name}: 今日已经领取过了'
    if res.text.count('NOT_READY'):
        return f'{name}: 未升级正确卡片'
    raise_error(name, res)


def get_promos() -> dict:
    name = '获取活动信息'
    url = 'https://api.hamsterkombatgame.io/clicker/get-promos'
    res = LOCAL.session.post(url, json={})
    if res.text.count('promoId'):
        promos = {}
        for promo in res.json().get('promos'):
            promos.update({promo.get('promoId'): promo.get('keysPerDay')})
        for promo in res.json().get('states'):
            promo_id = promo.get('promoId')
            promos.update({promo_id: promos.get(promo_id) - promo.get('receiveKeysToday')})
        return promos
    raise_error(name, res)


def get_client_token(promo_id, proxy) -> str:
    name = '获取游戏Token'
    session = get_session()
    session.proxies = proxy
    url = "https://api.gamepromo.io/promo/login-client"
    current_time = int(time.time() * 1000)
    random_part = random.randint(100, 999)
    random_first = int(str(current_time)[:10] + str(random_part))
    app_tokens = {
        "fe693b26-b342-4159-8808-15e3ff7f8767": "74ee0b5b-775e-4bee-974f-63e7f4d5bacb",
        "b4170868-cef0-424f-8eb9-be0622e8e8e3": "d1690a07-3780-4068-810f-9b5bbf2931b2",
        "c4480ac7-e178-4973-8061-9ed5b2e17954": "82647f43-3f87-402d-88dd-09a90025313f",
        "43e35910-c168-4634-ad4f-52fd764a843f": "d28721be-fd2d-4b45-869e-9f253b554e50"
    }
    payload = {"appToken": app_tokens.get(promo_id), "clientId": f"{random_first}-3472514666961597005",
               "clientOrigin": "deviceid"}
    res = session.post(url, json=payload)
    if res.text.count('clientToken'):
        return res.json().get("clientToken")
    raise_error(name, res)


def get_key(promo_id, proxy) -> str:
    name = '生成Key'
    session = get_session()
    session.proxies = proxy
    session.headers.update({
        "Content-Type": "application/json; charset=utf-8",
        "Host": "api.gamepromo.io",
        'Authorization': f"Bearer {LOCAL.client_token}"
    })
    res = None
    for i in range(50):
        payload = {"promoId": promo_id, "eventId": str(uuid.uuid4()), "eventOrigin": "undefined"}
        res = session.post("https://api.gamepromo.io/promo/register-event", json=payload)
        if res.text.count('hasCode') and res.json().get('hasCode'):
            payload = {"promoId": promo_id}
            res = session.post(url="https://api.gamepromo.io/promo/create-code", json=payload)
            if res.text.count('promoCode'):
                return res.json().get('promoCode')
        time.sleep(5)
    raise_error(name, res)


def apply_promo(key) -> str:
    name = '领取活动奖励'
    payload = {"promoCode": key}
    res = LOCAL.session.post("https://api.hamsterkombatgame.io/clicker/apply-promo", json=payload)
    if res.text.count('clickerUser'):
        return f"{name}: 成功"
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
        query_result = query_daily_cipher()
        if not query_result.get('dailyKeysMiniGame').get('isClaimed'):
            info = star()
            if type(info) is str and info.count('未到游戏时间'):
                logger.info(info)
            else:
                logger.info('开始MiniGame')
                result = claim_key(info.get('id'))
                logger.success(result)
        if not query_result.get('dailyCipher').get('isClaimed'):
            result = claim_daily_cipher(query_result.get('dailyCipher').get('cipher'))
            logger.success(result)
        result = claim_daily_combo()
        logger.success(result)
        promos = get_promos()

        for promo_id, count in promos.items():
            LOCAL.client_token = get_client_token(promo_id, proxy)
            for i in range(count):
                logger.info("正在生成Key，时间可能比较久")
                key = get_key(promo_id, proxy)
                result = apply_promo(key)
                logger.info(result)


if __name__ == '__main__':
    Task(TASK_NAME, FILE_NAME).run()
