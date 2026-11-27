
import os
import time
import requests

from dotenv import load_dotenv


load_dotenv()


class EmbeddingError(Exception):
    """Embedding 服务异常。"""
    pass


class EmbeddingService:
    """Doubao Embedding Vision Dense + Sparse 服务。"""

    def __init__(self):

        self.api_key = os.getenv("ARK_API_KEY")

        self.model_name = "doubao-embedding-vision-251215"

        self.api_url = (
            "https://ark.cn-beijing.volces.com"
            "/api/v3/embeddings/multimodal"
        )

        # 第一版实验统一采用 1024 维
        self.dimensions = 1024

        # Corpus：论文文本
        self.corpus_instruction = (
            "Instruction:Compress the text into one word.\n"
            "Query:"
        )

        # Query：用户问题
        self.query_instruction = (
            "Target_modality: text.\n"
            "Instruction:为这个句子生成表示以用于检索相关文章\n"
            "Query:"
        )

    @staticmethod
    def _normalize_sparse_vector(sparse: object) -> list[dict]:
        """统一 API 返回的 Sparse 向量格式并校验。"""

        if (
            isinstance(sparse, dict)
            and isinstance(sparse.get("indices"), list)
            and isinstance(sparse.get("values"), list)
            and len(sparse["indices"]) == len(sparse["values"])
        ):
            sparse = [
                {"index": index, "value": value}
                for index, value in zip(
                    sparse["indices"],
                    sparse["values"]
                )
            ]

        if not isinstance(sparse, list) or not sparse:
            raise EmbeddingError(
                "API 返回的 Sparse 向量不存在或为空。"
            )

        normalized = []

        for item in sparse:
            if isinstance(item, dict):
                index = item.get("index")
                value = item.get("value")

            elif isinstance(item, (list, tuple)) and len(item) == 2:
                index, value = item

            else:
                raise EmbeddingError(
                    "Sparse 向量元素格式不正确。"
                )

            if (
                not isinstance(index, int)
                or isinstance(index, bool)
                or index < 0
            ):
                raise EmbeddingError(
                    "Sparse 向量 index 必须是非负整数。"
                )

            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
            ):
                raise EmbeddingError(
                    "Sparse 向量 value 必须是数值。"
                )

            normalized.append({
                "index": index,
                "value": float(value)
            })

        return normalized

    def _request_embedding(
        self,
        text: str,
        instruction: str
    ) -> dict:

        if not self.api_key:
            raise EmbeddingError(
                "未配置 ARK_API_KEY，请检查 .env 文件。"
            )

        if not isinstance(text, str) or not text.strip():
            raise EmbeddingError("输入文本不能为空。")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model_name,
            "input": [
                {
                    "type": "text",
                    "text": text
                }
            ],
            "instructions": instruction,
            "dimensions": self.dimensions,
            "encoding_format": "float",
            "sparse_embedding": {
                "type": "enabled"
            }
        }

        start_time = time.perf_counter()

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=(10, 60)
            )

            response.raise_for_status()

            result = response.json()

            data = result.get("data")

            if isinstance(data, list):
                if not data:
                    raise EmbeddingError(
                        "API 返回的 data 是空列表。"
                    )
                data = data[0]

            if not isinstance(data, dict):
                raise EmbeddingError(
                    "API 返回的 data 结构不正确。"
                )

            # 提取稠密向量
            embedding = data.get("embedding")

            if (
                not isinstance(embedding, list)
                or len(embedding) != self.dimensions
            ):
                raise EmbeddingError(
                    f"Dense 向量异常：预期 {self.dimensions} 维。"
                )

            if not all(
                isinstance(value, (int, float))
                for value in embedding
            ):
                raise EmbeddingError(
                    "Dense 向量中包含非数值内容。"
                )

            # 提取稀疏向量
            sparse_embedding = self._normalize_sparse_vector(
                data.get("sparse_embedding")
            )

            usage = result.get("usage", {})

            elapsed_ms = (
                time.perf_counter() - start_time
            ) * 1000

            return {
                "embedding": embedding,
                "dense_embedding": embedding,
                "sparse_embedding": sparse_embedding,
                "sparse_nonzero_count": len(sparse_embedding),
                "model_name": result.get(
                    "model",
                    self.model_name
                ),
                "dimensions": len(embedding),
                "prompt_tokens": usage.get("prompt_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "elapsed_ms": round(elapsed_ms, 2),
                "request_id": result.get("id")
            }

        except requests.exceptions.RequestException as error:
            # 不在错误信息中输出 API Key
            detail = ""

            if error.response is not None:
                detail = error.response.text[:500]

            raise EmbeddingError(
                f"Doubao API 请求失败：{error}；{detail}"
            ) from error

        except (KeyError, TypeError, ValueError) as error:
            if isinstance(error, EmbeddingError):
                raise

            raise EmbeddingError(
                f"解析 API 响应失败：{error}"
            ) from error

    def embed_document(self, text: str) -> dict:
        """将论文 Chunk 转换为向量。"""

        return self._request_embedding(
            text,
            self.corpus_instruction
        )

    def embed_query(self, query: str) -> dict:
        """将用户问题转换为向量。"""

        return self._request_embedding(
            query,
            self.query_instruction
        )

    def embed_texts(self, texts: list[str]) -> list[dict]:
        """批量处理多条论文文本。"""

        if not isinstance(texts, list) or not texts:
            raise EmbeddingError(
                "texts 必须是非空列表。"
            )

        return [
            self.embed_document(text)
            for text in texts
        ]


embedding_service = EmbeddingService()

