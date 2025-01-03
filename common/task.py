import re
import json
import time
import asyncio

from concurrent import futures
from abc import ABCMeta, abstractmethod

from common.util import *

LOCK = threading.Lock()
LOCAL = threading.local()

base_logger = get_logger()


def get_thread_number(task_num: int) -> int:
    """
    获取线程数
    :param task_num: 任务数量
    :return: 线程数
    """
    value = os.getenv(ENV_THREAD_NUMBER)
    if value and value.isdigit():
        return int(value)
    else:
        thread_num = THREAD_NUMBER
        base_logger.info(f"暂未设置线程数或设置有误，设置默认数量{thread_num}")
    if thread_num > task_num:
        thread_num = task_num
        base_logger.info(f"线程数量大于任务数量，设置任务数量{thread_num}")
    if thread_num < 1:
        thread_num = 1
        base_logger.info(f"线程数量不能小于1，设置最低数量{thread_num}")
    return thread_num


def get_proxy_api(task_name: str, use_ipv6: bool = False) -> str:
    """
    获取代理API
    :param task_name: 任务名
    :param use_ipv6: 是否取IPv6
    :return: API链接
    """
    api_url = ''
    disable = os.getenv(ENV_DISABLE_PROXY)
    if task_name and disable:
        items = disable.split("&")
        if task_name in items:
            base_logger.info("当前任务已设置禁用代理")
            return api_url
    if use_ipv6:
        api_url = os.getenv(ENV_PROXY_API_IPV6)
    if not api_url:
        api_url = os.getenv(ENV_PROXY_API)
    if not api_url:
        base_logger.info("暂未设置代理API，不使用代理")
    return api_url


def get_max_try() -> int:
    value = os.getenv(ENV_MAX_TRY)
    if value and value.isdigit():
        return int(value)
    base_logger.info(f"暂未设置尝试次数或设置有误，设置默认次数{MAX_TRY}")
    return MAX_TRY


def is_exist(env_name: str, task_name: str) -> int:
    disable_items = os.getenv(env_name)
    if not disable_items:
        return True
    items = disable_items.split("&")
    if task_name in items:
        return False
    return True


def get_delay_min() -> int:
    value = os.getenv(ENV_DELAY_MIN)
    if value and value.isdigit():
        return int(value)
    base_logger.info(f"暂未设置最小延迟或最设置有误，设置默认最小延迟{DELAY_MIN}")
    return DELAY_MIN


def get_delay_max() -> int:
    value = os.getenv(ENV_DELAY_MAX)
    if value and value.isdigit():
        return int(value)
    base_logger.info(f"暂未设置最大延迟或最设置有误，设置默认最大延迟{DELAY_MAX}")
    return DELAY_MAX


def get_proxy(api_url: str, logger, _proxies: list) -> str:
    """
    提取代理IP
    :param api_url: API链接
    :param logger: 日志输出
    :param _proxies: 代理数组
    :return:
    """
    if not api_url:
        return ""

    with LOCK:
        if len(_proxies) <= 0:
            for try_num in range(MAX_TRY):
                try:
                    res = requests.get(api_url)
                    ips = re.findall("(?:\d+\.){3}\d+:\d+", res.text)
                    if len(ips) < 1:
                        ips = re.findall("(\S+:\S+@\S+:\d+)", res.text)
                    if len(ips) < 1:
                        logger.error(f"API代理提取失败，请求响应: {res.text}")
                        raise Exception("代理提取失败")
                    else:
                        [_proxies.append(ip) for ip in ips]
                        break
                except:
                    if try_num < MAX_TRY - 1:
                        logger.error(f"API代理提取失败，请检查余额或是否已添加白名单，3秒后第{try_num + 1}次重试")
                        time.sleep(3)
                    else:
                        logger.error(f"API代理提取失败，请检查余额或是否已添加白名单")

    proxy = _proxies.pop(0) if len(_proxies) > 0 else None
    if proxy:
        proxy = f"http://{proxy}"
    return proxy


class BaseTask(metaclass=ABCMeta):
    def __init__(self, task_name: str, file_name: str, use_ipv6: bool = False, disable_task_proxy: bool = False, is_delay: bool = True):
        self.task_name = task_name
        self.file_name = file_name
        self.use_ipv6 = use_ipv6
        self.disable_task_proxy = disable_task_proxy
        self.is_delay = is_delay

        self.task_count = 0
        self.success_count = 0
        self.fail_data = []
        self.logger = get_logger()
        self.thread_num = THREAD_NUMBER
        self.max_try = MAX_TRY
        self.proxy_api = ''
        self.proxies = []

        self.logger.info("=====开始读取配置=====")
        self.load_config()
        self.logger.info("=====配置读取完毕=====\n")

        if self.is_delay and os.getenv(ENV_ENVIRONMENT) != 'dev':
            delay_min = get_delay_min()
            delay_max = get_delay_max()
            delay = random.randint(delay_min, delay_max + 1)
            self.logger.info(f"随机延迟{delay}秒后开始运行任务")
            time.sleep(delay)

    def load_config(self):
        self.thread_num = get_thread_number(self.task_count)
        if not self.disable_task_proxy:
            self.proxy_api = get_proxy_api(self.task_name, self.use_ipv6)
        self.max_try = get_max_try()
        if self.is_delay:
            self.is_delay = is_exist(ENV_DISABLE_DELAY, self.task_name)

    def run(self):
        if self.task_count < 1:
            self.logger.error("任务数量为0，程序退出")
            return

        self.logger.info(f"=====开始运行任务=====")
        with futures.ThreadPoolExecutor(max_workers=self.thread_num) as pool:
            tasks = [pool.submit(self.main, index) for index in range(self.task_count)]
            futures.wait(tasks)
            for future in futures.as_completed(tasks):
                if future.result():
                    self.success_count += 1
        self.logger.info(f"=====任务运行完毕=====\n")

        self.logger.info("=====开始统计数据=====")
        self.statistics()
        self.logger.info("=====数据统计完毕=====\n")

        self.logger.info("=====开始保存文本=====")
        self.save()
        self.logger.info("=====文本保存完毕=====\n")

    @abstractmethod
    def main(self, index: int) -> bool:
        """
        主逻辑
        :param index: 索引
        :return: 是否成功
        """

    def statistics(self):
        """数据统计"""
        if self.fail_data:
            log_data = f"-----失败任务统计({len(self.fail_data)})-----\n"
            log_data += "\n".join([fail for fail in self.fail_data])
            self.logger.error(log_data)

    def save(self):
        """保存数据"""


class QLTask(BaseTask):
    def __init__(self, task_name: str, file_name: str, use_ipv6: bool = False, disable_task_proxy: bool = False, is_delay: bool = True,
                 shuffle: bool = True):
        self.lines = []
        self.shuffle = shuffle
        if is_exist(ENV_DISABLE_SHUFFLE, self.task_name):
            self.shuffle = False
        super().__init__(task_name, file_name, use_ipv6, disable_task_proxy, is_delay)
        if self.shuffle:
            random.shuffle(self.lines)

    def load_config(self):
        self.lines = load_txt(self.file_name)
        self.task_count = len(self.lines)
        super().load_config()

    def main(self, index: int) -> bool:
        """
        主逻辑
        :param index: 索引
        :return: 是否成功
        """
        logger = get_logger(index + 1)
        datas = self.lines[index].strip().split("----")
        for try_num in range(1, self.max_try + 1):
            logger.info(f"第{try_num}次运行任务: {datas[0]}")
            proxy = get_proxy(self.proxy_api, logger, self.proxies)
            if proxy:
                logger.info(f"使用代理: {proxy.split('//')[1]}")
            try:
                self.task(index, datas, proxy, logger)
                LOCAL.__dict__.clear()
                return True
            except TaskException as e:
                tb_next = e.__traceback__.tb_next.tb_next
                if not tb_next:
                    tb_next = e.__traceback__.tb_next
                logger.error(f"任务失败({tb_next.tb_lineno} - {e})")
                self.fail_data.append(f"【{index + 1}】{datas[0]}----{e}")
                break
            except Exception as e:
                tb_next = e.__traceback__.tb_next.tb_next
                if not tb_next:
                    tb_next = e.__traceback__.tb_next
                logger.error(f"第{try_num}次任务失败({tb_next.tb_lineno} - {repr(e)})")
                if try_num >= self.max_try:
                    self.fail_data.append(f"【{index + 1}】{datas[0]}----{e}")
        LOCAL.__dict__.clear()
        return False

    @abstractmethod
    def task(self, index: int, datas: list[str], proxy: str, logger):
        """
        任务
        :param index: 索引
        :param datas: 数据
        :param proxy: 代理
        :param logger: 日志
        """