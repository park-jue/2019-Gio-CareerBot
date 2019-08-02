from flask import Flask, request, jsonify
import xml.etree.ElementTree as ET
import urllib.request

app = Flask(__name__)

def callAPI(code):
    api_key = 'WNJYIARSPD1Y41842SV5X2VR1HK'
    url_format = 'http://openapi.work.go.kr/opi/opi/opia/jobSrch.do?authKey={api_key}&returnType=XML&target=JOBDTL&jobGb=1&jobCd={jobCd}&dtlGb=1'

    url = url_format.format(api_key=api_key, jobCd=str(code))

    tree = ET.parse(urllib.request.urlopen(url))

    return tree

def makeSimpleText(text):
    dataSend = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": text
                    }
                }
            ]
        }
    }
    return jsonify(dataSend)


@app.route('/test', methods = ['post'])
def hello_world():
    req = request.get_json()
    content = req['action']
    content = content['detailParams']
    params = content['직업분류']
    value = params['value']



    if params!= None:
        tree = callAPI(value)
        dataSend = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "직무 : " + tree.find('jobSum').text
                        }
                    },
                    {
                        "simpleText": {
                            "text": "되는 방법 : " + tree.find('way').text
                        }
                    }
                ]
            }
        }
        return jsonify(dataSend)

    else:
        dataSend = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "직업이 없나봐"
                        }
                    }
                ]
            }
        }
        return jsonify(dataSend)



if __name__ == "__main__":
    app.run(host = '0.0.0.0', port=5000, debug=True)