
import os
import requests
from dotenv import load_dotenv


def test_sparse_embedding():
    """验证 Doubao Embedding Vision 的 Dense + Sparse 输出。"""

    load_dotenv()

    api_key = os.getenv("ARK_API_KEY")

    if not api_key:
        raise RuntimeError("没有读取到 ARK_API_KEY，请检查项目根目录的 .env 文件")

    url = "https://ark.cn-beijing.volces.com/api/v3/embeddings/multimodal"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "doubao-embedding-vision-251215",
        "input": [
            {
                "type": "text",
                "text": "大语言模型在学术文献阅读中的应用"
            }
        ],
        "instructions": "Instruction:Compress the text into one word.\nQuery:",
        "dimensions": 1024,
        "encoding_format": "float",
        "sparse_embedding": {
            "type": "enabled"
        }
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        result = response.json()

    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Embedding API 请求失败：{exc}") from exc

    data = result.get("data")

    if isinstance(data, list):
        if not data:
            raise RuntimeError("API 返回的 data 是空列表")
        data = data[0]

    if not isinstance(data, dict):
        raise RuntimeError("API 返回的数据结构不符合预期")

    dense = data.get("embedding")
    sparse = data.get("sparse_embedding")

    if not isinstance(dense, list) or len(dense) != 1024:
        raise RuntimeError("Dense 向量不存在或维度不是 1024")

    if not isinstance(sparse, list) or not sparse:
        raise RuntimeError("Sparse 向量不存在或为空")

    for item in sparse:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("index"), int)
            or not isinstance(item.get("value"), (int, float))
        ):
            raise RuntimeError("Sparse 向量元素格式不正确")

    print("========== Sparse API 验证成功 ==========")
    print("模型：", result.get("model"))
    print("Dense 向量维度：", len(dense))
    print("Sparse 非零元素数量：", len(sparse))
    print("Sparse 前 5 个元素：", sparse[:5])
    print("Token 使用情况：", result.get("usage"))
    print("=========================================")


if __name__ == "__main__":
    test_sparse_embedding()
