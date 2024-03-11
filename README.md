# Xiaobo-Task-Public [![Twitter](https://img.shields.io/twitter/follow/0xiaobo)](https://twitter.com/intent/follow?screen_name=0xiaobo)

各种撸毛项目完成每日、每周任务，链上交互等。  
推荐使用[青龙面板](https://github.com/whyour/qinglong)(建议debian版本)运行(自行学习安装使用)。  
青龙拉库命令(定时建议隔2-5小时拉取一次)

```
ql repo https://github.com/Xiaobooooo/xiaobo-task-public.git "" task|util|notify common
```

有BUG或需要更新的项目请准备好项目详细信息然后提交[issues](https://github.com/Xiaobooooo/xiaobo-ql-open/issues)

## 低价推特账号

便宜Twitter|X令牌号(可定制昵称、关注项目方等)：[XiaoboFaka](https://www.xiaobofaka.xyz/)

## 提示！！！

代码比较烂，有能力的自行修改更新  
所有项目皆有被女巫、封号的可能，如造成损失本仓库不负任何责任，介意勿用  
所有项目皆有被女巫、封号的可能，如造成损失本仓库不负任何责任，介意勿用  
所有项目皆有被女巫、封号的可能，如造成损失本仓库不负任何责任，介意勿用

## 环境变量

### 通用环境变量

| 环境变量名         | 变量介绍                              | 
|---------------|-----------------------------------|
| THREAD_NUMBER | 线程数(默认5线程 )                       | 
| DELAY_MIN     | 任务启动随机延迟最小数(默认300，单位秒)            | 
| DELAY_MAX     | 任务启动随机延迟最大数(默认3600，单位秒)           |
| DISABLE_DELAY | 关闭随机延迟的项目名称，多个项目使用&连接             |
| PROXY_API     | 代理提取API链接(协议: HTTP/HTTPS 格式: TXT) |
| DISABLE_PROXY | 禁用代理的项目名称，多个项目使用&连接               |
| MAX_TRY       | 任务尝试次数(默认3次)                      | 

### 项目环境变量

| 环境变量名    | 变量介绍                  | 适用项目   |
|----------|-----------------------|--------|
| QNA3_RPC | 签到发送交易使用的RPC(默认opBNB) | Qna3签到 |

## 已更新项目(点击项目名跳转项目入口)

| 项目                                                            | 文本                   | 格式       | 功能    | 建议定时             |
|---------------------------------------------------------------|----------------------|----------|-------|------------------|
| [Qna3](https://qna3.ai/vote)                                  | Qna3Wallet.txt       | 地址----私钥 | 签到、领取 | 签到每天1次、领取一个月1-3次 |
| [Ulti-Pilot](https://pilot.ultiverse.io/?inviteCode=8dKkU)    | UltiPilotAddress.txt | 地址----私钥 | 探索    | 早晚各1次            |
| [Web3Go-Reiki](https://reiki.web3go.xyz?ref=80621285de961cb2) | Web3GoWallet.txt     | 地址----私钥 | 签到    | 每日一次             |

## 语言

| 语言     | 推荐版本                                                            |
|--------|-----------------------------------------------------------------|
| Python | [3.10.6](https://www.python.org/downloads/release/python-3106/) |

## 使用模块依赖

| 语言     | 模块名        | 推荐版本       | 
|--------|------------|------------|
| Python | requests   | 2.31.0 及以上 |
| Python | tls-client | 1.0.1 及以上  |
| Python | loguru     | 0.7.2 及以上  |
| Python | web3       | 6.15.1 及以上 |

