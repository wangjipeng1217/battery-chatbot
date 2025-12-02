import os
import glob
import google.generativeai as genai
from pymongo import MongoClient
from pypdf import PdfReader
from dotenv import load_dotenv
import time

# 加载环境变量
load_dotenv()

# 配置 Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 配置 MongoDB
client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]
collection = db["documents"]

def get_embedding(text):
    """调用 Gemini API 获取向量"""
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        print(f"Error embedding text: {e}")
        return None

def process_pdfs(data_dir="scripts/data"):
    # 清空旧数据 (可选)
    collection.delete_many({})
    print("Old data cleared.")

    pdf_files = glob.glob(os.path.join(data_dir, "*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {data_dir}. Please add some battery docs.")
        return

    for pdf_path in pdf_files:
        print(f"Processing {pdf_path}...")
        reader = PdfReader(pdf_path)
        full_text = ""
        
        # 简单的文本提取
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        
        # 简单的切分策略 (Chunking) [cite: 32]
        # 每 1000 字符切分，重叠 100 字符
        chunk_size = 1000
        overlap = 100
        chunks = []
        
        for i in range(0, len(full_text), chunk_size - overlap):
            chunk = full_text[i:i + chunk_size]
            # 过滤太短的 chunk
            if len(chunk) > 50: 
                chunks.append(chunk)

        print(f"Generated {len(chunks)} chunks from {os.path.basename(pdf_path)}")

        # 生成向量并存储
        for i, chunk_text in enumerate(chunks):
            embedding = get_embedding(chunk_text)
            if embedding:
                doc = {
                    "text": chunk_text,
                    "source": os.path.basename(pdf_path),
                    "chunk_id": i,
                    "embedding": embedding
                }
                collection.insert_one(doc)
                # 避免触发 API 速率限制
                time.sleep(0.5) 
    
    print("Indexing complete! Data stored in MongoDB.")

if __name__ == "__main__":
    # 确保 scripts/data 目录下有 PDF 文件
    os.makedirs("scripts/data", exist_ok=True)
    process_pdfs()