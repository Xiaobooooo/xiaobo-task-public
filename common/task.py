import random
import re
import time
from abc import ABCMeta, abstractmethod
from concurrent import futures

import requests

from common.notify import send
from common.util import LOCK, load_txt, get_env, get_logger, TaskException, log, LOCAL

ENV_THREAD_NUMBER = "THREAD_NUMBER"
ENV_DELAY_MIN = "DELAY_MIN"
ENV_DELAY_MAX = "DELAY_MAX"
ENV_DISABLE_DELAY = "DISABLE_DELAY"
ENV_PROXY_API = "PROXY_API"
ENV_DISABLE_PROXY = "DISABLE_PROXY"
ENV_MAX_TRY = "MAX_TRY"
ENV_YES_CAPTCHA_KEY = 'YES_CAPTCHA_KEY'
ENV_CAPTCHA_RUN_KEY = 'CAPTCHA_RUN_KEY'

DELAY_MIN = 300
DELAY_MAX = 3600
MAX_TRY = 3

proxies = []


def get_thread_number(task_num: int) -> int:
    """
    获取线程数
    :param task_num: 任务数量
    :return: 线程数
    """
    thread_num = 5
    value = get_env(ENV_THREAD_NUMBER)
    if value != "":
        try:
            thread_num = int(value)
        except:
            log.info(f"线程数设置有误，设置默认数量{thread_num}")
    else:
        log.info(f"暂未设置线程数，设置默认数量{thread_num}")
    if thread_num > task_num:
        thread_num = task_num
        log.info(f"线程数量大于任务数量，设置任务数量{task_num}")
    if thread_num < 1:
        thread_num = 1
        log.info("线程数量不能小于0，设置最低数量1")
    return thread_num


def get_disable_delay(task_name: str) -> int:
    disable = get_env(ENV_DISABLE_DELAY)
    items = disable.split("&")
    if task_name in items:
        return False
    return True


def get_max_try() -> int:
    value = get_env(ENV_MAX_TRY)
    if value:
        try:
            return int(value)
        except:
            log.info(f"尝试次数设置有误，设置默认次数{MAX_TRY}")
    else:
        log.info(f"暂未设置尝试次数，设置默认次数{MAX_TRY}")
    return MAX_TRY


def get_delay_min() -> int:
    value = get_env(ENV_DELAY_MIN)
    if value:
        try:
            return int(value)
        except:
            log.info(f"最小延迟设置有误，设置默认最小延迟{MAX_TRY}")
    return DELAY_MIN


def get_delay_max() -> int:
    value = get_env(ENV_DELAY_MAX)
    if value:
        try:
            return int(value)
        except:
            log.info(f"最大延迟设置有误，设置默认最大延迟{MAX_TRY}")
    return DELAY_MAX


def get_proxy_api(task_name: str) -> str:
    """
    获取代理API
    :param task_name: 任务名
    :return: API链接
    """
    api_url = ""
    disable = get_env(ENV_DISABLE_PROXY)
    if task_name and disable:
        items = disable.split("&")
        if task_name in items:
            log.info("当前任务已设置禁用代理")
            return api_url
    api_url = get_env(ENV_PROXY_API)
    if not api_url:
        log.info("暂未设置代理API，不使用代理")
    return api_url


def get_proxy(api_url: str, logger) -> str:
    """
    提取代理IP
    :param api_url: API链接
    :param logger: 日志输出
    :return:
    """
    if not api_url:
        return ""

    with LOCK:
        if len(proxies) <= 0:
            for try_num in range(MAX_TRY):
                try:
                    res = requests.get(api_url)
                    ips = re.findall("(?:\d+\.){3}\d+:\d+", res.text)
                    if len(ips) < 1:
                        logger.error(f"API代理提取失败，请求响应: {res.text}")
                        raise Exception("代理提取失败")
                    else:
                        [proxies.append(ip) for ip in ips]
                        break
                except:
                    if try_num < MAX_TRY - 1:
                        logger.error(f"API代理提取失败，1秒后第{try_num + 1}次重试")
                        time.sleep(1)
                    else:
                        logger.error(f"API代理提取失败，请检查余额或是否已添加白名单")
    proxy = proxies.pop(0) if len(proxies) > 0 else None
    if proxy:
        logger.info(f"使用代理: {proxy}")
        proxy = f"http://{proxy}"
    return proxy


class QLTask(metaclass=ABCMeta):
    def __init__(self, task_name: str, file_name: str):
        self.task_name = task_name
        self.file_name = file_name
        self.success = 0
        self.fail_data = []
        self.logger = log

        self.logger.info("=====开始读取配置=====")
        self.lines = load_txt(self.file_name)
        self.total = len(self.lines)
        self.thread_num = get_thread_number(self.total)
        is_delay = get_disable_delay(self.task_name)
        self.api_url = get_proxy_api(self.task_name)
        self.max_try = get_max_try()
        self.logger.info("=====配置读取完毕=====\n")

        if is_delay:
            delay_min = get_delay_min()
            delay_max = get_delay_max()
            delay = random.randint(delay_min, delay_max + 1)
            self.logger.info(f"随机延迟{delay}秒后开始运行任务")
            time.sleep(delay)

    def run(self):
        self.logger.info(f"=====开始运行任务=====")
        with futures.ThreadPoolExecutor(max_workers=self.thread_num) as pool:
            tasks = [pool.submit(self.main, index) for index in range(self.total)]
            futures.wait(tasks)
            for future in futures.as_completed(tasks):
                if future.result():
                    self.success += 1
        self.logger.info(f"=====任务运行完毕=====\n")

        self.logger.info("=====开始统计数据=====")
        self.statistics()
        self.logger.info("=====数据统计完毕=====\n")

        self.logger.info("=====开始保存文本=====")
        self.save()
        self.logger.info("=====文本保存完毕=====\n")

        push_data = self.get_push_data()
        if push_data:
            self.logger.info(f"=====开始推送消息=====")
            send(self.task_name, push_data)
            self.logger.info(f"=====消息推送完毕=====")

    def main(self, index: int) -> bool:
        """
        主逻辑
        :param index: 索引
        :return: 是否成功
        """
        logger = get_logger(index + 1)
        datas = self.lines[index].strip().split("----")
        if index + 1 >= self.total:
            next_datas = self.lines[0].strip().split("----")
        else:
            next_datas = self.lines[index + 1].strip().split("----")
        for try_num in range(1, self.max_try + 1):
            logger.info(f"第{try_num}次运行任务: {datas[0]}")
            proxy = get_proxy(self.api_url, logger)
            try:
                self.task(index, datas, proxy, logger, next_datas)
                LOCAL.__dict__.clear()
                return True
            except TaskException as e:
                logger.error(f"任务失败({e.__traceback__.tb_next.tb_next.tb_lineno} - {repr(e)})")
                self.fail_data.append(f"【{index + 1}】{e}")
                break
            except Exception as e:
                logger.error(f"第{try_num}次任务失败({e.__traceback__.tb_next.tb_next.tb_lineno} - {repr(e)})")
                if try_num >= self.max_try:
                    self.fail_data.append(f"【{index + 1}】{e}")
        LOCAL.__dict__.clear()
        return False

    def statistics(self):
        """数据统计"""
        if self.fail_data:
            log_data = "-----失败任务统计-----\n"
            log_data += "\n".join([fail for fail in self.fail_data])
            self.logger.error(log_data)

    def get_push_data(self) -> str:
        """
        推送数据
        :return: 推送数据
        """
        return f"总任务数: {self.total}\n任务成功数: {self.success}\n任务失败数: {len(self.fail_data)}"

    def save(self):
        """保存数据"""

    @abstractmethod
    def task(self, index: int, datas: list, proxy: str, logger, next_datas: list) -> str or None:
        """
        任务
        :param index: 序号
        :param datas: 数据
        :param proxy: 代理
        :param logger: 日志输出
        :param next_datas: 下一条数据
        :return: 是否成功
        """
