# 该文件只负责管理 ChromaDB 中的向量数据，不负责调用 Doubao，也不负责查询 MySQL。

import json
import math
from pathlib import Path

import chromadb


class VectorStoreError(Exception):
    """向量数据库操作异常。"""
    pass


class ChromaVectorStore:
    """学术文献 Dense + Sparse 混合向量存储。"""

    COLLECTION_NAME = "literature_chunks_hybrid_v1"
    RRF_K = 60
    CANDIDATE_MULTIPLIER = 4
    MIN_CANDIDATE_K = 20

    def __init__(self):

        self.base_dir = Path(__file__).resolve().parent.parent

        self.persist_dir = (
            self.base_dir / "storage" / "vector_store"
        )

        self.persist_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self.model_name = "doubao-embedding-vision-251215"
        self.dimensions = 1024

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir)
        )

        self.collection = (
            self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                configuration={
                    "hnsw": {
                        "space": "cosine"
                    }
                },
                metadata={
                    "embedding_model": self.model_name,
                    "embedding_dimensions": self.dimensions,
                    "vector_type": "hybrid"
                },
                embedding_function=None
            )
        )

    @staticmethod
    def _validate_paper_id(paper_id: int) -> None:
        if not isinstance(paper_id, int) or paper_id <= 0:
            raise VectorStoreError(
                "paper_id 必须是正整数。"
            )

    @staticmethod
    def _validate_top_k(top_k: int) -> None:
        if not isinstance(top_k, int) or top_k <= 0:
            raise VectorStoreError(
                "top_k 必须是正整数。"
            )

    def _validate_dense_embedding(self, embedding: object) -> None:
        if (
            not isinstance(embedding, list)
            or len(embedding) != self.dimensions
        ):
            raise VectorStoreError(
                f"向量必须是 {self.dimensions} 维。"
            )

        if not all(
            isinstance(value, (int, float))
            for value in embedding
        ):
            raise VectorStoreError(
                "向量中包含非数值内容。"
            )

    @staticmethod
    def _normalize_sparse_vector(sparse: object) -> list[dict]:
        """统一 Sparse 向量格式，并合并重复 index。"""

        if sparse is None:
            return []

        if isinstance(sparse, dict):
            indices = sparse.get("indices")
            values = sparse.get("values")

            if (
                isinstance(indices, list)
                and isinstance(values, list)
                and len(indices) == len(values)
            ):
                pairs = zip(indices, values)
            else:
                raise VectorStoreError(
                    "Sparse 向量字典必须包含等长的 indices 和 values。"
                )

        elif isinstance(sparse, list):
            pairs = []

            for item in sparse:
                if isinstance(item, dict):
                    pairs.append(
                        (item.get("index"), item.get("value"))
                    )

                elif isinstance(item, (list, tuple)) and len(item) == 2:
                    pairs.append((item[0], item[1]))

                else:
                    raise VectorStoreError(
                        "Sparse 向量元素格式不正确。"
                    )

        else:
            raise VectorStoreError(
                "Sparse 向量格式不正确。"
            )

        merged = {}

        for index, value in pairs:
            if (
                not isinstance(index, int)
                or isinstance(index, bool)
                or index < 0
            ):
                raise VectorStoreError(
                    "Sparse 向量 index 必须是非负整数。"
                )

            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
            ):
                raise VectorStoreError(
                    "Sparse 向量 value 必须是数值。"
                )

            merged[index] = merged.get(index, 0.0) + float(value)

        return [
            {"index": index, "value": merged[index]}
            for index in sorted(merged)
        ]

    @staticmethod
    def _serialize_sparse_vector(sparse: list[dict]) -> str:
        return json.dumps(
            {
                "indices": [item["index"] for item in sparse],
                "values": [item["value"] for item in sparse]
            },
            separators=(",", ":")
        )

    def _sparse_vector_from_metadata(
        self,
        metadata: dict | None
    ) -> list[dict]:
        if not metadata or not metadata.get("sparse_vector"):
            return []

        try:
            raw = metadata["sparse_vector"]

            if isinstance(raw, str):
                raw = json.loads(raw)

            return self._normalize_sparse_vector(raw)

        except (ValueError, TypeError, VectorStoreError):
            return []

    @staticmethod
    def _sparse_to_dict(sparse: list[dict]) -> dict[int, float]:
        return {
            item["index"]: item["value"]
            for item in sparse
        }

    def upsert_chunks(self, chunks: list[dict]) -> int:
        """
        保存或更新一篇论文的 Dense + Sparse Chunk 向量。

        每个 Chunk 需要包含：
        paper_id、chunk_index、page_number、content、embedding，
        并建议包含 sparse_embedding。
        """

        if not chunks:
            raise VectorStoreError(
                "不能保存空的 Chunk 列表。"
            )

        ids = []
        documents = []
        metadatas = []
        embeddings = []

        paper_ids = set()

        for chunk in chunks:
            paper_id = chunk.get("paper_id")
            chunk_index = chunk.get("chunk_index")
            page_number = chunk.get("page_number")
            content = chunk.get("content")
            embedding = chunk.get("embedding")
            sparse_embedding = self._normalize_sparse_vector(
                chunk.get("sparse_embedding")
            )

            self._validate_paper_id(paper_id)

            if (
                not isinstance(chunk_index, int)
                or chunk_index < 0
            ):
                raise VectorStoreError(
                    "chunk_index 必须是非负整数。"
                )

            if (
                not isinstance(page_number, int)
                or page_number <= 0
            ):
                raise VectorStoreError(
                    "page_number 必须是正整数。"
                )

            if (
                not isinstance(content, str)
                or not content.strip()
            ):
                raise VectorStoreError(
                    "Chunk 原文不能为空。"
                )

            self._validate_dense_embedding(embedding)

            paper_ids.add(paper_id)

            vector_id = (
                f"paper_{paper_id}_chunk_{chunk_index}"
            )

            ids.append(vector_id)
            documents.append(content)
            embeddings.append(embedding)

            metadatas.append({
                "paper_id": paper_id,
                "chunk_index": chunk_index,
                "page_number": page_number,
                "embedding_model": self.model_name,
                "embedding_dimensions": self.dimensions,
                "sparse_vector": self._serialize_sparse_vector(
                    sparse_embedding
                ),
                "sparse_nonzero_count": len(sparse_embedding)
            })

        if len(paper_ids) != 1:
            raise VectorStoreError(
                "一次只能保存同一篇论文的 Chunk。"
            )

        paper_id = next(iter(paper_ids))

        old_result = self.collection.get(
            where={"paper_id": paper_id},
            include=["metadatas"]
        )

        old_ids = set(old_result["ids"])
        new_ids = set(ids)

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        stale_ids = list(old_ids - new_ids)

        if stale_ids:
            self.collection.delete(ids=stale_ids)

        return len(ids)

    def count(self) -> int:
        """返回向量库中的总记录数。"""

        return self.collection.count()

    def get_paper_chunks(self, paper_id: int) -> dict:
        """根据论文 ID 查看已保存的 Chunk。"""

        self._validate_paper_id(paper_id)

        return self.collection.get(
            where={"paper_id": paper_id},
            include=["documents", "metadatas"]
        )

    def delete_paper_chunks(self, paper_id: int) -> int:
        """
        删除指定论文在向量库中的全部 Chunk。

        返回实际删除的记录数；
        该论文在向量库中没有记录时返回 0，不视为错误。
        """

        self._validate_paper_id(paper_id)

        try:
            existing = self.collection.get(
                where={"paper_id": paper_id},
                include=["metadatas"]
            )

        except Exception as error:

            raise VectorStoreError(
                f"向量库查询失败：{error}"
            ) from error

        ids = existing.get("ids") or []

        if not ids:
            return 0

        try:
            self.collection.delete(
                where={"paper_id": paper_id}
            )

        except Exception as error:

            raise VectorStoreError(
                f"向量库删除失败：{error}"
            ) from error

        return len(ids)

    def search_dense(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        paper_id: int | None = None
    ) -> list[dict]:
        """使用 Dense 向量检索。"""

        self._validate_dense_embedding(query_embedding)
        self._validate_top_k(top_k)

        if paper_id is not None:
            self._validate_paper_id(paper_id)

        total_count = self.collection.count()

        if total_count == 0:
            return []

        result_count = min(top_k, total_count)

        query_args = {
            "query_embeddings": [query_embedding],
            "n_results": result_count,
            "include": [
                "documents",
                "metadatas",
                "distances"
            ]
        }

        if paper_id is not None:
            query_args["where"] = {
                "paper_id": paper_id
            }

        query_result = self.collection.query(
            **query_args
        )

        ids = query_result["ids"][0]
        documents = query_result["documents"][0]
        metadatas = query_result["metadatas"][0]
        distances = query_result["distances"][0]

        results = []

        for rank, (
            vector_id,
            document,
            metadata,
            distance
        ) in enumerate(
            zip(ids, documents, metadatas, distances),
            start=1
        ):
            dense_distance = float(distance)
            dense_similarity = 1 - dense_distance

            results.append({
                "id": vector_id,
                "content": document,
                "paper_id": metadata["paper_id"],
                "chunk_index": metadata["chunk_index"],
                "page_number": metadata["page_number"],
                "distance": dense_distance,
                "similarity": dense_similarity,
                "dense_distance": dense_distance,
                "dense_similarity": dense_similarity,
                "sparse_score": None,
                "dense_rank": rank,
                "sparse_rank": None,
                "rrf_score": 1 / (self.RRF_K + rank),
                "retrieval_sources": ["dense"]
            })

        return results

    def search_sparse(
        self,
        query_sparse: object,
        top_k: int = 5,
        paper_id: int | None = None
    ) -> list[dict]:
        """使用 Sparse 向量做词项级相似度召回。"""

        query_vector = self._normalize_sparse_vector(
            query_sparse
        )

        if not query_vector:
            raise VectorStoreError(
                "Sparse Query 向量不能为空。"
            )

        self._validate_top_k(top_k)

        if paper_id is not None:
            self._validate_paper_id(paper_id)

        get_args = {
            "include": ["documents", "metadatas"]
        }

        if paper_id is not None:
            get_args["where"] = {
                "paper_id": paper_id
            }

        stored_result = self.collection.get(
            **get_args
        )

        if not stored_result["ids"]:
            return []

        query_index = self._sparse_to_dict(query_vector)
        query_norm = math.sqrt(
            sum(
                value * value
                for value in query_index.values()
            )
        )

        if query_norm == 0:
            return []

        results = []

        for vector_id, document, metadata in zip(
            stored_result["ids"],
            stored_result["documents"],
            stored_result["metadatas"]
        ):
            stored_vector = self._sparse_vector_from_metadata(
                metadata
            )

            if not stored_vector:
                continue

            stored_index = self._sparse_to_dict(
                stored_vector
            )

            stored_norm = math.sqrt(
                sum(
                    value * value
                    for value in stored_index.values()
                )
            )

            if stored_norm == 0:
                continue

            dot_product = sum(
                value * stored_index.get(index, 0.0)
                for index, value in query_index.items()
            )

            score = dot_product / (
                query_norm * stored_norm
            )

            if score <= 0:
                continue

            score = min(float(score), 1.0)

            results.append({
                "id": vector_id,
                "content": document,
                "paper_id": metadata["paper_id"],
                "chunk_index": metadata["chunk_index"],
                "page_number": metadata["page_number"],
                "distance": 1 - score,
                "similarity": score,
                "dense_distance": None,
                "dense_similarity": None,
                "sparse_score": score,
                "dense_rank": None,
                "sparse_rank": None,
                "rrf_score": 0.0,
                "retrieval_sources": ["sparse"]
            })

        results.sort(
            key=lambda item: item["sparse_score"],
            reverse=True
        )

        for rank, item in enumerate(
            results[:top_k],
            start=1
        ):
            item["sparse_rank"] = rank
            item["rrf_score"] = 1 / (self.RRF_K + rank)

        return results[:top_k]

    def _fuse_results(
        self,
        dense_results: list[dict],
        sparse_results: list[dict]
    ) -> list[dict]:
        """使用 RRF 融合两路召回结果。"""

        fused = {}

        for item in dense_results:
            fused[item["id"]] = dict(item)

        for item in sparse_results:
            vector_id = item["id"]

            if vector_id not in fused:
                fused[vector_id] = dict(item)
                continue

            current = fused[vector_id]
            dense_rank = current.get("dense_rank")
            sparse_rank = item.get("sparse_rank")

            current["sparse_score"] = item.get(
                "sparse_score"
            )

            if dense_rank is not None and sparse_rank is not None:
                current["rrf_score"] = (
                    1 / (self.RRF_K + dense_rank)
                    + 1 / (self.RRF_K + sparse_rank)
                )

            elif sparse_rank is not None:
                current["rrf_score"] = (
                    1 / (self.RRF_K + sparse_rank)
                )

            if "sparse" not in current["retrieval_sources"]:
                current["retrieval_sources"].append(
                    "sparse"
                )

        return sorted(
            fused.values(),
            key=lambda item: (
                -item["rrf_score"],
                item.get("dense_rank")
                or self.RRF_K,
                item.get("sparse_rank")
                or self.RRF_K
            )
        )

    def search(
        self,
        query_embedding: list[float] | None = None,
        query_sparse: object | None = None,
        top_k: int = 5,
        paper_id: int | None = None
    ) -> list[dict]:
        """
        执行 Dense + Sparse 混合检索。

        只传入 Dense 或 Sparse 时，自动退化为单路检索。
        """

        self._validate_top_k(top_k)

        if paper_id is not None:
            self._validate_paper_id(paper_id)

        use_dense = query_embedding is not None
        use_sparse = query_sparse is not None

        if use_dense:
            self._validate_dense_embedding(
                query_embedding
            )

        if not use_dense and not use_sparse:
            raise VectorStoreError(
                "至少需要提供 Dense 或 Sparse Query 向量。"
            )

        if use_dense and not use_sparse:
            return self.search_dense(
                query_embedding,
                top_k=top_k,
                paper_id=paper_id
            )

        if use_sparse and not use_dense:
            return self.search_sparse(
                query_sparse,
                top_k=top_k,
                paper_id=paper_id
            )

        candidate_k = max(
            top_k * self.CANDIDATE_MULTIPLIER,
            self.MIN_CANDIDATE_K
        )

        dense_results = self.search_dense(
            query_embedding,
            top_k=candidate_k,
            paper_id=paper_id
        )

        sparse_results = self.search_sparse(
            query_sparse,
            top_k=candidate_k,
            paper_id=paper_id
        )

        fused_results = self._fuse_results(
            dense_results,
            sparse_results
        )

        return fused_results[:top_k]


vector_store = ChromaVectorStore()
