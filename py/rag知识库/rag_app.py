#!/usr/bin/env python3

import os
import sys

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

def main():
    CHROMA_DB_DIR = "./chroma_db"

    if not os.path.exists(CHROMA_DB_DIR):
        print(f"错误: 未找到本地数据库 {CHROMA_DB_DIR}，请先运行 ingest.py 进行入库！")
        sys.exit(1)

    # 1. 加载本地 Embedding 模型（直接读取本地缓存，不联网）
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-large-zh-v1.5",
        model_kwargs={
            'device': 'cpu',
            'local_files_only': True
        },
        encode_kwargs={'normalize_embeddings': True}
    )

    # 2. 直接从本地目录加载已有的向量数据库
    vector_store = Chroma(
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_DIR
    )

    # 3. 启用 MMR 检索器（多样性打散算法，确保长文本列表不丢失）
    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 30,
            "fetch_k": 100,
            "lambda_mult": 0.35,
        }
    )

    # 4. 优化辅助函数：强制将文件名拼进上下文送给 AI
    def format_docs(docs):
        formatted_list = []

        for doc in docs:
            source_file = doc.metadata.get("source_file", "未知文件")
            formatted_chunk = f"【来自文件: {source_file}】\n内容片段:\n{doc.page_content}"
            formatted_list.append(formatted_chunk)

        return "\n\n---\n\n".join(formatted_list)

    # 5. 设置大模型（DeepSeek）
    os.environ["OPENAI_API_KEY"] = "sk-qqqqqqqqqqqqqqqqqqqqqe"
    os.environ["OPENAI_BASE_URL"] = "https://api.deepseek.com"
    llm = ChatOpenAI(model="deepseek-v4-flash", temperature=0)

    # 6. 组装现代 LCEL RAG 链
    system_prompt = (
        "你是一个技术专家和资深系统运维架构师。请利用以下检索到的【历史生产事故复盘文档】来回答用户的问题。\n"
        "请严格基于上下文回答，不要瞎编。如果上下文中没有提到相关解决办法，请直接回答：'基于现有事故库未检索到相关解决方案'。\n\n"
        "【已知历史事故上下文】:\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    rag_chain = (
        {"context": retriever | format_docs, "input": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # 7. 交互式对话循环（变成一个真正的命令行小助手）
    while True:
        try:
            question = input("\n请输入您的运维问题 (输入 exit 退出): ").strip()
            if not question:
                continue

            if question.lower() == 'exit':
                print("检测到退出命令，程序结束")
                sys.exit(0)

            print("🤖 正在检索并思考中...")
            answer = rag_chain.invoke(question)
            print(f"\nAI 回答:\n{answer}")

        except KeyboardInterrupt:
            print("\n用户中断，退出程序")
            sys.exit(0)

        except Exception as e:
            print(f"发生错误: {e}")

if __name__ == "__main__":
    main()