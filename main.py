import sys
import configparser
from PyQt5.QtWidgets import QApplication
from gui import FloatingWindow
from aitools import GlobalKeyboardHook
import os
import importlib.util

def get_config_path(filename):
    """
    获取配置文件路径，支持开发环境和打包环境
    :param filename: 配置文件名
    :return: 配置文件完整路径
    """
    if getattr(sys, 'frozen', False):
        # 打包环境优先尝试exe同级目录，再尝试_MEIPASS临时目录
        base_dir = os.path.dirname(sys.executable)
        print("exe路径：",base_dir)
        print("config.ini路径：",os.path.join(base_dir, filename))
        print("config.py路径：",os.path.join(base_dir, "config.py"))
        print("config.ini存在：",os.path.exists(os.path.join(base_dir, filename)))
        print("config.py存在：",os.path.exists(os.path.join(base_dir, "config.py")))
        if not os.path.exists(os.path.join(base_dir, filename)):          
            base_dir = getattr(sys, '_MEIPASS', base_dir)
            print("临时目录路径：",base_dir)
            print("config.ini路径：",os.path.join(base_dir, filename))
            print("config.py路径：",os.path.join(base_dir, "config.py"))
            print("config.ini存在：",os.path.exists(os.path.join(base_dir, filename)))
            print("config.py存在：",os.path.exists(os.path.join(base_dir, "config.py")))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))  # 开发环境
    return os.path.join(base_dir, filename)

CONFIG_FILE = get_config_path('config.ini')

def get_api_key_and_mode():
    """
    从config.ini获取API密钥和模式设置
    :return: (api_key, radio_mode)
    """
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE, encoding='utf-8')
        api_key = config['Window'].get('api_key', '') if 'Window' in config else ''
        radio_mode = config['Window'].get('radio_mode', 'shift_enter') if 'Window' in config else 'shift_enter'
        return api_key, radio_mode
    return '', 'shift_enter'

def load_config_module():
    """
    动态加载config.py模块
    :return: 加载成功的config模块对象
    """
    config_path = get_config_path('config.py')
    if os.path.exists(config_path):
        try:
            # 先尝试重新加载已导入的模块
            if 'config' in sys.modules:
                importlib.reload(sys.modules['config'])
                print(f"config.py已重新加载 {sys.modules['config']}")
                return sys.modules['config']
            
            # 如果模块未导入，则从文件加载
            spec = importlib.util.spec_from_file_location("config", config_path)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            print(f"如果模块未导入，则从文件加载 config.py已加载 {config_module}")
            return config_module
        except Exception as e:
            print(f"加载config.py失败: {e}")
            return None
    return None

def get_auto_send_setting():
    """从配置文件中读取auto_send设置"""
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE, encoding='utf-8')
        auto_send = config['Window'].get('auto_send', 'false') if 'Window' in config else 'false'
        return auto_send.lower() == 'true'
    return False

class AppController:
    def __init__(self):
        self.api_key, self.radio_mode = get_api_key_and_mode()
        self.hook = None
        self.window = FloatingWindow()
        self.window.toggle_btn.clicked.connect(self.toggle_hook)
        # 修改连接方式，确保关于按钮不会触发钩子释放
        self.window.stop_btn.clicked.connect(self.show_about_safely)
        self.window.radio1.toggled.connect(self.update_radio_mode)
        self.window.radio2.toggled.connect(self.update_radio_mode)
        # 监听自动发送复选框状态变化
        self.window.auto_send_check.stateChanged.connect(self.update_auto_send_from_ui)
        # 初始化API_KEY
        if self.api_key:
            self.start_hook()
            self.window.toggle_btn.setChecked(True)
            self.window.toggle_btn.setText("停用")
        else:
            self.window.toggle_btn.setChecked(False)
            self.window.toggle_btn.setText("启用")
            
    def update_auto_send_from_config(self):
        """从配置文件读取auto_send设置并应用到hook对象"""
        if self.hook:
            auto_send = get_auto_send_setting()
            self.hook.AutoSend = auto_send        

    def update_api_key_from_config(self):
        """从配置文件读取api-key设置并应用到hook对象"""
        if self.hook:
            self.api_key,_ = get_api_key_and_mode()
            self.hook.API_KEY = self.api_key
            self.hook.set_api_key(self.api_key)
         
    def update_auto_send_from_ui(self, state):
        """从UI更新auto_send设置到hook对象"""
        from PyQt5.QtCore import Qt
        if self.hook:
            self.hook.AutoSend = (state == Qt.Checked)
            print(f"从UI更新自动发送设置: {self.hook.AutoSend}")
            
    def show_about_safely(self):
        """
        安全地显示关于对话框，确保不会影响钩子状态
        该方法替代直接连接到window.stop_btn的方式，提供额外的保护层
        """
        # 保存当前钩子状态
        had_hook = self.hook is not None
        # 显示关于对话框
        self.window.show_about()
        # 如果显示对话框导致钩子被释放，则恢复钩子
        if had_hook and self.hook is None:          
            self.start_hook()

    def update_radio_mode(self):
        # 只要切换单选框就更新radio_mode并同步到钩子
        self.api_key, self.radio_mode = get_api_key_and_mode()
        if self.hook:
            self.hook.set_radio_mode(self.radio_mode)
           

    def toggle_hook(self):
        if self.window.toggle_btn.isChecked():
            self.start_hook()
            self.window.toggle_btn.setText("停用")
        else:
            self.stop_hook()
            self.window.toggle_btn.setText("启用")

    def start_hook(self):
        if not self.hook:
            self.hook = GlobalKeyboardHook()
            # 用config.ini的api_key覆盖
            self.hook.API_KEY = self.api_key
            # 设置快捷键模式
            if hasattr(self.hook, 'set_radio_mode'):
                self.hook.set_radio_mode(self.radio_mode)
            # 设置AutoSend属性
            self.update_auto_send_from_config()
            # 同步更新API_KEY
            self.update_api_key_from_config()
             # 同步更新API_KEY
            if hasattr(self.hook, 'set_api_key'):  
                self.hook.set_api_key(self.api_key)
            else:             
                self.hook.API_KEY = self.api_key

            self.hook.set_hook()
        else:
            # 确保hook实例存在时也更新API_KEY
            self.hook.API_KEY = self.api_key
            # 更新AutoSend属性
            self.update_auto_send_from_config()

    def stop_hook(self):
        """
        停止钩子功能
        该方法只应由用户主动点击停用按钮或退出程序时调用
        不应被对话框等UI事件间接触发
        """
        # 检查调用来源，避免被关于对话框等UI事件间接触发
        import traceback
        stack = traceback.extract_stack()
        # 检查整个调用堆栈，而不仅仅是直接调用者
        for frame in stack:
            # 检查是否有任何与对话框相关的调用
            if 'show_about' in frame.name or 'closeEvent' in frame.name or 'AboutDialog' in frame.name:              
                return
            
        if self.hook:
            self.hook.unset_hook()
            self.hook = None
            self.window.toggle_btn.setChecked(False)
            self.window.toggle_btn.setText("启用")

if __name__ == "__main__":
    # 单实例检查
    import socket
    try:
        # 尝试创建socket server
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('localhost', 12345))
    except socket.error:
        # 如果端口已被占用，说明已有实例运行
        print("程序已在运行中")
        sys.exit(0)
        
    app = QApplication(sys.argv)
    controller = AppController()
    
    # 将controller设置为window的属性，以便在gui.py中访问
    controller.window.controller = controller
    
    # 注册程序退出时的钩子释放
    import atexit
    def cleanup():     
        if controller and controller.hook:
            controller.hook.unset_hook()
    
    # 仅在程序真正退出时才释放钩子
    atexit.register(cleanup)
    
    sys.exit(app.exec_())