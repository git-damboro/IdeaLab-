# app/utils.py

import numpy as np
from rank_bm25 import BM25Okapi
from typing import List, Dict

# 可调参数：BM25 最多用多少篇文档建索引，防止一次性加载太多文档导致进程被系统 Killed
# 在内存相对紧张的环境下，将上限降到 5000，可以显著降低内存占用
MAX_BM25_DOCS = 5000

class HybridSearcher:
    def __init__(self, mongo_col):
        """
        延迟构建 BM25 索引，避免启动时一次性吃光内存。
        第一次调用 search() 时才真正去 MongoDB 拉数据并建索引。
        """
        self.mongo_col = mongo_col
        self.bm25 = None
        self.doc_ids = []
        self.corpus = []
        self.index_built = False
        print("✅ HybridSearcher 初始化完成（延迟构建索引）")

    def _build_index_if_needed(self):
        """在首次搜索时构建索引（只建一次）"""
        if self.index_built:
            return

        if self.mongo_col is None:
            print("⚠️ MongoDB 未连接，无法构建 BM25 索引")
            return

        print(f"⚙️ 正在构建 BM25 关键词索引（最多使用 {MAX_BM25_DOCS} 篇文档）...")
        self.doc_ids = []
        self.corpus = []

        # 只取需要的字段，按批次读取，避免一次性占太多内存
        batch_size = 1000
        cursor = self.mongo_col.find(
            {}, {"paper_id": 1, "combined_text": 1}
        ).batch_size(batch_size)

        count = 0
        for doc in cursor:
            self.doc_ids.append(doc["paper_id"])
            text = doc.get("combined_text", "") or ""
            self.corpus.append(text.lower().split())
            count += 1

            if count % 5000 == 0:
                print(f"   📊 已收集 {count} 篇文档用于 BM25 索引...")

            # 达到上限就停，避免过多占用内存
            if count >= MAX_BM25_DOCS:
                break

        if not self.corpus:
            print("⚠️ 没有可用于 BM25 的文档，跳过索引构建")
            return

        print(f"   📊 总共使用 {count} 篇文档构建 BM25 索引，开始计算 BM25...")
        self.bm25 = BM25Okapi(self.corpus)
        self.index_built = True
        print(f"✅ BM25 索引构建完成，共 {len(self.doc_ids)} 篇文档")
    
    def search(self, query: str, top_k: int = 50) -> List[Dict]:
        """执行关键词搜索（第一次调用时会触发索引构建）"""
        self._build_index_if_needed()

        if self.bm25 is None:
            # 没有索引（可能 Mongo 不可用或没有文档），返回空列表
            return []

        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)

        # 获取分数最高的 top_k 个索引
        top_n_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_n_indices:
            score = scores[idx]
            if score > 0:  # 过滤掉完全不相关的结果
                results.append({
                    "paper_id": self.doc_ids[idx],
                    "score": float(score)
                })
        return results
    def warmup(self):
        """
        在后台线程里调用，用于服务启动后预先构建 BM25 索引。
        多次调用也没关系，内部会自己判断是否已经构建过。
        """
        print("🚀 BM25 预热：开始后台构建索引（如果尚未构建）...")
        self._build_index_if_needed()
        print("✅ BM25 预热完成")

def reciprocal_rank_fusion(vector_results, keyword_results, k=60):
    """
    RRF 算法：融合 向量检索 和 关键词检索 的排名
    公式: score = 1 / (k + rank)
    """
    fused_scores = {}
    
    # 1. 处理向量结果
    for rank, item in enumerate(vector_results):
        pid = item['paper_id']
        if pid not in fused_scores: fused_scores[pid] = 0
        fused_scores[pid] += 1 / (k + rank + 1)
        
    # 2. 处理关键词结果
    for rank, item in enumerate(keyword_results):
        pid = item['paper_id']
        if pid not in fused_scores: fused_scores[pid] = 0
        fused_scores[pid] += 1 / (k + rank + 1)
    
    # 3. 排序并转换为列表
    sorted_results = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    
    # 还原为字典列表格式
    return [{"paper_id": pid, "score": score} for pid, score in sorted_results]
