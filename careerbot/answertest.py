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

    context_list = []
    for c in context:
        context_list.append(c['name'])

    if len(context) != 0:
        if 'check_career' in context_list: # 진로고민 분기 context
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

        reply = [
                {
                "messageText": "정서문제로 힘들어요",
                "action": "block",
                "blockId": '5d30223b92690d00011f3bf9',
                "label": "정서문제"
            },
                {
                "messageText": "정보가 부족해요",
                "action": "block",
                "blockId": '5d2ff688ffa748000122d00f',
                "label": "정보탐색 부족"
            },
                {
                "messageText": "저를 잘 모르겠어요",
                "action": "block",
                "blockId": '5d37f6c0ffa748000122f068',
                "label": "자기이해 부족"
            },
                {
                "messageText": "주변 상황에 어려움이 있어요",
                "action": "block",
                "blockId": '5d2ffd4d8192ac000132b7f4',
                "label": "외부환경 문제"
            }
        ]

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

# 흥미검사 스킬
@app.route('/check_interest', methods=['post'])
def check_interest():
    req = request.get_json()
    content = req['action']
    content = content['detailParams']

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
    content = req['action']
    content = content['detailParams']

    comment = {
        "현실형" : "특징\n분명하고 질서정연하고 체계적인 것을 좋아하고, 연장/기계를 조작하는 활동내지는 기술에 흥미로워 함"
                "\n\n성격\n현실적이고 신중한 성격"
                "\n\n선호하는 직업\n기술자, 가동기계 및 항공기 조종사, 정비사, 농부, 엔지니어, 전기.기계기사, 군인,경찰,소방관,운동선수 등",
        "탐구형" : "특징\n관찰적,상직적,체계적이며 물리적,생물학적,문화적 현상의 창조적인 탐구를 수반하는 활동을 흥미로워 함"
                "\n\n성격\n분석적이고 지적인 성격"
                "\n\n선호하는 직업\n언어학자, 심리학자, 시장 조사분석가, 과학자, 생물학자, 화학자, 물리학자, 인류학자, 지질학자, 경영 분석가 등",
        "예술형" : "특징\n예술/창조적 표현, 변화와 다양성을 선호하고 틀에 박힌 것 보다는 자유롭고, 상징적인 활동에 흥미로워 함"
                "\n\n성격\n경험에 대해 개방적인 성격"
                "\n\n선호하는 직업\n예술가, 작곡가, 음악가, 무대감독, 작가, 배우, 소설가, 미술가, 무용가, 디자이너, 광고, 기획자 등",
        "사회형" : "특징\n타인의 문제를 듣고, 이해하고, 잘 도와주며 치료해주고 봉사하는 활동에 흥미로워 함"
                "\n\n성격\n배려심과 친화력이 있는 성격"
                "\n\n선호하는 직업\n사회복지사, 교육자, 간호사, 유치원 교사, 종교지도자, 상담가, 임상치료가, 언어치료사 등",
        "관습형" : "특징\n정해진 원칙과 계획에 따라 자료를 정리/조작하는 일을 좋아하고 체계적인 작업환경에서 사무적, 계산적 능력을 발휘하는 활동에 흥미로워 함"
                "\n\n성격\n조용하고 차분한 성격"
                "\n\n선호하는 직업\n공인회계사, 경제분석가, 세무사, 경리사원, 감사원, 안전관리사, 사서, 법무사, 의무기록사, 은행사무원 등",
        "진취형" : "특징\n조직의 목적과 이익을 얻기 위해 타인을 지도/계획/통제/관리 일과 그 결과로 얻어지는 명예/권위에 흥미로워 함"
                "\n\n성격\n진취적이고 외향적인 성격"
                "\n\n선호하는 직업\n기업경영인, 정치가, 판사, 영업사원, 상품구매인, 보험회사원, 판매원, 연출가, 변호사 등"
    }

    result = content['흥미검사']['value']
    result = makeSimpleText(comment[result])
    quest = makeSimpleText("흥미있는 직업을 선택해주세요")

    return SendMessage([result, quest])


if __name__ == "__main__":
    app.run(host = '0.0.0.0', port=5000, debug=True)