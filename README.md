# Xiaobo-Task-Public [![Twitter](https://img.shields.io/twitter/follow/0xiaobo)](https://twitter.com/intent/follow?screen_name=0xiaobo)

各种撸毛项目完成每日、每周任务，链上交互等。  
推荐使用[青龙面板](https://github.com/whyour/qinglong)(建议debian版本)运行(自行学习安装使用)。  
青龙拉库命令(定时建议隔3-8小时拉取一次)

```
ql repo https://github.com/Xiaobooooo/xiaobo-task-public.git "" task|util|notify|expire common
```

有BUG或需要更新的项目请准备好项目详细信息然后提交[issues](https://github.com/Xiaobooooo/xiaobo-ql-open/issues)

## 提示！！！

代码比较烂，有能力的自行修改更新  
所有项目皆有被女巫、封号的可能，如造成损失本仓库不负任何责任，介意勿用  
所有项目皆有被女巫、封号的可能，如造成损失本仓库不负任何责任，介意勿用  
所有项目皆有被女巫、封号的可能，如造成损失本仓库不负任何责任，介意勿用

## 环境变量

### 通用环境变量

| 环境变量名           | 变量介绍                                                                            |
|-----------------|---------------------------------------------------------------------------------|
| THREAD_NUMBER   | 线程数(默认10线程)                                                                     |
| MAX_TRY         | 任务尝试次数(默认3次)                                                                    |
| DISABLE_SHUFFLE | 禁用乱序执行的项目名称，多个项目使用&连接                                                           |
| PROXY_API       | 代理提取API链接(协议:HTTP 分隔:换行 文本格式:TXT 代理格式:host:port 或 username:password@host:port ) |
| DISABLE_PROXY   | 禁用代理的项目名称，多个项目使用&连接                                                             |
| DELAY_MIN       | 任务启动随机延迟最小数(默认300，单位秒)                                                          |
| DELAY_MAX       | 任务启动随机延迟最大数(默认1800，单位秒)                                                         |
| DISABLE_DELAY   | 关闭随机延迟的项目名称，多个项目使用&连接                                                           |

### 项目环境变量

| 环境变量名           | 变量介绍     | 适用项目                         |
|-----------------|----------|------------------------------|
| YES_CAPTCHA_KEY | 人机验证解决方案 | Bera_领水                      |
| HEMI_RPC        | Hemi链RPC | Hemi_Swap、Hemi_CreateCapsule |

## 已更新项目(点击项目名跳转项目入口)

### 有效项目

| 项目                                                                                                            | 文本             | 格式(一行一个) | 功能           | 
|---------------------------------------------------------------------------------------------------------------|----------------|----------|--------------|
| [Hemi_交互](https://points.absinthe.network/hemi/start)(邀请码:ecd5454c)                                           | HemiWallet.txt | 地址----私钥 | Hemi部分链上交互任务 | 
| [Bera_领水](https://bartio.faucet.berachain.com/)(登录需要[YES_CAPTCHA_KEY](https://yescaptcha.com/i/iwRpT7)处理人机验证) | BeraWallet.txt | 地址       | 熊链领水         | 

### 无效项目

| 项目                                                                                                                                                                                                                                                                                                                                                    | 文本                                     | 格式                                                  | 功能                                                | 
|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------|-----------------------------------------------------|---------------------------------------------------|
| [Qna3](https://qna3.ai/vote)                                                                                                                                                                                                                                                                                                                          | Qna3Wallet.txt                         | 地址----私钥                                            | 签到、领取                                             | 
| [Ulti-Pilot](https://pilot.ultiverse.io/?inviteCode=8dKkU)                                                                                                                                                                                                                                                                                            | UltiPilotAddress.txt                   | 地址----私钥                                            | 探索                                                | 
| [Web3Go-Reiki](https://reiki.web3go.xyz?ref=80621285de961cb2)                                                                                                                                                                                                                                                                                         | Web3GoWallet.txt                       | 地址----私钥                                            | 签到                                                | 
| [Zeta-XP](https://hub.zetachain.com/zh-CN/xp?code=YWRkcmVzcz0weDgwQjhCZURCYjI1N2UxMjQ4MDljYUI2MzdmZUY0MDc3RTAyNDYzMTEmZXhwaXJhdGlvbj0xNzEyNzU3MjA0JnI9MHhmZWNmZTkzN2ZiNjJhNzMwMmIxMjU2Yzk4YjNiMWZjMzI4YzgxNmZjMGI0YTkxMzQ5YTJhYzllNzBkYWNmYmQ5JnM9MHgxNWZmNjA1MmJjYmQ1YjZjODM0NzJmNjc5ZDZmMGU2ZTc0MjNkY2Y5NWVlNWI4ZjUxMGE0ZDYzNDkwYzc5NDIyJnY9Mjg%3D) | ZetaWallet.txt                         | 地址----私钥                                            | XP注册、部分链上交互任务                                     | 注册仅一次、交互一周一次          |
| [Fuel](https://faucet-beta-5.fuel.network/)(需要[YES_CAPTCHA_KEY](https://yescaptcha.com/i/iwRpT7)处理人机验证)                                                                                                                                                                                                                                               | FuelWallet.txt                         | 地址                                                  | 领水                                                | 
| [GM-Network](https://launchpad.gmnetwork.ai/mission?invite_code=Y5FBPE)(登录需要[YES_CAPTCHA_KEY](https://yescaptcha.com/i/iwRpT7)处理人机验证)                                                                                                                                                                                                                 | GMWallet.txt(登录) GMWalletToken.txt(签到) | 地址----私钥(GMWallet) 地址----私钥----Token(GMWalletToken) | 每日签到                                              | 
| [HamsterKombat/仓鼠快打](https://t.me/hamster_kombat_bOt/start?startapp=kentId6697084893)                                                                                                                                                                                                                                                                 | HamsterKombatToken.txt                 | 名称标识----Token                                       | 点击、每日奖励(Cipher/MiniGame/PlayGround)、任务(Earn、卡片升级) | 

## 语言

| 语言     | 推荐版本                                                            |
|--------|-----------------------------------------------------------------|
| Python | [3.10.6](https://www.python.org/downloads/release/python-3106/) |

## 使用模块依赖

| 语言     | 模块名           | 推荐版本      | 
|--------|---------------|-----------|
| Python | python-dotenv | 1.0.1 及以上 |
| Python | loguru        | 0.7.2 及以上 |
| Python | curl_cffi     | 0.7.2 及以上 |
| Python | web3          | 7.3.0 及以上 |

