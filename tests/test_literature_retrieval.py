
from agent.agents.literature_retrieval import (
    literature_retrieval_agent
)


def main():

    print("=" * 60)
    print("Literature Retrieval Agent 独立测试")
    print("=" * 60)

    # 测试输入
    state = {
        "user_query": "这篇论文主要研究了什么问题？",
        "paper_ids": []
    }

    print("\n用户问题：")
    print(state["user_query"])

    # 执行 Agent
    try:
        result = literature_retrieval_agent(state)

        print("\nAgent 执行成功！")

        retrieval_result = result.get(
            "retrieval_result", []
        )

        print(f"\n检索结果数量：{len(retrieval_result)}")

        for item in retrieval_result:

            print("\n" + "-" * 50)

            print(f"排名：{item['rank']}")
            print(f"论文 ID：{item['paper_id']}")
            print(f"Chunk ID：{item['chunk_id']}")
            print(f"页码：{item['page_number']}")
            print(f"RRF 分数：{item['rrf_score']}")

            print("\n原文内容：")
            print(item["content"][:500])

        if not retrieval_result:
            print("\n注意：检索没有返回结果。")
            print("请检查向量库中是否存在已完成向量化的论文。")

    except Exception as error:
        print("\nAgent 执行失败！")
        print(f"错误类型：{type(error).__name__}")
        print(f"错误信息：{error}")

    print("\n" + "=" * 60)
    print("测试结束")
    print("=" * 60)


if __name__ == "__main__":
    main()
