
# Embedding 检索实验计划

## 1. 实验目的

研究不同文本向量表示及检索策略
对学术文献阅读辅助系统检索效果的影响。

## 2. 固定实验条件

- Embedding 模型：doubao-embedding-vision-251215
- 向量维度：1024
- 文本分块：chunk_size=1200
- 文本重叠：overlap=150
- 检索数据：相同的学术论文集合
- 测试问题：同一批人工标注的问题

## 3. 实验方案

| 编号 | 检索方式 | 说明 |
|---|---|---|
| A | Dense | 稠密向量检索基线 |
| B | Sparse | 稀疏向量检索 |
| C | Hybrid | 稠密与稀疏混合检索 |
| D | Multi | 多向量检索探索 |

## 4. 评价指标

- Recall@K：相关文本是否被召回
- MRR：相关文本的排名表现
- Evidence Support Rate：回答是否得到原文证据支持
- Response Time：检索响应时间
- Token Usage：Embedding 调用 Token 消耗
- API Cost：API 调用成本

## 5. 实验注意事项

不同方案使用相同的论文、问题和标注标准。

模型版本、向量维度、分块参数及检索参数应完整记录。
