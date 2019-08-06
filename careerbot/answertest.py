from flask import Flask, request, jsonify
from firebase import firebase
import random
import xml.etree.ElementTree as ET
import urllib.request

app = Flask(__name__)
firebase = firebase.FirebaseApplication("https://gio-careerbot.firebaseio.com/", None)

# 일반 말풍선 출력 / message_list : json list형식
def SendMessage(message_list):
    temp = {
        "version": "2.0",
        "template": {
            "outputs": message_list
        }
    }
    return jsonify(temp)

# 말풍선 + 바로가기 버튼 출력 / message_list, reply_list : json list형식
def SendReply(message_list, reply_list):
    temp = {
        "version": "2.0",
        "template": {
            "outputs": message_list,
            "quickReplies": reply_list
        }
    }
    return jsonify(temp)

# text 을 담은 json 리턴 / 위에 두 메서드와 같이 씀
def makeSimpleText(text):
    dataSend = {
        "simpleText": {
            "text": text
        }
    }
    return dataSend

# 워크넷 직업소개 OPEN API 호출
def callAPI(code):
    api_key = 'WNJYIARSPD1Y41842SV5X2VR1HK'
    url_format = 'http://openapi.work.go.kr/opi/opi/opia/jobSrch.do?authKey={api_key}&returnType=XML&target=JOBDTL&jobGb=1&jobCd={jobCd}&dtlGb=1'

    url = url_format.format(api_key=api_key, jobCd=str(code))

    tree = ET.parse(urllib.request.urlopen(url))

    return tree


# fallback 스킬, context에 따라 멘트 구별
@app.route('/fallback', methods = ['post'])
def fallback():
    req = request.get_json()
    answer = req['userRequest']['utterance']
    Uid = req['userRequest']['user']['id']
    context = req['contexts']

    context_list = []
    for c in context:
        context_list.append(c['name'])

    if len(context) != 0:
        if 'check_career' in context_list: # 진로고민 분기 context
            return SendMessage([makeSimpleText('네/아니오로 다시 한번 대답해주세요')])

        if 'input_name' in context_list:
            firebase.patch('/User/' + Uid, {'name' : answer})
            result = firebase.get('/UI/start/input_age', None)
            return result

        if 'input_age' in context_list:
            return SendMessage([makeSimpleText("Asdfasdf")])


    i = random.randint(0, 2)
    comment = ['무엇을 원하는지 잘 모르겠어요', '이해하기 어려워요', '제가 할 수 있는 일이 아니에요']

    return SendMessage([makeSimpleText(comment[i])]) # 3가지 fallback 멘트중 하나 랜덤출력

# 챗봇 시작 스킬 / 인적사항이 없으면 인적사항 입력블록으로
@app.route('/start', methods = ['post'])
def start_bot():
    req = request.get_json()
    Uid = req['userRequest']['user']['id']

    isNull = firebase.get('/User/' + Uid + '/isNull', None)

    if isNull == None or isNull == 1:
       result = firebase.get('/UI/start/get_information', None)
       firebase.patch('/User/' + Uid, {'isNull' : 1})
       return jsonify(result)

    else:
        result = firebase.get('UI/start/start_bot')
        return jsonify(result)


@app.route('/get_information', methods = ['post'])
def get_information():
    req = request.get_json()
    context = req['contexts']
    Uid = req['userRequest']['user']['id']

    age = req['userRequest']['utterance']
    firebase.patch('/User/' + Uid, {'age' : age})

    return SendMessage([makeSimpleText("")])

# 진로고민 분기 스킬 / 발화조건 => 대답 Entity
@app.route('/career_branch', methods = ['post'])
def career_branch():
    req = request.get_json()
    answer = req['action']['detailParams']['답변']['value'] # 긍정 or 부정

    if answer == '긍정':
        return SendMessage([makeSimpleText('와 준비된 분이시군요?\n\n 어떤 일을 생각하시고 계신가요?')])
    elif answer == '부정':
        result = firebase.get('/UI/career_branch/disagree', None)

        return jsonify(result)
    else:
        return SendMessage([makeSimpleText('예/아니오로 다시 대답해주세요.')])


# 희망진로 스킬
@app.route('/call_worknet', methods=['post'])
def call_worknet():
    req = request.get_json()
    value = req['action']['detailParams']['직업분류']['value']

    tree = callAPI(value)
    dataSend = []
    dataSend.append(makeSimpleText("직무 : " + tree.find('jobSum').text))
    dataSend.append(makeSimpleText("되는 방법 : " + tree.find('way').text))

    return SendMessage(dataSend)


# 흥미검사 스킬
@app.route('/check_interest', methods=['post'])
def check_interest():
    req = request.get_json()
    content = req['action']['detailParams']

    interest = []
    result = ""

    for key in content.keys():
        if content[key]['value'] not in interest:
            interest.append(content[key]['value'])

    reply = []
    for i in interest:
        result = result + i + " "

        re = {
            "messageText": i,
            "action": "message",
            "label": i
        }
        reply.append(re)

    comment = [makeSimpleText("흥미 검사 결과 " + result + "이 나왔습니다. 각 흥미에 대해 알고싶다면 아래 버튼을 눌러주세요")]

    return SendReply(comment, reply)


# 흥미검사 답변 스킬
@app.route('/interest_result', methods=['post'])
def interest_result():
    req = request.get_json()
    content = req['action']['detailParams']

    comment = firebase.get('/UI/interest_result/interest_list', None)

    result = content['흥미검사']['value']
    result = makeSimpleText(comment[result])
    quest = makeSimpleText("흥미있는 직업을 선택해주세요")

    return SendMessage([result, quest])


if __name__ == "__main__":
    app.run(host = '0.0.0.0', port=5000, debug=True)