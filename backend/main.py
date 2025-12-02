import os
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
import google.generativeai as genai
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware

# 加载环境变量
load_dotenv()

app = FastAPI()

# --- 2. 添加中间件配置 (放在 app = FastAPI() 之后) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源 (生产环境可以改为具体域名)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- 配置 ---
# MongoDB 连接 [cite: 52]
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
doc_collection = db["documents"]
chat_collection = db["chat_history"]

# Gemini 配置 [cite: 42, 92]
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro-latest') # 使用轻量级 Flash 模型

# --- 内存缓存 (In-Memory Index) ---
# 为了在免费实例上快速检索，启动时将向量加载到内存 [cite: 58]
print("Loading search index...")
cached_docs = []
cached_embeddings = []

def load_index():
    global cached_docs, cached_embeddings
    cursor = doc_collection.find({}, {"text": 1, "source": 1, "embedding": 1})
    docs = list(cursor)
    if docs:
        cached_docs = docs
        # 转换为 numpy 数组以便计算
        cached_embeddings = np.array([d['embedding'] for d in docs])
        print(f"Loaded {len(cached_docs)} documents into memory.")
    else:
        print("Warning: No documents found in MongoDB. Please run build_index.py.")

load_index()

# --- 数据模型 ---
class ChatInput(BaseModel):
    conversation_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    sources: list[str] = []

# --- 辅助函数 ---
def get_query_embedding(text):
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_query"
    )
    return np.array(result['embedding']).reshape(1, -1)

def retrieve_documents(query_embedding, top_k=3):
    """执行简单的余弦相似度搜索"""
    if len(cached_embeddings) == 0:
        return []
    
    # 计算相似度
    similarities = cosine_similarity(query_embedding, cached_embeddings)[0]
    # 获取 top_k 索引
    top_indices = similarities.argsort()[-top_k:][::-1]
    
    results = []
    for idx in top_indices:
        # 简单的阈值过滤，避免不相关的内容
        if similarities[idx] > 0.3:
            results.append(cached_docs[idx])
    return results

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"status": "Battery Bot Backend is running"}

@app.post("/chat-input") # [cite: 50]
def chat_input(data: ChatInput):
    user_msg = data.message
    conv_id = data.conversation_id

    # 1. 存储用户消息 [cite: 20]
    chat_collection.insert_one({
        "conversation_id": conv_id,
        "role": "user",
        "text": user_msg,
        "timestamp": datetime.now()
    })

    # 2. RAG 检索 [cite: 36, 37]
    q_embed = get_query_embedding(user_msg)
    relevant_docs = retrieve_documents(q_embed)
    
    # 构建上下文
    context_text = "\n\n".join([f"Source ({d['source']}): {d['text']}" for d in relevant_docs])
    
    # 3. 生成回答 [cite: 38]
    if not context_text:
        # 如果没有检索到相关内容 [cite: 19]
        system_instruction = "You are a helpful assistant. The user asked a question but I couldn't find specific documents. Politely say you don't have information on that specific topic in your database."
        prompt = user_msg
    else:
        # [cite: 15, 17]
        system_instruction = f"""
        You are an expert on EV batteries. 
        Answer the question based STRICTLY on the context provided below.
        If the answer is not in the context, say "I don't know based on the available documents".
        Keep answers concise and technical.
        
        Context:
        {context_text}
        """
        prompt = f"Question: {user_msg}"

    try:
        chat = model.start_chat(history=[
            {"role": "user", "parts": system_instruction},
            {"role": "model", "parts": "Understood. I will answer based on the context."}
        ])
        response = chat.send_message(prompt)
        bot_reply = response.text
    except Exception as e:
        print(f"LLM Error: {e}")
        bot_reply = "Sorry, I encountered an error generating the response."

    # 4. 存储机器人回复 [cite: 20]
    chat_collection.insert_one({
        "conversation_id": conv_id,
        "role": "bot",
        "text": bot_reply,
        "timestamp": datetime.now()
    })

    # 提取来源文件名用于前端显示
    sources = list(set([d['source'] for d in relevant_docs]))

    return {"response": bot_reply, "sources": sources}

@app.get("/history/{conversation_id}") # [cite: 51]
def get_history(conversation_id: str):
    # 获取历史记录并按时间排序
    cursor = chat_collection.find({"conversation_id": conversation_id}).sort("timestamp", 1)
    messages = []
    for doc in cursor:
        messages.append({
            "role": doc["role"],
            "text": doc["text"],
            "timestamp": doc["timestamp"].isoformat()
        })
    return {"history": messages}