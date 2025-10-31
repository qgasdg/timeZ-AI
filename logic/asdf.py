import os
import time
import json
import glob
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


# =========================================
# 기본 설정
# =========================================
DOWNLOAD_DIR = "~/Downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

SAVE_DIR = os.path.join(DOWNLOAD_DIR, "report")
os.makedirs(SAVE_DIR, exist_ok=True)

SESSION_ID = "REDACTED_SESSION_ID"

CHECKPOINT_FILE = "download_failures.json"
MAX_ROUNDS = 3


# =========================================
# 드라이버 생성
# =========================================
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1400,900")
    prefs = {
        "download.default_directory": os.path.abspath(DOWNLOAD_DIR),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options,
    )

    # 세션 쿠키 넣기
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
    except Exception as e:
        print("[driver] session inject failed:", e)

    return driver


driver = create_driver()


# =========================================
# 프레임 순회 유틸
# =========================================
def iter_all_frames(driver, depth=0, max_depth=2):
    if depth > max_depth:
        return
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for idx, fr in enumerate(frames):
        yield [idx]
        try:
            driver.switch_to.frame(fr)
            for sub in iter_all_frames(driver, depth + 1, max_depth):
                yield [idx] + sub
        except Exception:
            pass
        finally:
            driver.switch_to.default_content()


def switch_to_frame_path(driver, frame_path):
    driver.switch_to.default_content()
    for idx in frame_path:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if idx < len(iframes):
            driver.switch_to.frame(iframes[idx])
        else:
            raise IndexError("frame index out of range")


def click_anywhere(driver, value, css_selectors=None, xpaths=None, wait_sec=1.5):
    css_selectors = css_selectors or []
    xpaths = xpaths or []

    # root
    driver.switch_to.default_content()
    for sel in css_selectors:
        try:
            WebDriverWait(driver, wait_sec).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
            ).click()
            return True
        except Exception:
            pass

    for xp in xpaths:
        try:
            WebDriverWait(driver, wait_sec).until(
                EC.element_to_be_clickable((By.XPATH, xp))
            ).click()
            return True
        except Exception:
            pass

    # 모든 iframe
    for frame_path in iter_all_frames(driver):
        try:
            switch_to_frame_path(driver, frame_path)
        except Exception:
            continue

        for sel in css_selectors:
            try:
                WebDriverWait(driver, wait_sec).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                ).click()
                driver.switch_to.default_content()
                return True
            except Exception:
                pass

        for xp in xpaths:
            try:
                WebDriverWait(driver, wait_sec).until(
                    EC.element_to_be_clickable((By.XPATH, xp))
                ).click()
                driver.switch_to.default_content()
                return True
            except Exception:
                pass

    driver.switch_to.default_content()
    return False


# =========================================
# 다운로드 감지 / 이동
# =========================================
def wait_for_new_files(download_dir: str, before: set, timeout: int = 5):
    start = time.time()
    while time.time() - start < timeout:
        now_files = set(os.listdir(download_dir))
        new_files = list(now_files - before)
        real_new = [
            f
            for f in new_files
            if not f.endswith(".crdownload")
            and os.path.isfile(os.path.join(download_dir, f))
        ]
        if real_new:
            return real_new
        time.sleep(0.1)
    return []


def _pick_latest_download(download_dir: str, created_after: float = None):
    candidates = []
    patterns = ["*.xlsx", "*.xls", "*.xlsm", "*.xlsb"]
    for p in patterns:
        for path in glob.glob(os.path.join(download_dir, p)):
            try:
                mtime = os.path.getmtime(path)
            except FileNotFoundError:
                continue
            if created_after is not None and mtime < created_after:
                continue
            candidates.append((mtime, path))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def move_downloaded_files(
    download_dir: str, save_dir: str, value: str, new_files: list, click_time: float
):
    full_paths = []
    for name in new_files:
        full = os.path.join(download_dir, name)
        if os.path.isfile(full) and not name.endswith(".crdownload"):
            full_paths.append(full)

    if not full_paths:
        latest = _pick_latest_download(download_dir, created_after=click_time - 1.0)
        if latest:
            full_paths = [latest]
        else:
            print("  ⚠️ 새로 생긴 파일을 못 찾음")
            return False

    full_paths.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    main_src = full_paths[0]

    wait_start = time.time()
    while not os.path.exists(main_src) and time.time() - wait_start < 5:
        time.sleep(0.1)

    if not os.path.exists(main_src):
        print(f"  ⚠️ {main_src} 파일이 최종적으로도 없음 → 이동 실패")
        return False

    _, ext = os.path.splitext(main_src)
    if not ext:
        ext = ".xlsx"

    main_dst = os.path.join(save_dir, f"{value}{ext}")

    if os.path.exists(main_dst):
        os.remove(main_dst)

    try:
        os.rename(main_src, main_dst)
        print(f"  ✅ {value} 대표 파일 이동/이름변경 → {main_dst}")
    except FileNotFoundError:
        print("  ⚠️ 첫 번째 rename 실패 → 최신 엑셀 다시 찾기")
        latest = _pick_latest_download(download_dir, created_after=click_time - 1.0)
        if not latest or not os.path.exists(latest):
            print("  ⚠️ 재시도에도 파일을 못 찾음")
            return False
        os.rename(latest, main_dst)
        print(f"  ✅ {value} 재시도 후 이동 완료 → {main_dst}")

    for extra_src in full_paths[1:]:
        extra_name = os.path.basename(extra_src)
        extra_dst = os.path.join(save_dir, extra_name)
        if os.path.exists(extra_dst):
            os.remove(extra_dst)
        try:
            os.rename(extra_src, extra_dst)
            print(f"  ✅ 추가 파일 이동 → {extra_dst}")
        except FileNotFoundError:
            print(f"  ⚠️ {extra_src} 는 이동 못 함")

    return True


# =========================================
# JS export
# =========================================
def try_js_export_in_iframe(value: str) -> bool:
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if not iframes:
        return False

    driver.switch_to.frame(iframes[0])

    js = """
    var out = { called: false, methods: [] };
    try {
        if (window.report) {
            for (var k in window.report) {
                try {
                    if (typeof window.report[k] === 'function') {
                        out.methods.push(k);
                    }
                } catch (e) {}
            }
            if (typeof window.report.exportReport === 'function') {
                try {
                    window.report.exportReport('EXCEL2007');
                    out.called = true;
                    out.used = 'exportReport(EXCEL2007)';
                } catch (e1) {
                    try {
                        window.report.exportReport('EXCEL');
                        out.called = true;
                        out.used = 'exportReport(EXCEL)';
                    } catch (e2) {}
                }
            } else if (typeof window.report.save === 'function') {
                try {
                    window.report.save('EXCEL2007');
                    out.called = true;
                    out.used = 'save(EXCEL2007)';
                } catch (e3) {
                    try {
                        window.report.save('EXCEL');
                        out.called = true;
                        out.used = 'save(EXCEL)';
                    } catch (e4) {}
                }
            }
        }
    } catch (e) {
        out.error = e.toString();
    }
    return out;
    """

    info = driver.execute_script(js)
    driver.switch_to.default_content()

    print(f"   ℹ️ {value} JS export 결과:", info)
    return bool(info and info.get("called"))


# =========================================
# xlsx 먼저 강제로 찾는 헬퍼
# =========================================
def click_xlsx_first(driver, value) -> bool:
    """
    저장 드롭다운에서 *.xlsx / Excel 2007 / xlsx 가 보이는 모든 프레임을 다 훑어서
    하나라도 클릭되면 True, 아니면 False.
    👉 이게 실패하면 옵션(옵션수정) 절대 가지 않게 할 거임.
    """
    xpaths = [
        "//*[contains(text(),'엑셀저장(*.xlsx)')]",
        "//*[contains(text(),'엑셀 저장(*.xlsx)')]",
        "//*[contains(text(),'Excel 2007')]",
        "//*[contains(text(),'xlsx')]",
    ]

    # 1) 루트에서 먼저
    driver.switch_to.default_content()
    for xp in xpaths:
        try:
            WebDriverWait(driver, 1.5).until(
                EC.element_to_be_clickable((By.XPATH, xp))
            ).click()
            print(f"   ✅ {value} 저장 드롭다운에서 xlsx 항목 클릭 (root)")
            driver.switch_to.default_content()
            return True
        except Exception:
            pass

    # 2) 안 보이면 모든 iframe 뒤지기
    for frame_path in iter_all_frames(driver):
        try:
            switch_to_frame_path(driver, frame_path)
        except Exception:
            continue

        for xp in xpaths:
            try:
                WebDriverWait(driver, 1.5).until(
                    EC.element_to_be_clickable((By.XPATH, xp))
                ).click()
                print(
                    f"   ✅ {value} 저장 드롭다운에서 xlsx 항목 클릭 (frame={frame_path})"
                )
                driver.switch_to.default_content()
                return True
            except Exception:
                continue

    driver.switch_to.default_content()
    return False


# =========================================
# DOM 경로 (순서 고정 버전)
# =========================================
def try_dom_save_click(value: str) -> bool:
    # 1) 저장 아이콘
    ok = click_anywhere(
        driver,
        value,
        css_selectors=[
            '[title*="저장"]',
            '[alt*="저장"]',
            'img[title*="저장"]',
        ],
        xpaths=[
            "//*[text()='저장']",
            "//*[normalize-space()='저장']",
            "//button[normalize-space()='저장']",
            "//span[normalize-space()='저장']/ancestor::button[1]",
        ],
        wait_sec=2,
    )
    if not ok:
        return False
    print(f"   ✅ {value} 저장 아이콘 클릭")

    # 2) ✅✅ 여기서 xlsx가 반드시 먼저
    xlsx_ok = click_xlsx_first(driver, value)
    if not xlsx_ok:
        print(f"   ⚠️ {value} xlsx 항목을 어디서도 못 찾음 → 옵션 진입 안 함")
        return False

    # 3) 그 다음에만 옵션(옵션수정)
    option_frame_path = None
    for frame_path in [[]] + list(iter_all_frames(driver)):
        try:
            switch_to_frame_path(driver, frame_path)
        except Exception:
            continue
        try:
            el = WebDriverWait(driver, 0.6).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//*[contains(text(),'옵션수정')] | //*[contains(text(),'옵션 수정')] | //*[normalize-space()='옵션'] | //span[contains(text(),'옵션')]/ancestor::button[1]",
                    )
                )
            )
            el.click()
            option_frame_path = frame_path
            print(f"   ✅ {value} 옵션(옵션수정) 버튼 클릭 (frame={frame_path})")
            break
        except Exception:
            continue
    driver.switch_to.default_content()

    # 4) '하나의 시트' 클릭
    single_clicked = click_anywhere(
        driver,
        value,
        xpaths=[
            "//*[contains(text(),'하나의 시트')]",
            "//*[contains(text(),'1개의 시트')]",
            "//*[contains(text(),'1 개의 시트')]",
            "//*[contains(text(),'단일 시트')]",
        ],
        wait_sec=1.5,
    )
    if single_clicked:
        print(f"   ✅ {value} '하나의 시트' 항목 클릭")

        # 5) 옵션창 내부에서 오른쪽(마지막) 버튼 클릭
        saved_in_same_modal = False
        if option_frame_path is not None:
            try:
                switch_to_frame_path(driver, option_frame_path)

                candidate_xpaths = [
                    "//input[@type='button' and (@value='저장' or @value='확인' or @value='적용')]",
                    "//button[normalize-space()='저장']",
                    "//button[normalize-space()='확인']",
                    "//button[normalize-space()='적용']",
                    "//span[normalize-space()='저장']/ancestor::button[1]",
                    "//span[normalize-space()='확인']/ancestor::button[1]",
                ]

                buttons = []
                for xp in candidate_xpaths:
                    elems = driver.find_elements(By.XPATH, xp)
                    if elems:
                        buttons.extend(elems)

                if buttons:
                    target_btn = buttons[-1]  # 맨 오른쪽
                    WebDriverWait(driver, 1.0).until(
                        EC.element_to_be_clickable(target_btn)
                    ).click()
                    print(
                        f"   ✅ {value} (옵션창 내부) 오른쪽/마지막 '저장·확인' 클릭 성공"
                    )
                    saved_in_same_modal = True
                else:
                    print(f"   ⚠️ {value} (옵션창) 버튼 목록을 못 찾음")
            finally:
                driver.switch_to.default_content()

        if not saved_in_same_modal:
            extra_ok = click_anywhere(
                driver,
                value,
                xpaths=[
                    "//input[@type='button' and @value='저장']",
                    "//input[@type='button' and @value='확인']",
                    "//button[normalize-space()='저장']",
                    "//button[normalize-space()='확인']",
                    "//button[normalize-space()='적용']",
                    "//span[normalize-space()='저장']/ancestor::button[1]",
                ],
                wait_sec=1.5,
            )
            if extra_ok:
                print(f"   ✅ {value} (fallback) 옵션창 저장/확인 클릭")
            else:
                print(f"   ⚠️ {value} (옵션창) 저장/확인 버튼은 못 눌렀음 → 그래도 진행")
    else:
        print(f"   ⚠️ {value} '하나의 시트' 항목을 못 눌렀음")

    # 6) 최종 저장
    final_saved = click_anywhere(
        driver,
        value,
        xpaths=[
            "//button[normalize-space()='저장']",
            "//span[normalize-space()='저장']/ancestor::button[1]",
            "//*[text()='저장']",
            "//input[@type='button' and @value='저장']",
        ],
        wait_sec=0.5,
    )
    if final_saved:
        print(f"   ✅ {value} 최종 저장 버튼 클릭")
    else:
        print(f"   ⚠️ {value} 최종 저장 버튼까지는 못 눌렀음")

    return True


# =========================================
# 체크포인트 유틸
# =========================================
def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return data.get("failed", [])
            except Exception:
                return []
    return []


def save_checkpoint(failed_list):
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump({"failed": failed_list}, f, ensure_ascii=False, indent=2)


def list_saved_values(save_dir: str):
    roots = []
    for fname in os.listdir(save_dir):
        root, _ = os.path.splitext(fname)
        if root:
            roots.append(root)
    return set(roots)


# =========================================
# 메인 루프
# =========================================
try:
    df = pd.read_csv("logic/filtered_output.csv", encoding="utf-8")
    all_values = df["value"].dropna().tolist()

    existing_values = list_saved_values(SAVE_DIR)
    prev_failed = load_checkpoint()

    if prev_failed:
        print("💾 이전 실행에서 실패한 값이 있어서 그거부터 다시 시도합니다.")
        pending_values = [v for v in prev_failed if v not in existing_values]
    else:
        pending_values = [v for v in all_values if v not in existing_values]

    print(
        f"시작 시점: 전체 {len(all_values)}개 중 이미 받은 것 {len(existing_values)}개 → 남은 것 {len(pending_values)}개"
    )

    for round_idx in range(1, MAX_ROUNDS + 1):
        print(
            f"\n===== {round_idx} 라운드 시작 (남은 개수: {len(pending_values)}) ====="
        )
        new_failed = []

        for value in pending_values:
            print(f"▶ 처리중: {value}")

            popup_url = (
                f"https://sugang.inha.ac.kr/STD/SU_65002/LecPlan_Rpt.aspx?Value={value}"
            )

            try:
                driver.get(popup_url)
            except WebDriverException:
                print("  ⚠️ 드라이버가 죽어서 재생성합니다.")
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = create_driver()
                driver.get(popup_url)

            time.sleep(0.3)

            target_path = os.path.join(SAVE_DIR, f"{value}.xlsx")
            if os.path.exists(target_path):
                print(f"  ℹ️ {value}는 이미 있음 → 스킵")
                continue

            before_files = set(os.listdir(DOWNLOAD_DIR))
            click_time = time.time()

            js_ok = try_js_export_in_iframe(value)

            if not js_ok:
                print(f"  ⚠️ {value} JS export 불가 → DOM 경로로")
                dom_ok = try_dom_save_click(value)
                if not dom_ok:
                    print(f"  ⚠️ {value} DOM에서도 저장을 못 찾음 → 실패로 기록")
                    new_failed.append(value)
                    continue

            new_files = wait_for_new_files(DOWNLOAD_DIR, before_files)
            if not new_files:
                print(f"  ⚠️ {value} 20초 안에 새 파일이 안 생김 → 실패로 기록")
                new_failed.append(value)
                continue

            ok = move_downloaded_files(
                DOWNLOAD_DIR, SAVE_DIR, value, new_files, click_time
            )
            if not ok:
                print(f"  ⚠️ {value} 파일 이동 실패 → 실패로 기록")
                new_failed.append(value)
                continue

            time.sleep(0.1)

        save_checkpoint(new_failed)

        if not new_failed:
            print("✅ 모든 값 처리 완료")
            break
        else:
            print(
                f"⚠️ 이번 라운드에서 실패한 값들: {len(new_failed)}개 → 다음 라운드에서 재시도"
            )
            existing_values = list_saved_values(SAVE_DIR)
            pending_values = [v for v in new_failed if v not in existing_values]

    if pending_values:
        print("🚨 아직도 안 내려온 값들 있음. download_failures.json 확인해봐.")
    else:
        save_checkpoint([])

finally:
    try:
        driver.quit()
    except Exception:
        pass
