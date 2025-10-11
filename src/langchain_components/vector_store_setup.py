from typing import List
from langchain_core.documents import Document
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter

def setup_vectore_store_and_retriver(
    documents: List[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
):
    """
    设置向量存储并返回一个检索对象
    该函数接受文档列表，将它们分成块，为每个块创建嵌入，
    将它们存储在Chroma矢量存储中，然后返回矢量存储的检索器

    Args: 
    documents：一个LangChain文档对象的列表
    chunk_size：每个文本块的大小
    chunk_overlap：连续块之间的重叠。
    
    return：一个LangChain检索器实例。
    """
    #1.分块
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    splits = text_splitter.split_documents(documents)

    # 2. 创建embeddings
    embeddings = OpenAIEmbeddings()

    # 3. 将块存储在vector存储库中
    # This creates an in-memory Chroma vector store.
    vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)

    # 4. 创建并返回一个 retriever
    retriever = vectorstore.as_retriever()

    return retriever


