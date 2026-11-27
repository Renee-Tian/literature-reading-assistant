
# 基于大语言模型的学术文献阅读辅助系统

Academic Literature Reading Assistant System Based on Large Language Models

## 1. 项目简介

本项目是一个基于大语言模型的学术文献阅读辅助系统，旨在利用大语言模型、检索增强生成（RAG）和多智能体协作技术，辅助用户完成学术文献的理解、信息提取和知识检索。

系统采用 Supervisor + Multi-Agent 架构，通过 LangGraph 实现多个专业智能体的任务分配与协作，帮助用户提高学术文献阅读和信息整理效率。

本项目为本科毕业设计项目，目前处于开发阶段。

## 2. 项目建设目标

- 实现学术 PDF 文献上传、解析与管理。
- 利用大语言模型生成结构化文献阅读报告。
- 基于 RAG 实现论文内容检索与智能问答。
- 通过多智能体协作完成不同类型的文献分析任务。
- 提供原文依据、阅读记录和个人笔记管理功能。

## 3. 核心功能

### 3.1 文献管理
- PDF 文件上传与管理
- 文献基本信息提取
- 文献列表与详情展示

### 3.2 智能文献阅读
- 论文摘要生成
- 研究背景与研究问题提取
- 研究方法与主要结论分析
- 创新点和局限性整理

### 3.3 文献智能问答
- 基于 RAG 的论文知识检索
- 自然语言问答
- 原文证据定位与页码展示

### 3.4 多智能体协作
- Supervisor 总控智能体
- Literature Reading Agent：文献阅读与解读
- Literature QA Agent：文献检索与问答
- Research Analysis Agent：研究方法与实验分析

## 4. 系统技术架构

系统采用模块化单体架构，使用 LangGraph 组织多智能体协作。

整体架构：

用户请求
    |
    v
Supervisor 总控智能体
    |
    +-- Literature Reading Agent
    |
    +-- Literature QA Agent
    |
    +-- Research Analysis Agent
    |
    v
结果整合与返回

## 5. 技术栈

| 技术 | 用途 |
|---|---|
| Python | 核心开发语言 |
| Flask | 后端 Web 框架 |
| HTML / CSS / JavaScript | 前端开发 |
| 大语言模型 API | 文献理解与内容生成 |
| LangGraph | 多智能体工作流编排 |
| RAG | 文献知识检索 |
| BGE Embedding | 文本向量化 |
| ChromaDB | 向量数据存储 |
| MySQL | 业务数据管理 |
| PyMuPDF | PDF 文档解析 |

## 6. 项目目录结构

```text
literature-reading-assistant/
├── routes/                  # 后端接口
├── services/                # 业务服务
├── agent/                   # 多智能体系统
│   ├── agents/              # 专业 Agent
│   ├── tools/               # Agent 工具
│   └── nodes/               # LangGraph 节点
├── document/                # PDF 文档处理
├── ai/                      # 大语言模型调用
├── rag/                     # RAG 知识检索
├── models/                  # 数据模型
├── database/                # 数据库管理
├── templates/               # HTML 页面
├── static/                  # 前端静态资源
├── storage/                 # 文件与向量数据
├── tests/                   # 测试代码
├── docs/                    # 项目文档
├── app.py                   # 项目启动入口
├── config.py                # 项目配置
├── requirements.txt         # 项目依赖
└── README.md                # 项目说明
```

## 7. 开发进度

- [x] 项目总体架构规划
- [x] 项目目录结构设计
- [ ] Flask 基础工程建设
- [ ] 文献管理与 PDF 解析
- [ ] 大语言模型接入
- [ ] RAG 知识检索
- [ ] 三个专业 Agent 开发
- [ ] Supervisor 与 LangGraph 多智能体协作
- [ ] 前端开发与系统整合
- [ ] 系统测试与实验评价

## 8. 项目目标

最终实现一个集学术文献管理、智能阅读、知识问答和多智能体协作于一体的学术文献阅读辅助系统。
