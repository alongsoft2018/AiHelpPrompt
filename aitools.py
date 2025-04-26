import sys
import ctypes
from ctypes import wintypes
from core.electron_text_extractor_v2 import get_electron_input_text
from core.deepseek_server import deepseek_api_chat
import atexit
import keyboard
import pyperclip
import threading
from config import APP_CONFIGS, TITLE_MATCH_HANDLERS
import logging
import time

logging.basicConfig(format='%(asctime)s %(levelname)s [%(module)s]: %(message)s', level=logging.DEBUG)

class GlobalKeyboardHook:
    def __init__(self):
        self.window_configs = list(APP_CONFIGS.values())
        self.HHOOK          = ctypes.c_void_p
        self.WH_KEYBOARD_LL = 13
        self.WM_KEYDOWN     = 0x0100
        self.hook_id        = None
        self.callback       = None
        self.user32         = ctypes.WinDLL('user32', use_last_error=True)
        self.kernel32       = ctypes.WinDLL('kernel32', use_last_error=True)
        self.LRESULT        = ctypes.c_int64
        self._set_types()
        self.ULONG_PTR      = ctypes.c_uint32 if ctypes.sizeof(ctypes.c_void_p) == 4 else ctypes.c_uint64       
        # 获取屏幕高度 - 用于处理判断用户是否在浏览器的网址执行回车键的异常机制
        self.screen_height = ctypes.windll.user32.GetSystemMetrics(1)
        # 定义鼠标位置结构体
        class POINT(ctypes.Structure):
            _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]
        self.POINT = POINT
        self.API_KEY        = ""
        self.ai_response    = ''
        self.MaxMagLen      = 200   #用户输入的最大信息阈值
        self.ignore_enter   = False #用于区分回车键是否是程序还是用户
        self.save_usermsg_list  = [] #保存用户原始的需求
        self.AutoSend       = False #是否直接发送信息- 或者等用户自己发送
        class KBDLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ('vkCode', wintypes.DWORD),
                ('scanCode', wintypes.DWORD),
                ('flags', wintypes.DWORD),
                ('time', wintypes.DWORD),
                ('dwExtraInfo', self.ULONG_PTR)
            ]
        self.KBDLLHOOKSTRUCT = KBDLLHOOKSTRUCT
        self.user32.UnhookWindowsHookEx.argtypes = (self.HHOOK,)
        self.user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        # 注册退出钩子，但使用弱引用避免对话框关闭时触发
        # 注意：仅在主程序退出时才应释放钩子
        # atexit.register(self.unset_hook) # 移除自动注册，由主程序控制钩子生命周期
        # windows下检测权限
        self.check_permission()

    def check_permission(self):
        if ctypes.windll.shell32.IsUserAnAdmin() == 0:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, __file__, None, 1
            )
            sys.exit()

    def _set_types(self):
        self.user32.SetWindowsHookExW.argtypes = (
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.HINSTANCE,
            wintypes.DWORD
        )
        self.user32.SetWindowsHookExW.restype = self.HHOOK
        self.user32.CallNextHookEx.argtypes = (
            self.HHOOK,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM
        )
        self.user32.CallNextHookEx.restype = self.LRESULT
        
    def set_api_key(self, api_key):
        """
        更新API_KEY的值
        :param api_key: 新的API_KEY值
        """
        self.API_KEY = api_key
    
    def initMsg(self):
        """
        初始化消息处理流程，包含剪贴板清空、全选、复制等操作，并增加异常捕获和详细日志，防止COM库或剪贴板异常导致流程中断。
        """
        clipboard_text = ""
        try:
            # 确保之前的键盘操作已完全释放
            keyboard.release('ctrl')
            keyboard.release('shift')
            keyboard.release('alt')
            time.sleep(0.05)
            
            # 清空剪贴板
            pyperclip.copy("")
            logging.debug('清空剪贴板')
            
            # 全选文字 - 使用send代替press/release组合，更可靠
            logging.debug('开始全选')
            keyboard.send('ctrl+a')
            time.sleep(0.1)
            
            # 全选后复制内容到剪贴板中
            logging.debug('开始复制')
            keyboard.send('ctrl+c')
            time.sleep(0.1)
            
            # 提取原信息
            clipboard_text = pyperclip.paste()
            if clipboard_text != '':
                # 有可能用户在浏览器的网址输入框中输入信息导致异常，需要过滤http开头的信息，如果发现直接跳过
                self.save_usermsg_list.append(clipboard_text)
                logging.debug(f"获取的文本：{clipboard_text}")
                
                # 判断clipboard_text开头是否是#号开头的特殊指令
                if clipboard_text.startswith('#'):
                    # 如果是则直接模拟发送
                    logging.debug('initMsg 特殊指令-> 直接模拟发送')   
                    keyboard.send('enter')
                    time.sleep(0.1)                 
                    return clipboard_text

                # 删除选中的文本
                logging.debug('开始删除')
                keyboard.send('delete')
                time.sleep(0.1)
                
                # 粘贴提示信息
                pyperclip.copy("正在优化提示词,请稍后...")
                logging.debug('开始粘贴')
                keyboard.send('ctrl+v')
                time.sleep(0.1)
                logging.debug('完成粘贴')

              
                return clipboard_text
        except Exception as e:
            logging.error(f"initMsg流程异常: {e}")
            # 若COM或剪贴板异常，返回空字符串，后续流程可走B计划
            return ""
        return clipboard_text
    
    def send2aiserver(self,config_name):
        # 将用户输入的需求发送到ai服务端进行提示词的完善
        self.ai_response = ''
        if self.API_KEY == "":
           logging.error('未设置Api-Key')
           return None
        # 构建结构化提示词模板     
        old_text = self.initMsg()
        # 通过操控剪贴板获取内容
        if old_text != '' and old_text is not None:
            text = old_text
        # else:# 采用B计划-获取信息
        #     logging.error('采用B计划-获取信息')
        #     text = get_electron_input_text(config_name=config_name)
        
        # 增加特殊指令的处理
        if text is not None:       
            if text.startswith('#'):
                logging.info(f'send2aiserver 特殊指令-> 直接模拟发送: {text}')
                self.ignore_enter = False
                return text
        else:
            logging.error('ERR: send2aiserver -> 取内容错误')
            return None    

        if text != '':
            logging.info(f'拦截输入框文本: {text}')
            system_prompt = f"""请严格按照以下框架分析用户需求并生成专业提示词：
            - Role: 领域专家角色定位 特别注意：开头一定要加上‘你是一位’的开头，如你是一位资深的程序员，你是一位资深的医生等。
            - Background: 基于用户输入需求的背景说明
            - Profile: 专业背景与核心能力描述
            - Skills: 需要具备的专项技能清单
            - Goals: 分阶段实现的核心目标
            - Constraints: 开发限制与边界条件
            - Workflow: 分步骤实现路径
            - Examples: 关键环节的示例说明（编程类的含核心代码示例）
            - OutputFormat: 输出内容格式要求
            - Initialization: 初始化引导语句
            - Other: 其他扩展 - 对需求进行分类的更细致的处理，设定如下：
                - 1. 编程类：
                    - 1.1: 定义函数的参数需要写上函数的类型，比如python用from typing import Optional, Dict, List, Tuple
                    - 1.2: 编写语言比如python使用pygame，qt5,dearpygui等涉及gui显示需求时，如果用户输入的是需求是非英文的，需要考虑编码的问题，引入正确的字库，避免Gui显示中文乱码
                - 2. 医药咨询类：
                    - 2.1: 涉及儿童相关的医药生病咨询，需要考虑咨询人（大概率是父母）的情绪，做好适当的安抚，避免咨询人过度紧张而不能理智的说明病情
                    - 2.2: 最后一定要告知咨询人，上述建议只是基于病情描述的推理，只能做参考，情况紧急的病情必须就近到专业的医疗机构治疗
                - 3. 人文，历史，地理，典籍等: - 引入的字，词，短文等需要备注上出处。
                - 4. 其他扩展要求:
                    - 4.1 请根据用户输入的需求的语言与生成的提示词保持一致性，即输入的中文-提示词也需要中文-并告知Ai大模型，回复也请使用中文回复     
            当前用户需求是：{text} """
        else:
            logging.error('ERR: send2aiserver -> 取内容错误')
            return None
        

        post_messages = [
            {
                "role": "system",
                "content": """【身份与职责】
                    您作为专业提示词工程师，需严格遵循以下工作准则：

                    【核心原则】
                    1. 真实性优先
                    - 只处理用户明确提供的信息
                    - 拒绝任何形式的推测、假设或虚构
                    - 当信息不足时，必须主动要求补充细节

                    2. 精确转化
                    - 保持输入/输出语言严格一致
                    - 中文需求对应中文提示词及中文回复
                    - 确保技术术语准确无歧义
             

                    3. 身份一致性维护
                    - 输出提示词需完全模拟终端用户身份
                    - 确保大模型无法识别工程师介入痕迹
                    - 最终输出须符合直接用户请求特征

                    4. 自动化响应机制
                    - 对问候/测试类信息启用直接转发协议
                    - 保持原始语句结构及用词零修改
                    - 适用范围包括但不限于：问候语、身份询问、功能测试等基础交互
                    
                    5. 特殊功能
                    - 当用户输入的原始信息开头是#号时，将其视为特殊指令,过滤掉#号后将后面的全部信息直接转发协议
                    - 保持原始语句结构及用词零修改
                    """
            },
            {
                "role": "user",
                "content": system_prompt
            }
        ]

        success, response, full_res = deepseek_api_chat(self.API_KEY, post_messages)
        
        if success:
            logging.info(response)
            self.ai_response = response
            
            try:
                # 确保之前的键盘操作已完全释放
                keyboard.release('ctrl')
                keyboard.release('shift')
                keyboard.release('alt')
                time.sleep(0.05)
                
                # 全选文本
                logging.debug('完成AI回复-> 开始全选')
                keyboard.send('ctrl+a')
                time.sleep(0.1)
                
                # 删除选中的文本
                logging.debug('开始删除')
                keyboard.send('delete')
                time.sleep(0.1)
                
                # 复制AI回复到剪贴板
                pyperclip.copy(response)  # 将文本复制到剪贴板
                time.sleep(0.1)
                
                # 粘贴AI回复
                logging.debug('将文本复制到剪贴板-> 开始粘贴')
                keyboard.send('ctrl+v')  # 粘贴
                time.sleep(0.1)
                logging.debug('更新提示词完成')
                
                # 如果需要自动发送，则发送回车键
                if self.AutoSend:
                    keyboard.send('enter')   # 发送回车键
                    time.sleep(0.05)
            except Exception as e:
                logging.error(f"AI回复处理过程中出现异常: {e}")
            finally:
                # 无论如何都重置ignore_enter标志
                self.ignore_enter = False
                
            return response
        else:
            self.ai_response = ''
            logging.error(f"请求失败：{response} {full_res}")
            return None

    def set_radio_mode(self, mode):
        """设置快捷键模式: mode为'shift_enter'、'ctrl_enter'或'enter'"""
        self.radio_mode = mode
    
    def low_level_keyboard_proc(self, nCode, wParam, lParam):
        if nCode == 0 and wParam == self.WM_KEYDOWN:
            kb_struct = ctypes.cast(lParam, ctypes.POINTER(self.KBDLLHOOKSTRUCT)).contents      
            # 检测任意Shift键状态 (0xA0是左Shift, 0xA1是右Shift)
            left_shift_state = self.user32.GetAsyncKeyState(0xA0) & 0x8000
            right_shift_state = self.user32.GetAsyncKeyState(0xA1) & 0x8000
            shift_state = left_shift_state or right_shift_state
            
            # 检测Ctrl键状态 (0xA2是左Ctrl, 0xA3是右Ctrl)
            left_ctrl_state = self.user32.GetAsyncKeyState(0xA2) & 0x8000
            right_ctrl_state = self.user32.GetAsyncKeyState(0xA3) & 0x8000
            ctrl_state = left_ctrl_state or right_ctrl_state
            
            # 判断快捷键模式
            if hasattr(self, 'radio_mode') and self.radio_mode == 'enter':           
                if kb_struct.vkCode == 0x0D and not shift_state and not ctrl_state:
                    logging.info('快捷键模式 - enter模式')
                    enter_trigger = True
                else:
                    enter_trigger = False
            elif hasattr(self, 'radio_mode') and self.radio_mode == 'ctrl_enter':
                if kb_struct.vkCode == 0x0D and ctrl_state:
                    logging.info('快捷键模式 - ctrl+enter模式')
                    enter_trigger = True
                else:
                    enter_trigger = False
            else:                       
                enter_trigger = kb_struct.vkCode == 0x0D and shift_state
                if enter_trigger:
                    logging.info('快捷键模式 - shift+enter模式')
            
            if enter_trigger:
                window_title = None
                for config_name, config in APP_CONFIGS.items():
                    match_type = config.get('title_match', {}).get('type', 'exact')
                    match_value = config.get('title_match', {}).get('value', '')
                    match_func = TITLE_MATCH_HANDLERS.get(match_type, lambda t, v: t == v)
                    hwnd = self.user32.GetForegroundWindow()
                    buffer = ctypes.create_unicode_buffer(512)
                    self.user32.GetWindowTextW(hwnd, buffer, 512)
                    window_title = buffer.value
                    if match_func(window_title, match_value):
                        break
                else:
                    config_name = None
                for config in self.window_configs:
                    match_type = config.get('title_match', {}).get('type', 'exact')
                    match_value = config.get('title_match', {}).get('value', '')
                    match_func = TITLE_MATCH_HANDLERS.get(match_type, lambda t, v: t == v)
                    if match_func(window_title, match_value) and not self.ignore_enter:
                        pt = self.POINT()
                        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                        logging.info(f'当前鼠标位置: {pt.x,pt.y} {self.screen_height * 0.35}')
                        # 如果鼠标在屏幕的上方25%区域 一般是浏览器地址栏
                        if pt.y > self.screen_height * 0.25: 
                            threading.Thread(target=self.send2aiserver,args=[config_name,]).start()
                            self.ignore_enter = True
                            return 1  # 阻止事件传递   
                        else:
                            logging.info('本次回车键触发可能在浏览器地址栏中，不拦截！')
                            return 0
                return 0
        return self.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

    def set_hook(self):
        if self.hook_id is not None:
            logging.warning("钩子已注册，无需重复注册")
            return
        callback_type = ctypes.WINFUNCTYPE(self.LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        # 绑定实例方法
        self.callback = callback_type(lambda nCode, wParam, lParam: self.low_level_keyboard_proc(nCode, wParam, lParam))
        self.hook_id = self.user32.SetWindowsHookExW(self.WH_KEYBOARD_LL, self.callback, None, 0)
        if not self.hook_id:
            error_code = self.kernel32.GetLastError()
            raise ctypes.WinError(error_code)

    # 新增：卸载钩子的函数
    def unset_hook(self):       
        if self.hook_id is not None:
            try:
                self.user32.UnhookWindowsHookEx(self.hook_id)
                logging.info("钩子已释放")
            except Exception as e:
                logging.error(f"释放钩子时发生异常: {e}")
            self.hook_id = None
        else:
            logging.warning("钩子未注册，无需释放")

    def message_loop(self):
        msg = wintypes.MSG()
        while self.user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
            self.user32.TranslateMessage(ctypes.byref(msg))
            self.user32.DispatchMessageW(ctypes.byref(msg))

if __name__ == "__main__":
    hook = GlobalKeyboardHook()
    try:
        hook.set_hook()
        logging.info("钩子已设置，等待事件... (按Ctrl+C退出)")
        hook.message_loop()
    except KeyboardInterrupt:
        logging.info("用户中断，退出程序")      
        hook.unset_hook() 
    finally:
        hook.unset_hook()  # 确保无论如何退出都释放钩子

    
   