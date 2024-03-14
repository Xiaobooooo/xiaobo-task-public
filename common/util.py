import os
import sys
import threading

import requests
import tls_client
from loguru import logger
from requests import Response
from tls_client.settings import ClientIdentifiers

LOCK = threading.Lock()
LOCAL = threading.local()

logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <5}</level> | "
                              "<cyan>【{extra[name]}】</cyan> - <level>{message}</level>")
log = logger.bind(name="Xiaobo_Task")


class TaskException(Exception):
    def __init__(self, name, message):
        super().__init__(f"{name}: {message}")


def get_logger(index: int | str = "Xiaobo_Task"):
    return logger.bind(name=index)


def load_txt(file_name: str) -> list:
    """
    读取文本
    :param file_name: 文件名
    :return: 文本数组
    """
    if not file_name.endswith(".txt"):
        file_name += ".txt"
    lines = []
    log.info(f"正在读取文本<{file_name}>")
    if not os.path.exists(file_name):
        log.error(f"不存在<{file_name}>文本，请创建文件后重试")
        sys.exit()
    with open(sys.path[0] + "/" + file_name, "r+") as f:
        while True:
            line = f.readline().strip()
            if line is None or line == "":
                break
            lines.append(line)
    log.info(f"<{file_name}>文本读取完毕，总计数量: {len(lines)}")
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
    mode = "a+" if append else "w+"
    log.info(f"正在写入文本<{file_name}>")
    with LOCK:
        try:
            with open(sys.path[0] + "/" + file_name, mode) as f:
                f.write(text)
            log.info(f"<{file_name}>文本写入成功")
            return True
        except BaseException as e:
            log.error(f"<{file_name}>文本写入失败: {repr(e)}")
            return False


def del_file(file_name: str) -> bool:
    """
    删除文本
    :param file_name: 文件名
    :return: 删除结果
    """
    if not file_name.endswith(".txt"):
        file_name += ".txt"
    log.info(f"正在删除<{file_name}>文件")
    if os.path.isfile(file_name):
        try:
            os.remove(file_name)
            return True
        except BaseException as e:
            log.error(f"文件删除失败:{repr(e)}")
    else:
        log.error(f"{file_name}不存在或是一个文件夹")
    return False


def get_env(env_name: str) -> str:
    """
    获取环境变量
    :param env_name: 环境变量名
    :return: 环境变量值
    """
    log.info(f"正在读取环境变量【{env_name}】")
    try:
        if env_name in os.environ:
            env_val = os.environ[env_name]
            if len(env_val) > 0:
                log.info(f"读取到环境变量【{env_name}】")
                return env_val
    except Exception as e:
        log.error(f"环境变量【{env_name}】读取失败: {repr(e)}")
    return ""


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
    return None


def raise_error(name: str, response: Response, un_auths: list = None, msg_key: str = None):
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
    un_login = ["未登录", "登录失效", "无效Token", "请先登录", "请登录" "unauthorized"]
    if un_auths:
        un_login.extend(un_auths)
    for un_auth in un_login:
        if text.lower().count(un_auth.lower()):
            raise TaskException(name, "登录过期或被封禁、冻结")

    body = response.json() if text.startswith("{") and text.endswith("}") else {}
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


def get_session(user_agent: str = None, is_tls: bool = True, client: ClientIdentifiers = "chrome_120", decode: str = None):
    if not user_agent:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/12.0.0.0 Safari/537.36"
    if is_tls:
        session = tls_client.Session(client_identifier=client, random_tls_extension_order=True, additional_decode=decode)
    else:
        session = requests.session()
    session.headers.update({"User-Agent": user_agent})
    return session


def get_android_session(user_agent: str = "okhttp/4.13.0", is_tls: bool = True,
                        client: ClientIdentifiers = "okhttp4_android_13", decode: str = None):
    return get_session(user_agent, is_tls, client, decode)
