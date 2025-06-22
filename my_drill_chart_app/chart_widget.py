import os
import json
import re
from PyQt5.QtWidgets import (
    QWidget, QLineEdit, QPushButton, QMessageBox, QInputDialog,
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QTextEdit,
    QLabel, QCheckBox, QRadioButton, QButtonGroup
)
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from data_manager import save_data_as_json

# 엄지홀 변환 함수
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
                    return None  # 이미 변환된 값
                val_int = int(val_str)
                # 우선 1배부터 체크 (즉, 그대로 사용)
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
            move = (diff / 2) / 64  # inch
            mm = round(move * 25.4 * 0.7071, 2)
            return f"{base}>{mm:.2f}{after_barbell}"

    except Exception as e:
        print(f"엄지홀 변환 오류: {e}")
    return value



class ChartWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("지공차트 입력기")
        self.setGeometry(100, 100, 1000, 700)

        svg_path = "chart.svg"
        renderer = QSvgRenderer(svg_path)
        self.svg_size = renderer.defaultSize()

        # Classic용 SVG
        self.classic_chart = QSvgWidget("chart.svg", self)
        self.classic_chart.setGeometry(0, 0, self.svg_size.width(), self.svg_size.height())
        self.classic_chart.move(0, 90)
        self.classic_chart.show()
        
        
        # Thumbless용 SVG
        self.thumbless_chart = QSvgWidget("chart_thumbless.svg", self)
        self.thumbless_renderer = QSvgRenderer("chart_thumbless.svg")
        self.thumbless_size = self.thumbless_renderer.defaultSize()
        self.thumbless_chart.setGeometry(0, 0, self.thumbless_size.width(), self.thumbless_size.height())
        self.thumbless_chart.move(0, 90)  # classic과 동일하게 y축 하강
        self.thumbless_chart.hide()
        
        self.thumbless_hidden_indices = [8, 9, 10, 11, 12, 13, 14, 15, 16]

        self.field_inputs = []
        self.placeholders = [
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

        
        bold_font = QFont()
        bold_font.setPointSize(16)
        bold_font.setBold(True)

        bold_large_font = QFont()
        bold_large_font.setPointSize(18)
        bold_large_font.setBold(True)
        
        # 엄지홀 전용 폰트
        thumb_font = QFont()
        thumb_font.setPointSize(16)  # 2pt 줄임
        thumb_font.setBold(True)

        cut_font = QFont()
        cut_font.setPointSize(12)
        cut_font.setBold(True)

        self.hole_indices = {0, 4, 10}
        self.cut_indices = {15, 16}

        for idx, pos in enumerate(input_positions):
            inp = QLineEdit(self)
            inp.setText("")
            inp.setAlignment(Qt.AlignCenter)
            
            if idx in [1, 2, 3, 5, 6, 7, 11, 12, 13, 14]:  # 중지/약지 피치값은 폰트 13pt로 줄이기
                small_font = QFont()
                small_font.setPointSize(13)  # 기존보다 3pt 줄이기
                small_font.setBold(True)
                inp.setFont(small_font)
                inp.setFixedSize(90, 50)
                inp.setStyleSheet("background: transparent; color: black; border: none;")
            
            elif idx in self.cut_indices:
                inp.setFont(cut_font)
                inp.setFixedSize(70, 40)
                inp.setStyleSheet("background: transparent; color: black; border: none;")
            elif idx >= 15:
                inp.setFont(cut_font)
                inp.setFixedSize(70, 40)
                inp.setStyleSheet("background: transparent; color: black; border: none;")
            elif idx in self.hole_indices:
                if idx == 10:  # 엄지홀만 다르게
                    inp.setFont(thumb_font)
                    inp.setFixedSize(180, 50)
                else:
                    inp.setFont(bold_large_font)
                    inp.setFixedSize(90, 50)
                inp.setStyleSheet("background: transparent; color: black; border: none;")
            else:
                inp.setFont(bold_font)
                inp.setFixedSize(90, 50)
                inp.setStyleSheet("background: transparent; color: black; border: none;")
        
            inp.move(pos[0], pos[1])
            inp.setEnabled(False)
            self.field_inputs.append(inp)
            
        self.name_input = QLineEdit(self)
        self.name_input.setFont(bold_font)
        self.name_input.setFixedSize(120, 50)
        self.name_input.setAlignment(Qt.AlignCenter)
        self.name_input.setReadOnly(True)
        self.name_input.setStyleSheet("background: transparent; color: black;")
        self.name_input.move(10, 10)

        self.id_input = QLineEdit(self)
        self.id_input.setFont(bold_font)
        self.id_input.setFixedSize(80, 50)
        self.id_input.setAlignment(Qt.AlignCenter)
        self.id_input.setReadOnly(True)
        self.id_input.setStyleSheet("background: transparent; color: black;")
        self.id_input.move(140, 10)
        
        self.hand_group = QButtonGroup(self)
        self.left_radio = QRadioButton("왼손", self)
        self.left_radio.setFont(bold_font)
        self.left_radio.move(230, 10)
        self.hand_group.addButton(self.left_radio)
        
        self.right_radio = QRadioButton("오른손", self)
        self.right_radio.setFont(bold_font)
        self.right_radio.move(230, 40)
        self.hand_group.addButton(self.right_radio)
        
        self.right_radio.setChecked(True)
        
        self.left_radio.setEnabled(False)
        self.right_radio.setEnabled(False)
        
        # 스타일 선택 라디오버튼 (클래식 / 덤리스)
        self.classic_radio = QRadioButton("클래식", self)
        self.thumbless_radio = QRadioButton("덤리스", self)
        self.classic_radio.setFont(bold_font)
        self.thumbless_radio.setFont(bold_font)
        self.classic_radio.setChecked(True)  # 기본은 클래식
        
        self.style_group = QButtonGroup(self)
        self.style_group.addButton(self.classic_radio)
        self.style_group.addButton(self.thumbless_radio)
        
        # 위치 설정 (예: id_input 오른쪽에 세로 정렬)
        self.classic_radio.move(330, 10)
        self.thumbless_radio.move(330, 40)
        
        # 초기 비활성화 (편집 모드일 때만 변경 가능하게)
        self.classic_radio.setEnabled(False)
        self.thumbless_radio.setEnabled(False)
        
        self.classic_radio.toggled.connect(self.apply_style_mode)
        self.thumbless_radio.toggled.connect(self.apply_style_mode)
        
        self.load_button = QPushButton("불러오기", self)
        self.load_button.setFont(bold_font)
        self.load_button.setFixedSize(100, 50)
        self.load_button.move(510, 10)  # 기존 230 → 280
        self.load_button.clicked.connect(self.load_data_dialog)
        
        self.edit_button = QPushButton("편집", self)
        self.edit_button.setFont(bold_font)
        self.edit_button.setFixedSize(100, 50)
        self.edit_button.move(620, 10)  # 기존 340 → 390
        self.edit_button.clicked.connect(self.toggle_edit_or_save)
        
        self.new_button = QPushButton("새로 만들기", self)
        self.new_button.setFont(bold_font)
        self.new_button.setFixedHeight(50)
        self.new_button.setFixedWidth(120)
        self.new_button.move(
            self.edit_button.x() + self.edit_button.width() + 10,
            self.edit_button.y()
        )
        self.new_button.clicked.connect(self.create_new_chart)


        self.edit_mode = False
        self.load_button.show()
        self.edit_button.hide()
        self.new_button.show()
        self.new_button.move(self.edit_button.x(), self.edit_button.y())
        
        small_font = QFont()
        small_font.setPointSize(12)
        small_font.setBold(True)

        self.pap_x_input = QLineEdit(self)
        self.pap_x_input.setFont(small_font)
        self.pap_x_input.setPlaceholderText("PAP 수평거리")
        self.pap_x_input.setFixedSize(145, 30)
        
        
        self.pap_y_input = QLineEdit(self)
        self.pap_y_input.setFont(small_font)
        self.pap_y_input.setPlaceholderText("PAP 수직거리")
        self.pap_y_input.setFixedSize(145, 30)
        


        self.layout_input = QLineEdit(self)
        self.layout_input.setFont(small_font)
        self.layout_input.setPlaceholderText("레이아웃")
        self.layout_input.setFixedSize(300, 30)
        

        self.tilt_input = QLineEdit(self)
        self.tilt_input.setFont(small_font)
        self.tilt_input.setPlaceholderText("틸트")
        self.tilt_input.setFixedSize(300, 30)
        

        self.rotation_input = QLineEdit(self)
        self.rotation_input.setFont(small_font)
        self.rotation_input.setPlaceholderText("로테이션")
        self.rotation_input.setFixedSize(300, 30)
        
        self.pap_x_input.move(self.svg_size.width() + 20, 80)
        self.pap_y_input.move(self.svg_size.width() + 175, 80)
        self.layout_input.move(self.svg_size.width() + 20, 115)
        self.tilt_input.move(self.svg_size.width() + 20, 150)
        self.rotation_input.move(self.svg_size.width() + 20, 185)
        
        self.pap_x_input.setReadOnly(True)
        self.pap_y_input.setReadOnly(True)
        self.pap_x_input.setStyleSheet("background: lightgray; color: black;")
        self.pap_y_input.setStyleSheet("background: lightgray; color: black;")

        self.layout_input.setReadOnly(True)
        self.layout_input.setStyleSheet("background: lightgray; color: black;")

        self.tilt_input.setReadOnly(True)
        self.tilt_input.setStyleSheet("background: lightgray; color: black;")

        self.rotation_input.setReadOnly(True)
        self.rotation_input.setStyleSheet("background: lightgray; color: black;")
        
                # 고객 메모 입력칸
        self.memo_box = QTextEdit(self)
        self.memo_box.setReadOnly(True)
        self.memo_box.setStyleSheet("background: lightgray; color: black;")
        self.memo_box.setFont(QFont("Arial", 14))
        self.memo_box.setPlaceholderText("MEMO")
        self.memo_box.setFixedSize(300, self.svg_size.height() - 300)  # 200 → 140 (30x4칸 만큼 더 줄임)
        self.memo_box.move(self.svg_size.width() + 20, 230)  # 200 → 190 (위로 올림)
        self.memo_box.setReadOnly(True)
        
        # 변환 버튼
        self.convert_button = QPushButton("변환", self)
        self.convert_button.setFont(QFont("Arial", 10, QFont.Bold))
        self.convert_button.setFixedSize(60, 30)
        self.convert_button.clicked.connect(self.convert_inches)
        self.convert_button.move(self.svg_size.width() + 260, self.memo_box.y() + 
        self.memo_box.height() + 10)

        
        self.setFixedSize(self.svg_size.width() + 350, self.svg_size.height() + 150)
          # 유지해도 무방
        self.convert_mode = False  # 변환 상태 여부
        self.original_values = {}  # 원래 값을 저장해두는 딕셔너리
        self.current_data = {}
        
                        # 2x2 입력칸 (가로로 넓게, 세로로 촘촘하게)
                # 2x2 입력칸 (가로로 넓게, 세로로 촘촘하게)
        self.extra_inputs = []

        # 네 개의 개별 QLineEdit 정의
        self.first_x = QLineEdit(self)
        self.first_y = QLineEdit(self)
        self.second_x = QLineEdit(self)
        self.second_y = QLineEdit(self)

        self.extra_inputs = [self.first_x, self.first_y, self.second_x, self.second_y]
        
        # ✅ "엄지라이트" 인덱스를 찾아서 해당 위젯을 가져옴
        thumb_index = self.placeholders.index("엄지라이트")
        thumb_rp_widget = self.field_inputs[thumb_index]
        thumb_rp_x = thumb_rp_widget.x()
        thumb_rp_y = thumb_rp_widget.y()
        
        # 위치 및 크기 설정
        cell_width = 80
        cell_height = 30
        gap_x = 20
        gap_y = 3
        offset_y = -80
        offset_x = 18  # ← 오른쪽으로 이동

        # 좌측 열 (first_x, first_y)
        self.first_x.setFixedSize(cell_width, cell_height)
        self.first_x.move(thumb_rp_x + offset_x, thumb_rp_y + offset_y)

        self.first_y.setFixedSize(cell_width, cell_height)
        self.first_y.move(thumb_rp_x + offset_x, thumb_rp_y + offset_y + cell_height + gap_y)

        # 우측 열 (second_x, second_y)
        self.second_x.setFixedSize(cell_width, cell_height)
        self.second_x.move(thumb_rp_x + offset_x + cell_width + gap_x, thumb_rp_y + offset_y)

        self.second_y.setFixedSize(cell_width, cell_height)
        self.second_y.move(thumb_rp_x + offset_x + cell_width + gap_x, thumb_rp_y + offset_y + cell_height + gap_y)

        
        # 스타일 설정
        small_box_style = "background: lightgray; color: black;"
        small_box_font = QFont("Arial", 12, QFont.Bold)
        
        for box in [self.first_x, self.first_y, self.second_x, self.second_y]:
            box.setFont(small_box_font)
            box.setFixedHeight(30)
            box.setReadOnly(True)
            box.setAlignment(Qt.AlignCenter)
            box.setStyleSheet(small_box_style)
        
        # 기본 텍스트
        self.first_x.setText("x = ")
        self.first_y.setText("y = ")
        self.second_x.setText("x = ")
        self.second_y.setText("y = ")

        convert_btn_x = self.convert_button.x()
        convert_btn_y = self.convert_button.y()
        
        self.center_label = QLabel("동서울그랜드볼링장", self)
        self.center_label.setFont(QFont("Arial", 10))
        label_width = self.center_label.sizeHint().width()

        # 토글 체크박스
        self.center_toggle = QCheckBox(self)
        self.center_toggle.move(
            convert_btn_x - 60,  # 버튼 왼쪽으로 60px 떨어짐 (조절 가능)
            convert_btn_y + 6    # 버튼과 수평 정렬 (약간 아래로 정렬)
        )
        self.center_toggle.setChecked(False)  # 기본 상태는 체크 안됨
        self.center_toggle.stateChanged.connect(self.recalculate_offset_with_toggle)
        
        self.center_label.move(convert_btn_x - 60 - label_width - 5,
                                convert_btn_y + 4
        )
    
    def reset_ui_before_load(self):
        self.edit_mode = False
        self.convert_mode = False
        self.original_values.clear()
    
        self.first_x.setText("x = ")
        self.first_y.setText("y = ")
        self.second_x.setText("x = ")
        self.second_y.setText("y = ")
    
        self.edit_button.setText("편집")
        self.edit_button.hide()
        self.load_button.show()
        self.convert_button.show()
        self.classic_radio.setChecked(True)
        self.right_radio.setChecked(True)
    
        self.classic_radio.setEnabled(False)
        self.thumbless_radio.setEnabled(False)
        self.left_radio.setEnabled(False)
        self.right_radio.setEnabled(False)
    
        for idx, field in enumerate(self.field_inputs):
            field.setText("")
            field.setEnabled(False)
            field.setStyleSheet("background-color: transparent; color: white; border: none; font-weight: bold;")
            field.setPlaceholderText(self.placeholders[idx])
    
        self.pap_x_input.setText("")
        self.pap_y_input.setText("")
        self.layout_input.setText("")
        self.tilt_input.setText("")
        self.rotation_input.setText("")
        self.memo_box.setPlainText("")
        self.center_toggle.setChecked(False)
    
        self.new_button.move(self.load_button.x() + self.load_button.width() + 10, self.load_button.y())
    
    
    
    def recalculate_offset_with_toggle(self):
        if not hasattr(self, "base_coords"):
            return
    
        fx = self.base_coords.get("fx", 0.0)
        fy = self.base_coords.get("fy", 0.0)
        sx = self.base_coords.get("sx", 0.0)
        sy = self.base_coords.get("sy", 0.0)
    
        if self.center_toggle.isChecked():
            self.first_x.setText(f"x = {-fy:.2f}")
            self.first_y.setText(f"y = {fx:.2f}")
            self.second_x.setText(f"x = {-sy:.2f}")
            self.second_y.setText(f"y = {sx:.2f}")
        else:
            self.first_x.setText(f"x = {fx:.2f}")
            self.first_y.setText(f"y = {fy:.2f}")
            self.second_x.setText(f"x = {sx:.2f}")
            self.second_y.setText(f"y = {sy:.2f}")

    
    
    def toggle_edit_or_save(self):
        if not self.edit_mode:
            if self.convert_mode:
                # 변환된 상태면 원래 인치 값으로 되돌림
                for i, original in self.original_values.items():
                    self.field_inputs[i].setText(original)
                self.convert_mode = False
                
            self.edit_mode = True
            self.edit_button.setText("저장")
            self.load_button.hide()
            self.convert_button.hide()
            
            self.left_radio.setEnabled(True) 
            self.right_radio.setEnabled(True)
            
            self.classic_radio.setEnabled(self.edit_mode)
            self.thumbless_radio.setEnabled(self.edit_mode)
            
            for idx, inp in enumerate(self.field_inputs):
                inp.setEnabled(True)
                inp.setPlaceholderText(self.placeholders[idx])
                inp.setStyleSheet("background-color: #3399FF; color: black; border: 1px solid black;")
            self.pap_x_input.setReadOnly(False)
            self.pap_y_input.setReadOnly(False)
            self.layout_input.setReadOnly(False)
            self.tilt_input.setReadOnly(False)
            self.rotation_input.setReadOnly(False)
            self.memo_box.setReadOnly(False)
            
            self.pap_x_input.setStyleSheet("background-color: #3399FF; color: white; border: 1px solid black;")
            self.pap_y_input.setStyleSheet("background-color: #3399FF; color: white; border: 1px solid black;")
            self.layout_input.setStyleSheet("background-color: #3399FF; color: white; border: 1px solid black;")
            self.tilt_input.setStyleSheet("background-color: #3399FF; color: white; border: 1px solid black;")
            self.rotation_input.setStyleSheet("background-color: #3399FF; color: white; border: 1px solid black;")
            self.memo_box.setStyleSheet("background-color: #3399FF; color: white; border: 1px solid black;")
        else:
            if self.convert_mode:
                for i, original in self.original_values.items():
                    self.field_inputs[i].setText(original)
                self.convert_mode = False
                self.original_values = {}
                self.first_x.setText("x = ")
                self.first_y.setText("y = ")
                self.second_x.setText("x = ")
                self.second_y.setText("y = ")
            name = self.name_input.text().strip()
            cid = self.id_input.text().strip()
            self.pap_x_input.setReadOnly(True)
            self.pap_y_input.setReadOnly(True)
            self.layout_input.setReadOnly(True)
            self.tilt_input.setReadOnly(True)
            self.rotation_input.setReadOnly(True)
            self.left_radio.setEnabled(False)
            self.right_radio.setEnabled(False)
            self.memo_box.setReadOnly(True)
            self.memo_box.setStyleSheet("background: lightgray; color: black;")
            self.pap_x_input.setStyleSheet("background: lightgray; color: black;")
            self.pap_y_input.setStyleSheet("background: lightgray; color: black;")
            self.layout_input.setStyleSheet("background: lightgray; color: black;")
            self.tilt_input.setStyleSheet("background: lightgray; color: black;")
            self.rotation_input.setStyleSheet("background: lightgray; color: black;")

            if not name or not cid:
                base_name = "이름"
                existing = os.listdir("data")
                count = 1
                while f"{base_name}_{count}.json" in existing:
                    count += 1
                if not name:
                    name = f"{base_name}_{count}"
                if not cid:
                    cid = f"{count}"

            values = [f.text().strip() for f in self.field_inputs]
            data = {
                "이름": name,
                "전화번호뒷자리": cid,
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
                "PAP": {
                    "수평": self.pap_x_input.text().strip(),
                    "수직": self.pap_y_input.text().strip()
                },
                "레이아웃": self.layout_input.text().strip(),
                "틸트": self.tilt_input.text().strip(),
                "로테이션": self.rotation_input.text().strip(),
                "메모": self.memo_box.toPlainText(),
                "CUT": {
                    "중약지": values[15],
                    "엄지": values[16]
                },
                "브릿지": values[17],
                "토글상태": self.center_toggle.isChecked(),
                "hand": "왼손" if self.left_radio.isChecked() else "오른손",
                "grip": "덤리스" if self.thumbless_radio.isChecked() else "클래식"
            }
            self.memo_box.setReadOnly(True)

            save_data_as_json(name, cid, data)
            QMessageBox.information(self, "성공", f"{name}_{cid}.json 저장 완료")
            print(f"field_inputs 개수: {len(self.field_inputs)}")
            self.edit_mode = False
            self.edit_button.setText("편집")
            self.load_button.show()
            self.convert_button.show()
            for idx, inp in enumerate(self.field_inputs):
                inp.setEnabled(False)
                inp.setPlaceholderText("")
                if idx in self.hole_indices or idx in self.cut_indices:
                    inp.setStyleSheet("background: transparent; color: black; border: none;")
                else:
                    inp.setStyleSheet("background: transparent; color: black; border: none;")
        
    def apply_style_mode(self):
        if self.thumbless_radio.isChecked():
            self.classic_chart.hide()
            self.thumbless_chart.show()
            for idx in self.thumbless_hidden_indices:
                self.field_inputs[idx].setVisible(False)
    
            self.first_x.setVisible(False)
            self.first_y.setVisible(False)
            self.second_x.setVisible(False)
            self.second_y.setVisible(False)
        else:
            self.thumbless_chart.hide()
            self.classic_chart.show()
            for idx in self.thumbless_hidden_indices:
                self.field_inputs[idx].setVisible(True)
    
            self.first_x.setVisible(True)
            self.first_y.setVisible(True)
            self.second_x.setVisible(True)
            self.second_y.setVisible(True)
    
        if self.edit_mode:
            for idx, inp in enumerate(self.field_inputs):
                if inp.isVisible():
                    inp.setEnabled(True)
                    inp.setPlaceholderText(self.placeholders[idx])
                    inp.setStyleSheet("background-color: #3399FF; color: black; border: 1px solid black;")
    
        # ✅ 모든 입력 필드의 스타일을 '일반 보기 모드'로 초기화
        for idx, inp in enumerate(self.field_inputs):
            inp.setEnabled(False)
            inp.setStyleSheet("background: transparent; color: black; border: none; font-weight: bold;")
        
        # 🔄 현재 edit_mode에 따라 field 스타일 재적용
        if self.edit_mode:
            for idx, inp in enumerate(self.field_inputs):
                inp.setEnabled(True)
                inp.setPlaceholderText(self.placeholders[idx])
                if idx in self.hole_indices or idx in self.cut_indices:
                    inp.setStyleSheet("background-color: #3399FF; color: white; border: 1px solid black; font-weight: bold;")
                else:
                    inp.setStyleSheet("background-color: #3399FF; color: black; border: 1px solid black; font-weight: bold;")
        else:
            for idx, inp in enumerate(self.field_inputs):
                inp.setEnabled(False)
                inp.setPlaceholderText("")
                if idx in self.hole_indices or idx in self.cut_indices:
                    inp.setStyleSheet("background: transparent; color: black; border: none;")
                else:
                    inp.setStyleSheet("background: transparent; color: black; border: none;")
                        
    def create_new_chart(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("새 차트 만들기")
        dialog.setFixedSize(400, 400)

        layout = QVBoxLayout(dialog)

        name_label = QLabel("이름")
        name_input = QLineEdit()
        name_input.setPlaceholderText("예: 홍길동")
        name_input.setFont(QFont("Arial", 12))
        layout.addWidget(name_label)
        layout.addWidget(name_input)

        id_label = QLabel("전화번호 뒷자리")
        id_input = QLineEdit()
        id_input.setPlaceholderText("예: 1234")
        id_input.setFont(QFont("Arial", 12))
        layout.addWidget(id_label)
        layout.addWidget(id_input)

        list_label = QLabel("저장된 파일 목록")
        layout.addWidget(list_label)
        file_list = QListWidget()
        file_list.setSelectionMode(QListWidget.NoSelection)  # 선택 불가
        file_list.setFocusPolicy(Qt.NoFocus)  # 포커스 제거
        file_list.setDisabled(True)  # 클릭 방지용 비활성화
        layout.addWidget(file_list)

        directory = os.path.join(os.getcwd(), "data")
        all_files = [f for f in os.listdir(directory) if f.endswith(".json")]

        def update_file_list():
            name_filter = name_input.text().strip()
            id_filter = id_input.text().strip()
            file_list.clear()
            for file in all_files:
                base = file.replace(".json", "")
                if name_filter in base and id_filter in base:
                    file_list.addItem(file)

        name_input.textChanged.connect(update_file_list)
        id_input.textChanged.connect(update_file_list)
        update_file_list()  # 초기 실행

        ok_button = QPushButton("확인")
        layout.addWidget(ok_button)

        def on_confirm():
            name = name_input.text().strip()
            cid = id_input.text().strip()
            if not name or not cid:
                QMessageBox.warning(dialog, "입력 오류", "이름과 전화번호를 모두 입력하세요.")
                return

            filename = f"{name}_{cid}.json"
            filepath = os.path.join(directory, filename)
            if os.path.exists(filepath):
                QMessageBox.critical(dialog, "중복 오류", f"이미 존재하는 이름+ID 조합입니다: {filename}")
                return
                
            self.name_input.clear()
            self.id_input.clear()
            self.memo_box.clear()
            self.pap_x_input.clear()
            self.pap_y_input.clear()
            self.layout_input.clear()
            self.tilt_input.clear()
            self.rotation_input.clear()
            self.center_toggle.setChecked(False)
            self.classic_radio.setChecked(True)
            self.right_radio.setChecked(True)
            
            for inp in self.field_inputs:
                inp.setText("")
            
            # ✅ 입력된 정보 설정
            self.name_input.setText(name)
            self.id_input.setText(cid)
        
            # ✅ 편집모드 활성화
            self.edit_mode = True
            self.classic_radio.setEnabled(True)
            self.thumbless_radio.setEnabled(True)
            self.left_radio.setEnabled(True)
            self.right_radio.setEnabled(True)
        
            self.edit_button.setText("저장")
            self.edit_button.show()
            self.convert_button.hide()
            self.load_button.hide()
        
            # 필드 활성화 및 스타일 지정
            for idx, inp in enumerate(self.field_inputs):
                inp.setEnabled(True)
                if idx in self.hole_indices or idx in self.cut_indices:
                    inp.setStyleSheet("background-color: blue; color: white; border: 1px solid black; font-weight: bold;")
                else:
                    inp.setStyleSheet("background-color: blue; color: white; border: 1px solid black; font-weight: bold;")

            # 초기 SVG 적용
            self.apply_style_mode()
            
            for idx, inp in enumerate(self.field_inputs):
                inp.setPlaceholderText(self.placeholders[idx])

            dialog.accept()

        ok_button.clicked.connect(on_confirm)
        result = dialog.exec_()
    
        if result == QDialog.Accepted:
            self.load_button.show()
            self.edit_button.show()
            self.new_button.move(self.edit_button.x() + self.edit_button.width() + 10, self.edit_button.y())
        else:
            self.edit_mode = False
            name_filled = bool(self.name_input.text().strip())
            id_filled = bool(self.id_input.text().strip())
    
            if name_filled and id_filled:
                self.edit_button.show()
                self.new_button.move(self.edit_button.x() + self.edit_button.width() + 10, self.edit_button.y())
            else:
                self.edit_button.hide()
                self.new_button.move(self.load_button.x() + self.load_button.width() + 10, self.load_button.y())
                
                
    def load_data_dialog(self):
        self.reset_ui_before_load()
        if self.convert_mode:
            self.convert_mode = False
            for i, original in self.original_values.items():
                self.field_inputs[i].setText(original)
            self.original_values = {}
            self.first_x.setText("x = ")
            self.first_y.setText("y = ")
            self.second_x.setText("x = ")
            self.second_y.setText("y = ")
        
        dialog = QDialog(self)
        dialog.setWindowTitle("고객 차트 불러오기")
        layout = QVBoxLayout(dialog)
    
        search_input = QLineEdit()
        search_input.setPlaceholderText("이름 또는 전화번호 뒷자리 검색")
        layout.addWidget(search_input)
    
        list_widget = QListWidget()
        layout.addWidget(list_widget)
    
        all_files = [f for f in os.listdir("data") if f.endswith(".json")]
    
        def update_list(filter_text=""):
            list_widget.clear()
            for file in all_files:
                display = file.replace(".json", "")
                if filter_text in display:
                    list_widget.addItem(display)
    
        update_list()
        search_input.textChanged.connect(lambda text: update_list(text))
    
        def on_item_selected(item):
            # ✅ 편집모드 진입 막기
            self.edit_mode = False
            self.edit_button.setText("편집")
    
            file_path = os.path.join("data", item.text() + ".json")
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
    
            self.name_input.setText(data.get("이름", ""))
            self.id_input.setText(data.get("전화번호뒷자리", ""))
    
            self.field_inputs[0].setText(data.get("중지", {}).get("사이즈", ""))
            self.field_inputs[1].setText(data.get("중지", {}).get("피치", {}).get("left", ""))
            self.field_inputs[2].setText(data.get("중지", {}).get("피치", {}).get("reverse", ""))
            self.field_inputs[3].setText(data.get("중지", {}).get("피치", {}).get("forward", ""))
            self.field_inputs[4].setText(data.get("약지", {}).get("사이즈", ""))
            self.field_inputs[5].setText(data.get("약지", {}).get("피치", {}).get("right", ""))
            self.field_inputs[6].setText(data.get("약지", {}).get("피치", {}).get("reverse", ""))
            self.field_inputs[7].setText(data.get("약지", {}).get("피치", {}).get("forward", ""))
            self.field_inputs[8].setText(data.get("스팬", {}).get("중지", ""))
            self.field_inputs[9].setText(data.get("스팬", {}).get("약지", ""))
            self.field_inputs[10].setText(data.get("엄지", {}).get("사이즈", ""))
            self.field_inputs[11].setText(data.get("엄지", {}).get("피치", {}).get("left", ""))
            self.field_inputs[12].setText(data.get("엄지", {}).get("피치", {}).get("right", ""))
            self.field_inputs[13].setText(data.get("엄지", {}).get("피치", {}).get("reverse", ""))
            self.field_inputs[14].setText(data.get("엄지", {}).get("피치", {}).get("forward", ""))
            self.field_inputs[15].setText(data.get("CUT", {}).get("중약지", ""))
            self.field_inputs[16].setText(data.get("CUT", {}).get("엄지", ""))
            self.field_inputs[17].setText(data.get("브릿지", ""))
    
            pap_data = data.get("PAP", {})
            if isinstance(pap_data, dict):
                self.pap_x_input.setText(pap_data.get("수평", ""))
                self.pap_y_input.setText(pap_data.get("수직", ""))
            elif isinstance(pap_data, str):
                match = re.match(r"([\d\s/\.]+)\s*-\s*(-?[\d\s/\.]+)", pap_data)
                if match:
                    self.pap_x_input.setText(match.group(1).strip())
                    self.pap_y_input.setText(match.group(2).strip())
                else:
                    self.pap_x_input.setText("")
                    self.pap_y_input.setText("")
            else:
                self.pap_x_input.setText("")
                self.pap_y_input.setText("")
    
            self.layout_input.setText(data.get("레이아웃", ""))
            self.tilt_input.setText(data.get("틸트", ""))
            self.rotation_input.setText(data.get("로테이션", ""))
            self.memo_box.setPlainText(data.get("메모", ""))
            self.center_toggle.setChecked(bool(data.get("토글상태", False)))
    
            # ✅ 오른손/왼손
            hand = data.get("hand", "오른손")
            if hand == "왼손":
                self.left_radio.setChecked(True)
            else:
                self.right_radio.setChecked(True)
    
            # ✅ 클래식/덤리스
            grip = data.get("그립방식", "클래식")
            if grip == "덤리스":
                self.thumbless_radio.setChecked(True)
            else:
                self.classic_radio.setChecked(True)
                
            grip = data.get("grip", "클래식")
            if grip == "덤리스":
                self.thumbless_radio.setChecked(True)
            else:
                self.classic_radio.setChecked(True)
    
            dialog.accept()
            
        if not self.edit_mode:
            for inp in self.field_inputs:
                inp.setPlaceholderText("")
    
        list_widget.itemClicked.connect(on_item_selected)
        result = dialog.exec_()
    
        if result == QDialog.Accepted:
            self.load_button.show()
            self.edit_button.show()
            self.new_button.move(self.edit_button.x() + self.edit_button.width() + 10, self.edit_button.y())
            
            self.apply_style_mode()
            
        else:
            self.edit_mode = False
            name_filled = bool(self.name_input.text().strip())
            id_filled = bool(self.id_input.text().strip())
            if name_filled and id_filled:
                self.edit_button.show()
                self.new_button.move(self.edit_button.x() + self.edit_button.width() + 10, self.edit_button.y())
            else:
                self.edit_button.hide()
                self.new_button.move(self.load_button.x() + self.load_button.width() + 10, self.load_button.y())
        

        
    def convert_inches(self):
        print("변환 버튼 눌림")
    
        if self.convert_mode:
            print("복원 모드: 원래 값으로 되돌립니다.")
        
            for i, original in self.original_values.items():
                self.field_inputs[i].setText(original)
        
            self.convert_mode = False
            self.toggle_applied = False
        
            self.first_x.setText("x =")
            self.first_y.setText("y =")
            self.second_x.setText("x =")
            self.second_y.setText("y =")
            return
            
        self.original_values = {}
        for i in [1, 2, 5, 6, 10, 11, 12, 13, 14]:
            raw = self.field_inputs[i].text().strip()
            self.original_values[i] = raw

        # 최초 변환 시작
        self.convert_mode = True
        self.original_data = self.current_data.copy() if self.current_data else {}
        
        
        def convert_fraction(value):
            if not value:
                return None
            value = value.strip()
        
            if "mm" in value.lower():
                return None  # 이미 변환된 값이면 무시
        
            try:
                # 혼합분수 처리 ("1 1/4")
                if ' ' in value and '/' in value:
                    whole, frac = value.split()
                    num, den = frac.split('/')
                    return int(whole) + int(num) / int(den)
        
                # 단일 분수 처리 ("3/8")
                elif '/' in value:
                    num, den = value.split('/')
                    return int(num) / int(den)
        
                # 정수 ("1") 또는 소수 ("1.5")
                else:
                    return float(value)
        
            except Exception as e:
                print(f"[변환 오류] '{value}' → {e}")
                return None

        def inch_to_mm(inch_val):
            return round(inch_val * 25.4, 2)

        # 중지/약지 사이즈 저장만
        for i in [0, 4]:
            raw = self.field_inputs[i].text().strip()
            self.original_values[i] = raw

        # 피치값 변환
        for i in [1, 2, 5, 6, 11, 12, 13, 14]:
            raw = self.field_inputs[i].text().strip()
            self.original_values[i] = raw
            val_inch = convert_fraction(raw)
            if val_inch is not None:
                mm = inch_to_mm(val_inch)
                self.field_inputs[i].setText(f"{mm:.2f} mm")

        # 엄지홀 오발 처리
        i = 10
        raw = self.field_inputs[i].text().strip()
        self.original_values[i] = raw
        self.field_inputs[i].setText(parse_thumb_oblong_strict(raw))

        # 좌표계산용 mm 값
        def get_mm(index):
            raw = self.field_inputs[index].text().replace(" mm", "").strip()
            try:
                return float(raw)
            except:
                return 0.0

        left_mm = get_mm(11)
        right_mm = get_mm(12)
        reverse_mm = get_mm(13)
        forward_mm = get_mm(14)

        thumb_raw = self.field_inputs[10].text()
        thumb_mm = 0.0
        if ">" in thumb_raw:
            try:
                mm_part = thumb_raw.split(">")[1]
                mm_extracted = re.findall(r"[\d.]+", mm_part)
                if mm_extracted:
                    thumb_mm = float(mm_extracted[0])
            except:
                thumb_mm = 0.0

        if self.left_radio.isChecked():  # 왼손
            fx = right_mm - left_mm - thumb_mm
            fy = forward_mm - reverse_mm - thumb_mm
            sx = right_mm - left_mm + thumb_mm
            sy = forward_mm - reverse_mm + thumb_mm
        else:  # 오른손
            fx = right_mm - left_mm - thumb_mm
            fy = forward_mm - reverse_mm + thumb_mm
            sx = right_mm - left_mm + thumb_mm
            sy = forward_mm - reverse_mm - thumb_mm

        self.base_coords = {
            "fx": fx,
            "fy": fy,
            "sx": sx,
            "sy": sy
        }
    
        self.recalculate_offset_with_toggle()
        
        self.toggle_applied = self.center_toggle.isChecked()

    def recalculate_offset_with_toggle(self):
        if not hasattr(self, "base_coords"):
            return
    
        fx = self.base_coords.get("fx", 0.0)
        fy = self.base_coords.get("fy", 0.0)
        sx = self.base_coords.get("sx", 0.0)
        sy = self.base_coords.get("sy", 0.0)
    
        if self.center_toggle.isChecked():
            # ✅ 위치 바꾸고 부호 바꿈 (회전 아님)
            self.first_x.setText(f"x = {fy:.2f}")
            self.first_y.setText(f"y = {-fx:.2f}")
            self.second_x.setText(f"x = {sy:.2f}")
            self.second_y.setText(f"y = {-sx:.2f}")
        else:
            # ✅ 원래대로 복원
            self.first_x.setText(f"x = {fx:.2f}")
            self.first_y.setText(f"y = {fy:.2f}")
            self.second_x.setText(f"x = {sx:.2f}")
            self.second_y.setText(f"y = {sy:.2f}")
