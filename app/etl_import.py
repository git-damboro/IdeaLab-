import os
import sys
import time
import traceback
import bibtexparser
from bibtexparser.customization import convert_to_unicode
import re
import hashlib
from pymongo import MongoClient
from pymilvus import (
    connections,
    FieldSchema, CollectionSchema, DataType,
    Collection, utility
)
from openai import OpenAI
from tqdm import tqdm
from dotenv import load_dotenv

# --- 设置 ---
sys.stdout.reconfigure(encoding='utf-8')
print("🚀 [Step 1] 脚本启动...")

# --- 1. 加载环境变量 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(CURRENT_DIR, "..", ".env")

if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    print("❌ 错误：找不到 .env 文件")
    sys.exit(1)

API_KEY = os.getenv("ALIBABA_API_KEY")
if not API_KEY:
    print("❌ 错误：.env 中没有 ALIBABA_API_KEY")
    sys.exit(1)

# --- 2. 配置 ---
BIB_FILE_PATH = os.path.join(CURRENT_DIR, "..", "data", "anthology+abstracts1.bib")
MONGO_URI = os.getenv("MONGO_URI")
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")

# 导入策略：默认清空后全量导入；如需断点续跑，可设置 CLEAR_BEFORE_IMPORT=false
CLEAR_BEFORE_IMPORT = os.getenv("CLEAR_BEFORE_IMPORT", "true").lower() == "true"
# 断点续跑：遇到已存在 paper_id 时跳过，避免重复
SKIP_EXISTING = os.getenv("SKIP_EXISTING", "true").lower() == "true"

MONGO_DB_NAME = "research_db"
MONGO_COLLECTION = "papers"
MILVUS_COLLECTION = "paper_vectors"

EMBEDDING_MODEL = "text-embedding-v4"
EMBEDDING_DIM = 512 

# --- 3. 初始化 OpenAI ---
try:
    client = OpenAI(
        api_key=API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
except Exception as e:
    print(f"❌ OpenAI 初始化失败: {e}")
    sys.exit(1)

# --- 辅助函数：清洗年份和月份 ---
def clean_year(year_str):
    """将年份字符串转换为整数，如果无法转换则返回 0"""
    if not year_str: return 0
    # 提取字符串中的前4位数字
    match = re.search(r'\d{4}', str(year_str))
    return int(match.group()) if match else 0

def clean_month(month_str):
    """
    规范化月份：
    - 数字/数字字符串 -> 英文全称
    - 英文缩写/全称 -> 英文全称
    - 已是中文的保持不变（前端有映射）
    """
    if not month_str:
        return ""
    m = str(month_str).strip().strip("{}")  # 去掉 bibtex 中常见的花括号包裹
    m_lower = m.lower().rstrip(".")  # 兼容 "Jun." 这类写法

    month_map = {
        "jan": "January", "january": "January",
        "feb": "February", "february": "February",
        "mar": "March", "march": "March",
        "apr": "April", "april": "April",
        "may": "May",
        "jun": "June", "june": "June",
        "jul": "July", "july": "July",
        "aug": "August", "august": "August",
        "sep": "September", "sept": "September", "september": "September",
        "oct": "October", "october": "October",
        "nov": "November", "november": "November",
        "dec": "December", "december": "December",
        # 兼容中文月份
        "一月": "一月", "二月": "二月", "三月": "三月", "四月": "四月",
        "五月": "五月", "六月": "六月", "七月": "七月", "八月": "八月",
        "九月": "九月", "十月": "十月", "十一月": "十一月", "十二月": "十二月",
    }

    # 数字月份（1/01/6/12）
    if m_lower.isdigit():
        num = int(m_lower)
        if 1 <= num <= 12:
            english_full = [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ][num - 1]
            return english_full

    # 英文映射
    if m_lower in month_map:
        return month_map[m_lower]

    # 首字母大写兜底，避免返回单个数字等异常值
    return m.capitalize()

def normalize_text(text):
    """
    清洗文本：
    - 去除多余的花括号
    - 去除多余空白
    """
    if not text:
        return ""
    cleaned = str(text).replace("{", "").replace("}", "")
    return " ".join(cleaned.split())

def get_embedding(text):
    try:
        text = text.replace("\n", " ")
        # 截断过长的文本，防止 API 报错 (v4 支持较长，但保险起见)
        text = text[:8000] 
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[text],
            dimensions=EMBEDDING_DIM
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"\n⚠️ Embedding API 警告: {e}")
        time.sleep(2)
        return None

def connect_db():
    print("🔌 [Step 4] 连接数据库...")
    mongo_client = MongoClient(MONGO_URI)
    mongo_db = mongo_client[MONGO_DB_NAME]
    mongo_col = mongo_db[MONGO_COLLECTION]
    if CLEAR_BEFORE_IMPORT:
        mongo_col.delete_many({}) # 清空旧数据
        print("   🧹 已清空 MongoDB 旧数据")
    
    # 💡 创建索引：这对你后续的年份筛选和混合检索至关重要
    mongo_col.create_index([("year_int", 1)]) # 年份索引
    mongo_col.create_index([("paper_id", 1)], unique=True) # ID 索引
    print("   ✅ MongoDB 连接成功 (索引已建立)")

    # Milvus 连接（带重试机制）
    max_retries = 5
    for retry in range(max_retries):
        try:
            connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
            print("   ✅ Milvus 连接成功")
            break
        except Exception as e:
            if retry < max_retries - 1:
                wait_time = (retry + 1) * 2  # 2s, 4s, 6s, 8s
                print(f"   ⚠️ Milvus 连接失败，{wait_time}秒后重试 ({retry + 1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                print(f"   ❌ Milvus 连接失败，已重试 {max_retries} 次: {e}")
                raise
    
    return mongo_col

def init_milvus():
    if utility.has_collection(MILVUS_COLLECTION):
        if CLEAR_BEFORE_IMPORT:
            try:
                utility.drop_collection(MILVUS_COLLECTION)
                print("   🧹 已清空 Milvus 旧集合")
            except Exception as e:
                # 避免因代理节点切换等原因导致报错中断，回退为"保留并复用"
                print(f"⚠️ 清空 Milvus 集合失败，将保留现有集合继续导入（可设置 CLEAR_BEFORE_IMPORT=false 避免重试）。原因: {e}")
                try:
                    collection = Collection(name=MILVUS_COLLECTION)
                    collection.load()
                    return collection
                except Exception as e2:
                    print(f"❌ 回退加载 Milvus 集合失败: {e2}")
                    raise
        else:
            collection = Collection(name=MILVUS_COLLECTION)
            collection.load()
            print("   ✅ Milvus 集合已加载（保留历史，用于断点续跑）")
            return collection

    fields = [
        FieldSchema(name="paper_id", dtype=DataType.INT64, is_primary=True, auto_id=False),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)
    ]
    schema = CollectionSchema(fields, description="Research Paper Embeddings")
    collection = Collection(name=MILVUS_COLLECTION, schema=schema)
    
    index_params = {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 256}}
    collection.create_index(field_name="embedding", index_params=index_params)
    return collection

def load_bib_data(filepath):
    """一次性读取 BibTeX 文件（小文件使用）"""
    print(f"📂 [Step 3] 读取数据: {filepath}")
    if not os.path.exists(filepath):
        print("❌ 文件不存在")
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        parser.customization = convert_to_unicode
        return bibtexparser.load(f, parser=parser).entries

def load_bib_data_chunked(filepath):
    """分批读取 BibTeX 文件（生成器版本）- 边解析边 yield，实现流式处理"""
    chunk_size = 500
    
    print("   📦 使用流式分批处理模式...")
    print("   ⏳ 正在读取文件（边解析边导入）...")
    
    # 使用正则表达式匹配完整的 BibTeX 条目
    entry_pattern = re.compile(r'@\w+\s*\{[^@]*(?:\{[^{}]*\}[^@]*)*\}', re.DOTALL)
    
    chunk_texts = []
    entry_count = 0
    chunk_count = 0
    total_parsed = 0
    
    try:
        # 分块读取文件，每次读取 5MB（减小内存占用）
        chunk_size_bytes = 5 * 1024 * 1024  # 5MB
        buffer = ""
        total_bytes = 0
        file_size = os.path.getsize(filepath)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            while True:
                chunk = f.read(chunk_size_bytes)
                if not chunk:
                    break
                
                buffer += chunk
                total_bytes += len(chunk)
                
                # 查找完整的条目（匹配 @type{...} 格式）
                matches = list(entry_pattern.finditer(buffer))
                if matches:
                    # 处理找到的条目（除了最后一个，可能不完整）
                    for match in matches[:-1]:
                        entry_text = match.group(0)
                        chunk_texts.append(entry_text)
                        entry_count += 1
                        
                        if entry_count >= chunk_size:
                            # 解析当前批次并立即 yield（流式处理）
                            full_chunk = '\n'.join(chunk_texts)
                            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
                            parser.customization = convert_to_unicode
                            try:
                                chunk_entries = bibtexparser.loads(full_chunk, parser=parser).entries
                                total_parsed += len(chunk_entries)
                                chunk_count += 1
                                print(f"   ✅ 已解析 {total_parsed} 条记录（第 {chunk_count} 批）...")
                                yield chunk_entries  # 👈 关键：立即 yield，不等待全部解析
                                chunk_texts = []
                                entry_count = 0
                            except Exception as e:
                                print(f"   ⚠️ 解析第 {chunk_count + 1} 批时出错: {e}")
                                chunk_texts = []
                                entry_count = 0
                    
                    # 保留最后一个匹配之后的内容（可能是不完整的条目）
                    if matches:
                        last_match_end = matches[-1].end()
                        buffer = buffer[last_match_end:]
                
                # 显示进度（每50MB提示一次）
                if total_bytes % (50 * 1024 * 1024) < chunk_size_bytes:
                    progress = (total_bytes / file_size) * 100
                    print(f"   📖 已读取 {total_bytes / 1024 / 1024:.1f}MB / {file_size / 1024 / 1024:.1f}MB ({progress:.1f}%)...")
        
        # 处理剩余的条目
        if buffer.strip():
            remaining_matches = list(entry_pattern.finditer(buffer))
            for match in remaining_matches:
                entry_text = match.group(0)
                chunk_texts.append(entry_text)
                entry_count += 1
        
        # 处理最后一批
        if chunk_texts:
            full_chunk = '\n'.join(chunk_texts)
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            parser.customization = convert_to_unicode
            try:
                chunk_entries = bibtexparser.loads(full_chunk, parser=parser).entries
                total_parsed += len(chunk_entries)
                chunk_count += 1
                print(f"   ✅ 已解析最后一批，总共 {total_parsed} 条记录")
                yield chunk_entries
            except Exception as e:
                print(f"   ⚠️ 解析最后一批时出错: {e}")
        
    except MemoryError as e:
        print(f"   ❌ 内存不足: {e}")
        print(f"   ⚠️ 已解析 {total_parsed} 条记录，但未完成全部解析")
    except Exception as e:
        print(f"   ❌ 读取文件时出错: {e}")
        traceback.print_exc()

def process_and_insert():
    print(f"📚 开始流式导入...")
    mongo_col = connect_db()
    milvus_col = init_milvus()

    # 断点续跑：预取已存在的paper_id，避免重复写入
    existing_ids = set()
    if SKIP_EXISTING and not CLEAR_BEFORE_IMPORT:
        try:
            existing_ids = set(mongo_col.distinct("paper_id"))
            print(f"   🔁 检测到 {len(existing_ids)} 条已存在记录，导入时将跳过")
        except Exception as e:
            print(f"⚠️ 获取已存在ID失败，继续全量导入: {e}")

    mongo_docs = []
    milvus_ids = []
    milvus_vectors = []
    batch_size = 20  # 👈 增大批量大小（从 10 改为 20，提高效率）
    
    # 统计信息
    stats = {
        'total': 0,  # 改为动态计数
        'processed': 0,
        'skipped': 0,
        'failed': 0,
        'success': 0,
        'embedding_failed': 0,
        'insert_failed': 0
    }

    def generate_id(string_key):
        """
        生成稳定、跨平台一致且符合 int64 范围的 ID。
        - 使用 sha256 保证一致性
        - 仅取前 8 字节，并截断到 63 bit，避免超出 MongoDB/Milvus 的 int64 限制
        """
        digest = hashlib.sha256(string_key.encode("utf-8")).digest()
        val = int.from_bytes(digest[:8], byteorder="big", signed=False)
        # 截断到有符号 63bit（最大 2^63-1），避免 8-byte 溢出
        return val & ((1 << 63) - 1)

    def insert_batch():
        """插入当前批次的数据"""
        nonlocal mongo_docs, milvus_ids, milvus_vectors
        if not mongo_docs:
            return
        
        try:
            # MongoDB 批量插入（ordered=False 表示即使部分失败也继续）
            mongo_col.insert_many(mongo_docs, ordered=False)
            stats['success'] += len(mongo_docs)
        except Exception as e:
            # 如果批量插入失败，尝试逐个插入
            print(f"\n⚠️ MongoDB 批量插入失败，尝试逐个插入: {e}")
            for doc_item in mongo_docs:
                try:
                    mongo_col.insert_one(doc_item)
                    stats['success'] += 1
                except Exception as e2:
                    stats['insert_failed'] += 1
                    print(f"  ❌ 插入失败 (paper_id: {doc_item.get('paper_id')}): {e2}")
        
        try:
            # Milvus 批量插入
            if milvus_ids and milvus_vectors:
                milvus_col.insert([milvus_ids, milvus_vectors])
        except Exception as e:
            stats['insert_failed'] += len(milvus_ids)
            print(f"\n⚠️ Milvus 批量插入失败: {e}")
            # Milvus 插入失败不影响继续，因为可以后续重建
        
        mongo_docs = []
        milvus_ids = []
        milvus_vectors = []

    # 👇 关键修改：流式处理，边解析边导入
    file_size_mb = os.path.getsize(BIB_FILE_PATH) / (1024 * 1024)
    if file_size_mb > 50:
        # 大文件使用流式处理（生成器）
        print(f"   📊 文件大小: {file_size_mb:.1f} MB，使用流式处理模式")
        entries_generator = load_bib_data_chunked(BIB_FILE_PATH)
    else:
        # 小文件一次性加载
        print(f"   📊 文件大小: {file_size_mb:.1f} MB，一次性加载")
        entries = load_bib_data(BIB_FILE_PATH)
        entries_generator = [entries]  # 包装成可迭代对象
        stats['total'] = len(entries)  # 小文件可以提前知道总数
    
    # 开始流式导入
    print(f"   ⏳ 开始导入（边解析边导入）...")
    
    for entries_batch in entries_generator:
        if stats['total'] == 0:  # 大文件需要动态计数
            stats['total'] += len(entries_batch)
        
        for entry in tqdm(entries_batch, desc=f"导入中 (总计: {stats['total']})", leave=False):
            stats['processed'] += 1
            try:
                # 1. 基础字段提取
                title = normalize_text(entry.get('title', ''))
                abstract = normalize_text(entry.get('abstract', ''))
                bib_key = entry.get('ID', '')

                if not title or not bib_key:
                    stats['skipped'] += 1
                    continue

                current_id = generate_id(bib_key + title)

                if SKIP_EXISTING and current_id in existing_ids:
                    # 跳过已存在的数据，支持断点续跑
                    stats['skipped'] += 1
                    continue
                
                # 2. Embedding（带重试机制）
                text_to_embed = f"Title: {title}\nAbstract: {abstract}"
                embedding = None
                max_retries = 3
                for retry in range(max_retries):
                    embedding = get_embedding(text_to_embed)
                    if embedding is not None:
                        break
                    if retry < max_retries - 1:
                        wait_time = (retry + 1) * 2  # 递增等待时间：2s, 4s, 6s
                        print(f"\n⚠️ Embedding 失败，{wait_time}秒后重试 ({retry + 1}/{max_retries})...")
                        time.sleep(wait_time)
                
                if embedding is None:
                    stats['embedding_failed'] += 1
                    print(f"\n❌ 论文 {bib_key} Embedding 失败，跳过")
                    continue

                # 3. 构造 MongoDB 文档
                # 复制 .bib 中的所有原始字段
                doc = entry.copy()
                
                # 添加/覆盖 系统需要的规范化字段
                doc.update({
                    "paper_id": current_id,     # 用于关联 Milvus
                    "title": title,             # 清洗后的标题
                    "abstract": abstract,       # 清洗后的摘要
                    "year_int": clean_year(entry.get('year')),  # 整数年份，方便筛选
                    "month_clean": clean_month(entry.get('month')), # 规范月份
                    "combined_text": f"{title} {abstract}",     # 用于 BM25 关键词检索
                    "ai_summary": None,         # 占位符：等待后续大模型生成
                    "ai_summary_generated": False # 标记：是否已生成
                })

                mongo_docs.append(doc)
                milvus_ids.append(current_id)
                milvus_vectors.append(embedding)

                time.sleep(0.1)  # 👈 减少延迟（从 0.3 改为 0.1，提高速度）

                # 批量插入（带错误处理）
                if len(mongo_docs) >= batch_size:
                    insert_batch()
                    
            except Exception as e:
                stats['failed'] += 1
                print(f"\n❌ 处理论文时出错 (bib_key: {entry.get('ID', 'unknown')}): {e}")
                traceback.print_exc()
                # 继续处理下一条，不中断整个导入流程
                continue

    # 处理剩余的文档
    insert_batch()

    # 刷新并加载 Milvus 集合
    try:
        milvus_col.flush()
        milvus_col.load()
        print("\n✅ Milvus 数据已刷新并加载")
    except Exception as e:
        print(f"\n⚠️ Milvus 刷新/加载失败: {e}")
    
    # 打印统计信息
    print("\n" + "="*50)
    print("📊 导入统计信息:")
    print(f"  总记录数: {stats['total']}")
    print(f"  已处理: {stats['processed']}")
    print(f"  ✅ 成功插入: {stats['success']}")
    print(f"  ⏭️  跳过（已存在）: {stats['skipped']}")
    print(f"  ❌ 失败: {stats['failed']}")
    print(f"  ⚠️  Embedding 失败: {stats['embedding_failed']}")
    print(f"  ⚠️  插入失败: {stats['insert_failed']}")
    print("="*50)
    
    if stats['success'] > 0:
        print("\n✅ 数据导入完成！")
    else:
        print("\n⚠️ 警告：没有成功导入任何数据，请检查错误信息")

if __name__ == "__main__":
    process_and_insert()