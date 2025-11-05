# test_unflatten.py
import json


def unflatten_dict(flat_dict):
    """
    CSV의 flatten된 컬럼('A.B.C' 형태)을 중첩 dict로 복원.
    - 중간 경로가 문자열인 경우 dict로 강제 변환하여 충돌 해결
    - 키 타입 안전: key를 str로 변환 후 split
    """
    result = {}
    for key, value in flat_dict.items():
        if key is None:
            continue
        key = str(key)
        if not key or key.startswith("__"):
            # __filename 같은 메타키는 무시 (필요시 제거)
            continue

        parts = list(str(key).split("."))  # 안전 분해
        d = result
        for p in parts[:-1]:
            if p not in d:
                d[p] = {}
            elif isinstance(d[p], str):
                # 중간 노드가 문자열이면 dict로 덮어써 충돌 해결
                d[p] = {}
            d = d[p]
        d[parts[-1]] = value
    return result


def assert_equal(a, b, msg=""):
    if a != b:
        raise AssertionError(f"{msg}\nExpected: {b}\nActual:   {a}")


def run_tests():
    # ① 단일 문자열형: 강의목표가 문자열만 있는 경우
    case1 = {"강의목표": "단일 문자열 목표"}
    out1 = unflatten_dict(case1)
    assert_equal(out1, {"강의목표": "단일 문자열 목표"}, "case1 실패")

    # ② 다단 구조형: 강의목표.목표1~2만 있는 경우
    case2 = {"강의목표.목표1": "이론", "강의목표.목표2": "실습"}
    out2 = unflatten_dict(case2)
    assert_equal(out2, {"강의목표": {"목표1": "이론", "목표2": "실습"}}, "case2 실패")

    # ③ 비어있는 강의목표 + 목표1 존재: 문자열("")을 dict로 승격
    case3 = {"강의목표": "", "강의목표.목표1": "이론"}
    out3 = unflatten_dict(case3)
    assert_equal(out3, {"강의목표": {"목표1": "이론"}}, "case3 실패")

    # ④ 강의목표 문자열 + 목표1 동시 존재: 부모 문자열을 dict로 덮어써 병합
    case4 = {"강의목표": "요약문", "강의목표.목표1": "세부1", "강의목표.목표2": "세부2"}
    out4 = unflatten_dict(case4)
    expected4 = {"강의목표": {"목표1": "세부1", "목표2": "세부2"}}
    assert_equal(out4, expected4, "case4 실패 (부모 문자열 충돌 병합)")

    # ⑤ 더 깊은 중첩: 평가기준 루트가 문자열이어도 하위키로 덮어써야 함
    case5 = {"평가기준": "", "평가기준.중간고사": "30 %", "평가기준.기말고사": "40 %"}
    out5 = unflatten_dict(case5)
    expected5 = {"평가기준": {"중간고사": "30 %", "기말고사": "40 %"}}
    assert_equal(out5, expected5, "case5 실패")

    # ⑥ 리스트 문자열은 unflatten 단계에선 그대로 두는게 기본 동작(선택 파싱)
    case6 = {"강의목표": '["목표A","목표B"]'}
    out6 = unflatten_dict(case6)
    assert_equal(
        out6, {"강의목표": '["목표A","목표B"]'}, "case6 실패 (리스트 문자열 보존)"
    )

    # ⑦ 메타키 무시: __filename 등은 건너뜀
    case7 = {"__filename": "X.json", "강의목표.목표1": "OK"}
    out7 = unflatten_dict(case7)
    expected7 = {"강의목표": {"목표1": "OK"}}
    assert_equal(out7, expected7, "case7 실패 (메타키 무시)")

    print("✅ 모든 unflatten 테스트 통과")


if __name__ == "__main__":
    run_tests()
