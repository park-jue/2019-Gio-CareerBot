from flask import Flask, request, jsonify
import random
import xml.etree.ElementTree as ET
import urllib.request

app = Flask(__name__)

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
    context = req['contexts']

    if len(context) != 0:
        if context[0]['name'] == 'check_career': # 진로고민 분기 context
            return SendMessage([makeSimpleText('네/아니오로 다시 한번 대답해주세요')])

    i = random.randint(0, 2)
    comment = ['무엇을 원하는지 잘 모르겠어요', '이해하기 어려워요', '제가 할 수 있는 일이 아니에요']

    return SendMessage([makeSimpleText(comment[i])]) # 3가지 fallback 멘트중 하나 랜덤출력

# 진로고민 분기 스킬 / 발화조건 => 대답 Entity
@app.route('/career_branch', methods = ['post'])
def career_branch():
    req = request.get_json()
    answer = req['action']
    answer = answer['detailParams']
    answer = answer['답변']
    answer = answer['value'] # 긍정 or 부정

    if answer == '긍정':
        return SendMessage([makeSimpleText('어떤 진로를 희망하고 있나요?')])
    elif answer == '부정':
        comment = []
        comment.append(makeSimpleText('네 진로를 결정하는게 쉽지는 않지요.\n그래도 이렇게 상담을 통해 진로고민을 해결하려고 시도하신 것은 참 잘하신 것 같습니다.'))
        comment.append(makeSimpleText('제가 몇가지 질문을 하면서 진로를 정할 수 있도록 돕도록 할게요 ^^'))
        comment.append(makeSimpleText('진로를 결정하지 못한 이유는 무엇인지 먼저 알려주세요.'))

        reply1 = {
            "messageText": "정서문제로 힘들어요",
            "action": "block",
            "blockId": '5d30223b92690d00011f3bf9',
            "label": "정서문제"
        }

        reply2 = {
            "messageText": "정보가 부족해요",
            "action": "block",
            "blockId": '5d2ff688ffa748000122d00f',
            "label": "정보탐색 부족"
        }

        reply3 = {
            "messageText": "저를 잘 모르겠어요",
            "action": "block",
            "blockId": '5d37f6c0ffa748000122f068',
            "label": "자기이해 부족"
        }

        reply4 = {
            "messageText": "주변 상황에 어려움이 있어요",
            "action": "block",
            "blockId": '5d2ffd4d8192ac000132b7f4',
            "label": "외부환경 문제"
        }

        reply = [reply1, reply2, reply3, reply4]
        return SendReply(comment, reply)
    else:
        return SendMessage([makeSimpleText('예/아니오로 다시 대답해주세요.')])

# 희망진로 스킬
@app.route('/call_worknet', methods=['post'])
def call_worknet():
    req = request.get_json()
    content = req['action']
    content = content['detailParams']
    params = content['직업분류']
    value = params['value']

    tree = callAPI(value)
    dataSend = []
    dataSend.append(makeSimpleText("직무 : " + tree.find('jobSum').text))
    dataSend.append(makeSimpleText("되는 방법 : " + tree.find('way').text))

    return SendMessage(dataSend)


if __name__ == "__main__":
    app.run(host = '0.0.0.0', port=5000, debug=True)