import os
import time
import datetime
import sys
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from pymilvus import connections, Collection
from openai import OpenAI
from dotenv import load_dotenv
from passlib.context import CryptContext
from jose import JWTError, jwt
import bcrypt
import concurrent.futures
import threading

if __name__ == "__main__":
    sys.modules.setdefault("backend", sys.modules[__name__])

# Ensure Windows console can print unicode logs.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 兼容性补丁
if not hasattr(bcrypt, '__about__'):
    try:
        bcrypt.__about__ = type("about", (object,), {"__version__": bcrypt.__version__})
    except:
        pass

try:
    from utils import HybridSearcher, reciprocal_rank_fusion
except ModuleNotFoundError:
    from app.utils import HybridSearcher, reciprocal_rank_fusion
try:
    from app.password_utils import truncate_bcrypt_password
except ModuleNotFoundError:
    from password_utils import truncate_bcrypt_password
try:
    from app.auth_bootstrap import bootstrap_default_admin, user_requires_password_change
except ModuleNotFoundError:
    from auth_bootstrap import bootstrap_default_admin, user_requires_password_change
try:
    from app.password_policy import get_password_policy_error
except ModuleNotFoundError:
    from password_policy import get_password_policy_error
import jieba
import jieba.analyse

# --- 配置 ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)
load_dotenv(os.path.join(current_dir, "..", ".env"))

API_KEY = os.getenv("ALIBABA_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

LLM_MODEL_NAME = "qwen2.5-72b-instruct"
EMBEDDING_MODEL_NAME = "text-embedding-v4"
SECRET_KEY = "your_super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 

# 【修改点】API 文档标题改为中文
app = FastAPI(title="智能文献检索系统 API")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 数据库 ---
mongo_client = None
try:
    if not MONGO_URI:
        raise ValueError("MONGO_URI环境变量未设置")
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000, connectTimeoutMS=10000)
    # 测试连接
    mongo_client.admin.command('ping')
    print("✅ MongoDB连接成功")
except Exception as e:
    print(f"❌ MongoDB连接失败: {e}")
    print("⚠️  请检查MONGO_URI环境变量和MongoDB服务状态")
    # 创建一个虚拟客户端，避免后续代码崩溃
    mongo_client = None

if mongo_client:
    db = mongo_client["research_db"]
    papers_col = db["papers"]
    users_col = db["users"]
    history_col = db["search_history"]
    favorites_col = db["favorites"]
    folders_col = db["folders"] # 新增：文件夹表
    summary_cache_col = db["summary_cache"]  # 推荐原因缓存集合
else:
    # 如果MongoDB未连接，创建占位符
    db = None
    papers_col = None
    users_col = None
    history_col = None
    favorites_col = None
    folders_col = None
    summary_cache_col = None

try:
    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT, timeout=3)
    milvus_col = Collection("paper_vectors")
    # 不在启动时 load，避免卡死
    # milvus_col.load()
    print("⚠️ Milvus 连接成功（延迟加载，启动时不 load）")
except Exception as e:
    print(f"⚠️  Milvus连接失败: {e}")
    print("⚠️  当前仅使用 BM25 关键词检索，向量检索暂时关闭")
    milvus_col = None

try:
    hybrid_searcher = HybridSearcher(papers_col)
    # 注意：这里不再在启动时后台预热 BM25，
    # 避免在内存较小的环境下一上来就构建完整索引导致进程被系统 Killed。
    # HybridSearcher 会在第一次调用 search() 时按需延迟构建索引。
    print("✅ HybridSearcher 初始化成功（按需构建 BM25 索引，已关闭启动预热）")
except Exception as e:
    print(f"⚠️  HybridSearcher初始化失败: {e}")
    hybrid_searcher = None

client = OpenAI(api_key=API_KEY, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# --- 模型 ---
class UserRegister(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    role_codes: List[str] = []
    must_change_password: bool = False

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class SearchQuery(BaseModel):
    user_id: str
    question: str
    year_start: int = 2000
    year_end: int = 2030
    top_k: int = 100
    page: int = 1  # 当前页码
    page_size: int = 10  # 每页数量 

class ChatQuery(BaseModel):
    user_query: str
    context_papers: Optional[List[dict]] = None

class FavoriteAddRequest(BaseModel):
    user_id: str
    paper: Dict[str, Any]
    folder_name: str = "默认收藏夹"

class FavoriteRemoveRequest(BaseModel):
    user_id: str
    paper_id: int

class FolderRequest(BaseModel):
    user_id: str
    folder_name: str

class SummaryRequest(BaseModel):
    paper_id: int
    user_query: Optional[str] = None  # 可选，如果有则生成推荐原因

class BatchSummaryRequest(BaseModel):
    paper_ids: List  # 可以是 int 或 str，后端会统一处理
    user_query: str
    paper_titles: Optional[List[str]] = None  # 可选的标题列表，用于ID不匹配时通过标题匹配
    
    class Config:
        # 允许任意类型，因为 paper_id 可能是 int 或 str
        arbitrary_types_allowed = True

# --- 函数 ---
def verify_password(plain_password, hashed_password):
    try:
        # Bcrypt accepts at most 72 bytes, not 72 Unicode characters.
        if not plain_password or not hashed_password:
            return False
        return pwd_context.verify(truncate_bcrypt_password(plain_password), hashed_password)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def get_password_hash(password):
    # Bcrypt accepts at most 72 bytes, not 72 Unicode characters.
    return pwd_context.hash(truncate_bcrypt_password(password))

def create_access_token(data: dict):
    try:
        to_encode = data.copy()
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    except Exception as e:
        print(f"Token creation error: {e}")
        raise

def get_current_auth_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if users_col is None:
        raise HTTPException(status_code=500, detail="数据库未连接，请检查MongoDB服务")

    user = users_col.find_one({"username": username})
    if not user:
        raise credentials_exception
    return user

def seed_default_admin():
    try:
        created = bootstrap_default_admin(
            users_col,
            admin_username=ADMIN_USERNAME,
            admin_password=ADMIN_PASSWORD,
            hash_password=get_password_hash,
            now=datetime.datetime.now,
        )
        if created:
            print(f"✅ 默认管理员已创建: {ADMIN_USERNAME}，首次登录后请立即修改密码")
        elif ADMIN_USERNAME and ADMIN_PASSWORD and get_password_policy_error(ADMIN_PASSWORD):
            print(f"⚠️ 默认管理员未创建: ADMIN_PASSWORD 不符合密码策略（{get_password_policy_error(ADMIN_PASSWORD)}）")
    except Exception as e:
        print(f"⚠️ 默认管理员初始化失败: {e}")

seed_default_admin()

def get_query_embedding(text):
    try:
        resp = client.embeddings.create(model=EMBEDDING_MODEL_NAME, input=[text], dimensions=512)
        return resp.data[0].embedding
    except Exception as e:
        print(f"Embedding Error: {e}")
        return None

def extract_keywords(query, top_k=5):
    """
    从中文/混合查询中提取关键词，优先使用 jieba TF-IDF。
    返回一个去重后的关键词列表（短语）。
    """
    try:
        # jieba.analyse.extract_tags 返回按权重排序的关键词
        kws = jieba.analyse.extract_tags(query, topK=top_k)
    except Exception as e:
        print(f"Keyword extract error: {e}")
        kws = []
    # 去重保序
    seen = set()
    dedup = []
    for kw in kws:
        if kw and kw not in seen:
            seen.add(kw)
            dedup.append(kw)
    return dedup

def translate_keywords_to_english(keywords):
    """
    将中文关键词列表翻译为简短的英文关键词列表。
    使用已有的大模型客户端；失败则返回空列表。
    """
    if not keywords:
        return []
    try:
        prompt = (
            "Translate the following Chinese academic keywords into concise English keywords. "
            "Return a JSON array of strings only. Keep order, keep it short.\n"
            f"Keywords: {', '.join(keywords)}"
        )
        resp = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = resp.choices[0].message.content.strip()
        # 粗解析：尝试作为 JSON 数组，否则按逗号切分
        import json
        try:
            arr = json.loads(text)
            if isinstance(arr, list):
                cleaned = []
                for it in arr:
                    s = str(it).strip()
                    if s:
                        cleaned.append(s)
                return cleaned
        except Exception:
            pass
        # 兜底：按逗号分隔
        parts = [p.strip() for p in text.split(",") if p.strip()]
        return parts
    except Exception as e:
        print(f"Keyword translate error: {e}")
        return []

def expand_queries(original_query):
    """
    构造查询变体列表：
    - 原始查询
    - 中文关键词拼接
    - 英文关键词拼接（翻译自中文关键词）
    """
    variants = []
    if original_query:
        variants.append(original_query.strip())
    keywords = extract_keywords(original_query, top_k=6) if original_query else []
    if keywords:
        variants.append(" ".join(keywords))
        en_keywords = translate_keywords_to_english(keywords)
        if en_keywords:
            variants.append(" ".join(en_keywords))
    # 保持唯一
    uniq = []
    seen = set()
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            uniq.append(v)
    return uniq

def rrf_merge(result_lists, k=60):
    """
    对多个结果列表进行 RRF 融合。
    输入：result_lists = [[{"paper_id": id, "score": s}, ...], ...]
    输出：按融合得分排序的列表 [{"paper_id": id, "score": fused_score}, ...]
    """
    fused = {}
    for lst in result_lists:
        for rank, item in enumerate(lst):
            pid = item.get("paper_id")
            if pid is None:
                continue
            fused[pid] = fused.get(pid, 0) + 1.0 / (k + rank + 1)
    # 转换为列表排序
    fused_list = [{"paper_id": pid, "score": score} for pid, score in fused.items()]
    fused_list.sort(key=lambda x: x["score"], reverse=True)
    return fused_list
def _generate_summary_internal(doc, user_query=None):
    """
    根据用户查询和论文摘要，生成推荐这篇论文的原因
    不依赖 HTTP 请求，供后端内部调用
    """
    # 如果有用户查询，生成推荐原因（不缓存，因为不同查询会有不同原因）
    if user_query:
        # 优化 prompt，缩短长度以提高生成速度
        title = doc.get('title', '未知标题')
        abstract = doc.get('abstract', '无摘要')
        # 限制摘要长度，避免 prompt 过长
        if len(abstract) > 500:
            abstract = abstract[:500] + "..."
        
        prompt = (
            f"用户查询：{user_query}\n"
            f"论文：{title}\n"
            f"摘要：{abstract}\n\n"
            f"用中文写一段推荐原因（80-120字），说明这篇论文与查询的相关性及帮助。"
        )
    else:
        # 如果没有用户查询，生成普通总结（兼容旧逻辑）
        prompt = f"请阅读这篇学术论文，用中文写一段简短总结（100字内）。\n标题: {doc['title']}\n摘要: {doc['abstract']}"
    
    try:
        # 优化API调用参数，加快生成速度
        response = client.chat.completions.create(
            model=LLM_MODEL_NAME, 
            messages=[{"role": "user", "content": prompt}],
            timeout=15,  # 减少超时时间到15秒
            temperature=0.5,  # 降低温度，加快生成速度并提高一致性
            max_tokens=150  # 限制最大token数，加快生成（80-120字约150 tokens）
        )
        summary = response.choices[0].message.content
        
        # 确保返回的内容不为空
        if not summary or len(summary.strip()) < 10:
            print(f"Warning: Empty or too short summary for paper {doc['paper_id']}")
            return None
        
        # 只有在没有用户查询时才缓存到数据库（普通总结可以缓存）
        if not user_query:
            papers_col.update_one({"paper_id": doc["paper_id"]}, {"$set": {"ai_summary": summary}})
        
        return summary
    except Exception as e:
        print(f"Auto summary failed for {doc['paper_id']}: {e}")
        import traceback
        print(traceback.format_exc())
        return None
# ==================== 接口定义 ====================

@app.post("/auth/register")
def register(user: UserRegister):
    try:
        # 检查MongoDB连接
        if mongo_client is None or users_col is None:
            raise HTTPException(status_code=500, detail="数据库未连接，请检查MongoDB服务")
        
        if users_col.find_one({"username": user.username}):
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        policy_error = get_password_policy_error(user.password)
        if policy_error:
            raise HTTPException(status_code=400, detail=policy_error)
        
        users_col.insert_one({
            "username": user.username,
            "password_hash": get_password_hash(user.password),
            "role_codes": ["user"],
            "status": "active",
            "must_change_password": False,
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now()
        })
        
        # 自动创建默认收藏夹
        if folders_col is not None:
            try:
                folders_col.insert_one({
                    "user_id": user.username,
                    "folder_name": "默认收藏夹",
                    "created_at": datetime.datetime.now()
                })
            except Exception as e:
                print(f"Folder creation error: {e}")
        
        return {"msg": "注册成功"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Register error: {e}")
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")

@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        # 检查MongoDB连接
        if mongo_client is None or users_col is None:
            raise HTTPException(status_code=500, detail="数据库未连接，请检查MongoDB服务")
        
        # 验证输入
        if not form_data.username or not form_data.password:
            raise HTTPException(status_code=400, detail="用户名和密码不能为空")
        
        # 查询用户
        try:
            user = users_col.find_one({"username": form_data.username})
        except Exception as db_error:
            print(f"Database query error: {db_error}")
            raise HTTPException(status_code=500, detail="数据库查询失败，请稍后重试")
        
        if not user:
            raise HTTPException(status_code=400, detail="用户名或密码错误")
        
        # 检查密码哈希是否存在
        if "password_hash" not in user:
            print(f"User {form_data.username} missing password_hash")
            raise HTTPException(status_code=400, detail="用户数据异常，请重新注册")
        
        # 验证密码
        try:
            password_valid = verify_password(form_data.password, user["password_hash"])
        except Exception as pwd_error:
            print(f"Password verification error: {pwd_error}")
            raise HTTPException(status_code=500, detail="密码验证失败，请稍后重试")
        
        if not password_valid:
            raise HTTPException(status_code=400, detail="用户名或密码错误")
        
        # 创建token
        try:
            token = create_access_token(data={"sub": user["username"]})
        except Exception as token_error:
            print(f"Token creation error: {token_error}")
            raise HTTPException(status_code=500, detail="令牌生成失败，请稍后重试")
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": user["username"],
            "role_codes": user.get("role_codes") or ["user"],
            "must_change_password": user_requires_password_change(user),
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Login error: {e}")
        print(f"Traceback: {error_trace}")
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")

@app.post("/auth/change-password")
def change_password(req: ChangePasswordRequest, current_user=Depends(get_current_auth_user)):
    if users_col is None:
        raise HTTPException(status_code=500, detail="数据库未连接，请检查MongoDB服务")

    policy_error = get_password_policy_error(req.new_password)
    if policy_error:
        raise HTTPException(status_code=400, detail=policy_error)

    if not verify_password(req.current_password, current_user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="当前密码错误")

    users_col.update_one(
        {"username": current_user["username"]},
        {
            "$set": {
                "password_hash": get_password_hash(req.new_password),
                "must_change_password": False,
                "updated_at": datetime.datetime.now(),
            }
        },
    )
    return {"msg": "密码修改成功"}

def _save_summary_to_cache(paper_id: int, user_query: str, summary: str):
    """将推荐原因保存到缓存"""
    if summary_cache_col is None:
        return
    try:
        cache_key = f"{user_query}|||{paper_id}"
        summary_cache_col.update_one(
            {"cache_key": cache_key},
            {
                "$set": {
                    "paper_id": paper_id,
                    "user_query": user_query,
                    "summary": summary,
                    "created_at": datetime.datetime.now()
                }
            },
            upsert=True
        )
    except Exception as e:
        print(f"⚠️ 保存推荐原因到缓存失败: {e}")

def _get_summary_from_cache(paper_id: int, user_query: str) -> Optional[str]:
    """从缓存获取推荐原因"""
    if summary_cache_col is None:
        return None
    try:
        cache_key = f"{user_query}|||{paper_id}"
        cached = summary_cache_col.find_one({"cache_key": cache_key})
        if cached and cached.get("summary"):
            return cached["summary"]
    except Exception as e:
        print(f"⚠️ 从缓存获取推荐原因失败: {e}")
    return None

def _generate_remaining_summaries_background(final_papers: List[Dict], docs_map: Dict, user_query: str):
    """后台任务：为剩余的论文生成推荐原因并存储到缓存"""
    if len(final_papers) <= 10:
        return
    
    remaining_papers = final_papers[10:]
    print(f"🔄 后台任务开始：为剩余的 {len(remaining_papers)} 篇论文生成推荐原因...")
    
    # 分批处理，避免一次性处理太多
    batch_size = 20
    for batch_start in range(0, len(remaining_papers), batch_size):
        batch_end = min(batch_start + batch_size, len(remaining_papers))
        batch_papers = remaining_papers[batch_start:batch_end]
        
        print(f"📦 处理批次 {batch_start//batch_size + 1}：论文 {batch_start + 10} 到 {batch_end + 9}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_paper_id = {
                executor.submit(_generate_summary_internal, docs_map[paper_obj["id"]], user_query): paper_obj["id"]
                for paper_obj in batch_papers if paper_obj["id"] in docs_map
            }
            
            for future in concurrent.futures.as_completed(future_to_paper_id):
                paper_id = future_to_paper_id[future]
                
                try:
                    summary = future.result(timeout=30)
                    if summary and summary.strip():
                        # 保存到缓存
                        _save_summary_to_cache(paper_id, user_query, summary.strip())
                        print(f"✅ 后台任务：已为论文 {paper_id} 生成推荐原因并保存到缓存")
                    else:
                        print(f"⚠️ 后台任务：论文 {paper_id} 生成推荐原因失败（返回为空）")
                except Exception as e:
                    print(f"❌ 后台任务：为论文 {paper_id} 生成推荐原因时出错: {e}")
        
        # 批次之间稍作延迟，避免API限流
        if batch_end < len(remaining_papers):
            time.sleep(0.5)
    
    print(f"🎉 后台任务完成：剩余 {len(remaining_papers)} 篇论文的推荐原因生成完成")

@app.post("/search")
async def search_papers(req: SearchQuery, background_tasks: BackgroundTasks):
    start_time = time.time()
    print(f"--- 开始搜索: {req.question} ---")
    
    # 1. 记录历史 (不变)
    if req.user_id and history_col is not None:
        try:
            history_col.update_one(
                {"user_id": req.user_id, "query": req.question},
                {"$set": {"timestamp": datetime.datetime.now()}},
                upsert=True
            )
        except Exception as e:
            print(f"History update error: {e}")

    # 2. 构造查询变体（关键词增强）
    expanded_queries = expand_queries(req.question)
    print(f"🔍 查询变体: {expanded_queries}")

    # 3. 向量检索（主查询）
    t1 = time.time()
    query_vec = get_query_embedding(req.question)
    vector_results = []
    id_to_vector_score = {}
    SEARCH_LIMIT = 100 
    
    if query_vec:
        try:
            if milvus_col is None:
                print("⚠️  Milvus collection未加载，跳过向量检索")
            else:
                res = milvus_col.search(
                    data=[query_vec], anns_field="embedding",
                    param={"metric_type": "COSINE", "params": {"nlist": 10}},
                    limit=SEARCH_LIMIT, output_fields=["paper_id"]
                )
                if res and len(res) > 0 and len(res[0]) > 0:
                    # 调试：打印第一个 hit 的结构
                    if len(res[0]) > 0:
                        first_hit = res[0][0]
                        print(f"🔍 Milvus hit 结构调试:")
                        print(f"   hit 类型: {type(first_hit)}")
                        print(f"   hit.id: {first_hit.id}")
                        print(f"   hit 属性: {dir(first_hit)}")
                        if hasattr(first_hit, 'entity'):
                            print(f"   hit.entity: {first_hit.entity}")
                            print(f"   hit.entity 类型: {type(first_hit.entity)}")
                            if first_hit.entity:
                                print(f"   hit.entity 内容: {first_hit.entity}")
                                if isinstance(first_hit.entity, dict):
                                    print(f"   hit.entity keys: {first_hit.entity.keys()}")
                    
                    for idx, hit in enumerate(res[0]):
                        # 重要：使用 output_fields 中的 paper_id，而不是 hit.id
                        # hit.id 是 Milvus 的内部ID，可能与 MongoDB 的 paper_id 不一致
                        # 尝试从 entity 中获取 paper_id
                        paper_id = None
                        
                        # 方式1：从 entity 字典中获取
                        if hasattr(hit, 'entity') and hit.entity:
                            if isinstance(hit.entity, dict):
                                paper_id = hit.entity.get("paper_id")
                            elif hasattr(hit.entity, 'get'):
                                paper_id = hit.entity.get("paper_id")
                        
                        # 方式2：直接访问属性
                        if paper_id is None and hasattr(hit, 'paper_id'):
                            paper_id = hit.paper_id
                        
                        # 方式3：如果还是没有，使用 hit.id（但这是错误的，需要警告）
                        if paper_id is None:
                            paper_id = hit.id
                            if idx < 3:  # 只打印前3个的警告
                                print(f"⚠️  Milvus hit[{idx}] 未找到 paper_id，使用 hit.id: {paper_id} (这可能不正确！)")
                        
                        # 确保 paper_id 是整数类型
                        if isinstance(paper_id, (int, float)):
                            paper_id = int(paper_id)
                        elif isinstance(paper_id, str) and paper_id.isdigit():
                            paper_id = int(paper_id)
                        else:
                            print(f"⚠️  Milvus 返回的 paper_id 类型异常: {type(paper_id)}, 值: {paper_id}")
                            continue
                            
                        vector_results.append({"paper_id": paper_id, "score": hit.distance})
                        id_to_vector_score[paper_id] = hit.distance
                    print(f"✅ 向量检索找到 {len(vector_results)} 个结果，示例ID: {[r['paper_id'] for r in vector_results[:3]]}")
                else:
                    print("⚠️  向量检索未找到结果")
        except Exception as e:
            print(f"⚠️  向量检索失败: {e}")
            vector_results = []

    # 4. 关键词检索（对所有变体进行 BM25 搜索）
    keyword_lists = []
    if hybrid_searcher:
        for q in expanded_queries:
            try:
                kr = hybrid_searcher.search(q, top_k=SEARCH_LIMIT)
                keyword_lists.append(kr)
                print(f"✅ 关键词检索[{q}] 找到 {len(kr)} 个结果")
            except Exception as e:
                print(f"Keyword search error ({q}): {e}")
                keyword_lists.append([])

    # 5. 融合排序：向量 + 多个关键词列表
    result_lists = []
    if vector_results:
        result_lists.append(vector_results)
    result_lists.extend(keyword_lists)
    fused_list = rrf_merge(result_lists) if result_lists else []

    # 6. 批量查询 MongoDB
    if papers_col is None:
        raise HTTPException(status_code=500, detail="数据库未连接，请检查MongoDB服务")
    
    if not fused_list:
        print("⚠️  融合排序结果为空，尝试使用关键词结果")
        keyword_fallback = keyword_lists[0] if keyword_lists else []
        if keyword_fallback:
            fused_list = keyword_fallback[:SEARCH_LIMIT]
        elif vector_results:
            fused_list = vector_results[:SEARCH_LIMIT]
        else:
            print("⚠️  没有任何搜索结果")
            return {"results": [], "time_taken": time.time() - start_time, "total": 0, "message": "未找到匹配的论文"}
    
    target_ids = [item["paper_id"] for item in fused_list[:SEARCH_LIMIT]]
    print(f"📊 准备查询 {len(target_ids)} 篇论文，示例ID（前5个）: {target_ids[:5]}")
    print(f"📊 示例ID类型: {[type(pid).__name__ for pid in target_ids[:5]]}")
    cursor = papers_col.find({"paper_id": {"$in": target_ids}})
    docs_map = {doc["paper_id"]: doc for doc in cursor}
    print(f"📊 从MongoDB获取到 {len(docs_map)} 篇论文数据")
    if len(docs_map) < len(target_ids):
        missing_count = len(target_ids) - len(docs_map)
        missing_ids = [pid for pid in target_ids if pid not in docs_map]
        print(f"⚠️  有 {missing_count} 篇论文在MongoDB中不存在，示例缺失ID: {missing_ids[:5]}")
        print(f"⚠️  缺失ID类型: {[type(pid).__name__ for pid in missing_ids[:5]]}")
        # 尝试查找数据库中实际存在的ID（用于对比）
        sample_docs = list(papers_col.find({}, {"paper_id": 1}).limit(5))
        if sample_docs:
            print(f"📋 数据库中示例ID: {[doc['paper_id'] for doc in sample_docs]}")
            print(f"📋 数据库中示例ID类型: {[type(doc['paper_id']).__name__ for doc in sample_docs]}")

    # 6. 获取收藏状态 (不变)
    user_fav_ids = []
    if req.user_id and favorites_col is not None:
        try:
            favs = favorites_col.find({"user_id": req.user_id}, {"paper_id": 1})
            user_fav_ids = [f["paper_id"] for f in favs]
        except Exception as e:
            print(f"Favorites query error: {e}")
            user_fav_ids = []

    final_papers = []
    
    # 计算融合分数的最大值，用于归一化
    max_fused_score = fused_list[0].get("score", 0.1) if fused_list and len(fused_list) > 0 else 0.1

    # 7. 组装结果
    for item in fused_list:
        if len(final_papers) >= SEARCH_LIMIT: break
        doc = docs_map.get(item["paper_id"])
        if not doc: 
            print(f"⚠️  论文 {item['paper_id']} 在MongoDB中不存在")
            continue

        # 年份检查：如果没有year_int，尝试从year字段获取
        p_year = doc.get("year_int", 0)
        if p_year == 0:
            year_str = doc.get("year", "")
            if year_str:
                try:
                    p_year = int(str(year_str)[:4]) if str(year_str)[:4].isdigit() else 0
                except:
                    p_year = 0
        
        # 如果年份为0或不在范围内，跳过
        if p_year == 0 or p_year < req.year_start or p_year > req.year_end: 
            continue

        # 计算匹配度分数：优先使用向量分数，如果没有则使用融合分数
        raw_score = id_to_vector_score.get(item["paper_id"])
        fused_score = item.get("score", 0)  # RRF融合分数
        
        if raw_score is not None:
            # 向量分数转换为百分比（余弦相似度范围通常是0-1，转换为0-100）
            # 余弦相似度通常在-1到1之间，但通常都是正数，所以直接乘以100
            score_value = max(0, min(float(raw_score) * 100, 100.0))
        elif fused_score > 0:
            # 使用融合分数，RRF分数范围通常在0.01-0.1之间（取决于k值和排名）
            # 需要归一化到0-100范围，使用最大值归一化
            # 由于fused_list已经按分数降序排序，第一个分数最高
            if max_fused_score > 0:
                # 归一化：当前分数 / 最高分数 * 100
                score_value = min(float(fused_score) / max_fused_score * 100, 100.0)
            else:
                score_value = 50.0
        else:
            # 如果都没有，使用一个默认值
            score_value = 50.0
        
        # 确保分数在合理范围内
        score_value = max(0, min(score_value, 100.0))

        # 构建基础对象
        # 注意：ai_summary 初始为空，后续会根据用户查询生成推荐原因
        # 重要：确保ID类型一致，使用数据库中的原始paper_id
        paper_id = doc["paper_id"]
        # 确保ID是整数类型（MongoDB中存储的是Int64，需要转换为Python int）
        if isinstance(paper_id, (int, float)):
            paper_id = int(paper_id)
        elif isinstance(paper_id, str) and paper_id.isdigit():
            paper_id = int(paper_id)
        
        paper_obj = {
            "id": paper_id,  # 确保使用整数类型的ID
            "title": doc["title"],
            "year": p_year,
            "month": doc.get("month_clean", ""),
            "abstract": doc["abstract"],
            "ai_summary": None,  # 初始为空，后续生成推荐原因
            "url": doc.get("url", "#"),
            "score": round(score_value, 1),  # 使用数字，保留1位小数，便于前端排序和显示
            "is_favorited": doc["paper_id"] in user_fav_ids
        }
        final_papers.append(paper_obj)

    # 重要：final_papers 已经按融合分数排序（相关性从高到低）
    # 但前端可能会再次排序，所以我们需要确保返回的数据已经按 score 降序排序
    # 按 score 降序排序，确保前端显示的顺序与后端一致
    final_papers.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # 为第一页（前10个）的论文生成推荐原因（同步生成，确保返回时就有推荐原因）
    # 如果是第一页，同步生成前10个；如果是其他页，不生成（让前端使用已生成的）
    page_size = getattr(req, 'page_size', 10)
    page = getattr(req, 'page', 1)
    
    # 只处理第一页的同步生成
    if page == 1:
        first_10_papers = final_papers[:10]
        print(f"正在为第一页（前10个）的 {len(first_10_papers)} 篇论文生成推荐原因（同步）...")
        print(f"前10篇论文的ID（按score排序后）: {[p['id'] for p in first_10_papers]}")
        
        if first_10_papers and req.question:
            # 并行生成前10个的推荐原因，提高速度
            # 使用字典记录 paper_id 到索引的映射，确保正确更新
            paper_id_to_idx = {paper_obj["id"]: idx for idx, paper_obj in enumerate(first_10_papers)}
            
            # 初始化前10个论文的ai_summary为None，确保字段存在
            for idx in range(min(10, len(final_papers))):
                if "ai_summary" not in final_papers[idx]:
                    final_papers[idx]["ai_summary"] = None
            
            print(f"初始化了前10篇论文的 ai_summary 字段")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(first_10_papers), 10)) as executor:
                # 创建 future 到 paper_id 的映射
                future_to_paper_id = {
                    executor.submit(_generate_summary_internal, docs_map[paper_obj["id"]], req.question): paper_obj["id"]
                    for paper_obj in first_10_papers if paper_obj["id"] in docs_map
                }
            
            # 使用列表收集所有结果，确保所有任务都完成
            summary_results = {}
            
            for future in concurrent.futures.as_completed(future_to_paper_id):
                paper_id = future_to_paper_id[future]
                idx = paper_id_to_idx.get(paper_id)
                
                if idx is None:
                    print(f"⚠️ 找不到论文 {paper_id} 的索引")
                    continue
                    
                try:
                    summary = future.result(timeout=30)  # 减少超时时间到30秒
                    if summary and summary.strip():
                        summary_results[paper_id] = summary.strip()
                    else:
                        print(f"⚠️ 论文 {paper_id} 生成推荐原因失败（返回为空或只有空格）")
                        summary_results[paper_id] = None
                except concurrent.futures.TimeoutError:
                    print(f"⏱️ 论文 {paper_id} 生成推荐原因超时")
                    summary_results[paper_id] = None
                except Exception as e:
                    print(f"❌ 为论文 {paper_id} 生成推荐原因时出错: {e}")
                    import traceback
                    print(traceback.format_exc())
                    summary_results[paper_id] = None
            
            # 所有任务完成后，统一更新到 final_papers，并保存到缓存
            print(f"=== 开始更新 {len(summary_results)} 篇论文的推荐原因 ===")
            for paper_id, summary in summary_results.items():
                idx = paper_id_to_idx.get(paper_id)
                if idx is not None and idx < len(final_papers):
                    if summary:
                        final_papers[idx]["ai_summary"] = summary
                        # 保存到缓存，供翻页时使用
                        _save_summary_to_cache(paper_id, req.question, summary)
                        print(f"✅ 已为论文 {paper_id} 更新推荐原因（索引 {idx}，长度 {len(summary)}）并保存到缓存")
                    else:
                        final_papers[idx]["ai_summary"] = None
                        print(f"⚠️ 论文 {paper_id} 推荐原因为空（索引 {idx}）")
                else:
                    print(f"❌ 论文 {paper_id} 索引无效（idx={idx}, total={len(final_papers)}）")
            print(f"=== 更新完成 ===")
            
            # 启动后台任务，为剩余的论文生成推荐原因
            if len(final_papers) > 10:
                print(f"📋 启动后台任务，为剩余的 {len(final_papers) - 10} 篇论文生成推荐原因...")
                background_tasks.add_task(
                    _generate_remaining_summaries_background,
                    final_papers,
                    docs_map,
                    req.question
                )
    else:
        # 如果不是第一页，不生成推荐原因（前端应该使用已生成的）
        print(f"第 {page} 页，跳过推荐原因生成（应该使用已生成的）")
    
    total_time = time.time() - start_time
    
    # 详细检查前10篇论文的推荐原因生成情况
    first_10_with_summary = sum(1 for p in final_papers[:10] if p.get("ai_summary"))
    print(f"--- 前10篇论文中，{first_10_with_summary} 篇有推荐原因 ---")
    
    # 详细打印前10篇论文的ai_summary字段状态
    print("=== 前10篇论文的推荐原因状态 ===")
    for i, paper in enumerate(final_papers[:10]):
        has_summary = bool(paper.get("ai_summary"))
        summary_len = len(paper.get("ai_summary", "")) if paper.get("ai_summary") else 0
        print(f"  [{i+1}] Paper ID: {paper.get('id')}, 有推荐原因: {has_summary}, 长度: {summary_len}")
        if has_summary:
            print(f"      预览: {paper.get('ai_summary', '')[:50]}...")
        else:
            print(f"      ⚠️ 缺少推荐原因！")
    print("=== 检查完成 ===")
    
    print(f"--- 接口总耗时: {total_time:.4f}s ---")
    print(f"--- 返回结果数量: {len(final_papers)} ---")
    
    # 确保返回的数据格式正确
    if not isinstance(final_papers, list):
        final_papers = []
    
    # 再次验证：确保前10篇论文都有ai_summary字段（即使是None）
    for i in range(min(10, len(final_papers))):
        if "ai_summary" not in final_papers[i]:
            print(f"⚠️ 警告：论文 {final_papers[i].get('id')} 缺少 ai_summary 字段，设置为 None")
            final_papers[i]["ai_summary"] = None
    
    return {
        "results": final_papers,
        "time_taken": total_time,
        "total": len(final_papers)
    }

@app.post("/paper/summary")
def generate_summary_api(req: SummaryRequest):
    """生成单个论文的推荐原因或总结"""
    doc = papers_col.find_one({"paper_id": req.paper_id})
    if not doc: raise HTTPException(status_code=404, detail="Paper not found")
    
    # 如果有用户查询，生成推荐原因（不缓存）
    if req.user_query:
        try:
            summary = _generate_summary_internal(doc, req.user_query)
            if summary:
                return {"summary": summary, "cached": False, "paper_id": req.paper_id}
            else:
                return {"summary": "生成失败，请稍后重试", "cached": False, "paper_id": req.paper_id}
        except Exception as e:
            print(f"Error generating recommendation for paper {req.paper_id}: {e}")
            return {"summary": f"生成失败: {str(e)}", "cached": False, "paper_id": req.paper_id}
    
    # 否则生成普通总结（可以缓存）
    if doc.get("ai_summary") and len(doc["ai_summary"]) > 5:
        return {"summary": doc["ai_summary"], "cached": True, "paper_id": req.paper_id}
        
    prompt = f"请阅读这篇学术论文，用中文写一段简短总结（100字内）。\n标题: {doc['title']}\n摘要: {doc['abstract']}"
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL_NAME, messages=[{"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content
        papers_col.update_one({"paper_id": req.paper_id}, {"$set": {"ai_summary": summary}})
        return {"summary": summary, "cached": False, "paper_id": req.paper_id}
    except Exception as e:
        return {"summary": f"生成失败: {str(e)}", "cached": False, "paper_id": req.paper_id}

@app.post("/paper/batch-summary")
async def batch_generate_summary_api(req: BatchSummaryRequest):
    """批量生成推荐原因，用于换页时生成当前页论文的推荐原因
    优先从缓存查询，如果没有再生成"""
    if not req.paper_ids or not req.user_query:
        raise HTTPException(status_code=400, detail="paper_ids and user_query are required")
    
    if papers_col is None:
        raise HTTPException(status_code=500, detail="数据库未连接，请检查MongoDB服务")
    
    # 统一处理 paper_ids 类型，确保都是 int（MongoDB 中存储的是 int）
    paper_ids_normalized = []
    for pid in req.paper_ids:
        try:
            # 统一转换为 int
            if isinstance(pid, str) and pid.isdigit():
                paper_ids_normalized.append(int(pid))
            elif isinstance(pid, (int, float)):
                paper_ids_normalized.append(int(pid))
            else:
                # 如果无法转换，记录警告但继续
                print(f"⚠️  无法转换论文ID类型: {pid} (类型: {type(pid).__name__})")
                paper_ids_normalized.append(pid)
        except Exception as e:
            print(f"⚠️  转换论文ID时出错: {pid}, 错误: {e}")
            paper_ids_normalized.append(pid)
    
    print(f"批量生成推荐原因: {len(paper_ids_normalized)} 篇论文, 查询: {req.user_query[:50]}...")
    print(f"论文ID列表（前5个）: {paper_ids_normalized[:5]}")
    print(f"论文ID类型: {[type(pid).__name__ for pid in paper_ids_normalized[:5]]}")
    print(f"🔍 接收到的请求数据: paper_titles={req.paper_titles}, 类型={type(req.paper_titles).__name__ if req.paper_titles is not None else 'NoneType'}")
    if req.paper_titles:
        print(f"🔍 标题列表长度: {len(req.paper_titles)}, 前3个标题: {req.paper_titles[:3] if len(req.paper_titles) >= 3 else req.paper_titles}")
    
    # 首先从缓存查询已生成的推荐原因
    results = {}
    cached_count = 0
    papers_to_generate = []
    
    print(f"🔍 先从缓存查询推荐原因...")
    for pid in paper_ids_normalized:
        cached_summary = _get_summary_from_cache(pid, req.user_query)
        if cached_summary:
            results[pid] = cached_summary
            cached_count += 1
            print(f"✅ 从缓存获取论文 {pid} 的推荐原因")
        else:
            papers_to_generate.append(pid)
    
    print(f"📊 缓存命中: {cached_count}/{len(paper_ids_normalized)} 篇论文")
    
    # 如果没有需要生成的论文，直接返回缓存结果
    if not papers_to_generate:
        print(f"✅ 所有论文的推荐原因都从缓存获取，直接返回")
        return {"results": results}
    
    # 批量查询论文（MongoDB 中存储的是 int 类型）
    # 使用与搜索接口相同的查询方式
    # 调试：打印查询前的ID信息
    print(f"🔍 调试：准备查询的ID列表: {paper_ids_normalized[:5]}")
    print(f"🔍 调试：ID类型: {[type(pid).__name__ for pid in paper_ids_normalized[:5]]}")
    
    # 尝试多种方式查询，确保能找到论文
    docs_map = {}
    found_pids_in_db = set()
    
    # 方式1：直接使用整数查询（MongoDB中存储的是int）
    cursor = papers_col.find({"paper_id": {"$in": paper_ids_normalized}})
    for doc in cursor:
        doc_pid = doc["paper_id"]
        found_pids_in_db.add(doc_pid)
        docs_map[doc_pid] = doc
        # 同时用请求的ID作为键（确保能匹配，即使类型略有不同）
        for orig_pid in paper_ids_normalized:
            if orig_pid == doc_pid or (isinstance(orig_pid, (int, float)) and isinstance(doc_pid, (int, float)) and int(orig_pid) == int(doc_pid)):
                docs_map[orig_pid] = doc
    
    # 方式2：如果第一次查询没找到，尝试使用字符串查询
    if len(docs_map) == 0:
        print("⚠️  第一次查询未找到，尝试字符串匹配...")
        paper_ids_as_str = [str(pid) for pid in papers_to_generate]
        cursor_str = papers_col.find({"paper_id": {"$in": paper_ids_as_str}})
        for doc in cursor_str:
            doc_pid = doc["paper_id"]
            found_pids_in_db.add(doc_pid)
            docs_map[doc_pid] = doc
            # 匹配原始ID
            for orig_pid in papers_to_generate:
                if str(orig_pid) == str(doc_pid) or int(orig_pid) == int(doc_pid):
                    docs_map[orig_pid] = doc
    
    # 方式3：如果还是没找到，尝试通过标题匹配（如果提供了标题列表）
    # 重要：即使方式1和方式2找到了一些论文，如果还有缺失的论文，也要尝试标题匹配
    missing_pids = [pid for pid in papers_to_generate if pid not in docs_map]
    if len(missing_pids) > 0:
        # 检查是否提供了标题列表（包括空列表的情况）
        has_titles = req.paper_titles is not None and len(req.paper_titles) > 0
        print(f"🔍 检查标题列表: paper_titles={req.paper_titles}, has_titles={has_titles}, 类型={type(req.paper_titles)}")
        if has_titles:
            print(f"⚠️  有 {len(missing_pids)} 篇论文未找到，尝试通过标题匹配...")
            print(f"🔍 标题列表长度: {len(req.paper_titles)}, 缺失论文数: {len(missing_pids)}")
            print(f"🔍 标题列表（前3个）: {req.paper_titles[:3] if len(req.paper_titles) >= 3 else req.paper_titles}")
            
            # 创建ID到标题的映射（只针对缺失的论文）
            # 需要找到缺失论文在原始列表中的索引
            id_to_title = {}
            for missing_pid in missing_pids:
                # 找到缺失论文在 papers_to_generate 中的索引
                try:
                    idx = papers_to_generate.index(missing_pid)
                    if idx < len(req.paper_titles):
                        id_to_title[missing_pid] = req.paper_titles[idx]
                    else:
                        print(f"⚠️  论文 {missing_pid} 的索引 {idx} 超出标题列表范围（长度 {len(req.paper_titles)}）")
                except ValueError:
                    print(f"⚠️  论文 {missing_pid} 不在 papers_to_generate 列表中")
            
            # 如果长度匹配，也可以直接按索引匹配
            if len(req.paper_titles) == len(papers_to_generate):
                # 重新创建完整的映射（更可靠）
                id_to_title = {pid: title for pid, title in zip(papers_to_generate, req.paper_titles) if pid in missing_pids}
            
            print(f"🔍 ID到标题映射数量: {len(id_to_title)}")
            
            # 批量查询所有可能的标题（使用正则表达式进行模糊匹配）
            import re
            for pid, title in id_to_title.items():
                if not title or len(title.strip()) < 5:
                    print(f"⚠️  论文 {pid} 的标题无效: '{title}'")
                    continue
                
                title_clean = title.strip()
                
                # 尝试精确匹配标题
                doc = papers_col.find_one({"title": title_clean})
                if doc:
                    doc_pid = doc["paper_id"]
                    docs_map[pid] = doc
                    docs_map[doc_pid] = doc
                    found_pids_in_db.add(doc_pid)
                    print(f"✅ 通过标题精确匹配找到论文: {pid} -> {doc_pid}, 标题: {title_clean[:50]}")
                    continue
                
                # 尝试部分匹配（标题的前40个字符，不区分大小写）
                if len(title_clean) > 20:
                    # 先尝试前40个字符
                    title_prefix = title_clean[:40]
                    doc = papers_col.find_one({"title": {"$regex": f"^{re.escape(title_prefix)}", "$options": "i"}})
                    if doc:
                        doc_pid = doc["paper_id"]
                        docs_map[pid] = doc
                        docs_map[doc_pid] = doc
                        found_pids_in_db.add(doc_pid)
                        print(f"✅ 通过标题前缀匹配找到论文: {pid} -> {doc_pid}, 标题前缀: {title_prefix}")
                        continue
                    
                    # 如果前40个字符没找到，尝试前20个字符
                    if len(title_clean) > 20:
                        title_prefix_short = title_clean[:20]
                        doc = papers_col.find_one({"title": {"$regex": f"^{re.escape(title_prefix_short)}", "$options": "i"}})
                        if doc:
                            doc_pid = doc["paper_id"]
                            docs_map[pid] = doc
                            docs_map[doc_pid] = doc
                            found_pids_in_db.add(doc_pid)
                            print(f"✅ 通过标题短前缀匹配找到论文: {pid} -> {doc_pid}, 标题前缀: {title_prefix_short}")
                            continue
                
                # 如果还是没找到，尝试包含匹配（标题的前15个字符）
                if len(title_clean) > 15:
                    title_keyword = title_clean[:15]
                    doc = papers_col.find_one({"title": {"$regex": re.escape(title_keyword), "$options": "i"}})
                    if doc:
                        doc_pid = doc["paper_id"]
                        docs_map[pid] = doc
                        docs_map[doc_pid] = doc
                        found_pids_in_db.add(doc_pid)
                        print(f"✅ 通过标题关键词匹配找到论文: {pid} -> {doc_pid}, 关键词: {title_keyword}")
                        continue
                
                print(f"❌ 无法通过标题匹配找到论文 {pid}, 标题: {title_clean[:50]}")
            
            if len(docs_map) > 0:
                print(f"✅ 通过标题匹配找到 {len(docs_map)} 篇论文")
            else:
                print(f"❌ 标题匹配未找到任何论文")
        else:
            print("⚠️  未提供标题列表，跳过标题匹配")
    
    # 方式4：如果还是没找到，尝试逐个查询（用于调试）
    if len(docs_map) == 0:
        print("⚠️  前三种方式都未找到，尝试逐个查询（用于调试）...")
        sample_id = papers_to_generate[0] if papers_to_generate else None
        if sample_id:
            # 尝试不同的查询方式
            test_doc = papers_col.find_one({"paper_id": sample_id})
            if test_doc:
                print(f"✅ 找到示例论文 {sample_id}，数据库中ID类型: {type(test_doc['paper_id']).__name__}")
            else:
                # 尝试字符串查询
                test_doc_str = papers_col.find_one({"paper_id": str(sample_id)})
                if test_doc_str:
                    print(f"✅ 找到示例论文（字符串查询）{sample_id}")
                else:
                    print(f"❌ 未找到示例论文 {sample_id}，数据库中可能不存在此ID")
                    # 打印数据库中前几个ID作为参考
                    sample_docs = list(papers_col.find({}, {"paper_id": 1}).limit(5))
                    if sample_docs:
                        print(f"📋 数据库中示例ID: {[doc['paper_id'] for doc in sample_docs]}")
                        print(f"📋 数据库中示例ID类型: {[type(doc['paper_id']).__name__ for doc in sample_docs]}")
    
    # 检查哪些论文在数据库中找到了
    found_ids = [pid for pid in papers_to_generate if pid in docs_map]
    missing_ids = [pid for pid in papers_to_generate if pid not in docs_map]
    
    print(f"📊 查询结果: 找到 {len(found_ids)} 篇论文，缺失 {len(missing_ids)} 篇论文")
    if missing_ids:
        print(f"⚠️  {len(missing_ids)} 篇论文在数据库中不存在: {missing_ids[:5]}")
        # 打印缺失论文的ID类型，帮助调试
        if missing_ids:
            print(f"  缺失论文ID类型: {[type(pid).__name__ for pid in missing_ids[:5]]}")
    
    if not found_ids:
        print("❌ 没有找到任何论文数据，无法生成推荐原因")
        # 对于未找到的论文，返回None，但保留已从缓存获取的结果
        for pid in missing_ids:
            results[pid] = None
        print(f"📊 返回结果：缓存 {cached_count} 篇，未找到 {len(missing_ids)} 篇")
        return {"results": results}
    
    print(f"📊 准备为 {len(found_ids)} 篇论文生成推荐原因...")
    
    # 初始化未缓存的论文结果
    for pid in papers_to_generate:
        if pid not in results:
            results[pid] = None
    
    # 并行生成推荐原因
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_pid = {
            executor.submit(_generate_summary_internal, docs_map[pid], req.user_query): pid 
            for pid in found_ids
        }
        
        for future in concurrent.futures.as_completed(future_to_pid):
            pid = future_to_pid[future]
            try:
                summary = future.result(timeout=60)  # 设置超时
                if summary and len(summary.strip()) >= 10:
                    summary_str = summary.strip()
                    results[pid] = summary_str
                    # 保存到缓存
                    _save_summary_to_cache(pid, req.user_query, summary_str)
                    print(f"✅ Generated summary for paper {pid} (length: {len(summary)}, preview: {summary[:50]}...) and saved to cache")
                else:
                    print(f"⚠️  Empty or invalid summary for paper {pid} (summary: {summary})")
                    results[pid] = None
            except concurrent.futures.TimeoutError:
                print(f"⏱️  Timeout generating summary for paper {pid} (超过60秒)")
                results[pid] = None
            except Exception as e:
                print(f"❌ Error generating summary for paper {pid}: {type(e).__name__}: {e}")
                import traceback
                print(traceback.format_exc())
                results[pid] = None
    
    success_count = len([r for r in results.values() if r and r.strip()])
    print(f"批量生成完成: {success_count}/{len(paper_ids_normalized)} 成功")
    
    # 打印详细的返回数据
    print(f"=== 批量生成返回数据 ===")
    print(f"返回的 results 字典长度: {len(results)}")
    print(f"有效的推荐原因数量: {success_count}")
    print(f"请求的论文ID数量: {len(paper_ids_normalized)}")
    
    # 检查每个结果
    for pid in paper_ids_normalized[:10]:  # 只打印前10个
        summary = results.get(pid)
        if summary and summary.strip():
            print(f"  ✅ Paper {pid} (类型: {type(pid).__name__}): 长度 {len(summary)}, 预览: {summary[:50]}...")
        else:
            print(f"  ❌ Paper {pid} (类型: {type(pid).__name__}): {summary}")
    
    # 过滤掉 None 和空字符串，只返回有效的推荐原因
    # 重要：保持原始ID类型（int 或 str），确保前端能正确匹配
    filtered_results = {}
    for pid in paper_ids_normalized:
        summary = results.get(pid)
        if summary and summary.strip():
            # 保持原始ID类型，确保前端能正确匹配
            filtered_results[pid] = summary.strip()
        else:
            # 即使生成失败，也返回 None，让前端知道这个ID已经处理过
            # 保持原始ID类型
            filtered_results[pid] = None
    
    # 为了兼容前端，同时返回字符串和数字类型的键
    # 前端发送的是数字，但可能期望字符串键，所以同时提供两种类型
    filtered_results_with_dual_keys = {}
    for pid in paper_ids_normalized:
        summary = results.get(pid)
        if summary and summary.strip():
            summary_value = summary.strip()
        else:
            summary_value = None
        
        # 同时添加数字键和字符串键
        if isinstance(pid, (int, float)):
            # 数字键
            filtered_results_with_dual_keys[pid] = summary_value
            # 字符串键
            filtered_results_with_dual_keys[str(pid)] = summary_value
        elif isinstance(pid, str):
            # 字符串键
            filtered_results_with_dual_keys[pid] = summary_value
            # 如果是数字字符串，也添加数字键
            if pid.isdigit():
                try:
                    filtered_results_with_dual_keys[int(pid)] = summary_value
                except:
                    pass
    
    filtered_results = filtered_results_with_dual_keys
    
    print(f"过滤后的结果: {len([r for r in filtered_results.values() if r])} 个有效推荐原因")
    print(f"=== 返回数据检查完成 ===")
    
    return {"results": filtered_results}

@app.post("/chat")
async def chat_agent(req: ChatQuery):
    try:
        # 容错：无上下文时使用空列表，且精简数量与长度，避免过长请求
        context_papers = (req.context_papers or [])[:3]
        print(f"[CHAT] incoming query='{req.user_query[:120] if req.user_query else ''}' ctx={len(context_papers)}")

        def safe_trim(text, limit=400):
            if not text:
                return ""
            t = str(text)
            return t if len(t) <= limit else t[:limit] + "..."

        context_str = ""
        for idx, p in enumerate(context_papers):
            context_str += (
                f"[{idx+1}] {p.get('title','未知标题')} ({p.get('year','')})\n"
                f"摘要: {safe_trim(p.get('abstract',''), 400)}\n"
                f"AI总结: {safe_trim(p.get('ai_summary',''), 400)}\n\n"
            )

        system_prompt = (
            "你是一个学术问答助手，使用中文简洁回答用户问题。"
            "如果给了上下文，请尽量基于上下文回答；若上下文不足，直接说明信息不足，不要编造。"
        )

        user_prompt = (
            f"用户问题: {req.user_query}\n"
            f"上下文（最多3篇，可为空）:\n{context_str}"
        )

        if not API_KEY:
            return {"response": "后端未配置模型 API_KEY，无法生成回答。"}

        try:
            response = client.chat.completions.create(
                model=LLM_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            content = ""
            try:
                content = response.choices[0].message.content or ""
            except Exception as e:
                print(f"Chat parse error: {e}")

            # 兜底：如果内容为空，自动降级重试一次；再为空则返回固定提示，保证前端有文案
            if not content.strip():
                print("Chat warn: model returned empty content, retrying with simplified prompt...")
                retry_sys = "你是一个学术问答助手，使用中文简洁回答用户问题，若信息不足请直接说明。"
                retry_user = f"用户问题: {req.user_query}"
                try:
                    retry_resp = client.chat.completions.create(
                        model=LLM_MODEL_NAME,
                        messages=[
                            {"role": "system", "content": retry_sys},
                            {"role": "user", "content": retry_user}
                        ]
                    )
                    retry_content = retry_resp.choices[0].message.content or ""
                    if retry_content.strip():
                        return {"response": retry_content}
                except Exception as ee:
                    print(f"Chat retry error: {ee}")
                # 二次失败/空内容的固定回复
                return {"response": "抱歉，本次未能生成回答，请稍后重试或简化问题后再问。"}

            return {"response": content}
        except Exception as e:
            print(f"Chat error (LLM call): {e}")
            return {"response": "抱歉，生成回答失败，请稍后重试。"}
    except Exception as e:
        print(f"Chat error: {e}")
        return {"response": f"抱歉，生成回答失败：{str(e)}"}

# --- 文件夹与收藏管理 ---

@app.get("/folders/{user_id}")
def get_user_folders(user_id: str):
    """获取用户的所有文件夹名"""
    if folders_col is None:
        return ["默认收藏夹"]
    
    try:
        cursor = folders_col.find({"user_id": user_id}).sort("created_at", 1)
        folders = [doc["folder_name"] for doc in cursor]
        # 确保至少有一个默认文件夹
        if "默认收藏夹" not in folders:
            folders.insert(0, "默认收藏夹")
        return folders
    except Exception as e:
        print(f"Get folders error: {e}")
        return ["默认收藏夹"]

@app.post("/folders/add")
def add_folder(req: FolderRequest):
    if folders_col is None:
        raise HTTPException(status_code=500, detail="数据库未连接，请检查MongoDB服务")
    
    try:
        if folders_col.find_one({"user_id": req.user_id, "folder_name": req.folder_name}):
            raise HTTPException(status_code=400, detail="文件夹已存在")
        folders_col.insert_one({
            "user_id": req.user_id,
            "folder_name": req.folder_name,
            "created_at": datetime.datetime.now()
        })
        return {"msg": "文件夹创建成功"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Add folder error: {e}")
        raise HTTPException(status_code=500, detail=f"创建文件夹失败: {str(e)}")

@app.post("/folders/delete")
def delete_folder(req: FolderRequest):
    if folders_col is None or favorites_col is None:
        raise HTTPException(status_code=500, detail="数据库未连接，请检查MongoDB服务")
    
    if req.folder_name == "默认收藏夹":
        raise HTTPException(status_code=400, detail="默认收藏夹不可删除")
    
    try:
        # 1. 删除文件夹
        folders_col.delete_one({"user_id": req.user_id, "folder_name": req.folder_name})
        # 2. 删除该文件夹下的所有收藏 (或者你可以选择移动到默认文件夹，这里选择直接删除)
        favorites_col.delete_many({"user_id": req.user_id, "folder_name": req.folder_name})
        return {"msg": "文件夹及内容已删除"}
    except Exception as e:
        print(f"Delete folder error: {e}")
        raise HTTPException(status_code=500, detail=f"删除文件夹失败: {str(e)}")

@app.get("/history/{user_id}")
def get_user_history(user_id: str):
    if history_col is None:
        return []
    
    try:
        cursor = history_col.find({"user_id": user_id}).sort("timestamp", -1).limit(20)
        return [doc["query"] for doc in cursor]
    except Exception as e:
        print(f"Get history error: {e}")
        return []

@app.get("/favorites/{user_id}")
def get_user_favorites(user_id: str):
    """获取所有收藏，并做数据清洗"""
    if favorites_col is None:
        return []
    
    try:
        # 按时间倒序排列
        cursor = favorites_col.find({"user_id": user_id}).sort("timestamp", -1)
        favs = []
        for doc in cursor:
            # 提取论文主体
            item = doc.get("paper", {})
            if not item: continue # 跳过脏数据
            
            # 补充 ID (转换 ObjectId)
            item["_id"] = str(doc["_id"])
            
            # 关键修复：兼容旧数据，如果数据库里没存 folder_name，默认为"默认收藏夹"
            item["folder"] = doc.get("folder_name", "默认收藏夹")
            
            favs.append(item)
        return favs
    except Exception as e:
        print(f"Get favorites error: {e}")
        return []

@app.post("/favorite/add")
def add_favorite(req: FavoriteAddRequest):
    """添加到指定文件夹"""
    if favorites_col is None:
        raise HTTPException(status_code=500, detail="数据库未连接，请检查MongoDB服务")
    
    try:
        pid = req.paper.get("id")
        # 检查是否已存在 (覆盖模式，防止重复)
        favorites_col.update_one(
            {"user_id": req.user_id, "paper_id": pid},
            {"$set": {
                "paper": req.paper,
                "folder_name": req.folder_name,
                "timestamp": datetime.datetime.now()
            }},
            upsert=True
        )
        return {"msg": f"已存入【{req.folder_name}】"}
    except Exception as e:
        print(f"Add favorite error: {e}")
        raise HTTPException(status_code=500, detail=f"添加收藏失败: {str(e)}")

@app.post("/favorite/remove")
def remove_favorite(req: FavoriteRemoveRequest):
    if favorites_col is None:
        raise HTTPException(status_code=500, detail="数据库未连接，请检查MongoDB服务")
    
    try:
        favorites_col.delete_one({"user_id": req.user_id, "paper_id": req.paper_id})
        return {"msg": "已取消收藏"}
    except Exception as e:
        print(f"Remove favorite error: {e}")
        raise HTTPException(status_code=500, detail=f"取消收藏失败: {str(e)}")

def include_v1_routes():
    if getattr(app.state, "v1_router_included", False):
        return

    from app.api.v1.router import router as v1_router
    from app.core.config import get_settings

    settings = get_settings()
    app.include_router(v1_router, prefix=settings.api_v1_prefix)
    app.state.v1_router_included = True


include_v1_routes()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
