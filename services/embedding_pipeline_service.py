#这个文件负责协调三个模块：
#1.MySQL:读取chunk
#2.Embedding:将chunk转换为embedding
#3.Vector Store:将embedding存储到向量存储中

from sqlalchemy import select

from database.db import db
from models import Paper,PaperChunk

from ai.embedding_service import embedding_service
from rag.vector_store import vector_store

class EmbeddingPipelineError(Exception):
    pass

class EmbeddingPipelineService:
    """负责将MySQL中的论文Chunk向量化写入ChromaDB"""

    @staticmethod
    def index_paper(paper_id:int) -> dict:
        """对指定论文执行完整的向量化入库流程"""

        #1.检查论文是否存在
        paper = db.session.get(Paper,paper_id)

        if paper is None:
            raise EmbeddingPipelineError(
                (f"论文不存在,paper_id={paper_id}")
            )

        #2.从MySQL读取论文的全部Chunk
        statement=(
            select(PaperChunk)
            .where(PaperChunk.paper_id == paper_id)
            .order_by(PaperChunk.chunk_index)
        )

        chunks = db.session.execute(
            statement
        ).scalars().all()

        if not chunks:
            raise EmbeddingPipelineError(
                (f"该论文没有Chunk,请先完成PDF解析和文本分块。paper_id={paper_id}")
            )

        #3.提取所有Chunk原文
        contents = [
            chunk.content
            for chunk in chunks
        ]
           
        #4.调用豆包生成向量
        #该方法逐条调用API，全部成功后才会返回

        embedding_results =(
            embedding_service.embed_texts(contents)
        )

        if len(embedding_results) != len(chunks):
            raise EmbeddingPipelineError(
                (f"Embedding数量与Chunk数量不一致。paper_id={paper_id}")
            )

        # 5. 组合ChromaDB需要的数据

        vector_chunks = []

        total_tokens = 0
        total_elapsed_ms = 0.0

        for chunk,result in zip(
            chunks,
            embedding_results):
            vector_chunks.append(
                {
                    "paper_id":paper_id,
                    "chunk_index":chunk.chunk_index,
                    "page_number":chunk.page_number,
                    "content":chunk.content,
                    "embedding":result["embedding"],
                    "sparse_embedding":result.get(
                        "sparse_embedding",
                        []
                    ),
                }
            )
            total_tokens += result["total_tokens"]
            total_elapsed_ms += result["elapsed_ms"] or 0
            
        #6.将向量存储到ChromaDB中
        saved_count = vector_store.upsert_chunks(
            vector_chunks
        )

        if saved_count != len(vector_chunks):
            raise EmbeddingPipelineError(
                (f"ChromaDB入库数量与Chunk数量不一致。paper_id={paper_id}")
            )
        
        #7.返回执行结果
        return{
            "paper_id":paper_id,

            "paper_title":paper.title,

            "chunks_count":len(chunks),

            "indexed_count":saved_count,

            "embedding_model":embedding_service.model_name,

            "dimensions":(
                embedding_service.dimensions
            ),

            "total_tokens":total_tokens,

            "embedding_time_ms":round(
                total_elapsed_ms,
                2
            ),

            "vector_store_count":vector_store.count()
        }

embedding_pipeline_service = EmbeddingPipelineService()