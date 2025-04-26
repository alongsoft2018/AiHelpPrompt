import requests
import json
import logging
from typing import Optional, Dict, List, Tuple

def deepseek_api_chat(
    api_key: str,
    messages: List[Dict[str, str]],
    model: str = "deepseek-chat",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    top_p: float = 1.0,
    timeout: int = 60
) -> Tuple[bool, str, Optional[Dict]]:
    """
    与DeepSeek API进行交互的聊天函数
    
    参数:
    - api_key: DeepSeek API密钥
    - messages: 消息历史列表，格式为 [{"role": "user", "content": "你的问题"}]
    - model: 使用的模型名称（默认：deepseek-chat）
    - temperature: 生成文本的随机性（0-2，默认0.7）
    - max_tokens: 生成的最大token数
    - top_p: 核采样概率（默认1.0）
    - timeout: 请求超时时间（秒）
    
    返回:
    (success, content, full_response)
    - success: 是否成功
    - content: 返回的文本内容（失败时为错误信息）
    - full_response: 完整的API响应（失败时为None）
    """
    
    # API端点（请根据实际文档调整）
    api_url = "https://api.deepseek.com/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p
    }
    
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    
    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()
        
        response_data = response.json()
        
        if "choices" not in response_data or len(response_data["choices"]) == 0:
            return (False, "API响应格式异常", None)
            
        content = response_data["choices"][0]["message"]["content"]
        return (True, content.strip(), response_data)
        
    except requests.exceptions.RequestException as e:
        error_msg = f"请求失败: {str(e)}"
        if hasattr(e, "response") and e.response is not None:       
            error_data = e.response.json()
            error_msg += f" | API返回错误: {error_data.get('message', '未知错误')}"       
            error_msg += f" | 状态码: {e.response.status_code}"
        return (False, error_msg, None)
    except (KeyError, json.JSONDecodeError) as e:
        return (False, f"响应解析失败: {str(e)}", None)

# 使用示例
if __name__ == "__main__":
    # 替换为你的API密钥
    API_KEY = "sk-eceb1a89e8644592a12bcd511a4c6184"
    logging.basicConfig(format='%(asctime)s %(levelname)s [%(module)s]: %(message)s', level=logging.INFO)
    test_messages = [
        {"role": "user", "content": "你好，请介绍一下你自己"}
    ]
    success, response, full_res = deepseek_api_chat(API_KEY, test_messages)
    if success:
        logging.info("回复内容：")
        logging.info(response)
    else:
        logging.error(f"请求失败：{response}")