import ctypes
import time
from ctypes import windll, wintypes, byref, Structure, POINTER, c_long, c_int, c_ulong, c_char, c_char_p, c_void_p, c_wchar_p, c_wchar, c_ushort,c_longlong
import re
import logging
# Windows API常量
OBJID_CLIENT = 0xFFFFFFFC
UIA_ValuePatternId = 10002
UIA_LegacyIAccessiblePatternId = 10018
UIA_TextPatternId = 10014

# IAccessible相关常量
ROLE_SYSTEM_TEXT = 42
STATE_SYSTEM_FOCUSABLE = 0x00100000
STATE_SYSTEM_FOCUSED = 0x00000004

# 定义Windows API函数和结构体
class VARIANT(Structure):
    _fields_ = [
        ('vt', c_ushort),
        ('wReserved1', c_ushort),
        ('wReserved2', c_ushort),
        ('wReserved3', c_ushort),
        ('llVal', c_longlong),
    ]

class POINT(Structure):
    _fields_ = [('x', c_long), ('y', c_long)]

class IAccessible(Structure):
    _fields_ = [('lpVtbl', c_void_p)]

# 加载必要的DLL
user32 = windll.user32
ole32 = windll.ole32
oleacc = windll.oleacc

# 初始化COM库
ole32.CoInitialize(None)

    
def get_hwnd_by_title_pattern(title_pattern):
    hwnd = None
    import win32gui
    def enum_handler(handle, result_list):
        window_text = win32gui.GetWindowText(handle)
        if re.search(title_pattern, window_text):
            result_list.append(handle)
    result = []
    win32gui.EnumWindows(enum_handler, result)
    if result:
        hwnd = result[0]
    return hwnd
def find_target_window(config):
    import ctypes
    import time
    import re
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    hwnds = []
    def get_window_z_order(hwnd):
        z = 0
        curr = hwnd
        while curr:
            curr = user32.GetWindow(curr, 3)  # GW_HWNDPREV
            if curr:
                z += 1
        return z
    def get_last_activity_time(hwnd):
        # 简化：返回当前时间戳，实际可扩展为真实活动时间
        return int(time.time())
    from config import TITLE_MATCH_HANDLERS
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum_proc(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            title = ctypes.create_unicode_buffer(512)
            class_name = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, 512)
            user32.GetClassNameW(hwnd, class_name, 256)
            match_rules = [
                class_name.value == "Chrome_WidgetWin_1",
                TITLE_MATCH_HANDLERS[config["title_match"]["type"]](title.value, config["title_match"]["value"])
            ]
            if all(match_rules):
                hwnds.append({
                    "hwnd": hwnd,
                    "z_order": get_window_z_order(hwnd),
                    "last_activity": get_last_activity_time(hwnd)
                })
        return True
    user32.EnumWindows(enum_proc, 0)
    if hwnds:
        return sorted(hwnds, key=lambda x: (-x["z_order"], -x["last_activity"]))[0]["hwnd"]
    return None
def get_electron_input_text(config_name=None, **kwargs):
    try:
        import config
        if config_name:
            conf = config.APP_CONFIGS.get(config_name)
            if not conf:
                raise ValueError(f"无效的配置名称: {config_name}")
            kwargs.update(conf)
        window_base_title = kwargs.get("window_base_title", None)
        control_name = kwargs.get("control_name", None)
        role = kwargs.get("role", ROLE_SYSTEM_TEXT)
        title_match = kwargs.get("title_match", None)
        hwnd = None
        if title_match:
            hwnd = find_target_window(kwargs)
        elif window_base_title:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, window_base_title)
            if not hwnd:
                hwnd = user32.GetForegroundWindow()
        else:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
        if not hwnd:
            logging.error("未能获取目标窗口")
            return None
        try:
            import comtypes.client as cc
            UIAutomation = cc.GetModule("UIAutomationCore.dll")
            IUIAutomation = cc.CreateObject("{ff48dba4-60ef-4201-aa87-54103eef594e}", interface=UIAutomation.IUIAutomation)
            root_element = IUIAutomation.ElementFromHandle(hwnd)
            name_condition = IUIAutomation.CreatePropertyCondition(UIAutomation.UIA_NamePropertyId, control_name)
            role_condition = IUIAutomation.CreatePropertyCondition(UIAutomation.UIA_LegacyIAccessibleRolePropertyId, role)
            and_condition = IUIAutomation.CreateAndCondition(name_condition, role_condition)
            found_element = root_element.FindFirst(UIAutomation.TreeScope_Descendants, and_condition)
            if found_element:
                value_pattern = found_element.GetCurrentPattern(UIAutomation.UIA_ValuePatternId)
                if value_pattern:
                    value_pattern = value_pattern.QueryInterface(UIAutomation.IUIAutomationValuePattern)
                    return value_pattern.CurrentValue
                legacy_pattern = found_element.GetCurrentPattern(UIA_LegacyIAccessiblePatternId)
                if legacy_pattern:
                    legacy_pattern = legacy_pattern.QueryInterface(UIAutomation.IUIAutomationLegacyIAccessiblePattern)
                    logging.info(f'方法2-1 {legacy_pattern.CurrentValue}')
                    return legacy_pattern.CurrentValue
                text_pattern = found_element.GetCurrentPattern(UIA_TextPatternId)
                if text_pattern:
                    text_pattern = text_pattern.QueryInterface(UIAutomation.IUIAutomationTextPattern)
                    text_range = text_pattern.DocumentRange
                    text =  text_range.GetText(-1)
                    logging.info(f'方法2: {text}')
                    return text
        except Exception as e:
            logging.error(f"UI Automation方法失败: {e}")
            return None
    except Exception as e:
        logging.error(f"获取Electron输入框内容失败: {e}")
        return None

if __name__ == "__main__":
    import config
    import time
    logging.basicConfig(format='%(asctime)s %(levelname)s [%(module)s]: %(message)s', level=logging.INFO)
    while True:
        logging.info("\n==== Electron 应用输入内容监控 ====")
        for app_name in config.APP_CONFIGS:
            try:
                text = get_electron_input_text(config_name=app_name)
                logging.info(f"[{app_name}] 输入内容: {text}")
            except Exception as e:
                logging.error(f"[{app_name}] 获取失败: {e}")
        time.sleep(2)
   