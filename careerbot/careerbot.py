from flask import Flask, request, jsonify
from firebase import firebase
import operator
import json
import random
import xml.etree.ElementTree as ET
import urllib.request

app = Flask(__name__)
firebase = firebase.FirebaseApplication("https://gio-careerbot-c1797.firebaseio.com/", None)

# 일반 말풍선 출력 템플릿 / message_list : json list형식
def SendMessage(message_list):
    temp = {
        "version": "2.0",
        "template": {
            "outputs": message_list
        }
    }
    return jsonify(temp)

# 말풍선 + 바로가기 버튼 출력 템플릿 / message_list, reply_list : json list형식
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
        if 'check_career' in context_list: # 진로고민 분기 context fallback
            return SendMessage([makeSimpleText('네/아니오로 다시 한번 대답해주세요')])

        elif 'input_name' in context_list: # 인적사항_입력 context
            firebase.patch('/User/' + Uid, {'name' : answer})
            result = firebase.get('/UI/start/input_age', None)
            return result

        elif 'input_experience' in context_list: # 전공입력 후 인적사항 입력 끝!
            firebase.patch('/User/' + Uid, {'experience': answer})
            firebase.patch('/User/' + Uid, {'isNull' : 0}) # 인적사항이 다 입력되면 isNull == 0
            return SendMessage([makeSimpleText("인적사항 입력이 끝났습니다!\n상담을 진행하시려면 아래 상담 시작하기 버튼을 눌러주세요.")])

        elif 'mbti_check' in context_list : # mbti 검사 context fallback
            return SendMessage([makeSimpleText('성격유형을 확인한 후 다시 한번 입력해주세요.')])

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
       return jsonify(result)

    else:
        result = firebase.get('/UI/start/start_bot', None)
        return jsonify(result)


@app.route('/get_information', methods = ['post'])
def get_information():
    req = request.get_json()
    context = req['contexts']
    Uid = req['userRequest']['user']['id']

    context_list = []
    for c in context:
        context_list.append(c['name'])

    # 이름/ 직무경험은 fallback스킬로 받음

    if 'input_sex' in context_list:  # 성별 입력 context 일경우
        sex = req['action']['detailParams']['sex']['value']
        firebase.patch('/User/' + Uid, {'sex' : sex})

    else: # 나이 입력
        age = req['userRequest']['utterance']
        firebase.patch('/User/' + Uid, {'age' : age})

    return SendMessage([makeSimpleText("")])

# 분기 스킬 / 발화조건 => 대답 Entity
@app.route('/branch', methods = ['post'])
def branch():
    req = request.get_json()
    answer = req['action']['detailParams']['답변']['value'] # 긍정 or 부정
    context = req['contexts']

    context_list = []
    for c in context:
        context_list.append(c['name'])

    if 'check_career' in context_list: # 진로_분기
        if answer == '긍정':
            return SendMessage([makeSimpleText('와 준비된 분이시군요?\n\n 어떤 일을 생각하시고 계신가요?')])
        else:
            result = firebase.get('/UI/career_branch/disagree', None)
            return jsonify(result)

    else: #직업선택_분기
        if answer == '긍정':
            result = firebase.get('/UI/result_branch/agree', None)
            return jsonify(result)
        else:
            result = makeSimpleText(firebase.get('/UI/result_branch/disagree', None))
            return SendMessage([result])

    return SendMessage([makeSimpleText('')])


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
    Uid = req['userRequest']['user']['id']
    context = req['contexts']

    content = req['action']['detailParams']['number']['value']
    index = req['action']['detailParams']['index']['value']

    firebase.patch("/User/" + Uid + "/interest_inventory/check_interest", { index: int(content) })

    if context[0]['name'] == 'check_interest_6':
        result = firebase.get('/User/' + Uid + "/interest_inventory/check_interest", None)
        result_sort = sorted(result.items(), key=operator.itemgetter(1), reverse=True)

        interest_list = []
        for r in result_sort:
            if len(interest_list) >= 2:
                if r[1] == result[interest_list[len(interest_list) - 1]]:
                    interest_list.append(r[0])
                    continue
                break

            interest_list.append(r[0])

        firebase.patch('/User/' + Uid + '/interest_inventory', {"interest" : interest_list})

        reply = []
        interest = ""
        for i in interest_list:
            interest = interest + i + " "

            re = {
                "messageText": i,
                "action": "message",
                "label": i
            }
            reply.append(re)

        comment = [makeSimpleText("흥미 검사 결과 " + interest + "이 나왔습니다. 각 흥미에 대해 알고싶다면 아래 버튼을 눌러주세요")]

        return SendReply(comment, reply)

    return SendMessage([makeSimpleText("")])

# 흥미검사 결과 스킬
@app.route('/interest_result', methods = ['post'])
def interest_result():
    req = request.get_json()
    content = req['action']['detailParams']

    comment = firebase.get('/UI/interest_result/interest_list', None)

    result = content['흥미검사']['value']
    result = makeSimpleText(comment[result])

    reply = []
    re = {
        "messageText": "뒤로",
        "action": "block",
        "blockId" : "5d4bb3988192ac0001b43e2e",
        "label": "뒤로"
    }
    reply.append(re)

    return SendReply([result], reply)

# 흥미검사 결과 - 뒤로가기 스킬
@app.route('/interest_back', methods = ['post'])
def interest_back():
    req = request.get_json()
    Uid = req['userRequest']['user']['id']

    interest_list = firebase.get('/User/' + Uid + "/interest_inventory/interest", None)
    reply = []
    interest = ""
    for i in interest_list:
        interest = interest + i + " "

        re = {
            "messageText": i,
            "action": "message",
            "label": i
        }
        reply.append(re)

    comment_1 = makeSimpleText("흥미 검사 결과 " + interest + "이 나왔습니다. 각 흥미에 대해 알고싶다면 아래 버튼을 눌러주세요.")
    comment_2 = makeSimpleText("유형별 대표직업을 확인했습니다. 그중 마음에 드는 직업을 선택하셨나요??")

    return SendReply([comment_1, comment_2], reply)

# 흥미검사 _ 직업 선택
@app.route('/select_job', methods = ['post'])
def select_job():
    req = request.get_json()
    Uid = req['userRequest']['user']['id']
    job = req['action']['detailParams']
    i = 0

    for i in range(0, 3):
        name = "job_" + str(i+1)
        firebase.patch('/User/' + Uid + "/cal_job", {i : {"name" : job[name]['value'], "score" : -1}})
        i += 1

    return SendMessage([makeSimpleText("")])

# 흥미검사 _ 직업 점수 계산
@app.route('/calculate_job', methods = ['post'])
def calculate_job():
    req = request.get_json()
    Uid = req['userRequest']['user']['id']
    context = req['contexts']
    user = firebase.get('/User/' + Uid + "/name", None)

    context_list = []
    for c in context:
        context_list.append(c['name'])

    sum = 0
    number = req['action']['detailParams']

    for n in number.keys():
        sum += int(json.loads(number[n]['value']))

    next_job = ""
    job = firebase.get('/User/' + Uid + '/cal_job', None)
    for i in range(0, 3):
        if job[i]["score"] == -1:
            firebase.patch('/User/' + Uid + "/cal_job/" + str(i), {"score" : sum})

            if 'calculate_3' not in context_list:
                next_job = job[i+1]['name']

            break

    if 'calculate_3' in context_list: # 3번째 직업 점수 매겼을 경우
        result = firebase.get('/User/' + Uid + '/cal_job', None)
        max = 0
        rec_job = ""
        for i in range(0, 3):
            if result[i]['score'] > max:
                max = result[i]['score']
                rec_job = result[i]['name']

        comment = []
        comment.append(makeSimpleText("3가지 직업중 '" + rec_job + "'직업을 가장 선호하시는군요."))
        comment.append(makeSimpleText("잘 결정하셨네요^^ " + user + "님은 잘하실 수 있을 겁니다. "))
        comment.append(makeSimpleText("이 직업의 간단한 정보를 안내해 드릴게요"))

        return SendMessage(comment)

    comment = []
    comment.append(makeSimpleText("다음으로 " + next_job + "에 대한 점수를 매겨주세요."))
    comment.append(makeSimpleText(firebase.get('/UI/interest_result/calculate_job', None)))

    return SendMessage(comment)

# 성격검사 스킬
@app.route('/check_MBTI', methods = ['post'])
def check_MBTI():
    req = request.get_json()
    Uid = req['userRequest']['user']['id']
    context = req['contexts']
    user = firebase.get('/User/' + Uid + "/name", None)

    context_list = []
    for c in context:
        context_list.append(c['name'])

    mbti = firebase.get('/User/' + Uid + '/MBTI', None)

    input_mbti = req['action']['detailParams']['mbti']['value']

    if 'mbti_1' not in context_list:
        input_mbti = mbti + input_mbti

    firebase.patch('/User/' + Uid, {'MBTI': input_mbti})

    if 'mbti_4' in context_list:
        mbti = firebase.get('/User/' + Uid + '/MBTI', None)

        comment = makeSimpleText(user + '님의 ' + firebase.get('/UI/mbti/' + mbti + '/description', None))
        career = makeSimpleText('추천직업으로는 ' + firebase.get('/UI/mbti/' + mbti + '/career', None) + '가 있어요')
        qes = makeSimpleText("성격유형별 대표직업을 확인했습니다. 그중 마음에 드는 직업을 선택하셨나요??")

        return SendMessage([comment, career, qes])

    return SendMessage([makeSimpleText('')])




if __name__ == "__main__":
    app.run(host = '0.0.0.0', port=5000, debug=True)