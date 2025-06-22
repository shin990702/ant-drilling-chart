# Directory structure:
# .
# ├── app.py
# ├── chart.svg
# ├── chart_thumbless.svg
# ├── requirements.txt
# └── data/  (folder for JSON files)

import base64
import json
import os
import re
import streamlit as st

st.set_page_config(layout="wide")

# Load SVG images and encode to base64 for embedding in HTML
CHART_SVG_PATH = "chart.svg"
CHART_THUMBLESS_PATH = "chart_thumbless.svg"
if not os.path.exists(CHART_SVG_PATH) or not os.path.exists(CHART_THUMBLESS_PATH):
    st.error("Required SVG files not found. Please ensure chart.svg and chart_thumbless.svg are present.")
    st.stop()
with open(CHART_SVG_PATH, "rb") as f:
    chart_svg_data = f.read()
with open(CHART_THUMBLESS_PATH, "rb") as f:
    chart_thumbless_data = f.read()
chart_svg_base64 = base64.b64encode(chart_svg_data).decode('utf-8')
chart_thumbless_base64 = base64.b64encode(chart_thumbless_data).decode('utf-8')

# Define field placeholders and absolute positions (matching original chart_widget.py coordinates)
placeholders = [
    "중지홀", "중지레프트", "중지리버스", "중지포워드",
    "약지홀", "약지라이트", "약지리버스", "약지포워드",
    "중지스판", "약지스판",
    "엄지홀", "엄지레프트", "엄지라이트", "엄지리버스", "엄지포워드",
    "중약지 CUT", "엄지 CUT", "브릿지"
]
input_positions = [
    (102, 200), (10, 203), (110, 110), (70, 312),
    (352, 200), (455, 203), (358, 110), (405, 312),
    (145, 432), (306, 432),
    (183, 660), (105, 680), (361, 680), (240, 780), (366, 542),
    (238, 272), (238, 550), (238, 203)
]
hole_indices = {0, 4, 10}
cut_indices = {15, 16}
thumbless_hidden_indices = [8, 9, 10, 11, 12, 13, 14, 15, 16]  # fields to hide in Thumbless mode

# 엄지홀 오블롱 변환 함수 (45도 각도에서 inch -> mm 변환)
def parse_thumb_oblong_strict(value: str) -> str:
    try:
        if ">" in value:
            base, after = value.split(">")
            if "))" in after:
                after, after_barbell = after.split("))")
                after_barbell = "))" + after_barbell
            else:
                after_barbell = ""
            valid_range = range(33, 96)
            def get_64_value(val_str):
                if '.' in val_str:
                    return None  # 이미 mm로 변환된 값은 처리 안 함
                val_int = int(val_str)
                if val_int in valid_range:
                    return val_int
                for f in [2, 4, 8, 16]:
                    candidate = val_int * f
                    if candidate in valid_range:
                        return candidate
                return None
            before_64 = get_64_value(base.strip())
            after_64 = get_64_value(after.strip())
            if before_64 is None or after_64 is None:
                return value
            diff = abs(after_64 - before_64)
            move = (diff / 2) / 64  # inch (64분할 값의 절반)
            mm = round(move * 25.4 * 0.7071, 2)  # 45도 오블롱 변환 (0.7071 배율)
            return f"{base}>{mm:.2f}{after_barbell}"
    except Exception as e:
        print(f"엄지홀 변환 오류: {e}")
    return value

# JSON 저장 유틸 함수
def save_data_as_json(name, cid, data, folder="data"):
    if not os.path.exists(folder):
        os.makedirs(folder)
    filename = f"{name}_{cid}.json"
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 세션 상태 초기화 (최초 실행 시)
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    # 상태 변수 기본값 설정
    st.session_state.edit_mode = False
    st.session_state.new_mode = False
    st.session_state.load_mode = False
    st.session_state.convert_mode = False
    st.session_state.original_values = {}
    st.session_state.base_coords = {}  # stores fx, fy, sx, sy after conversion
    # Initialize all field values to empty
    for i in range(len(placeholders)):
        st.session_state[f"field{i}"] = ""
    st.session_state.name = ""
    st.session_state.id = ""
    st.session_state.hand = "오른손"
    st.session_state.grip = "클래식"
    st.session_state.pap_x = ""
    st.session_state.pap_y = ""
    st.session_state.layout = ""
    st.session_state.tilt = ""
    st.session_state.rotation = ""
    st.session_state.memo = ""
    # 자동으로 가장 최근 JSON 파일 불러오기 (마지막 저장 데이터 로드)
    data_folder = "data"
    if os.path.isdir(data_folder):
        json_files = [f for f in os.listdir(data_folder) if f.endswith(".json")]
        if json_files:
            # sort by last modified time, descending
            json_files.sort(key=lambda x: os.path.getmtime(os.path.join(data_folder, x)), reverse=True)
            latest_file = json_files[0]
            try:
                with open(os.path.join(data_folder, latest_file), "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Load name/ID and all fields from JSON
                st.session_state.name = data.get("이름", "")
                st.session_state.id = data.get("전화번호뒷자리", "")
                if "중지" in data:
                    st.session_state.field0 = data["중지"].get("사이즈", "")
                    st.session_state.field1 = data["중지"].get("피치", {}).get("left", "")
                    st.session_state.field2 = data["중지"].get("피치", {}).get("reverse", "")
                    st.session_state.field3 = data["중지"].get("피치", {}).get("forward", "")
                if "약지" in data:
                    st.session_state.field4 = data["약지"].get("사이즈", "")
                    st.session_state.field5 = data["약지"].get("피치", {}).get("right", "")
                    st.session_state.field6 = data["약지"].get("피치", {}).get("reverse", "")
                    st.session_state.field7 = data["약지"].get("피치", {}).get("forward", "")
                if "스팬" in data:
                    st.session_state.field8 = data["스팬"].get("중지", "")
                    st.session_state.field9 = data["스팬"].get("약지", "")
                if "엄지" in data:
                    st.session_state.field10 = data["엄지"].get("사이즈", "")
                    st.session_state.field11 = data["엄지"].get("피치", {}).get("left", "")
                    st.session_state.field12 = data["엄지"].get("피치", {}).get("right", "")
                    st.session_state.field13 = data["엄지"].get("피치", {}).get("reverse", "")
                    st.session_state.field14 = data["엄지"].get("피치", {}).get("forward", "")
                if "CUT" in data:
                    st.session_state.field15 = data["CUT"].get("중약지", "")
                    st.session_state.field16 = data["CUT"].get("엄지", "")
                st.session_state.field17 = data.get("브릿지", "")
                pap_data = data.get("PAP", {})
                if isinstance(pap_data, dict):
                    st.session_state.pap_x = pap_data.get("수평", "")
                    st.session_state.pap_y = pap_data.get("수직", "")
                elif isinstance(pap_data, str):
                    # handle older format "X - Y"
                    match = re.match(r"([\d\s\/\.]+)\s*-\s*([\d\s\/\.]+)", pap_data)
                    if match:
                        st.session_state.pap_x = match.group(1).strip()
                        st.session_state.pap_y = match.group(2).strip()
                    else:
                        st.session_state.pap_x = ""
                        st.session_state.pap_y = ""
                st.session_state.layout = data.get("레이아웃", "")
                st.session_state.tilt = data.get("틸트", "")
                st.session_state.rotation = data.get("로테이션", "")
                st.session_state.memo = data.get("메모", "")
                st.session_state.hand = data.get("hand", "오른손")
                grip_mode = data.get("grip", data.get("그립방식", "클래식"))
                st.session_state.grip = grip_modee

                # 🔒 안전 보장: 누락된 키 미리 초기화 (예방 목적)
                if "center_toggle" not in st.session_state:
                    st.session_state.center_toggle = False

                # 모드 정리
                st.session_state.edit_mode = False
                st.session_state.load_mode = False

                # ✅ rerun은 맨 마지막에
                st.rerun()

            except Exception as e:
                print("자동 로드 실패:", e)

# Utility: revert conversion (restore original inch values if currently converted)
def revert_conversion():
    for idx, orig in st.session_state.original_values.items():
        st.session_state[f"field{idx}"] = orig
    st.session_state.convert_mode = False
    st.session_state.original_values.clear()
    st.session_state.base_coords.clear()

# Top control bar: Name/ID display, Hand/Grip radios, and action buttons
top_cols = st.columns([0.6, 0.6, 0.6, 0.4, 0.2, 0.4])
col_name, col_id, col_hand, col_grip, col_load, col_edit_new = top_cols

# Name and ID fields (read-only display)
if st.session_state.name and st.session_state.id:
    col_name.markdown(f"**이름:** {st.session_state.name}")
    col_id.markdown(f"**전화번호:** {st.session_state.id}")
else:
    col_name.markdown("**이름:** (없음)")
    col_id.markdown("**전화번호:** (없음)")

# Hand (왼손/오른손) and Grip (클래식/덤리스) selection
if st.session_state.edit_mode:
    selected_hand = col_hand.radio("손", ["오른손", "왼손"],
                               index=0 if st.session_state.get("hand", "오른손") != "왼손" else 1,
                               key="hand")
    selected_grip = col_grip.radio("그립", ["클래식", "덤리스"], index=0, key="grip")
else:
    # Display as text (disabled)
    col_hand.markdown(f"**손:** {st.session_state.hand}")
    col_grip.markdown(f"**그립:** {st.session_state.grip}")

# Action buttons (visible depending on mode)
if st.session_state.edit_mode:
    # In edit mode, use form submit for save; hide other action buttons
    pass
else:
    # "불러오기" button
    if col_load.button("불러오기"):
        if st.session_state.convert_mode:
            revert_conversion()
        st.session_state.load_mode = True
        st.session_state.new_mode = False
    # "편집" button (only if a chart is loaded/created)
    if st.session_state.name and st.session_state.id:
        if col_edit_new.button("편집"):
            if st.session_state.convert_mode:
                revert_conversion()
            st.session_state.edit_mode = True
    else:
        col_edit_new.write("")  # placeholder if no data
    # "새로 만들기" button
    if col_edit_new.button("새로 만들기", key="new_chart"):
        if st.session_state.convert_mode:
            revert_conversion()
        st.session_state.new_mode = True
        st.session_state.load_mode = False
    # "변환" (Convert) button
    conv_placeholder = st.empty()
    if conv_placeholder.button("변환", key="convert_btn"):
        if not st.session_state.convert_mode:
            # Start conversion (inch -> mm)
            st.session_state.original_values.clear()
            # Indices to convert (pitch values) and to preserve (hole sizes)
            pitch_indices = [1, 2, 3, 5, 6, 7, 11, 12, 13, 14]
            size_indices = [0, 4]
            thumb_index = 10
            # Save original values for all relevant fields
            for i in pitch_indices + size_indices + [thumb_index]:
                st.session_state.original_values[i] = st.session_state[f"field{i}"]
            # Conversion helper functions
            def convert_fraction(val_str):
                if not val_str:
                    return None
                s = val_str.strip().lower()
                if "mm" in s:
                    return None
                try:
                    if ' ' in s and '/' in s:
                        whole, frac = s.split()
                        num, den = frac.split('/')
                        return int(whole) + int(num)/int(den)
                    elif '/' in s:
                        num, den = s.split('/')
                        return int(num)/int(den)
                    else:
                        return float(s)
                except:
                    return None
            def inch_to_mm(inch_val):
                return round(inch_val * 25.4, 2)
            # Convert pitch fields to mm
            for i in pitch_indices:
                raw = st.session_state[f"field{i}"].strip()
                val_inch = convert_fraction(raw)
                if val_inch is not None:
                    st.session_state[f"field{i}"] = f"{inch_to_mm(val_inch):.2f} mm"
            # Convert thumb hole oval value
            st.session_state[f"field{thumb_index}"] = parse_thumb_oblong_strict(st.session_state[f"field{thumb_index}"].strip())
            # Calculate coordinates (fx, fy, sx, sy in mm)
            def get_mm(index):
                raw = st.session_state[f"field{index}"].replace("mm", "").strip()
                try:
                    return float(raw)
                except:
                    return 0.0
            left_mm = get_mm(11)
            right_mm = get_mm(12)
            reverse_mm = get_mm(13)
            forward_mm = get_mm(14)
            thumb_raw = st.session_state.field10
            thumb_mm = 0.0
            if ">" in thumb_raw:
                try:
                    mm_part = thumb_raw.split(">")[1]
                    mm_vals = re.findall(r"[\d\.]+", mm_part)
                    if mm_vals:
                        thumb_mm = float(mm_vals[0])
                except:
                    thumb_mm = 0.0
            # Determine coordinates based on hand (오른손/왼손)
            if st.session_state.hand == "왼손":
                fx = right_mm - left_mm - thumb_mm
                fy = forward_mm - reverse_mm - thumb_mm
                sx = right_mm - left_mm + thumb_mm
                sy = forward_mm - reverse_mm + thumb_mm
            else:  # 오른손
                fx = right_mm - left_mm - thumb_mm
                fy = forward_mm - reverse_mm + thumb_mm
                sx = right_mm - left_mm + thumb_mm
                sy = forward_mm - reverse_mm - thumb_mm
            st.session_state.base_coords = {"fx": fx, "fy": fy, "sx": sx, "sy": sy}
            st.session_state.convert_mode = True
        else:
            # If already in converted state, revert to original values
            revert_conversion()
        st.rerun()

# File loading UI (when "불러오기" clicked)
if st.session_state.load_mode:
    st.markdown("---")
    st.subheader("고객 차트 불러오기")
    search = st.text_input("이름 또는 전화번호 뒷자리 검색", key="search_term")
    data_folder = "data"
    all_files = [f[:-5] for f in os.listdir(data_folder) if f.endswith(".json")] if os.path.isdir(data_folder) else []
    filtered = [f for f in all_files if search in f]
    for fname in filtered:
        if st.button(fname, key=fname):
            file_path = os.path.join(data_folder, fname + ".json")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                st.error("파일을 불러올 수 없습니다.")
                st.session_state.load_mode = False
                break
            # Apply loaded data to session state
            st.session_state.name = data.get("이름", "")
            st.session_state.id = data.get("전화번호뒷자리", "")
            # Clear all fields
            for i in range(len(placeholders)):
                st.session_state[f"field{i}"] = ""
            if "중지" in data:
                st.session_state.field0 = data["중지"].get("사이즈", "")
                st.session_state.field1 = data["중지"].get("피치", {}).get("left", "")
                st.session_state.field2 = data["중지"].get("피치", {}).get("reverse", "")
                st.session_state.field3 = data["중지"].get("피치", {}).get("forward", "")
            if "약지" in data:
                st.session_state.field4 = data["약지"].get("사이즈", "")
                st.session_state.field5 = data["약지"].get("피치", {}).get("right", "")
                st.session_state.field6 = data["약지"].get("피치", {}).get("reverse", "")
                st.session_state.field7 = data["약지"].get("피치", {}).get("forward", "")
            if "스팬" in data:
                st.session_state.field8 = data["스팬"].get("중지", "")
                st.session_state.field9 = data["스팬"].get("약지", "")
            if "엄지" in data:
                st.session_state.field10 = data["엄지"].get("사이즈", "")
                st.session_state.field11 = data["엄지"].get("피치", {}).get("left", "")
                st.session_state.field12 = data["엄지"].get("피치", {}).get("right", "")
                st.session_state.field13 = data["엄지"].get("피치", {}).get("reverse", "")
                st.session_state.field14 = data["엄지"].get("피치", {}).get("forward", "")
            if "CUT" in data:
                st.session_state.field15 = data["CUT"].get("중약지", "")
                st.session_state.field16 = data["CUT"].get("엄지", "")
            st.session_state.field17 = data.get("브릿지", "")
            pap_data = data.get("PAP", {})
            if isinstance(pap_data, dict):
                st.session_state.pap_x = pap_data.get("수평", "")
                st.session_state.pap_y = pap_data.get("수직", "")
            elif isinstance(pap_data, str):
                match = re.match(r"([\d\s\/\.]+)\s*-\s*([\d\s\/\.]+)", pap_data)
                if match:
                    st.session_state.pap_x = match.group(1).strip()
                    st.session_state.pap_y = match.group(2).strip()
                else:
                    st.session_state.pap_x = ""
                    st.session_state.pap_y = ""
            st.session_state.layout = data.get("레이아웃", "")
            st.session_state.tilt = data.get("틸트", "")
            st.session_state.rotation = data.get("로테이션", "")
            st.session_state.memo = data.get("메모", "")
            st.session_state.hand = data.get("hand", "오른손")
            grip_mode = data.get("grip", data.get("그립방식", "클래식"))
            st.session_state.grip = grip_mode

            # 🔒 안전 보장: 누락된 키 미리 초기화 (예방 목적)
            if "center_toggle" not in st.session_state:
                st.session_state.center_toggle = False

            # 모드 정리
            st.session_state.edit_mode = False
            st.session_state.load_mode = False

            # ✅ rerun은 맨 마지막에
            st.rerun()

    if st.button("취소", key="cancel_load"):
        st.session_state.load_mode = False
        st.rerun()

# New chart creation UI (when "새로 만들기" clicked)
if st.session_state.new_mode:
    st.markdown("---")
    st.subheader("새 차트 만들기")
    new_name = st.text_input("이름", key="new_name")
    new_id = st.text_input("전화번호 뒷자리", key="new_id")
    # Show existing files matching input (for user reference)
    data_folder = "data"
    all_files = [f for f in os.listdir(data_folder) if f.endswith(".json")] if os.path.isdir(data_folder) else []
    filter_str = f"{new_name.strip()}_{new_id.strip()}" if new_name or new_id else ""
    filtered = [f for f in all_files if filter_str and filter_str in f]
    st.write("저장된 파일 목록:")
    st.write(", ".join(filtered) if filtered else "(검색 결과 없음)")
    col_cnf, col_cancel = st.columns(2)
    if col_cnf.button("확인", key="confirm_new"):
        if not new_name.strip() or not new_id.strip():
            st.warning("이름과 전화번호를 모두 입력하세요.")
        else:
            filename = f"{new_name.strip()}_{new_id.strip()}.json"
            filepath = os.path.join(data_folder, filename)
            if os.path.exists(filepath):
                st.error(f"이미 존재하는 파일: {filename}")
            else:
                # Initialize new chart data
                st.session_state.name = new_name.strip()
                st.session_state.id = new_id.strip()
                for i in range(len(placeholders)):
                    st.session_state[f"field{i}"] = ""
                st.session_state.pap_x = ""
                st.session_state.pap_y = ""
                st.session_state.layout = ""
                st.session_state.tilt = ""
                st.session_state.rotation = ""
                st.session_state.memo = ""
                st.session_state.hand = "오른손"
                st.session_state.grip = "클래식"
                st.session_state.new_mode = False
                st.session_state.edit_mode = True
                st.session_state.load_mode = False

                # 🔒 누락 방지용 세션 변수 미리 정의 (특히 rerun 직후 쓰이는 값들)
                if "center_toggle" not in st.session_state:
                    st.session_state.center_toggle = False
                if "convert_mode" not in st.session_state:
                    st.session_state.convert_mode = False
                if "base_coords" not in st.session_state:
                    st.session_state.base_coords = {}

                # ✅ rerun은 마지막에 호출
                st.rerun()
    if col_cancel.button("취소", key="cancel_new"):
        st.session_state.new_mode = False
        st.rerun()

# Editing form (if in edit_mode)
if st.session_state.edit_mode:
    st.markdown("---")
    st.subheader("차트 데이터 편집")
    with st.form("edit_form", clear_on_submit=False):
        # 18 overlay fields as input fields in form
        for idx, placeholder in enumerate(placeholders):
            st.text_input(placeholder, value=st.session_state.get(f"field{idx}", ""),
                          key=f"field{idx}", placeholder=placeholder)
        cols_pap = st.columns(2)
        cols_pap[0].text_input("PAP 수평거리", value=st.session_state.pap_x, key="pap_x", placeholder="PAP 수평거리")
        cols_pap[1].text_input("PAP 수직거리", value=st.session_state.pap_y, key="pap_y", placeholder="PAP 수직거리")
        st.text_input("레이아웃", value=st.session_state.layout, key="layout", placeholder="레이아웃")
        st.text_input("틸트", value=st.session_state.tilt, key="tilt", placeholder="틸트")
        st.text_input("로테이션", value=st.session_state.rotation, key="rotation", placeholder="로테이션")
        st.text_area("메모", value=st.session_state.memo, key="memo", placeholder="MEMO", height=150)
        save_submit = st.form_submit_button("저장")
    if save_submit:
        # On save, compile data and write to JSON
        name = st.session_state.name.strip()
        cid = st.session_state.id.strip()
        if not name or not cid:
            base_name = "이름"
            existing = os.listdir("data") if os.path.isdir("data") else []
            count = 1
            while f"{base_name}_{count}.json" in existing:
                count += 1
            if not name:
                name = f"{base_name}_{count}"
            if not cid:
                cid = str(count)
            st.session_state.name = name
            st.session_state.id = cid
        values = [st.session_state.get(f"field{i}", "").strip() for i in range(len(placeholders))]
        data = {
            "이름": st.session_state.name,
            "전화번호뒷자리": st.session_state.id,
            "중지": {
                "사이즈": values[0],
                "피치": {"left": values[1], "reverse": values[2], "forward": values[3]}
            },
            "약지": {
                "사이즈": values[4],
                "피치": {"right": values[5], "reverse": values[6], "forward": values[7]}
            },
            "스팬": {"중지": values[8], "약지": values[9]},
            "엄지": {
                "사이즈": values[10],
                "피치": {
                    "left": values[11], "right": values[12],
                    "reverse": values[13], "forward": values[14]
                }
            },
            "PAP": {"수평": st.session_state.pap_x.strip(), "수직": st.session_state.pap_y.strip()},
            "레이아웃": st.session_state.layout.strip(),
            "틸트": st.session_state.tilt.strip(),
            "로테이션": st.session_state.rotation.strip(),
            "메모": st.session_state.memo,
            "CUT": {"중약지": values[15], "엄지": values[16]},
            "브릿지": values[17],
            "토글상태": st.session_state.get("center_toggle", False),
            "hand": st.session_state.hand,
            "grip": st.session_state.grip
        }
        save_data_as_json(name, cid, data)
        st.success(f"{name}_{cid}.json 저장 완료")
        st.session_state.edit_mode = False
        if st.session_state.convert_mode:
            revert_conversion()
        st.rerun()

# Display chart with overlay fields (view mode)
if not st.session_state.edit_mode:
    st.markdown("---")
    st.subheader("차트 보기")
    # Choose the appropriate SVG image (classic or thumbless)
    current_svg_data = chart_svg_base64 if st.session_state.grip != "덤리스" else chart_thumbless_base64
    # Determine container height (SVG height + top offset 90px for header area)
    container_height = (757 + 90) if st.session_state.grip != "덤리스" else (286 + 90)
    html = f'''
    <div style="position: relative; width: 541px; height: {container_height}px; background-color: white;">
        <img src="data:image/svg+xml;base64,{current_svg_data}" style="position: absolute; top: 90px; left: 0px; width: 541px;"/>
    '''
    # Overlay each field value as a positioned input (read-only)
    for idx, (x, y) in enumerate(input_positions):
        if st.session_state.grip == "덤리스" and idx in thumbless_hidden_indices:
            continue  # skip hidden fields in thumbless mode
        value = st.session_state.get(f"field{idx}", "")
        display_value = value if value else ""
        placeholder_attr = placeholders[idx] if not value else ""
        # Base style: positioned over chart, transparent background, bold text
        style = "position: absolute; left: {left}px; top: {top}px; width: {w}px; height: {h}px; background: transparent; color: black; border: none; font-weight: bold; text-align: center;"
        # Adjust size/font for specific fields
        if idx in [1, 2, 3, 5, 6, 7, 11, 12, 13, 14]:
            style += " font-size: 13pt;"
        elif idx in cut_indices or idx >= 15:
            style += " width: 70px; height: 40px; font-size: 12pt;"
        elif idx in hole_indices:
            if idx == 10:
                style += " width: 180px; height: 50px; font-size: 16pt;"
            else:
                style += " width: 90px; height: 50px; font-size: 18pt;"
        else:
            style += " width: 90px; height: 50px; font-size: 16pt;"
        top_offset = y  # positions are already relative to container
        left_offset = x
        style = style.format(left=left_offset, top=top_offset, w=90, h=50)
        html += f'<input type="text" value="{display_value}" placeholder="{placeholder_attr}" readonly style="{style}"/>'
    # Coordinate output fields (only for Classic mode)
    if st.session_state.grip != "덤리스":
        thumb_x, thumb_y = input_positions[12]  # "엄지라이트" reference position
        base_fx = st.session_state.base_coords.get("fx", 0.0)
        base_fy = st.session_state.base_coords.get("fy", 0.0)
        base_sx = st.session_state.base_coords.get("sx", 0.0)
        base_sy = st.session_state.base_coords.get("sy", 0.0)
        if st.session_state.get("center_toggle", False):
            first_x_text = f"x = {base_fy:.2f}"
            first_y_text = f"y = {-base_fx:.2f}"
            second_x_text = f"x = {base_sy:.2f}"
            second_y_text = f"y = {-base_sx:.2f}"
        else:
            first_x_text = f"x = {base_fx:.2f}"
            first_y_text = f"y = {base_fy:.2f}"
            second_x_text = f"x = {base_sx:.2f}"
            second_y_text = f"y = {base_sy:.2f}"
        # If not converted yet, just show placeholder "x = "
        if not st.session_state.convert_mode:
            first_x_text = "x = "
            first_y_text = "y = "
            second_x_text = "x = "
            second_y_text = "y = "
        coord_style = "position: absolute; width: 80px; height: 30px; background: lightgray; color: black; font-weight: bold; text-align: center;"
        fx_left = thumb_x + 18
        fx_top = thumb_y - 80
        fy_top = fx_top + 30 + 3
        sx_left = fx_left + 80 + 20
        html += f'<input type="text" value="{first_x_text}" readonly style="{coord_style} left: {fx_left}px; top: {fx_top}px;"/>'
        html += f'<input type="text" value="{first_y_text}" readonly style="{coord_style} left: {fx_left}px; top: {fy_top}px;"/>'
        html += f'<input type="text" value="{second_x_text}" readonly style="{coord_style} left: {sx_left}px; top: {fx_top}px;"/>'
        html += f'<input type="text" value="{second_y_text}" readonly style="{coord_style} left: {sx_left}px; top: {fy_top}px;"/>'
    html += "</div>"
    # Render the HTML with embedded SVG and overlay inputs
    st.components.v1.html(html, height=container_height + 20)
    # Sidebar-equivalent panel for side inputs (PAP, layout, etc.) in view mode
    side_col = st.columns(1)[0]
    pap_cols = side_col.columns(2)
    pap_cols[0].text_input("PAP 수평거리", value=st.session_state.pap_x, disabled=True)
    pap_cols[1].text_input("PAP 수직거리", value=st.session_state.pap_y, disabled=True)
    side_col.text_input("레이아웃", value=st.session_state.layout, disabled=True)
    side_col.text_input("틸트", value=st.session_state.tilt, disabled=True)
    side_col.text_input("로테이션", value=st.session_state.rotation, disabled=True)
    side_col.text_area("메모", value=st.session_state.memo, disabled=True, height=150)
    # Center toggle checkbox (only meaningful after conversion)
    if st.session_state.convert_mode:
        side_col.checkbox("동서울그랜드볼링장", value=st.session_state.get("center_toggle", False), key="center_toggle")
    else:
        side_col.checkbox("동서울그랜드볼링장", value=False, disabled=True)
