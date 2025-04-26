import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QRadioButton, QButtonGroup, QSystemTrayIcon, QMenu, QAction, QDialog,QCheckBox
from PyQt5.QtCore import Qt,  QUrl
from PyQt5.QtGui import QPainter, QColor, QIcon,  QPixmap
from PyQt5.QtGui import QDesktopServices
import configparser
import os
from ctypes import wintypes, Structure, windll

class POINT(Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

class MSG(Structure):
    _fields_ = [
        ("hWnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]

# 动态获取配置文件路径，兼容开发环境和打包环境
if getattr(sys, 'frozen', False):
    CONFIG_FILE = os.path.join(os.path.dirname(sys.executable), 'config.ini')
else:
    CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.ini')

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.opacity = 0.85
        self.setWindowTitle("关于 文曲星-AI提词助手")
        # 修改窗口标志，使用Tool标志而不是Dialog标志，避免对话框影响钩子
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint | Qt.Tool)
        self.setFixedSize(400, 500)
        # 设置为非模态对话框，避免阻塞主窗口事件循环
        self.setModal(False)
               
        # 主布局
        main_layout = QVBoxLayout()
        
        # 头像区域
        avatar = QLabel(self)
        avatar_pixmap = QPixmap(os.path.join(os.path.dirname(__file__), 'res', '头像100x168.png'))
        avatar.setPixmap(avatar_pixmap.scaled(100, 168, Qt.KeepAspectRatio))
        avatar.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(avatar)
        
        # 文本区域
        text_label = QLabel(self)
        with open(os.path.join(os.path.dirname(__file__), 'res', 'abort.txt'), 'r', encoding='utf-8') as f:
            text_label.setText(f.read())
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(text_label)
        
        # 二维码和链接区域
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # 二维码横向布局
        qr_hlayout = QHBoxLayout()
        qr_hlayout.setSpacing(10)
        qr_hlayout.setContentsMargins(0, 0, 0, 0)
        # 支付宝二维码
        alipay_label = QLabel(self)
        alipay_pixmap = QPixmap(os.path.join(os.path.dirname(__file__), 'res', '支付宝.png'))
        alipay_label.setFixedSize(120, 120)
        alipay_label.setPixmap(alipay_pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        alipay_label.setAlignment(Qt.AlignCenter)
        qr_hlayout.addWidget(alipay_label)
        # 微信二维码
        wechat_label = QLabel(self)
        wechat_pixmap = QPixmap(os.path.join(os.path.dirname(__file__), 'res', '微信.png'))
        wechat_label.setFixedSize(120, 120)
        wechat_label.setPixmap(wechat_pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        wechat_label.setAlignment(Qt.AlignCenter)
        qr_hlayout.addWidget(wechat_label)
        bottom_layout.addLayout(qr_hlayout)
        
        # 按钮横向布局
        btn_hlayout = QHBoxLayout()
        btn_hlayout.setSpacing(8)
        btn_hlayout.setContentsMargins(0, 0, 0, 0)
        help_btn = QPushButton("使用说明", self)
        help_btn.setFixedHeight(32)
        help_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com")))
        # github_btn = QPushButton("访问项目Github", self)
        # github_btn.setFixedHeight(32)
        # github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com")))
        btn_hlayout.addWidget(help_btn)
       # btn_hlayout.addWidget(github_btn)
        bottom_layout.addLayout(btn_hlayout)
        main_layout.addLayout(bottom_layout)
        
        # GitHub链接和按钮区域
        # btn_vlayout = QVBoxLayout()
        # btn_vlayout.setSpacing(8)
        # btn_vlayout.setContentsMargins(0, 0, 0, 0)
        # help_btn = QPushButton("使用说明", self)
        # help_btn.setFixedHeight(32)
        # help_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com")))
        # github_btn = QPushButton("访问项目Github", self)
        # github_btn.setFixedHeight(32)
        # github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com")))
        # btn_vlayout.addWidget(help_btn)
        # btn_vlayout.addWidget(github_btn)
        # btn_vlayout.addStretch(1)
        # bottom_layout.addLayout(btn_vlayout)
        
        main_layout.addLayout(bottom_layout)
        
        # 关闭按钮
        #close_btn = QPushButton("关闭", self)
        #close_btn.clicked.connect(self.hide)
        #main_layout.addWidget(close_btn)
        
        self.setLayout(main_layout)
    def closeEvent(self, event):
        """
        重写关闭事件处理，仅隐藏窗口而不执行其他操作
        确保关闭操作不会影响钩子状态
        """
        print("隐藏关于对话框")
        # 只隐藏窗口，不触发实际的关闭事件
        self.hide()
        # 阻止事件继续传播，防止触发父窗口事件链
        event.ignore()
  
class FloatingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.drag_position = None
        self.opacity = 1
        self.initUI()      
        self.initTrayIcon()       
        self.api_key = ""
        self.load_config()  # 先加载配置（如api_key等）     
        # 启动时根据鼠标位置显示窗口（仅在未设置api_key时才显示）
        if not self.api_key or not self.api_key.strip():
            self.show_at_cursor()
        #self.hide()
    def update_api_key_display(self):
        # 仅用于界面显示掩码，不修改实际内容
        pass
    def load_config(self):
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE, encoding='utf-8')
            if 'Window' in config:
                x = int(config['Window'].get('x', '100'))
                y = int(config['Window'].get('y', '100'))
                w = int(config['Window'].get('width', '240'))
                h = int(config['Window'].get('height', '120'))
                self.opacity = float(config['Window'].get('opacity', '0.85'))
                self.setGeometry(x, y, w, h)
                self.setWindowOpacity(self.opacity)
                if 'auto_send' in config['Window']:
                    self.auto_send_check.setChecked(config['Window'].get('auto_send', 'false') == 'true')
                self.api_key = config['Window'].get('api_key', '')
                if hasattr(self, 'api_key_edit'):
                    self.api_key_edit.setText(self.api_key)
                
                radio_mode = config['Window'].get('radio_mode', '')

                # 根据配置设置单选按钮状态，但不重复连接信号
                if hasattr(self, 'radio1') and hasattr(self, 'radio2') and hasattr(self, 'radio3'):
                    if radio_mode == 'shift_enter':
                        self.radio1.setChecked(True)
                    elif radio_mode == 'enter':
                        self.radio2.setChecked(True)
                    else:  # ctrl_enter
                        self.radio3.setChecked(True)
              

                # 新增：根据api_key是否为空决定窗口显示
                if self.api_key.strip():
                   # print('检测到已设置apikey，隐藏窗口')
                    self.hide()
                else:
                    #print('检测到未设置apikey，显示窗口')
                    self.show_at_cursor()

    def initUI(self):
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(self.opacity)
        self.setGeometry(0, 0, 240, 120)
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), r'res/EARTH.ICO')))
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(10)  # 增加控件间距
        layout.setContentsMargins(10, 10, 10, 10)  # 增加边距
        # 顶部标题栏
        title_layout = QHBoxLayout()
        title_layout.setSpacing(10)
        
        # 图标
        icon_label = QLabel(self)
        icon_pixmap = QIcon(os.path.join(os.path.dirname(__file__), r'res/EARTH.ICO')).pixmap(28, 28)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setStyleSheet("padding: 2px;")
        title_layout.addWidget(icon_label)
        
        # 标题
        self.label = QLabel("文曲星AI提词助手 v1.0", self)
        self.label.setStyleSheet("color: #FFFFFF; font-size: 15px; font-weight: bold; padding: 2px;")
        self.label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        title_layout.addWidget(self.label)
        title_layout.addStretch(1)
        
        # 关闭按钮
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet("""
            QPushButton {
                color: white;
                background: transparent;
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 2px;
            }
            QPushButton:hover {
                color: #FF4444;
                background: rgba(255, 68, 68, 0.1);
                border-radius: 4px;
            }
        """)
        self.close_btn.clicked.connect(self.hide)
        title_layout.addWidget(self.close_btn)
        layout.addLayout(title_layout)
        # API-Key设置区域
        api_label_layout = QHBoxLayout()
        api_label_layout.setSpacing(10)
        
        # API-Key标签
        api_label = QLabel("1. 设置deepseek api-key:", self)
        api_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                padding: 4px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 6px;
            }
        """)
        api_label_layout.addWidget(api_label)
        
        # 官网按钮
        official_btn = QPushButton("deepseek官网", self)
        official_btn.setStyleSheet("""
            QPushButton {
                color: #00BFFF;
                background: rgba(0, 191, 255, 0.1);
                border: 1px solid #00BFFF;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(0, 191, 255, 0.2);
            }
        """)
        official_btn.setCursor(Qt.PointingHandCursor)
        official_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.deepseek.com/")))
        api_label_layout.addWidget(official_btn)
        
        layout.addLayout(api_label_layout)
        # API-Key输入框
        from PyQt5.QtWidgets import QLineEdit
        self.api_key_edit = QLineEdit(self)
        self.api_key_edit.setPlaceholderText("请输入Deepseek API-Key...")
        self.api_key_edit.setStyleSheet("""
            QLineEdit {
                color: #FFFFFF;
                background: rgba(34, 34, 34, 0.8);
                border: 2px solid #444;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                margin: 5px 0;
            }
            QLineEdit:focus {
                border-color: #00BFFF;
                background: rgba(34, 34, 34, 0.9);
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.5);
            }
        """)
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.textChanged.connect(self.update_api_key_display)
        layout.addWidget(self.api_key_edit)
        # 单选框标签
        radio_title = QLabel("2. 激活模式：输入信息后按下快捷键激活提示词的自动优化", self)
        radio_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                padding: 6px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                margin-top: 10px;
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(radio_title)
        
        # 单选框
        radio_layout = QHBoxLayout()
        radio_layout.setSpacing(15)
        
        radio_style = """
            QRadioButton {
                color: #FFFFFF;
                font-size: 13px;
                padding: 5px;
                spacing: 5px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #666;
                background: rgba(34, 34, 34, 0.8);
            }
            QRadioButton::indicator:hover {
                border-color: #00BFFF;
            }
            QRadioButton::indicator:checked {
                background: qradialgradient(
                    cx: 0.5, cy: 0.5,
                    fx: 0.5, fy: 0.5,
                    radius: 0.4,
                    stop: 0 #00BFFF,
                    stop: 0.6 #00BFFF,
                    stop: 0.7 transparent
                );
                border-color: #00BFFF;
            }
            QRadioButton:hover {
                color: #00BFFF;
            }
        """
        
        self.radio1 = QRadioButton("Shift+Enter模式", self)
        self.radio1.setStyleSheet(radio_style)
        self.radio2 = QRadioButton("Enter模式", self)
        self.radio2.setStyleSheet(radio_style)
        self.radio3 = QRadioButton("Ctrl+Enter模式", self)
        self.radio3.setStyleSheet(radio_style)
        
        self.radio_group = QButtonGroup(self)
        self.radio_group.addButton(self.radio1)
        self.radio_group.addButton(self.radio2)
        self.radio_group.addButton(self.radio3)
        
        radio_layout.addWidget(self.radio1)
        radio_layout.addWidget(self.radio2)
        radio_layout.addWidget(self.radio3)
        layout.addLayout(radio_layout)
        
        # 在初始化时连接信号，避免重复连接
        self.radio1.toggled.connect(lambda: self.update_radio_mode('shift_enter'))
        self.radio2.toggled.connect(lambda: self.update_radio_mode('enter'))
        self.radio3.toggled.connect(lambda: self.update_radio_mode('ctrl_enter'))
        
        self.radio1.setChecked(True)
        # AutoSend复选框
        auto_send_layout = QHBoxLayout()
        auto_send_layout.setSpacing(10)
        
        self.auto_send_check = QCheckBox("自动发送", self)
        self.auto_send_check.setStyleSheet("""
            QCheckBox {
                color: #FFFFFF;
                font-size: 13px;
                padding: 5px;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #666;
                background: rgba(34, 34, 34, 0.8);
            }
            QCheckBox::indicator:hover {
                border-color: #00BFFF;
            }
            QCheckBox::indicator:checked {
                background: #00BFFF;
                border-color: #00BFFF;
                image: url(checkmark.png);
            }
            QCheckBox:hover {
                color: #00BFFF;
            }
        """)
        self.auto_send_check.setChecked(False)
        self.auto_send_check.stateChanged.connect(self.update_auto_send)
        auto_send_layout.addWidget(self.auto_send_check)
        layout.addLayout(auto_send_layout)
        
        # 按钮区
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        button_style = """
            QPushButton {
                color: #FFFFFF;
                background: rgba(0, 191, 255, 0.2);
                border: 2px solid #00BFFF;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background: rgba(0, 191, 255, 0.3);
            }
            QPushButton:pressed {
                background: rgba(0, 191, 255, 0.4);
            }
            QPushButton:checked {
                background: #00BFFF;
                color: #FFFFFF;
            }
        """
        
        self.toggle_btn = QPushButton("启用", self)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setStyleSheet(button_style)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle_feature)
        btn_layout.addWidget(self.toggle_btn)
        
        self.vip_btn = QPushButton("设置", self)
        self.vip_btn.setStyleSheet(button_style)
        self.vip_btn.setCursor(Qt.PointingHandCursor)
        self.vip_btn.clicked.connect(self.save_all_settings)
        btn_layout.addWidget(self.vip_btn)
        
        self.stop_btn = QPushButton("关于", self)
        self.stop_btn.setStyleSheet(button_style)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(self.show_about)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        # 全局快捷键
        self.register_hotkey()
        self.hide()

    def update_auto_send(self, state):
        """
        更新AutoSend属性值，根据复选框状态设置是否自动发送回车键
        :param state: 复选框状态，Qt.Checked或Qt.Unchecked
        """
        # 直接通过self.controller访问钩子对象
        if hasattr(self, 'controller') and self.controller and self.controller.hook:
            self.controller.hook.AutoSend = (state == Qt.Checked)
            print(f"自动发送设置已更新: {self.controller.hook.AutoSend}")
            
    def update_radio_mode(self, mode):
        """
        更新快捷键模式，实时生效
        :param mode: 模式字符串，可以是'enter'、'ctrl_enter'或'shift_enter'
        """
        # 直接通过self.controller访问钩子对象
        if hasattr(self, 'controller') and self.controller and self.controller.hook:
            self.controller.hook.radio_mode = mode
            print(f"快捷键模式已更新: {self.controller.hook.radio_mode}")
      

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ALT and event.key() == Qt.Key_AsciiTilde:
            print(f'组合键：{event}')    
            self.toggle_window_visibility()
        else:
            print(f'{event}')    
    
    def register_hotkey(self):
        MOD_ALT = 0x0001
        VK_TILDE = 0xC0
        hwnd = int(self.winId())
        
        # 先尝试注销已有热键
        windll.user32.UnregisterHotKey(hwnd, 1)
        
        # 注册新热键并检查结果
        if not windll.user32.RegisterHotKey(hwnd, 1, MOD_ALT, VK_TILDE):
            error = windll.kernel32.GetLastError()
            print(f"热键注册失败，错误代码：{error}")
            # 常见错误：
            # 1409 (0x581): 热键已被占用
            # 5: 权限不足（需管理员权限）
       
            
    def nativeEvent(self, eventType, message):
        """修正后的原生事件处理"""
        msg = MSG.from_address(message.__int__())
        if msg.message == 0x0312:  # WM_HOTKEY
            if msg.wParam == 1:    # 匹配我们注册的热键ID
                self.toggle_window_visibility()
                return (True, 0)    # 返回处理成功
        return super().nativeEvent(eventType, message)

    def show_at_cursor(self):
        from PyQt5.QtGui import QCursor
        from PyQt5.QtWidgets import QApplication
        pos = QCursor.pos()
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        window_width = self.width()
        window_height = self.height()
        x = pos.x()
        y = pos.y()
        # 判断是否超出右侧
        if x + window_width > screen_width:
            x = max(0, screen_width - window_width)
        # 判断是否超出下侧
        if y + window_height > screen_height:
            y = max(0, screen_height - window_height)
        self.move(x, y)
        self.show()

    def initTrayIcon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(os.path.join(os.path.dirname(__file__), r'res/EARTH.ICO')))
        
        # 延迟显示托盘气泡提示，确保托盘图标完全初始化
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1000, lambda: self.tray_icon.showMessage(
            "文曲星AI提词助手",
            "程序已在后台运行，可按Alt+~键呼出设置界面",
            QSystemTrayIcon.Information,
            3000  # 显示3秒
        ))
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        # 显示/隐藏动作
        show_action = QAction("显示", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        # 设置动作
        # settings_action = QAction("设置", self)
        # settings_action.triggered.connect(self.show_settings)
        # tray_menu.addAction(settings_action)
        
        # 关于动作
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        tray_menu.addAction(about_action)
        
        # 退出动作
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
    def show_settings(self):
        # 这里可以添加设置窗口的逻辑
        print("显示设置窗口")
        
    def show_about(self):
        """
        显示关于对话框，确保不会影响全局钩子的生命周期
        """
        print("[DEBUG] 正在显示关于对话框...")
        # 采用单例模式，避免多次创建导致钩子状态混乱
        if not hasattr(self, '_about_dialog') or self._about_dialog is None:
            self._about_dialog = AboutDialog(self)
            # 确保对话框关闭时只是隐藏而不是销毁
            self._about_dialog.setAttribute(Qt.WA_DeleteOnClose, False)
            # 断开关于对话框的信号连接，防止影响主窗口
            self._about_dialog.finished.connect(lambda: None)
            self._about_dialog.rejected.connect(lambda: None)
            # 确保关闭事件不会触发任何可能导致钩子释放的操作
            def safe_close_event(event):
                self._about_dialog.hide()
                event.ignore()
            self._about_dialog.closeEvent = safe_close_event
        print("[DEBUG] 对话框创建完成，准备显示，父窗口:", self)
        # 使用非模态方式显示，避免阻塞主窗口事件循环
        self._about_dialog.show()
        print("[DEBUG] 对话框已显示(非模态)")
        
    def toggle_feature(self, checked):
        if checked:
            self.toggle_btn.setText("停用")
            # 这里可扩展为实际功能启停
        else:
            self.toggle_btn.setText("启用")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        #self.save_config()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(30, 30, 30, int(255 * self.opacity))
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    def save_config(self):
        config = configparser.ConfigParser()
        config['Window'] = {
            'x': str(self.x()),
            'y': str(self.y()),
            'width': str(self.width()),
            'height': str(self.height()),
            'opacity': str(self.opacity)
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)

    def save_all_settings(self):
        config = configparser.ConfigParser()
        self.api_key = self.api_key_edit.text()  # 立即更新api_key变量
        config['Window'] = {
            'x': str(self.x()),
            'y': str(self.y()),
            'width': str(self.width()),
            'height': str(self.height()),
            'opacity': str(self.opacity),
            'api_key': self.api_key,
            'radio_mode': 'shift_enter' if self.radio1.isChecked() else 'enter' if self.radio2.isChecked() else 'ctrl_enter',
            'auto_send': 'true' if self.auto_send_check.isChecked() else 'false'
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "提示", "设置已成功保存！")
    
    def toggle_window_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show_at_cursor()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FloatingWindow()
    sys.exit(app.exec_())