import random
import string
import threading

import loguru
from curl_cffi import requests

from common.constant import *


class TaskException(Exception):
    def __init__(self, name, message):
        super().__init__(f"{name}: {message}")


def get_logger(index: int | str = APPLICATION_NAME):
    return loguru.logger.bind(name=index)


def get_random_str(length: int = random.randint(8, 16)):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def load_dir(dir_name: str) -> list:
    """
    读取文本
    :param dir_name: 文件夹
    :return: 文本数组
    """
    files = os.listdir(f'{FILE_PATH}{dir_name}')
    new_files = [f'{FILE_PATH}{dir_name}/{file}' for file in files]
    return new_files


def json_get_value(json_data: dict | list, key: str = None) -> dict | list | str | int | None:
    """
    通过键取json值
    :param json_data:
    :param key:
    :return:
    """
    if not key:
        return None
    keys = key.split("/")
    for key in keys:
        if isinstance(json_data, dict):
            json_data = json_data.get(key)
        else:
            try:
                json_data = json_data[int(key)]
            except:
                return None
    return json_data


def raise_error(name: str, response: requests.Response, un_auths: list = None, msg_key: str = None):
    """
    获取响应中的错误消息，并抛出异常
    :param name: 操作
    :param response: 响应
    :param un_auths: 未登录标识
    :param msg_key: 消息key
    :return: 错误信息
    """
    msg = None
    text = response.text.strip()
    un_login = ["未登录", "登录失效", "无效Token", "请先登录", "请登录", "unauthorized"]
    if un_auths:
        un_login.extend(un_auths)
    for un_auth in un_login:
        if text.lower().count(un_auth.lower()):
            raise TaskException(name, "登录过期，请重新登录")

    body = response.json() if (text.startswith("{") and text.endswith("}") or text.startswith("[") and text.endswith("]")) else {}
    if body:
        if msg_key:
            msg = json_get_value(body, msg_key)
        if not msg:
            msg = body.get("msg") if body.get("msg") else body.get("message")

    if not msg:
        if text.count("<!DOCTYPE html>"):
            msg = f"{response.status_code} - HTML"
        else:
            msg = f"{response.status_code} - {text[:233]}"

    intercepts = ["You are unable to access", "Cloudflare to restrict access", "You do not have access to"]
    for intercept in intercepts:
        if text.count(intercept):
            msg = "请求被拦截"

    msg = f"{name}: {msg}"
    raise Exception(msg)


def get_session(proxy: str = None, timeout: int = 30, impersonate='chrome'):
    return requests.Session(proxy=proxy, timeout=timeout, impersonate=impersonate)


LOCK = threading.Lock()
base_logger = get_logger()


def load_txt(file_name: str) -> list:
    """
    读取文本
    :param file_name: 文件名
    :return: 文本数组
    """
    if not file_name.endswith(".txt"):
        file_name += ".txt"
    file_path = FILE_PATH + file_name
    if not os.path.exists(file_path):
        base_logger.error(f"不存在<{file_name}>文本")
        return []
    with open(file_path, "r+") as f:
        lines = f.readlines()
        lines = [line.strip() for line in lines if line.strip() != '']
    base_logger.info(f"<{file_name}>文本读取完毕，总计数量: {len(lines)}")
    return lines


def write_txt(file_name: str, text: str, append: bool = False) -> bool:
    """
    写入文本
    :param file_name: 文本名
    :param text: 写入文本内容
    :param append: 是否追加
    :return: 写入结果
    """
    if not file_name.endswith(".txt"):
        file_name += ".txt"
    file_path = FILE_PATH + file_name
    mode = "a+" if append else "w+"
    with LOCK:
        try:
            with open(file_path, mode) as f:
                f.write(text)
            base_logger.info(f"<{file_name}>文本写入成功")
            return True
        except BaseException as e:
            base_logger.error(f"<{file_name}>文本写入失败: {repr(e)}")
            return False


def del_file(file_name: str) -> bool:
    """
    删除文本
    :param file_name: 文件名
    :return: 删除结果
    """
    if not file_name.endswith(".txt"):
        file_name += ".txt"
    file_path = FILE_PATH + file_name
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
            base_logger.info(f"<{file_name}>文件删除成功")
            return True
        except BaseException as e:
            base_logger.error(f"文件删除失败:{repr(e)}")
    else:
        base_logger.error(f"{file_name}不存在或是一个文件夹")
    return False
