# 项目设计

## 项目模块拆分

| 模块名称 | 模块功能           |
| -------- | ------------------ |
| 登陆     | 进行登陆验证       |
| 上传     | 文件上传与表单填写 |
| 历史记录 | 提供历史记录查询   |
| 分析展示 | 分析后的结果界面   |

## 模块接口与功能详细描述

### 登陆模块

（注册 - 姓名 + 手机号 + 密码）

GET user_init



（登陆 - 姓名\手机号 + 密码）



## 开发计划

后端 选 Python -  flask

原因：门槛低，都能看懂。

带来的结果是=。=我自己的毕设处于代码复用的崇高懒惰目的估计也用python=。=

| URL                                                  | 调研结果                |
| ---------------------------------------------------- | ----------------------- |
| https://github.com/shekhargulati/flask-login-example | 纯登陆，调用flask-Login |
| https://github.com/tolgahanuzun/Flask-Login-Example  | 用来登陆ins的           |

安装依赖

```shell
pip3 install flask
pip3 install flask-login
```

问题解决

https://stackoverflow.com/questions/21701174/importerror-no-module-named-flask-ext-login

```python
from flask.ext.login import LoginManager
from flask_login import LoginManager
```

### 登陆

| 路径       | 功能                           |
| ---------- | ------------------------------ |
| /          | hello.html用于测试服务功能开启 |
| /login     | 登陆看板login.html             |
| /register  | 注册界面                       |
| /logout    | 登出logout.html                |
| /dashboard | 登陆后主界面 (尚未测试)        |

### 文件上传 + 表单填写

| 路径    | 功能                                            |
| ------- | ----------------------------------------------- |
| /upload | 选择上传文件并填写表单，事后返回dashboard主界面 |

### 历史记录

| 路径         | 功能                                                     |
| ------------ | -------------------------------------------------------- |
| /historylist | 可以查看历史上传的文件(在这里可以看到历史文件的处理进度) |

### 数据处理流程

输入文件通过文件上传功能上传至服务器。

服务器将新上传的输入文件加入处理队列

可以在/historylist路径中看到所有上传的文件的处理状态

| 状态名 | 解释                                                 |
| ------ | ---------------------------------------------------- |
| 已完成 | 已经分析完成，可以进行结果展示                       |
| 处理中 | 当前分析文件，正在流程处理中 (考虑展示百分比进度条?) |
| 等待中 | 等待处理文件队列...                                  |

## 操作流程

```python
'''
# TODO 晚上沟通一下是否需要这些步骤，是否有优化的空间
目前共十步
1 进入网站
2 强制跳转到登陆界面
3 注册
4 登陆
5 登陆至主界面
6 点击"新建"，填写表单并上传文件
7 点击提交后，跳转到历史上传页面
8 查看文件处理状态
9 等待完成后,点击文件图标
10 展示此文件处理结果
'''
```

### 唧唧歪歪

可以考虑上传文件后，有一个开始分析的按钮..?然后再开始分析

| 状态名 | 解释                             |
| ------ | -------------------------------- |
| 未分析 | 上传后，尚未点击 "开始分析"      |
| 准备中 | 建立分析然后开始排队等待分析处理 |

### 技术实现调研

python上传文件

官方推荐  http://docs.jinkan.org/docs/flask/patterns/fileuploads.html

一个简单例子=。= https://www.cnblogs.com/wongbingming/p/6802660.html