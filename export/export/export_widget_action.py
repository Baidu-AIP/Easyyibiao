
import os
import sys
import re
import json
import requests
import hashlib

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QDialog, QDesktopWidget, QMessageBox

from .exportWin import Ui_Dialog
from export.database.operation import SqLite
from export.progress_bar.progress_bar import UiUpload

# os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(os.path.dirname(sys.argv[0]), 'cacert.pem')


class ExportWindow(QDialog, Ui_Dialog):
    def __init__(self, parent=None):
        super(ExportWindow, self).__init__(parent)
        self.setupUi(self)
        self.center()
        self.parent = parent
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedSize(self.width(), self.height())
        self.api_key = ''
        self.secret_key = ''
        self.access_token = ''
        self.dataset_dict = dict()
        self.db = SqLite()
        self.open_dir = self.parent.lastOpenDir
        self.file_source_text.setHtml(self.open_dir)
        if self.get_key():
            token = self.get_key()
            self.akLineEdit.setText(token['ak'])
            self.skLineEdit.setText(token['sk'])
        self.crash_button.clicked.connect(self.crush_click)
        self.dataset_comboBox.currentTextChanged.connect(self.set_version)
        self.comfire_button.clicked.connect(self.upload)
        self.cancle_button.clicked.connect(self.cancel)
        self.progress_bar = ProgressBar()
        self.ak_confirm_flag = 0
        self.sk_confirm_flag = 0

    def upload(self):
        # 检查必填项是否为空
        if not self.akLineEdit.text() or not self.skLineEdit.text():
            self.show_warning('AK或SK为空!')
            return

        if self.dataset_comboBox.currentIndex() < 0 or self.version_comboBox.currentIndex() < 0:
            self.show_warning('数据集或版本为空!')
            return

        # 获取上传方式，数据集ID
        upload_type = 1 if self.incremental_upload.isChecked() else 2   # 1增量/2全量
        status, msg = self.get_dataset_id()
        if status == -1:
            self.show_information(msg)
            return
        dataset_id = msg

        # 获取label文件
        status, msg = self.get_labeled_file()
        if status == -1:
            self.show_information(msg)
            return
        elif status == 0:
            self.show_error(msg)
            return
        md5_dict, label_dict = msg

        # 检查AK SK是否修改
        access_token = self.check_token()
        if not access_token:
            return
        else:
            if access_token != self.access_token:
                self.show_warning('AK SK与所选数据集AK SK不一致，请刷新数据集列表')
                return

        # 上传数据
        upload = UploadLabelData(dataset_id, md5_dict, label_dict, upload_type, self)
        upload.upload_signal.connect(self.upload_recall)
        upload.progress_signal.connect(self.progress_recall)
        upload.start()
        self.close()

    def progress_recall(self, tup):
        self.progress_bar.show()
        total, value = tup
        self.progress_bar.change_progressbar_value(total, value)
        if value == total:
            self.show_upload_end(total)

    def show_upload_end(self, total):
        QMessageBox.information(self, 'OK', '导出已完成, 共成功导出%d张<html><head/><body><p><a href=\"https://ai.baidu.com/easydata/app/dataset/list\"><span style=\" text-decoration: underline; color:#0000ff;\">前往查看</span></a></p></body></html>' % total)

    def upload_recall(self, tup):
        status, msg = tup
        if status == -1:
            self.progress_bar.close()
            self.show_error(msg)
        elif status == 0:
            self.show_information(msg)

    def get_labeled_file(self):
        files = os.listdir(self.open_dir)
        json_file = []
        for file in files:
            if file.endswith('.json'):
                json_file.append(os.path.join(self.open_dir, file))
        if len(json_file) == 0:
            return -1, '该路径下没有已标注文件'

        label_dict = {}
        md5_dict = {}
        for file in json_file:
            with open(file, 'r', encoding='utf8') as f:
                content = json.loads(f.read())

                labels = []
                for label in content['shapes']:
                    if label['shape_type'] != 'rectangle':
                        return 0, str(file) + '标注格式有误'
                    labels.append({
                        'name': label['label'],
                        'x1': label['points'][0][0],
                        'y1': label['points'][0][1],
                        'x2': label['points'][1][0],
                        'y2': label['points'][1][1]
                    })

            data = {
                'fileContent': content['imageData'],
                'from': 'labelme',
                'labels': labels
            }
            md5 = hashlib.md5(str(content).encode('utf-8')).hexdigest()
            md5_dict[file] = md5
            label_dict[file] = data

        return 1, (md5_dict, label_dict)

    def get_dataset_id(self):
        dataset_name = self.dataset_comboBox.currentText()
        version = self.version_comboBox.currentText()
        dataset_id = self.dataset_dict[dataset_name][version]['id']
        if self.dataset_dict[dataset_name][version]['isImporting']:
            return -1, '该数据集正在导入，不可选取'
        elif self.dataset_dict[dataset_name][version]['isPublished']:
            return -1, '该数据集已发布，不可选取'
        elif self.dataset_dict[dataset_name][version]['isTraining']:
            return -1, '该数据集正在训练，不可选取'
        elif self.dataset_dict[dataset_name][version]['isInterAnnoing']:
            return -1, '该数据集正在智能标注，不可选取'
        elif self.dataset_dict[dataset_name][version]['isEtling']:
            return -1, '该数据集正在进行清洗，不可选取'
        elif self.dataset_dict[dataset_name][version]['isTeamAnnoing']:
            return -1, '该数据集正在进行团队标注， 不可选取'
        else:
            return 1, dataset_id

    def set_version(self):
        dataset_name = self.dataset_comboBox.currentText()
        if dataset_name == '请选择数据集' or dataset_name == '':
            return
        self.version_comboBox.clear()
        version_list = [vsn for vsn in self.dataset_dict[dataset_name].keys()]
        self.version_comboBox.addItems(version_list)

    def crush_click(self):
        """ get dataset list """
        self.api_key = self.akLineEdit.text()
        self.secret_key = self.skLineEdit.text()
        if not self.akLineEdit.text() or not self.skLineEdit.text():
            self.show_warning('AK或SK为空!')
        else:
            flag = self.get_token()
            if flag:
                self.get_dataset_list()

    def get_dataset_list(self):
        get_dataset = GetDataset(parent=self)
        status, msg = get_dataset.get_dataset_list()
        if status == -1:
            self.show_error(msg)
            return

        if len(msg['items']) == 0:
            self.show_warning('数据集为空，请新建数据集')
            return

        dataset_list = []
        for group in msg['items']:
            dataset_list.append(group['name'])
            self.dataset_dict[group['name']] = {}
            for version in group['versions']:
                vsn = 'V' + str(version['versionId'])
                self.dataset_dict[group['name']][vsn] = version

        self.dataset_comboBox.clear()
        self.version_comboBox.clear()
        self.dataset_comboBox.addItems(dataset_list)

    def check_token(self):
        sql = "SELECT access_token FROM token WHERE ak = '%s' AND sk = '%s' " % \
              (self.akLineEdit.text(), self.skLineEdit.text())
        data = self.db.execute(sql).fetchone()

        if data:
            access_token = data['access_token']
        else:
            get_token = GetAccessToken(self.akLineEdit.text(), self.skLineEdit.text())
            status, msg = get_token.token()
            if status == 1:
                access_token = msg
            else:
                if msg == 'unknown client id':
                    msg = 'AK不正确'
                elif msg == 'Client authentication failed':
                    msg = 'SK不正确'
                self.show_error(msg)
                return
        return access_token

    def get_token(self):
        sql = "SELECT access_token FROM token WHERE ak = '%s' AND sk = '%s' " % \
              (self.akLineEdit.text(), self.skLineEdit.text())
        data = self.db.execute(sql).fetchone()

        if data:
            self.access_token = data['access_token']
        else:
            get_token = GetAccessToken(self.api_key, self.secret_key)
            status, msg = get_token.token()
            if status == 1:
                self.access_token = msg
                sql = "INSERT INTO token (ak, sk, access_token) VALUES ('%s', '%s', '%s')" \
                      % (self.api_key, self.secret_key, self.access_token)
                self.db.execute(sql)
            else:
                if msg == 'unknown client id':
                    msg = 'AK不正确'
                elif msg == 'Client authentication failed':
                    msg = 'SK不正确'
                self.show_error(msg)
                return
        return True

    def get_key(self):
        return self.db.execute("SELECT ak, sk FROM token ORDER BY id DESC LIMIT 1").fetchone()

    def show_information(self, msg):
        QMessageBox.information(self, '', msg)

    def show_warning(self, msg):
        QMessageBox.warning(self, 'Warning', msg)

    def show_error(self, msg):
        QMessageBox.critical(self, 'Error', msg)

    def center(self):
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) / 2,
                  (screen.height() - size.height()) / 2)

    def cancel(self):
        self.close()


class UploadLabelData(QThread):
    upload_signal = pyqtSignal(tuple)
    progress_signal = pyqtSignal(tuple)

    def __init__(self, dataset_id, md5_dict, label_dict, upload_type, parent=None):
        super(UploadLabelData, self).__init__(parent)
        self.dataset_id = dataset_id
        self.md5_dict = md5_dict
        self.label_dict = label_dict
        self.parent = parent
        self.open_dir = self.parent.open_dir
        self.dir_id = -1
        self.access_token = self.parent.access_token
        self.upload_type = upload_type
        self.db = self.parent.db
        self.diff_list = []

    def run(self):
        self.get_dir_id()
        if self.upload_type == 1:
            status = self.increment_upload()
            if status == -1:
                return
        else:
            status = self.full_upload()
            if status == -1:
                return

    def get_dir_id(self):
        # 获取dir_id
        sql = "SELECT id FROM dir WHERE dirname = '%s' " % self.open_dir
        data = self.db.execute(sql).fetchone()
        if not data:
            insert = "INSERT INTO dir (dirname) VALUES ('%s') " % self.open_dir
            self.db.execute(insert)
            dir_sql = "SELECT id FROM dir WHERE dirname = '%s' " % self.open_dir
            dir_data = self.db.execute(dir_sql).fetchone()
            self.dir_id = dir_data['id']
        else:
            self.dir_id = data['id']

    def increment_upload(self):
        sql = "SELECT distinct dir_id FROM diff WHERE dir_id = %d " % self.dir_id
        data = self.db.execute(sql).fetchone()
        if not data:
            # 等同全量上传
            status = self.full_upload()
            if status == -1:
                return -1
        else:
            md5_sql = "SELECT md5 FROM diff WHERE dir_id = %d " % self.dir_id
            md5_data = self.db.execute(md5_sql).fetchall()
            old_md5_set = set()
            for row in md5_data:
                old_md5_set.add(row['md5'])

            # 查找修改文件
            changed_file = []
            for filename, md5 in self.md5_dict.items():
                if md5 not in old_md5_set:
                    changed_file.append(filename)

            # 判断是否没有修改
            if len(changed_file) == 0:
                self.upload_signal.emit((0, '没有新的标注信息!'))
                return -1

            # 上传数据
            num = len(changed_file)
            n = 0
            for f in changed_file:
                status = self.post_data(self.label_dict[f], f)
                if status == -1:
                    return -1
                self.diff_list.append(self.md5_dict[f])
                n += 1
                self.progress_signal.emit((num, n))

            # 更新diff
            self.update_diff()
            return 1

    def full_upload(self):
        num = len(self.label_dict)
        n = 0
        for filename, label_data in self.label_dict.items():
            status = self.post_data(label_data, filename)
            if status == -1:
                return -1
            self.diff_list.append(self.md5_dict[filename])
            n += 1
            self.progress_signal.emit((num, n))
        self.update_diff()
        return 1

    def update_diff(self):
        values = ""
        for row in self.md5_dict.values():
            values += "{},".format((self.dir_id, row))
        values = values.rstrip(',')

        delete_sql = "DELETE FROM diff WHERE dir_id = %d " % self.dir_id
        self.db.execute(delete_sql)

        insert_sql = "INSERT INTO diff (dir_id, md5) VALUES " + values
        self.db.execute(insert_sql)

    def update_diff_when_err(self):
        if len(self.diff_list) == 0:
            return
        values = ""
        for row in self.diff_list:
            values += "{},".format((self.dir_id, row))
        values = values.rstrip(',')

        insert_sql = "INSERT INTO diff (dir_id, md5) VALUES " + values
        self.db.execute(insert_sql)

    def post_data(self, data, filemane):
        url = 'https://aip.baidubce.com/rpc/2.0/easydata/dataset/addEntity?access_token='
        url = url + self.access_token
        headers = {
            "Content-Type": "application/json"
        }
        data['datasetId'] = self.dataset_id
        data = json.dumps(data)

        try:
            resp = requests.post(url=url, data=data, headers=headers)
            if resp.status_code != 200:
                if resp.status_code == 413:
                    msg = '%s: <br>%s' % (str(filemane), '该图片过大')
                    self.upload_signal.emit((-1, msg))
                    self.update_diff_when_err()
                else:
                    pattern = re.compile(r'<head><title>([\w\d\s]+)</title></head>')
                    search = re.search(pattern, resp.text)
                    err = search.group(1) if search else '请求错误 %d' % resp.status_code
                    msg = '%s: <br>%s' % (str(filemane), err)
                    self.upload_signal.emit((-1, msg))
                    self.update_diff_when_err()
                return -1
            resp = resp.json()
            if 'error_msg' in resp:
                msg = '%s: <br>%s' % (str(filemane), resp['error_msg'])
                self.upload_signal.emit((-1, msg))
                self.update_diff_when_err()
                return -1
        except Exception as e:
            msg = '%s: <br>%s' % (str(filemane), str(e))
            self.upload_signal.emit((-1, msg))
            self.update_diff_when_err()
            return -1
        return 1


class GetDataset(QThread):

    def __init__(self, parent=None):
        super(GetDataset, self).__init__(parent)
        self.parent = parent
        self.db = self.parent.db
        self.access_token = self.parent.access_token

    def get_dataset_list(self):
        url = 'https://aip.baidubce.com/rpc/2.0/easydata/dataset/simpleList?access_token='
        url = url + self.access_token
        data = {
            "from": "labelme",
            "projectType": 2,
            "templateType": 200
        }
        data = json.dumps(data)
        headers = {
            "Content-Type": "application/json"
        }

        try:
            resp = requests.post(url=url, data=data, headers=headers, timeout=30)
            resp = resp.json()
            if 'error_code' not in resp:
                return 1, resp
            else:
                if resp['error_code'] == 110:
                    get_token = GetAccessToken(self.parent.api_key, self.parent.secret_key)
                    status, msg = get_token.token()
                    if status == 1:
                        sql = "UPDATE token set access_token = '%s' where ak = '%s' and sk = '%s' " \
                              % (msg, self.parent.api_key, self.parent.secret_key)
                        self.db.execute(sql)
                        self.access_token = msg
                        self.get_dataset_list()
                    else:
                        return -1, msg
                else:
                    msg = resp['error_msg']
                    return -1, msg

        except Exception as e:
            return -1, str(e)


class GetAccessToken:
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key

    def token(self):
        token_url = 'https://aip.baidubce.com/oauth/2.0/token?'
        params = {
            'grant_type': 'client_credentials',
            'client_id': self.api_key,
            'client_secret': self.secret_key
        }

        try:
            resp = requests.get(token_url, params=params).json()
            if 'error' not in resp.keys():
                access_token = resp.get('access_token', '')
                return 1, access_token
            else:
                return -1, resp['error_description']
        except Exception as e:
            return -1, str(e)


class ProgressBar(QDialog, UiUpload):
    def __init__(self, auto_close=True, parent=None):
        super(ProgressBar, self).__init__(parent)
        self.setupUi(self)
        self.progressBar.setValue(0)
        self.auto_close = auto_close

    def change_progressbar_value(self, total, value):
        percent = int(value / total * 100)
        self.progressBar.setValue(percent)
        self.label_2.setText("%d%%(%d/%d)" % (percent, value, total))
        if self.auto_close and total == value:
            self.close()
