import asyncio
from typing import List, Optional, Dict, Any
from langchain_community.document_loaders import PubMedLoader as LangchainPubmedLoader
from langchain_core.documents import Document
import aiohttp
import xml.etree.ElementTree as ET

class PubMedLoader:
    """
    A custom async-native loader for PubMed articles.
    """
    def __init__(self, query: str, max_results: int = 5):
        self.query = query
        self.max_results = max_results
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    async def _fetch_ids(self, session: aiohttp.ClientSession) -> List[str]:
        search_url = f"{self.base_url}esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": self.query,
            "retmax": self.max_results,
            "usehistory": "y",
            "format": "json"
        }
        async with session.get(search_url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get("esearchresult", {}).get("idlist", [])

    async def _fetch_abstracts(self, session: aiohttp.ClientSession, pubmed_ids: List[str]) -> List[Dict[str, Any]]:
        if not pubmed_ids:
            return []
        fetch_url = f"{self.base_url}efetch.fcgi"
        params = {"db": "pubmed", "id": ",".join(pubmed_ids), "rettype": "xml"}
        async with session.get(fetch_url, params=params) as response:
            response.raise_for_status()
            xml_text = await response.text()
            articles = []
            try:
                root = ET.fromstring(xml_text)
                for article in root.findall(".//PubmedArticle"):
                    pmid_node = article.find(".//PMID")
                    pmid = pmid_node.text if pmid_node is not None else ""
                    
                    title_node = article.find(".//ArticleTitle")
                    title = title_node.text if title_node is not None else "No title available"
                    
                    abstract_node = article.find(".//Abstract/AbstractText")
                    abstract = abstract_node.text if abstract_node is not None else "No abstract available"
                    
                    articles.append({
                        "pmid": pmid,
                        "title": title,
                        "abstract": abstract,
                    })
            except ET.ParseError:
                pass  # Handle XML parsing errors gracefully
            return articles

    async def aload(self) -> List[Document]:
        docs = []
        async with aiohttp.ClientSession() as session:
            ids = await self._fetch_ids(session)
            if not ids:
                return []
            
            articles_data = await self._fetch_abstracts(session, ids)
            
            for article in articles_data:
                metadata = {
                    "source": f"https://pubmed.ncbi.nlm.nih.gov/{article['pmid']}/",
                    "title": article['title'],
                }
                docs.append(Document(page_content=article['abstract'], metadata=metadata))
        return docs

class PMCLoader:
    """
    从 PubMed Central (PMC) 加载文档的加载器。
    PMC 提供免费的全文生物医学和生命科学期刊文献。
    """
    def __init__(self, query: str, max_results: int = 5):
        self.query = query
        self.max_results = max_results
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    async def _fetch_ids(self, session: aiohttp.ClientSession) -> List[str]:
        search_url = f"{self.base_url}esearch.fcgi"
        params = {
            "db": "pmc",
            "term": self.query,
            "retmax": self.max_results,
            "usehistory": "y",
            "format": "json"
        }
        async with session.get(search_url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            return data.get("esearchresult", {}).get("idlist", [])

    async def _fetch_full_text(self, session: aiohttp.ClientSession, pmc_id: str) -> Optional[str]:
        fetch_url = f"{self.base_url}efetch.fcgi"
        params = {"db": "pmc", "id": pmc_id, "rettype": "xml"}
        async with session.get(fetch_url, params=params) as response:
            if response.status != 200:
                return None
            xml_text = await response.text()
            try:
                root = ET.fromstring(xml_text)
                # 提取正文段落
                body_text = " ".join([p.text for p in root.findall(".//body//p") if p.text])
                return body_text
            except ET.ParseError:
                return None

    async def aload(self) -> List[Document]:
        docs = []
        async with aiohttp.ClientSession() as session:
            ids = await self._fetch_ids(session)
            if not ids:
                return []
            
            tasks = [self._fetch_full_text(session, pmc_id) for pmc_id in ids]
            results = await asyncio.gather(*tasks)

            for pmc_id, text_content in zip(ids, results):
                if text_content:
                    metadata = {
                        "source": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/",
                        "pmc_id": pmc_id
                    }
                    docs.append(Document(page_content=text_content, metadata=metadata))
        return docs
