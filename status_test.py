import os
import json
import requests
import sys
from typing import Dict, Any, Tuple

# === input params start
app_id = os.getenv("APP_ID")        # app_id, required, 应用 ID
# 应用唯一标识，创建应用后获得。有关app_id 的详细介绍。请参考通用参数https://open.feishu.cn/document/ukTMukTMukTM/uYTM5UjL2ETO14iNxkTN/terminology。
app_secret = os.getenv("APP_SECRET")  # app_secret, required, 应用密钥
# 应用秘钥，创建应用后获得。有关 app_secret 的详细介绍，请参考https://open.feishu.cn/document/ukTMukTMukTM/uYTM5UjL2ETO14iNxkTN/terminology。
chat_id = os.getenv("CHAT_ID")      # chat_id, required, 会话 ID
# 目标会话ID（单聊或群组），用于设置机器人输入状态。参考文档：https://go.feishu.cn/s/6cRA2WAQc0s
user_id = os.getenv("USER_ID")      # user_id, required, 用户 ID
# 需要看到输入状态的用户ID。参考文档：https://go.feishu.cn/s/6cRA2WAQc0s
user_id_type = os.getenv("USER_ID_TYPE", "open_id")  # string, optional, 用户 ID 类型
# 用户ID类型，可选值：open_id、user_id、union_id。默认为 open_id。参考文档：https://go.feishu.cn/s/6cRA2WAQc0s
# === input params end

def get_tenant_access_token(app_id: str, app_secret: str) -> Tuple[str, Exception]:
    """获取 tenant_access_token

    Args:
        app_id: 应用ID
        app_secret: 应用密钥

    Returns:
        Tuple[str, Exception]: (access_token, error)
    """
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": app_id,
        "app_secret": app_secret
    }
    headers = {
        "Content-Type": "application/json; charset=utf-8"
    }
    try:
        print(f"POST: {url}")
        print(f"Request body: {json.dumps(payload)}")
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()
        print(f"Response: {json.dumps(result, ensure_ascii=False)}")

        if result.get("code", 0) != 0:
            print(f"ERROR: failed to get tenant_access_token: {result.get('msg', 'unknown error')}", file=sys.stderr)
            return "", Exception(f"failed to get tenant_access_token: {response.text}")

        return result["tenant_access_token"], None

    except Exception as e:
        print(f"ERROR: getting tenant_access_token: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"ERROR: Response body: {e.response.text}", file=sys.stderr)
        return "", e

def set_bot_input_status(tenant_access_token: str, chat_id: str, user_id: str, user_id_type: str, status: str) -> Tuple[bool, Exception]:
    """设置机器人输入状态

    Args:
        tenant_access_token: 租户访问令牌
        chat_id: 会话ID
        user_id: 用户ID
        user_id_type: 用户ID类型
        status: 输入状态 ("typing" 表示正在输入，"" 表示清除输入状态)

    Returns:
        Tuple[bool, Exception]: (success, error)
    """
    url = f"https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}/input_status"
    headers = {
        "Authorization": f"Bearer {tenant_access_token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {
        "user_id": user_id,
        "user_id_type": user_id_type,
        "status": status
    }
    
    try:
        print(f"PATCH: {url}")
        print(f"Headers: Authorization: Bearer [hidden]")
        print(f"Request body: {json.dumps(payload, ensure_ascii=False)}")
        
        response = requests.patch(url, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        print(f"Response: {json.dumps(result, ensure_ascii=False)}")
        
        if result.get("code", 0) != 0:
            print(f"ERROR: failed to set bot input status: {result.get('msg', 'unknown error')}", file=sys.stderr)
            return False, Exception(f"failed to set bot input status: {response.text}")
            
        print("Successfully set bot input status")
        return True, None
        
    except Exception as e:
        print(f"ERROR: setting bot input status: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"ERROR: Response body: {e.response.text}", file=sys.stderr)
        return False, e

def show_typing_status(tenant_access_token: str, chat_id: str, user_id: str, user_id_type: str) -> Tuple[bool, Exception]:
    """显示机器人正在输入状态
    
    Args:
        tenant_access_token: 租户访问令牌
        chat_id: 会话ID
        user_id: 用户ID
        user_id_type: 用户ID类型
        
    Returns:
        Tuple[bool, Exception]: (success, error)
    """
    return set_bot_input_status(tenant_access_token, chat_id, user_id, user_id_type, "typing")

def clear_typing_status(tenant_access_token: str, chat_id: str, user_id: str, user_id_type: str) -> Tuple[bool, Exception]:
    """清除机器人输入状态
    
    Args:
        tenant_access_token: 租户访问令牌
        chat_id: 会话ID
        user_id: 用户ID
        user_id_type: 用户ID类型
        
    Returns:
        Tuple[bool, Exception]: (success, error)
    """
    return set_bot_input_status(tenant_access_token, chat_id, user_id, user_id_type, "")

if __name__ == "__main__":
    # 验证必要参数
    if not app_id:
        print("ERROR: APP_ID is required", file=sys.stderr)
        exit(1)
    if not app_secret:
        print("ERROR: APP_SECRET is required", file=sys.stderr)
        exit(1)
    if not chat_id:
        print("ERROR: CHAT_ID is required", file=sys.stderr)
        exit(1)
    if not user_id:
        print("ERROR: USER_ID is required", file=sys.stderr)
        exit(1)
    
    print("Starting bot input status management...")
    
    # 获取 tenant_access_token
    tenant_access_token, err = get_tenant_access_token(app_id, app_secret)
    if err:
        print(f"ERROR: getting tenant_access_token: {err}", file=sys.stderr)
        exit(1)
    
    print(f"Successfully obtained tenant_access_token: {tenant_access_token[:10]}...")
    
    # 显示正在输入状态
    print("Setting bot typing status...")
    success, err = show_typing_status(tenant_access_token, chat_id, user_id, user_id_type)
    if err:
        print(f"ERROR: failed to show typing status: {err}", file=sys.stderr)
        exit(1)
    
    print("Bot typing status set successfully")
    
    # 清除输入状态（在实际应用中，这通常会在机器人完成响应后调用）
    print("Clearing bot typing status...")
    success, err = clear_typing_status(tenant_access_token, chat_id, user_id, user_id_type)
    if err:
        print(f"ERROR: failed to clear typing status: {err}", file=sys.stderr)
        exit(1)
    
    print("Bot typing status cleared successfully")
    print("Bot input status management completed")