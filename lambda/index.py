# lambda/index.py
import json
import os
import urllib.request
import urllib.error
import re  # 正規表現モジュールをインポート
from botocore.exceptions import ClientError

# Lambda コンテキストからリージョンを抽出する関数
def extract_region_from_arn(arn):
    # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"  # デフォルト値

# API URL（環境変数から取得、デフォルト値を設定）
API_URL = os.environ.get("API_URL", "https://ea92-34-125-139-201.ngrok-free.app")

def lambda_handler(event, context):
    try:
        # APIのURLを準備
        api_url = API_URL.rstrip('/')
        
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        
        # 会話履歴からプロンプトを構築
        prompt = ""
        for msg in conversation_history:
            if msg["role"] == "user":
                prompt += f"ユーザー: {msg['content']}\n"
            elif msg["role"] == "assistant":
                prompt += f"アシスタント: {msg['content']}\n"
        
        # 最新のメッセージを追加
        prompt += f"ユーザー: {message}\nアシスタント: "
        
        # APIリクエスト用のペイロードを構築
        request_payload = {
            "prompt": prompt,
            "max_new_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "do_sample": True
        }
        
        print("Calling API with payload:", json.dumps(request_payload))
        
        # urllib.requestを使用してAPIを呼び出し
        headers = {
            'Content-Type': 'application/json'
        }
        
        # JSONデータをエンコード
        data = json.dumps(request_payload).encode('utf-8')
        
        # リクエストオブジェクトを作成
        req = urllib.request.Request(f"{api_url}/generate", data=data, headers=headers, method='POST')
        
        # リクエストを送信し、レスポンスを取得
        with urllib.request.urlopen(req) as response:
            response_data = response.read()
            response_body = json.loads(response_data)
        
        print("API response:", json.dumps(response_body, default=str))
        
        # 応答の検証
        if not response_body.get('generated_text'):
            raise Exception("No response content from the API")
        
        # アシスタントの応答を取得
        assistant_response = response_body['generated_text']
        
        # アシスタントの応答を会話履歴に追加
        updated_history = conversation_history.copy()
        updated_history.append({
            "role": "user",
            "content": message
        })
        updated_history.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": updated_history
            })
        }
        
    except urllib.error.URLError as url_error:
        print("URLError:", str(url_error))
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": f"API connection error: {str(url_error)}"
            })
        }
        
    except Exception as error:
        print("Error:", str(error))
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }