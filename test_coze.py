"""
Coze API 连通性诊断脚本
"""
import json
import urllib.request
from urllib.error import HTTPError

# 直接从 config.py 导入配置
try:
    from config import COZE_API_KEY, COZE_WORKFLOW_ID, COZE_API_BASE
except ImportError:
    print("错误：无法从 config.py 导入配置。请确保该文件存在且包含所需变量。")
    exit(1)

def run_test():
    print("="*50)
    print("Coze API 连通性诊断开始")
    print("="*50)

    # 1. 打印当前使用的配置
    print(f"[配置检查]")
    print(f"  COZE_API_BASE: {COZE_API_BASE}")
    print(f"  COZE_WORKFLOW_ID: {COZE_WORKFLOW_ID}")
    print(f"  COZE_API_KEY: pat_...{COZE_API_KEY[-4:]}" if COZE_API_KEY else "未设置")
    print("-" * 50)

    if not all([COZE_API_KEY, COZE_WORKFLOW_ID, COZE_API_BASE]):
        print("诊断失败：一个或多个关键配置（API Key, Workflow ID, API Base）为空。")
        return

    # 2. 准备请求
    endpoint = "/workflow/run"
    url = f"{COZE_API_BASE}{endpoint}"
    
    headers = {
        "Authorization": f"Bearer {COZE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "workflow_id": COZE_WORKFLOW_ID,
        "user_id": "diag_test_user",
        "parameters": {
            "prompt": "这是一个连通性测试",
        },
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")

    print(f"[请求诊断]")
    print(f"  请求方法: POST")
    print(f"  完整URL: {url}")
    print("-" * 50)

    # 3. 发送请求
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            response_body = resp.read().decode()
            
            print(f"[响应诊断]")
            print(f"  HTTP状态码: {status}")
            
            if status == 200:
                print(f"  响应内容 (部分): {response_body[:200]}...")
                print(f"\n诊断成功：与 Coze API 的网络连接正常，且认证通过！")
                print("如果仍然失败，请检查你的工作流是否已发布，以及输入/输出参数名是否正确。")
            else:
                print(f"  响应内容: {response_body}")
                print(f"\n诊断失败：服务器返回了意外的状态码 {status}。")

    except HTTPError as e:
        print(f"[响应诊断]")
        print(f"  HTTP状态码: {e.code}")
        try:
            error_body = e.read().decode()
            print(f"  错误响应内容: {error_body}")
        except Exception:
            print("  无法读取错误响应内容。")
        
        if e.code == 404:
            print("\n诊断失败：404 Not Found。这几乎可以肯定是 COZE_API_BASE 配置错误。")
            print("请确认你使用的是 'https://api.coze.cn/v1' (国内版) 或 'https://api.coze.com/v1' (国际版)，且没有多余的斜杠或拼写错误。")
        elif e.code == 401:
            print("\n诊断失败：401 Unauthorized。这是典型的 COZE_API_KEY (个人访问令牌) 错误。请重新生成并配置。")
        elif e.code == 400:
             print("\n诊断失败：400 Bad Request。这通常意味着 COZE_WORKFLOW_ID 不存在或未发布。请检查工作流 ID。")
        else:
            print(f"\n诊断失败：收到了意外的 HTTP 错误 {e.code}。")
    except Exception as e:
        print(f"[异常诊断]")
        print(f"  在请求过程中发生异常: {e}")
        print("\n诊断失败：请检查你的网络连接、代理设置，或 COZE_API_BASE 地址是否正确。")

    print("="*50)

if __name__ == "__main__":
    run_test()
