import os
import requests
import arxiv
import time

# 定义数据保存路径 (根据之前的结构)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def download_file(url, filename):
    """
    通用文件下载函数，带简单的伪装头，防止被反爬
    """
    save_path = os.path.join(DATA_DIR, filename)
    
    # 如果文件已存在，跳过
    if os.path.exists(save_path):
        print(f"[SKIP] {filename} already exists.")
        return

    print(f"[DOWNLOADING] {filename} from {url}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"[SUCCESS] Saved to {save_path}")
    except Exception as e:
        print(f"[ERROR] Failed to download {filename}: {e}")

def fetch_manuals():
    """
    下载官方手册 (Hardcoded URLs)
    对应任务要求的: Tesla / Hyundai / BYD battery info 
    """
    manuals = [
        {
            "name": "Tesla_Model_3_Owners_Manual.pdf",
            # Tesla 官网的稳定 PDF 链接
            "url": "https://www.tesla.com/ownersmanual/model3/en_us/Owners_Manual.pdf"
        },
        {
            "name": "LFP_Battery_Guidelines.pdf",
            # 关于磷酸铁锂电池(LFP)的一份通用指南 (示例链接，如果不稳定可以用其他)
            "url": "https://www.cleanenergycouncil.org.au/documents/consumers/battery-guides/Lithium-Ion-Battery-Safety-Guide.pdf"
        }
    ]

    print("\n--- 1. Fetching Manuals & Guides ---")
    for doc in manuals:
        download_file(doc["url"], doc["name"])

def fetch_arxiv_papers():
    """
    使用 Arxiv API 爬取学术论文
    对应任务要求的: Degradation, SOH/SoC explanation 
    """
    print("\n--- 2. Crawling Arxiv for Battery Papers ---")
    
    # 搜索关键词：锂离子电池老化、健康状态估算
    query = "Lithium-ion battery State of Health degradation"
    
    # 构建搜索客户端
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=3,             # 下载前3篇最相关的
        sort_by=arxiv.SortCriterion.Relevance
    )

    results = list(client.results(search))

    for paper in results:
        # 清理文件名 (去除特殊字符)
        safe_title = "".join([c if c.isalnum() else "_" for c in paper.title])[:50]
        filename = f"Paper_{safe_title}.pdf"
        save_path = os.path.join(DATA_DIR, filename)
        
        if os.path.exists(save_path):
            print(f"[SKIP] {filename} already exists.")
            continue

        print(f"[CRAWLING] Paper: {paper.title}")
        try:
            paper.download_pdf(dirpath=DATA_DIR, filename=filename)
            print(f"[SUCCESS] Downloaded: {filename}")
            # 礼貌性延迟，避免被服务器拒绝
            time.sleep(1) 
        except Exception as e:
            print(f"[ERROR] Could not download paper: {e}")

if __name__ == "__main__":
    # 确保目录存在
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created directory: {DATA_DIR}")

    print(f"Starting download task to: {DATA_DIR}")
    
    # 执行下载
    fetch_manuals()
    fetch_arxiv_papers()
    
    print("\n[DONE] All documents ready for indexing.")