from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
    send_file
)

from models.paper import Paper
from services.paper_service import (
    PaperService,
    PaperNotFoundError,
    PaperValidationError
)

from services.document_processing_service import (
    DocumentProcessingService,
    DocumentProcessingError
)

from services.embedding_pipeline_service import (
    EmbeddingPipelineService,
    EmbeddingPipelineError
)


# 创建论文管理蓝图
paper_bp = Blueprint(
    "paper",
    __name__,
    url_prefix="/api/papers"
)

# 创建业务服务对象
paper_service = PaperService()

@paper_bp.route("/upload", methods=["POST"])
def upload_paper():
    """
    上传 PDF 论文。
    """

    # 从 multipart/form-data 中读取文件
    uploaded_file = request.files.get("file")

    try:
        if uploaded_file is None:
            raise PaperValidationError("请在 file 字段中上传 PDF。")

        paper = paper_service.upload_paper(uploaded_file)

        return jsonify({
            "status": "success",
            "message": "论文上传成功",
            "data": paper
        }), 201

    except PaperValidationError as error:

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400
    
@paper_bp.route("/", methods=["GET"])
def list_papers():
    """获取论文列表。"""

    try:
        limit = request.args.get(
            "limit",
            default=50,
            type=int
        )

        papers = paper_service.list_papers(limit)

        return jsonify({
            "status": "success",
            "total": len(papers),
            "data": papers
        })

    except PaperValidationError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400


@paper_bp.route("/<int:paper_id>", methods=["GET"])
def get_paper(paper_id):
    """获取论文详情。"""

    try:
        paper = paper_service.get_paper(paper_id)

        return jsonify({
            "status": "success",
            "data": paper
        })

    except PaperNotFoundError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 404

    except PaperValidationError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400


@paper_bp.route("/<int:paper_id>", methods=["PATCH"])
def update_paper(paper_id):
    """更新论文基本信息。"""

    data = request.get_json(silent=True)

    try:
        if data is None:
            raise PaperValidationError("请求必须包含有效的 JSON 数据。")

        paper = paper_service.update_paper(
            paper_id,
            data
        )

        return jsonify({
            "status": "success",
            "message": "论文信息更新成功",
            "data": paper
        })

    except PaperNotFoundError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 404

    except PaperValidationError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400
    
@paper_bp.route("/<int:paper_id>", methods=["DELETE"])
    
def delete_paper(paper_id):
    """
    删除论文记录和 PDF 文件。
    """

    try:
        paper_service.delete_paper(paper_id)

        return jsonify({
            "status": "success",
            "message": "论文及对应文件删除成功"
        })

    except PaperNotFoundError as error:

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 404

    except PaperValidationError as error:

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400


@paper_bp.route("/<int:paper_id>/process", methods=["POST"])
def process_paper(paper_id):
    """启动指定论文的解析和文本分块处理。"""

    try:
        result = DocumentProcessingService.process_paper(
            paper_id=paper_id
        )

        return jsonify({
            "status": "success",
            "message": "论文处理成功",
            "data": result
        }), 200

    except ValueError as error:
        # 论文不存在
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 404

    except DocumentProcessingError as error:
        # PDF 解析、文本分块或数据库处理失败
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500


@paper_bp.route("/<int:paper_id>/status", methods=["GET"])
def get_paper_processing_status(paper_id):
    """查询论文的文档处理状态。"""

    paper = Paper.query.get(paper_id)

    if paper is None:
        return jsonify({
            "status": "error",
            "message": f"论文不存在，paper_id={paper_id}"
        }), 404

    return jsonify({
        "status": "success",
        "data": {
            "paper_id": paper.id,
            "title": paper.title,
            "processing_status": paper.status,
            "error_message": paper.error_message
        }
    }), 200


@paper_bp.route("/<int:paper_id>/file", methods=["GET"])
def get_paper_file(paper_id):
    """
    以内联方式返回论文 PDF 文件。

    开启 conditional 支持，使 PDF.js 可以通过 Range 分段加载。
    """

    try:
        pdf_path = paper_service.get_pdf_path(paper_id)

    except PaperNotFoundError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 404

    except PaperValidationError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400

    return send_file(
        pdf_path,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=pdf_path.name,
        conditional=True
    )


@paper_bp.route("/<int:paper_id>/index", methods=["POST"])
def index_paper_embeddings(paper_id):
    """
    将指定论文的文本块向量化并写入 ChromaDB。

    本接口是 RAG 问答的前置步骤，
    只调用现有 EmbeddingPipelineService，不重新实现向量化逻辑。
    """

    try:
        # 先确认论文存在，便于区分 404 与业务异常
        paper_service.get_paper(paper_id)

    except PaperNotFoundError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 404

    except PaperValidationError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400

    try:
        result = EmbeddingPipelineService.index_paper(paper_id)

    except EmbeddingPipelineError as error:
        # 未完成解析、没有文本块等业务前置条件不满足
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400

    except Exception:

        current_app.logger.exception(
            "Paper embedding indexing failed | paper_id=%s",
            paper_id
        )

        return jsonify({
            "status": "error",
            "message": "向量化入库失败，请检查 Embedding 服务与网络连接"
        }), 500

    return jsonify({
        "status": "success",
        "message": "向量化入库成功",
        "data": result
    }), 200
