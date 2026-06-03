## rag知识库
> 使用模板清洗完的事故报告，写入到 wiki_事故复盘 的文件夹中。目前使用的文件命名模板：[YYYYMMDD][影响系统][故障内容].md
> 使用Chroma向量数据库保存数据
> 使用BAAI/bge-large-zh-v1.5模型，对报告进行分析
> 后端rag_app.py 接入DeepSeek V4 flash模型进行LLM对话