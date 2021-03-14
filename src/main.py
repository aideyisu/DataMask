from flask import Flask, render_template, Response, redirect, url_for,\
    request, session, abort
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, current_user, \
    login_required, login_user, logout_user
from pathlib import Path
import threading
import collections
import subprocess
import time
import os
import datetime
import pymysql
pymysql.install_as_MySQLdb()

ready = 0
operating = 1
waiting = 2

app = Flask(__name__, static_folder="static")
# PyClone 处理记录文件
open_file_name = "log_pyclone.txt"

# config
app.config.update(
    DEBUG=True,
    SECRET_KEY='secret_xxx'
)

# 这里登陆的是root用户，要填上自己的密码，MySQL的默认端口是3306，填上之前创建的数据库名jianshu,连接方式参考 \
# http://docs.sqlalchemy.org/en/latest/dialects/mysql.html
# mysql+pymysql://<username>:<password>@<host>/<dbname>[?<options>]
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:123456@127.0.0.1:3306/test'
# 设置sqlalchemy自动更跟踪数据库
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
# 查询时会显示原始SQL语句
app.config['SQLALCHEMY_ECHO'] = True
# 禁止自动提交数据处理
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = False
# 创建SQLAlichemy实例
db = SQLAlchemy(app)

# flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    # silly user model
    # 定义表名
    __tablename__ = 'users'
    # 定义字段
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), unique=True, index=True)
    phone = db.Column(db.String(64), unique=True)
    # email = db.Column(db.String(64),unique=True)
    password = db.Column(db.String(64))
    # role_id = db.Column(db.Integer, db.ForeignKey('roles.id')) # 设置外键

    def __init__(self, name, phone, password):
        # self.id = id
        self.name = name
        self.phone = phone
        self.password = password

    def __repr__(self):
        return "%d/%s/%s/%s" % (self.id, self.name, self.phone, self.password)


class UploadFile(db.Model):
    # upload file system model
    # 定义表名
    __tablename__ = 'files'
    # 定义字段
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 文件名称
    filename = db.Column(db.String(64),  index=True)
    ctime = db.Column(db.DateTime,  default=datetime.datetime.utcnow)
    # 文件状态  0为已完成 1为进行中 2为等待中 其余为预料之外情况
    status = db.Column(db.Integer,  index=True)
    uid = db.Column(db.Integer,  index=True)

    def __init__(self, filename, status, uid):
        self.filename = filename
        self.status = status
        self.uid = uid


# 上传的任务队列
upload_task_id_list = collections.deque()


def current_operate(current_file):
    # operate current upload file
    # 检测是否存在对应路径
    basepath = os.path.dirname(__file__)  # 当前文件所在路径
    my_file = Path(f'{basepath}/analysis_result/{str(current_file.uid)}')
    if not my_file.exists():
        # 检测是否存在id路径不存在
        os.makedirs(my_file)  # 只能创建单级目录 =.=对这个用法表示怀疑
        print(f'路径不存在 {my_file} 创建路径')

    # 初始化 pyclone 参数
    analysis_result_code = 0
    in_file_path = f'{basepath}/uploads/{str(current_file.uid)}/{current_file.filename}'
    working_dir_path = f'{basepath}/analysis_result/{str(current_file.uid)}/{current_file.filename}'

    # 打开一个文件作为收集途径
    with open(open_file_name, "w+") as file:
        # 调用 pyclone
        try:
            print("start a new task")
            analysis_result_code = subprocess.run(
                ["PyClone", "run_analysis_pipeline",
                 "--in_files", f'{in_file_path}',
                 "--working_dir", f'{working_dir_path}'], stdout=file).returncode
        except:
            # 吃错误大法...
            analysis_result_code = 1

    # 不为零代表出现异常情况
    if analysis_result_code != 0:
        print("任务异常")

    print("任务完成")
    # TODO 邮件通知功能
    turn_file_status_ready(current_file.id)     # 在这里把新的文件状态变更为已完成


def operator_task():
    # 多线程处理任务队列
    while True:
        # 检测任务队列是否为空
        length_task_list = len(upload_task_id_list)
        if length_task_list != 0:
            print(upload_task_id_list)
            # 将任务队列的第一个弹出来送去处理, leftpop
            current_task = upload_task_id_list.popleft()
            print(f"当前任务 {current_task}")
            turn_file_status_operating(current_task.id)  # 在这里将 task 状态变更为 处理中
            current_operate(current_task)
        else:
            print("current task list is nil, retry after 1 minute")
        time.sleep(60)  # 一分钟检测一次


def register_add_user(username, phone, password):
    # 多线程处理任务队列
    db.session.add(User(username, phone, password))
    db.session.commit()


def upload_add_file(upload_sql_obj):
    # tranfer upload file to the database
    db.session.add(upload_sql_obj)
    db.session.commit()


def turn_file_status_operating(upload_id):
    # turn status to operating
    current_file = UploadFile.query.get(upload_id)
    current_file.status = operating
    db.session.commit()


def turn_file_status_ready(upload_id):
    # turn status to ready
    current_file = UploadFile.query.get(upload_id)
    current_file.status = ready
    db.session.commit()


@app.route('/')
@login_required
def home():  # some protected url
    return render_template("hello.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # somewhere to login
    if request.method == 'POST':
        login_info = request.form.to_dict()
        user = User.query.filter_by(name=login_info.get("username")).first()

        if user:  # 用户存在 且 密码相同
            if user.password == login_info.get("password"):
                login_user(user)
                print(f'用户登陆 {user.id} : {user.name}')
                return redirect("/")

        return abort(401)
    else:
        return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    # somewhere to logout
    logout_user()
    return render_template("logout.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # create new user
    if request.method == "POST":
        login_info = request.form.to_dict()
        # TODO 重名检测未添加
        # 查询是否有重名 & 是否有
        # user_name = User.query.filter_by(name = login_info.get("username")).first()
        # user_phone = User.query.filter_by(name = login_info.get("phone")).first()

        # TODO register 里面 携带status_code 以及 source
        # if not user_name :
        #     return render_template("register.html")
        # elif not user_phone:
        #     return render_template("register.html")
        # else:
        print(
            f'新增用户 {login_info.get("username")} {login_info.get("phone")} {login_info.get("password")}')

        # 新增用户
        register_add_user(login_info.get("username"), login_info.get(
            "phone"), login_info.get("password"))

        return redirect("/login")
        # return redirect(request.args.get("next"))
    else:
        return render_template("register.html")


@app.route("/dashboard")
@login_required
def dashboard():
    # dashboard of system
    return render_template("dashboard.html")


@app.route("/upload", methods=["POST", "GET"])
@login_required
def upload():
    # upload file
    if request.method == "POST":
        f = request.files['file']
        basepath = os.path.dirname(__file__)  # 当前文件所在路径
        user_id = current_user.id
        print(f'当前登陆用户id {user_id}')

        # 检测是否存在对应路径
        my_file = Path(f'{basepath}/uploads/{str(user_id)}')
        if my_file.is_dir():
            # 存在
            print(f'路径存在 {my_file}')
        else:
            # 不存在
            os.mkdir(my_file)  # 只能创建单级目录
            print(f'路径不存在 {my_file}')

        # upload_path = os.path.join(basepath,"/uploads",secure_filename(f.filename))  #注意:没有的文件夹一定要先创建,不然会提示没有该路径
        f.save(f'{basepath}/uploads/{str(user_id)}/{secure_filename(f.filename)}')

        # 文件保存成功后,将此文件送入list
        # filename, ctime, status, uid
        upload_obj = UploadFile(secure_filename(
            f.filename), waiting, user_id)

        # 入库
        upload_add_file(upload_obj)

        # TODO 不能直接 传入文件对象id 因为要先入库再查询
        # TODO 直接通过 id 查询
        up_load_file_obj = UploadFile.query.filter_by(
            filename=f.filename).filter_by(
            uid=user_id).first()

        upload_task_id_list.append(up_load_file_obj)
        print(f'当前队列长度 {len(upload_task_id_list)}')
        print(upload_task_id_list)

        return redirect("upload_success.html")

    return render_template("upload.html")


@app.route("/upload_success")
@login_required
def upload_success():
    # upload success
    # 上传成功
    return render_template("upload_success.html")


@app.route("/history_list")
@login_required
def history_list():
    # history list
    # 历史上传记录
    uid = current_user.id
    basepath = os.path.dirname(__file__)  # 当前文件所在路径
    # 检测是否存在对应路径,读取list
    # my_file = Path(f'{basepath}/uploads/{str(uid)}')
    # file_name_list = os.listdir(my_file) if my_file.is_dir() else []

    # TODO 重构将这里完全变成查询数据库的操作
    '''

        通过用户id查询全部已上传文件并直接传输回来

    '''

    file_list = UploadFile.query.filter_by(uid=uid).all()

    # return render_template("history_list.html", history_list = file_name_list)
    return render_template("history_list.html", history_list=file_list, uid = uid)


# 用于分析结果的展示
@app.route("/analysis_result/<uploadname>")
@login_required
def analysis_result(uploadname):
    pass
    # TODO 通过file_id 直接展示对应的分析结果

    # TODO 对file_id 是否属于此用户 , 文件状态是否为ready 进行判断
    
    return render_template("analysis_result.html", uid=current_user.id, uploadname=uploadname)


# @login_required
@app.route("/download/<uid>/<uploadname>/<bigfiletype>/<smallfiletype>/<filename>", methods=['GET'])
# 不查数据库,通uploadname过uid + type + filename直接拼出来目标文件位置
def download_file(uid, uploadname, bigfiletype, smallfiletype, filename):

    # object_file_path = f'analysis_result/{str(current_user.id)}/{uploadname}/{smallfiletype}/{filename}'
    object_file_path = f'analysis_result/{uid}/{uploadname}/{bigfiletype}/{smallfiletype}/{filename}'
    if bigfiletype == "tables":
        object_file_path = f'analysis_result/{uid}/{uploadname}/{bigfiletype}/{filename}'

    # filepath是文件的路径，但是文件必须存储在static文件夹下， 比如images\test.jp
    return app.send_static_file(object_file_path)


@app.errorhandler(401)
def page_not_found(e):
    # handle login failed
    return Response('<p>Login failed</p>')


# callback to reload the user object
@login_manager.user_loader
def load_user(userid):
    user = User.query.get(userid)  # get为主键查询
    return user


if __name__ == "__main__":
    # TODO 测试operator_task
    threading_task = threading.Thread(target=operator_task)
    threading_task.start()

    app.debug = True  # 开启快乐幼儿源模式
    app.run()
