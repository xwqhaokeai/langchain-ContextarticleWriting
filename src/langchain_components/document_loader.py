import asyncio
from typing import List, Optional, Dict, Any
from langchain_community.document_loaders import PubMedLoader as LangchainPubmedLoader
from langchain_core.documents import Document
import aiohttp
import xml.etree.ElementTree as ET

class PubMedLoader(LangchainPubmedLoader):
    """
    扩展 Langchain 的 PubmedLoader 以支持异步加载和更灵活的元数据处理。
    """
    async def aload(self) -> List[Document]:
        return await asyncio.to_thread(self.load)

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
