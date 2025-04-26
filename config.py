import re
#from core.electron_text_extractor_v2 import ROLE_SYSTEM_TEXT
ROLE_SYSTEM_TEXT = 42
"""
    "type": "startswith", #开头匹配
    "type": "contains", #包含
    "type": "endswith", #结尾匹配
    "type": "exact", #完全匹配
    "type": "regex", #正则匹配
"""
APP_CONFIGS = {
    "deepseek": {
        "window_base_title": "DeepSeek - 探索未至之境",
        "control_name": "给 DeepSeek 发送消息 ",
        "role": ROLE_SYSTEM_TEXT,
        "title_match": {
            "type": "contains",
            "value": "DeepSeek"
        }
    },
    "qwen": {
        "window_base_title": "Qwen",
        "control_name": "有什么我能帮您的吗？",
        "role": ROLE_SYSTEM_TEXT,
        "title_match": {
            "type": "contains",
            "value": "Qwen"
        }
    },
    "cherry": {
        "window_base_title": "Cherry Studio",
        "control_name": "在这里输入消息...",
        "role": ROLE_SYSTEM_TEXT,
        "title_match": {
            "type": "exact",
            "value": "Cherry Studio"
        }
    },
    "Kimi": {
        "window_base_title": "Kimi - 会推理解析，能深度思考的AI助手",
        "control_name": "随时@你想要的Kimi+ 使用各种能力 ",
        "role": ROLE_SYSTEM_TEXT,
        "title_match": {
            "type": "contains",
            "value": "Kimi"
        }
    },
    "MasterGo": {
        "window_base_title": " - MasterGo",
        "control_name": "",
        "role": ROLE_SYSTEM_TEXT,
        "title_match": {
            "type": "contains",
            "value": "MasterGo"
        }
    },   
    "ChatGLM": {
        "window_base_title": "ChatGLM",
        "control_name": "",
        "role": ROLE_SYSTEM_TEXT,
        "title_match": {
            "type": "contains",
            "value": "ChatGLM"
        }
    },
    "Chatgpt": {
        "window_base_title": "ChatGPT",
        "control_name": "",
        "role": ROLE_SYSTEM_TEXT,
        "title_match": {
            "type": "contains",
            "value": "ChatGPT"
        }
    },
    "tongyi": {
        "window_base_title": "通义 - 你的使用AI助手",
        "control_name": "",
        "role": ROLE_SYSTEM_TEXT,
        "title_match": {
            "type": "contains",
            "value": "通义"
        }
    },
    "腾讯元宝": {
        "window_base_title": "腾讯元宝 - 轻松工作 多点生活",
        "control_name": "",
        "role": ROLE_SYSTEM_TEXT,
        "title_match": {
            "type": "contains",
            "value": "腾讯元宝"
        }
    },
    "智谱清言": {
        "window_base_title": "智谱清言",
        "control_name": "",
        "role": ROLE_SYSTEM_TEXT,
        "title_match": {
            "type": "contains",
            "value": "智谱清言"
        }
    },
    "百度AI搜索": {
        "window_base_title": "百度AI搜索",
        "control_name": "",
        "role": ROLE_SYSTEM_TEXT,
        "title_match": {
            "type": "contains",
            "value": "百度AI搜索"
        }
    },
    "Chatbox": {
        "window_base_title": "Chatbox",
        "control_name": "",
        "role": ROLE_SYSTEM_TEXT,
        "title_match": {
            "type": "contains",
            "value": "Chatbox"
        }
    }
}

TITLE_MATCH_HANDLERS = {
    "exact": lambda title, value: title == value,
    "contains": lambda title, value: value in title,
    "startswith": lambda title, value: title.startswith(value),
    "endswith": lambda title, value: title.endswith(value),
    "regex": lambda title, value: re.match(value, title)
}


