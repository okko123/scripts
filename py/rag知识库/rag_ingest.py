#!/usr/bin/env python3

import os
import shutil
import logging

from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

logging.basicConfig(
    filename = '/data/workdir/rag.log',
    format = '%(name)s - %(levelname)s - %(message)s',
    level = logging.INFO
)

def main():
    MD_DIR = "./wiki_事故复盘"
    CHROMA_DB_DIR = "./chroma_db"

    # 1. 初始化 Embedding 模型
    model_name = "BAAI/bge-large-zh-v1.5"
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

    if not os.path.exists(MD_DIR) or len(os.listdir(MD_DIR)) == 0:
        logging.error(f"错误: 找不到文档目录 {MD_DIR} 或目录为空！")
        return

    logging.info("👉 正在读取本地 MD 文件并进行双路切片（摘要 + 细节）...")
    headers_to_split_on = [
        ("#", "Header_1"),
        ("##", "Header_2"),
        ("###", "Header_3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    all_chunks = []

    # 遍历读取本地文件夹
    for file_name in os.listdir(MD_DIR):
        if file_name.endswith(".md"):
            file_path = os.path.join(MD_DIR, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()

            lines = file_content.split('\n')
            metadata_summary = "\n".join(lines[:12]) if len(lines) > 12 else file_content

            summary_doc = Document(
                page_content=f"这是故障文件的全局摘要：\n{metadata_summary}",
                metadata={
                    "source_file": file_name, 
                    "chunk_type": "global_summary", 
                    "knowledge_type": "accident_review"
                }
            )
            all_chunks.append(summary_doc)

            # 2. 制作细节级联切片
            chunks = markdown_splitter.split_text(file_content)

            for chunk in chunks:
                chunk.metadata["source_file"] = file_name
                chunk.metadata["chunk_type"] = "detail"
                chunk.metadata["knowledge_type"] = "accident_review"
                all_chunks.append(chunk)

    # 清理旧数据库
    if os.path.exists(CHROMA_DB_DIR):
        logging.info(f"清理旧的向量数据库: {CHROMA_DB_DIR}")
        shutil.rmtree(CHROMA_DB_DIR)

    logging.info(f"正在将 {len(all_chunks)} 个切片向量化并写入本地 Chroma 数据库...")

    # 初始化并持久化写入
    Chroma.from_documents(
        documents=all_chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DB_DIR
    )
    logging.info("静态数据入库成功！数据库已安全持久化到本地。")

if __name__ == "__main__":
    main()