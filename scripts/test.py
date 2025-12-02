import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# 如果你需要代理，记得加上这两行
# os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890" 
# os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("正在查询可用模型列表...")
try:
    for m in genai.list_models():
        # 只显示支持聊天/文本生成的模型
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"查询失败: {e}")