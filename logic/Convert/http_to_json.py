
import io
import json
import requests

import pandas as pd
from bs4 import BeautifulSoup


session_id = "REDACTED_SESSION_ID"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Whale/4.34.340.10 Safari/537.36",
    "Cookie": f"ASP.NET_SessionId={session_id};",
}

# url = "http://abeek.inha.ac.kr/ReportCurrinfo.aspx?yearterm=20252&haksu_no=MSE3015&bunban=001"
# url = "http://abeek.inha.ac.kr/ReportCurrinfo.aspx?yearterm=20252&haksu_no=MSE3010&bunban=001"
url = "http://abeek.inha.ac.kr/ReportCurrinfo.aspx?yearterm=20252&haksu_no=ARE4411&bunban=003"


res = requests.get(
    url,
    headers=headers,
)
print(res.status_code)

html = res.text
with open('output.html', 'w', encoding='utf-8') as f:
    f.write(html)

soup = BeautifulSoup(html, 'html.parser')

with open('output_pretty.html', 'w', encoding='utf-8') as f:
    table = soup.select_one('#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(15) > td ')
    print(table)
    f.write(table.prettify())
    # f.write(soup.prettify())


def get_text_by_selector(soup, selector):
    element = soup.select_one(selector)
    if element:
        return element.text.strip()
    return ""


data = {
    '교과목명': get_text_by_selector(soup, '#IContents_lblCurrName_Kor'),
    '담당교수명': get_text_by_selector(soup, '#IContents_lblWriteName'),
    '학수번호': get_text_by_selector(soup, "#IContents_lblCurrCode"),
    '분반': get_text_by_selector(soup, "#IContents_lblClass"),
    '학점': get_text_by_selector(soup, "#IContents_lblScoreGusung"),
    '교과목영문명': get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(3) tr:nth-child(2) > td'),
    '강의시간표': get_text_by_selector(soup, "#IContents_lblClassTime"),
    '강좌평가방법"': get_text_by_selector(soup, "#IContents_lblAppraisal"),
    '전공능력 및\n 핵심역량': get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(4) td'),
    '교수프로필(자세히보기)': get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) tr:nth-child(2) td'),
    "강의목표": [
        get_text_by_selector(soup, '#IContents_rptPO_trData_0 > td:nth-child(2)'),
        get_text_by_selector(soup, '#IContents_rptPO_trData_1 > td:nth-child(2)'),
        get_text_by_selector(soup, '#IContents_rptPO_trData_2 > td:nth-child(2)')
    ],
    
    "강의개요" : get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(5) td'),
    "교재" : get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(7) td:nth-child(2) td:nth-child(2)'),
    "부교재및참고도서" : get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(8) td:nth-child(2) td:nth-child(2)'),
    "수업 방법" : get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(9) td'),
    "수강시유의사항" : get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(11) td span#IContents_lbljosim'),
    "특별지원관련" : get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(1) td'),
    "Office Hour\n(상담시간)" : get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(4) > tr:nth-child(5) td:nth-child(2)'),
    "e-learning\n중간고사유형" : get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(11) td'),
    "평가기준": {
        "중간고사": get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(14) > td > table tr:nth-child(2) td:nth-child(1)'),
        "기말고사": get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(14) > td > table tr:nth-child(2) td:nth-child(2)'),
        "출석": get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(14) > td > table tr:nth-child(2) td:nth-child(3)'),
        "과제": get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(14) > td > table tr:nth-child(2) td:nth-child(4)'),
        "퀴즈": get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(14) > td > table tr:nth-child(2) td:nth-child(5)'),
        "토론": get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(14) > td > table tr:nth-child(2) td:nth-child(6)'),
        "기타": get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(14) > td > table tr:nth-child(2) td:nth-child(7)'),
        "계": get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(14) > td > table tr:nth-child(2) td:nth-child(8)'),
    },
    "평가기준\n세부내역" : get_text_by_selector(soup, '#container .contents > div:nth-child(2) > table:nth-child(5) > tr:nth-child(15) > td'),
    "주차별 강의진행계획서" : {
        "1주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_0 > td.type"),
        "강의방식": "",
        "강의내용": get_text_by_selector(soup, "#IContents_rptList_trData2_0 > td:nth-child(2)"),
        },
        "2주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_1 > td.type"),
        "강의방식": "",
        "강의내용": get_text_by_selector(soup, "#IContents_rptList_trData2_1 > td:nth-child(2)"),
        },
        "3주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_2 > td.type"),
        "강의방식": "",
        "강의내용": get_text_by_selector(soup, "#IContents_rptList_trData2_2 > td:nth-child(2)"),
        },
        "4주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_3 > td.type"),
        "강의방식": "",
        "강의내용": get_text_by_selector(soup, "#IContents_rptList_trData2_3 > td:nth-child(2)"),
        },
        "5주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_4 > td.type"),
        "강의방식": "",
        "강의내용": get_text_by_selector(soup, "#IContents_rptList_trData2_4 > td:nth-child(2)"),
        },
        "6주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_5 > td.type"),
        "강의방식": "",
        "강의내용": get_text_by_selector(soup, "#IContents_rptList_trData2_5 > td:nth-child(2)"),
        },
        "7주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_6 > td.type"),
        "강의방식": "",
        "강의내용": get_text_by_selector(soup, "#IContents_rptList_trData2_6 > td:nth-child(2)"),
        },
        "8주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_7 > td.type"),
        "강의방식": "",
        "강의내용": get_text_by_selector(soup, "#IContents_rptList_trData2_7 > td:nth-child(2)"),
        },
        "9주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_8 > td.type"),
        "강의방식": "",
        "강의내용": get_text_by_selector(soup, "#IContents_rptList_trData2_8 > td:nth-child(2)"),
        },
        "10주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_9 > td.type"),
        "강의방식": "",
        "강의내용": get_text_by_selector(soup, "#IContents_rptList_trData2_9 > td:nth-child(2)"),
        },
        "11주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_10 > td.type"),
        "강의방식": "",
        "강의내용": get_text_by_selector(soup, "#IContents_rptList_trData2_10 > td:nth-child(2)"),
        },
        "12주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_11 > td.type"),
        "강의방식": "",
        "강의내용": get_text_by_selector(soup, "#IContents_rptList_trData2_11 > td:nth-child(2)")
        },
        "13주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_12 > td.type"),
        "강의방식": "",
        "강의내용": get_text_by_selector(soup, "#IContents_rptList_trData2_12 > td:nth-child(2)"),
        },
        "14주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_13 > td.type"),
        "강의방식": "",
        "강의내용": get_text_by_selector(soup, "#IContents_rptList_trData2_13 > td:nth-child(2)")
        },
        "15주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_14 > td.type"),
        "강의방식": "",
        "시험및과제": get_text_by_selector(soup, "#IContents_rptList_trData2_14 > td:nth-child(2)")
        },
        "16주차": {
        "강의주제": get_text_by_selector(soup, "#IContents_rptList_trData_15 > td.type"),
        }
    }
}

with open('output.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
