import xml.etree.ElementTree as ET
import urllib.request

api_key = 'WNJYIARSPD1Y41842SV5X2VR1HK'
url_format = 'http://openapi.work.go.kr/opi/opi/opia/jobSrch.do?authKey={api_key}&returnType=XML&target=JOBDTL&jobGb=1&jobCd={jobCd}&dtlGb=1'

url = url_format.format(api_key = api_key, jobCd= '01111')

tree = ET.parse(urllib.request.urlopen(url))

print("역할 : " + tree.find('jobSum').text)
print("되는 법 : " + tree.find('way').text)

