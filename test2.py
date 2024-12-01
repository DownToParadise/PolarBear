import sys
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QSpinBox, QPushButton, QTextEdit, QFormLayout, QHBoxLayout, QFontComboBox, QCheckBox, QMainWindow, QTextBrowser, QWidget
from PyQt5.QtGui import QFont

class FontSettingsDialog(QDialog):
    def __init__(self, parent=None, current_font=QFont()):
        super().__init__(parent)
        self.current_font = current_font  # 保存传入的当前字体
        self.preview_text = "This is a preview of the font settings."
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Set Font Properties')

        # 字体家族组合框
        self.font_family_combo = QFontComboBox()
        self.font_family_combo.setCurrentFont(self.current_font)  # 设置当前字体

        # 字体大小微调框
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setValue(self.current_font.pointSize())
        self.font_size_spinbox.setRange(6, 100)
        # self.font_size_spinbox.valueChanged.connect(self.update_preview)

        # 粗体复选框
        self.bold_checkbox = QCheckBox('Bold')
        self.bold_checkbox.setChecked(self.current_font.bold())
        # self.bold_checkbox.stateChanged.connect(self.update_preview)

        # 斜体复选框
        self.italic_checkbox = QCheckBox("Italic", self)
        self.italic_checkbox.setChecked(self.current_font.italic())
        # self.italic_checkbox.stateChanged.connect(self.update_preview)

        # 预览文本编辑框
        self.preview_text_edit = QTextEdit()
        self.preview_text_edit.setReadOnly(True)
        self.update_preview()  # 初始化预览

        # 连接信号和槽
        self.font_family_combo.currentFontChanged.connect(self.update_preview)
        self.font_size_spinbox.valueChanged.connect(self.update_preview)
        self.bold_checkbox.stateChanged.connect(self.update_preview)
        self.italic_checkbox.stateChanged.connect(self.update_preview)

        # 布局
        form_layout = QFormLayout()
        form_layout.addRow('Font Family:', self.font_family_combo)
        form_layout.addRow('Font Size:', self.font_size_spinbox)
        form_layout.addRow(self.bold_checkbox, self.italic_checkbox)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.preview_text_edit)

        buttons = QHBoxLayout()
        confirm_button = QPushButton('Confirm')
        confirm_button.clicked.connect(self.accept)
        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(confirm_button)
        buttons.addWidget(cancel_button)

        layout.addLayout(buttons)
        self.setLayout(layout)

    def update_preview(self):
        # 根据当前设置更新预览文本
        font = self.font_family_combo.currentFont()
        font.setPointSize(self.font_size_spinbox.value())
        font.setBold(self.bold_checkbox.isChecked())
        font.setItalic(self.italic_checkbox.isChecked())
        self.preview_text_edit.setFont(font)
        self.preview_text_edit.setPlainText(self.preview_text)

    def get_selected_font(self):
        # 返回用户选择的字体
        font = self.font_family_combo.currentFont()
        font.setPointSize(self.font_size_spinbox.value())
        font.setBold(self.bold_checkbox.isChecked())
        font.setItalic(self.italic_checkbox.isChecked())
        return font

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Main Window')

        # 创建 QTextBrowser 用于显示文本
        self.text_browser = QTextBrowser(self)
        self.default_font = QFont('Arial', 12)  # 设置默认字体
        self.text_browser.setFont(self.default_font)
        self.text_browser.setPlainText("This is the main text browser where the font will be applied.")

        # 创建按钮用于打开字体设置对话框
        self.settings_button = QPushButton('Set Font', self)
        self.settings_button.clicked.connect(self.open_font_settings_dialog)

        # 布局
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.text_browser)
        layout.addWidget(self.settings_button)

        self.setCentralWidget(central_widget)

    def open_font_settings_dialog(self):
        # 打开字体设置对话框，并传入当前字体
        dialog = FontSettingsDialog(self, self.text_browser.font())
        if dialog.exec_() == QDialog.Accepted:
            # 获取用户选择的字体并应用到 QTextBrowser
            selected_font = dialog.get_selected_font()
            self.text_browser.setFont(selected_font)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())