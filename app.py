import os
import time

import numpy as np
import pandas as pd
import requests
from aip import AipOcr
from flask import Flask, make_response, render_template, request

app = Flask(__name__)


class Aiocr(object):

    def __init__(self, app_id, api_key, secret_key):
        self._app_id = app_id
        self._api_key = api_key
        self._secret_key = secret_key
        self._client = AipOcr(app_id, api_key, secret_key)

    def proc_form(self, image):
        """ 读取图片 """
        image = self.get_file_content(image)
        """ 调用表格文字识别同步接口 """
        return self._client.tableRecognitionAsync(image);

    def proc_from_res(self, req_id):
        """ 如果有可选参数 """
        options = {"result_type": "excel"}
        """ 带参数调用表格识别结果 """
        return self._client.getTableRecognitionResult(req_id, options)

    def get_file_content(self, file_path):
        with open(file_path, 'rb') as fp:
            return fp.read()

    # 文件下载函数
    def file_download(self, url, file_path):
        r = requests.get(url)
        with open(file_path, 'wb') as f:
            f.write(r.content)


@app.route('/', methods=['GET'])
def index():
    res = make_response(render_template('index.html'))
    return res


@app.route('/uploadImg', methods=['GET', 'POST'])
def uploadImg():
    if request.method == 'GET':
        res = make_response(render_template('index.html'))
        return res
    elif request.method == "POST":
        if 'myImg' in request.files:
            objFile = request.files.get('myImg')
            strFileName = objFile.filename
            strFilePath = "static/myImages/" + strFileName
            objFile.save(strFilePath)
            print(strFilePath)
            name = strFilePath

            """ 你的 APPID AK SK """
            APP_ID = '25436454'
            API_KEY = 'Y9GVo69Y6OF4mv0K7GbULuWP'
            SECRET_KEY = 'XeeRKNYaneDSEmSf77Y41GQx02jwdxcj'
            
            ai_ocr = Aiocr(APP_ID, API_KEY, SECRET_KEY)
            res = ai_ocr.proc_form(name)
            if 'error_code' in res.keys():
                print('Error! error_code: ', res['error_code'])
                sys.exit()
            for req in res['result']:
                resp = ai_ocr.proc_from_res(req['request_id'])
                while not ('error_code' in resp) and not resp['result']['ret_code'] == 3:
                    time.sleep(1)
                    resp = ai_ocr.proc_from_res(req['request_id'])
                    print(resp['result']['ret_msg'])
            
            url = resp['result']['result_data']
            # url = "http://bj.bcebos.com/v1/ai-edgecloud/102576B641A94152B78EF6B412D809F1.xls?authorization=bce-auth-v1%2Fd9272b4e9a38476db4470c2714e1339a%2F2022-01-02T08%3A13%3A30Z%2F172800%2F%2Fa0741ffb96d6a08829a332b1ece6c62b16b422793f9f8dae143c10785734cae0"
            print(url)
            xls_name = os.path.join(name.split('.')[0]) + '.xls'
            ai_ocr.file_download(url, xls_name)
            print('{0} 下载完成。'.format(xls_name))

            # 读取 xls 文件
            global df
            df = pd.read_excel(io=xls_name)
            df_html = df.to_html()
            return f"""
            <head>
                <title>识别结果</title>
                <link rel="stylesheet" href="../static/css/table.css" />
                <link rel="shortcut icon" href="../static/img/icon.JPG"/>
            </head>
                <html>
                    <body>
                    <div class="login">
                        <h2>XJTLU</h2>
                        <p style="color: white; margin-bottom: 20px">请您仔细核对没门课程的分数以及其对应的学分，若识别有误，请重新上传较为清晰的图片。</p>
                        <form  class="login_box" method="post" action="/result" enctype="multipart/form-data">
                            <div class="container" style="overflow:auto">{df_html}</div>
                            <div class="btn">
                                <a href={url} Class=sub>下载表格</a>
                                <input class="sub" type="submit" value="计算均分">
                            </div>
                        </form>
                    </div>
                    </body>
                </html>
            """

        else:
            err = "error"
            return err
    else:
        err = "error"
        return err


@app.route('/result', methods=['GET', 'POST'])
def result():
    if request.method == 'GET':
        res = make_response(render_template('index.html'))
        return res
    elif request.method == "POST":
        # 计算加权平均值
        global df
        elements = df['Mark'].values.tolist()
        elements = list(map(lambda x: x.strip('%'), elements))
        elements = np.array(elements, dtype=np.int8)
        weights = df['Credit'].values.tolist()
        avg = np.average(elements, weights=weights)
        print('Mark:', elements, '\nCredit', weights)
        print("Your weighted average score is:", avg)
        res = make_response(render_template('avg.html', avg=avg))
        return res


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5656, debug=True)
