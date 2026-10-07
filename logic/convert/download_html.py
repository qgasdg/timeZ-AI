import os
import time
import json
import traceback
import pandas as pd
import re
from urllib.parse import urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoAlertPresentException
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup

# ==============================
# 경로 설정
# ==============================
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", os.path.expanduser("~/Downloads"))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 이 파일이 있는 디렉터리 (스크립트 위치)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 개별 과목 저장 폴더
BASE_SAVE_DIR = os.path.join(BASE_DIR, "courses")
DOWN_SAVE_DIR = os.path.join(DOWNLOAD_DIR, "courses")
os.makedirs(BASE_SAVE_DIR, exist_ok=True)
os.makedirs(DOWN_SAVE_DIR, exist_ok=True)

SESSION_ID = os.environ["INHA_SESSION_ID"]


# ==============================
# 드라이버 생성
# ==============================
def create_driver() -> webdriver.Chrome:
    print("[driver] creating chrome driver...")
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1400,900")
    # chrome_options.add_argument("--headless=new")  # 필요하면 켜기

    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options,
    )
    print("[driver] chrome started")

    # 세션 심기
    try:
        driver.get("https://sugang.inha.ac.kr")
        driver.add_cookie(
            {
                "name": "ASP.NET_SessionId",
                "value": SESSION_ID,
                "domain": "sugang.inha.ac.kr",
                "path": "/",
            }
        )
        print("[driver] session cookie injected")
    except Exception as e:
        print("[driver] session inject failed:", e)

    return driver


# ==============================
# 유틸
# ==============================
def dismiss_alert_if_any(driver: webdriver.Chrome) -> str | None:
    try:
        alert = driver.switch_to.alert
        txt = alert.text
        alert.accept()
        print("[alert] dismissed:", txt)
        return txt
    except NoAlertPresentException:
        return None


def wait_page():
    time.sleep(1.2)


def get_query_param(url: str, key: str, default=None):
    q = parse_qs(urlparse(url).query)
    return q.get(key, [default])[0]


def get_text_after_label(soup: BeautifulSoup, label_candidates):
    """
    th/td 중에서 label_candidates 중 하나가 들어있는 셀을 찾고
    바로 다음 td의 텍스트를 가져온다.
    """
    for label in label_candidates:
        th = soup.find(
            lambda tag: tag.name in ["th", "td"] and label in tag.get_text(strip=True)
        )
        if th:
            td = th.find_next("td")
            if td:
                return td.get_text("\n", strip=True)
    return ""


# ==============================
# 주차별 강의계획 파싱
# ==============================
def parse_weekly_plan(soup: BeautifulSoup, url: str | None = None):
    """
    주차별 강의계획 파싱
    - 1~16주차만 받는다.
    - '보강계획', '휴업일' 버림.
    - '2025XXXX주차' 같은 날짜형 주차 전부 버림.
    """
    result = {}
    tables = soup.find_all("table")
    if not tables:
        print("[weekly] no tables found")
        return result

    candidate_tables = [tb for tb in tables if "주차" in tb.get_text()]
    if candidate_tables:
        target_table = max(candidate_tables, key=lambda t: len(t.find_all("tr")))
    else:
        target_table = max(tables, key=lambda t: len(t.find_all("tr")))

    rows = target_table.find_all("tr")

    headers = []
    if rows:
        headers = [h.get_text(strip=True) for h in rows[0].find_all(["th", "td"])]

    date_week_pat = re.compile(r"^20\d{6}주차$")

    def is_valid_week(text: str) -> bool:
        t = text.strip()
        bad_words = ["강의내용", "시험과제", "비고", "보강계획", "휴업일"]
        if t in bad_words:
            return False

        if date_week_pat.match(t):
            return False

        if "주차" in t and len(t) >= 10:
            return False

        if t.isdigit():
            return True

        if t.endswith("주") or t.endswith("주차"):
            num_part = t.replace("주차", "").replace("주", "").strip()
            return num_part.isdigit()

        return False

    for row in rows[1:]:
        cols = row.find_all(["td", "th"])
        if not cols:
            continue

        raw_week = cols[0].get_text(strip=True)

        if not is_valid_week(raw_week):
            continue

        if raw_week.isdigit():
            week_key = f"{raw_week}주차"
        else:
            if raw_week.endswith("주"):
                week_key = raw_week + "차"
            else:
                week_key = raw_week

        item = {}
        for idx, header in enumerate(headers[1:], start=1):
            val = cols[idx].get_text("\n", strip=True) if idx < len(cols) else ""

            if "주제" in header:
                item["강의주제"] = val
            elif "방식" in header:
                item["강의방식"] = val
            elif ("내용" in header) or ("학습" in header):
                item["강의내용"] = val
            elif ("과제" in header) or ("시험" in header) or ("비고" in header):
                item["시험및과제"] = val
            else:
                item[header] = val

        result[week_key] = item

    print(f"[weekly] parsed weeks: {list(result.keys())}")
    return result


# ==============================
# 한 페이지 파싱
# ==============================
def parse_course_page(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    교과목명 = get_text_after_label(soup, ["교과목명", "과목명", "교과목 명"])
    담당교수명 = get_text_after_label(soup, ["담당교수", "교수명", "담당교수명"])
    학수번호 = get_text_after_label(soup, ["학수번호", "과목코드", "과목번호"])
    분반 = get_text_after_label(soup, ["분반"])
    학점 = get_text_after_label(soup, ["학점", "이수학점"])
    교과목영문명 = get_text_after_label(soup, ["영문명", "교과목영문명"])
    강의시간표 = get_text_after_label(soup, ["수업시간", "강의시간", "강의시간표"])
    강좌평가방법 = get_text_after_label(soup, ["평가방법", "강좌평가방법"])
    전공능력핵심역량 = get_text_after_label(soup, ["전공능력", "핵심역량"])
    교수프로필 = get_text_after_label(
        soup, ["담당교원", "교수정보", "연락처", "교수프로필"]
    )
    강의목표 = get_text_after_label(soup, ["강의목표"])
    강의개요 = get_text_after_label(soup, ["강의개요", "교과목개요"])
    교재 = get_text_after_label(soup, ["교재", "주교재"])
    부교재 = get_text_after_label(soup, ["부교재", "참고도서"])
    강의진행방식 = get_text_after_label(soup, ["강의진행방식", "수업진행방법"])
    수업방법 = get_text_after_label(soup, ["수업 방법", "수업형태"])
    수강시유의사항 = get_text_after_label(
        soup, ["수강시 유의사항", "수강시유의사항", "유의사항"]
    )
    특별지원관련 = get_text_after_label(soup, ["특별지원", "장애학생"])
    office_hour = get_text_after_label(soup, ["상담시간", "Office Hour"])

    e_learning_mid = get_text_after_label(
        soup, ["e-learning", "중간고사유형", "e-learning중간고사유형"]
    )

    평가기준 = {
        "중간고사": "0 %",
        "기말고사": "0 %",
        "출석": "0 %",
        "과제": "0 %",
        "퀴즈": "0 %",
        "토론": "0 %",
        "기타": "0 %",
        "계": "100 %",
    }
    평가기준세부 = ""

    tables = soup.find_all("table")
    for tb in tables:
        txt = tb.get_text(" ", strip=True)
        if ("중간" in txt and "기말" in txt) or ("평가기준" in txt):
            for tr in tb.find_all("tr"):
                cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
                if len(cells) < 2:
                    continue
                key = cells[0].replace(" ", "")
                val = cells[1]
                for k in list(평가기준.keys()):
                    if k.replace(" ", "") in key:
                        평가기준[k] = val
            next_el = tb.find_next(string=lambda x: x and "출석점수" in x)
            if not next_el:
                next_div = tb.find_next("div")
                if next_div:
                    full_txt = next_div.get_text("\n", strip=True)
                    if "시험" in full_txt or "점수" in full_txt:
                        평가기준세부 = full_txt
            break

    if not 평가기준세부:
        detail_candidates = soup.find_all(
            string=lambda x: x and ("점수" in x or "기말시험" in x or "퀴즈" in x)
        )
        if detail_candidates:
            평가기준세부 = max(
                (c.parent.get_text("\n", strip=True) for c in detail_candidates),
                key=len,
                default="",
            )

    주차별 = parse_weekly_plan(soup, url)

    if not 학수번호:
        학수번호 = get_query_param(url, "haksu_no", "") or get_query_param(
            url, "CurrCode", ""
        )
    if not 분반:
        분반 = get_query_param(url, "bunban", "") or get_query_param(url, "ClassNo", "")

    try:
        학점_val = float(학점) if 학점 else 0.0
    except ValueError:
        m = re.search(r"(\d+(\.\d+)?)", 학점 or "")
        학점_val = float(m.group(1)) if m else 0.0

    course = {
        "교과목명": 교과목명,
        "담당교수명": 담당교수명,
        "학수번호": 학수번호,
        "분반": 분반,
        "학점": 학점_val,
        "교과목영문명": 교과목영문명,
        "강의시간표": 강의시간표 or "웹강의",
        "강좌평가방법": 강좌평가방법 or "상대평가",
        "전공능력 및\n핵심역량": 전공능력핵심역량,
        "교수프로필(자세히보기)": 교수프로필,
        "강의목표": 강의목표,
        "강의개요": 강의개요,
        "교재": 교재,
        "부교재및참고도서": 부교재,
        "강의진행방식": 강의진행방식,
        "수업 방법": 수업방법 or "강의식",
        "수강시유의사항": 수강시유의사항,
        "특별지원관련": 특별지원관련,
        "Office Hour\n(상담시간)": office_hour or "사전 예약으로 상담시간 조정",
        "e-learning\n중간고사유형": e_learning_mid or "기타",
        "평가기준": 평가기준,
        "평가기준\n세부내역": 평가기준세부,
        "주차별 강의진행계획서": 주차별,
    }

    print(f"[parse] {교과목명} ({학수번호}-{분반})")
    return course


# ==============================
# 개별 저장 함수
# ==============================
def save_course(course: dict, idx: int):
    # 파일명 구성
    haksu = course.get("학수번호", "").strip()
    bunban = course.get("분반", "").strip()

    if haksu:
        name = haksu
        if bunban:
            name = f"{haksu}-{bunban}"
    else:
        # 학수번호도 없으면 인덱스로
        name = f"course-{idx:03d}"

    filename = name + ".json"

    for base in (BASE_SAVE_DIR, DOWN_SAVE_DIR):
        path = os.path.join(base, filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(course, f, ensure_ascii=False, indent=2)
            print(f"[save] {path} 저장 완료")
        except Exception:
            print(f"[save-error] {path}")
            traceback.print_exc()


# ==============================
# 메인
# ==============================
def main():
    print("[run] abeek crawler start")
    print("[cwd]", os.getcwd())
    print("[base_dir]", BASE_DIR)

    csv_path = os.path.join(os.getcwd(), "filtered_http_output.csv")
    if not os.path.exists(csv_path):
        print(
            "[error] filtered_http_output.csv 파일이 없습니다. 여기서 찾았음:", csv_path
        )
        return

    df = pd.read_csv(csv_path, encoding="utf-8")
    if "value" not in df.columns:
        print(
            "[error] CSV에 'value' 컬럼이 없습니다. 실제 컬럼들:", df.columns.tolist()
        )
        return

    urls = df["value"].dropna().tolist()
    print(f"[info] URL 개수: {len(urls)}")
    if not urls:
        print("[warn] 가져올 URL이 없습니다. CSV 내용을 확인하세요.")
        return

    try:
        driver = create_driver()
    except Exception:
        print("[fatal] 드라이버 생성 실패")
        traceback.print_exc()
        return

    try:
        for i, url in enumerate(urls, start=1):
            print(f"[{i}/{len(urls)}] visit: {url}")
            try:
                driver.get(url)
            except Exception:
                print(f"[error] {url} 로드 실패")
                traceback.print_exc()
                continue

            dismiss_alert_if_any(driver)
            wait_page()

            html = driver.page_source
            course = parse_course_page(html, url)

            # ✅ 여기서 바로 저장
            save_course(course, i)

    except Exception as e:
        print("[loop-error]", e)
        traceback.print_exc()
    finally:
        driver.quit()
        print("[run] 드라이버 종료")

    input("끝. 엔터 누르면 닫힘...")


if __name__ == "__main__":
    main()
