import os

APPLICATION_NAME = 'Xiaobo_Task_Public'
# 任务通用环境变量名
ENV_ENVIRONMENT = "ENVIRONMENT"
ENV_THREAD_NUMBER = "THREAD_NUMBER"
ENV_PROXY_API = "PROXY_API"
ENV_PROXY_API_IPV6 = "PROXY_API_IPV6"
ENV_DISABLE_PROXY = "DISABLE_PROXY"
ENV_DELAY_MIN = "DELAY_MIN"
ENV_DELAY_MAX = "DELAY_MAX"
ENV_DISABLE_DELAY = "DISABLE_DELAY"
ENV_DISABLE_SHUFFLE = "DISABLE_SHUFFLE"
ENV_MAX_TRY = "MAX_TRY"
ENV_NO_CAPTCHA_KEY = 'NO_CAPTCHA_KEY'
ENV_YES_CAPTCHA_KEY = 'YES_CAPTCHA_KEY'
ENV_CAPTCHA_RUN_KEY = 'CAPTCHA_RUN_KEY'
# 任务通用环境变量默认值
THREAD_NUMBER = 10
MAX_TRY = 3
DELAY_MIN = 300
DELAY_MAX = 1800


def get_path():
    path = os.getcwd()
    paths = path.replace('\\', '/').split('/')
    for _ in range(len(paths)):
        _path = paths.pop()
        if _path.count('xiaobo'):
            path = '/'.join(paths) + (f'/{_path}' if os.getenv(ENV_ENVIRONMENT) == 'dev' else '')
            return path
    return ''


FILE_PATH = get_path() + "/data/"
