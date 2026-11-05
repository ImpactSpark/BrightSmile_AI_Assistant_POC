import httpx

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


class PubMedDocument:
    def __init__(self, pmid: str, title: str, abstract: str):
        self.pmid = pmid
        self.title = title
        self.abstract = abstract

    @property
    def source(self) -> str:
        return f"PubMed:{self.pmid}"

    @property
    def url(self) -> str:
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"

    @property
    def text(self) -> str:
        return f"{self.title}\n\n{self.abstract}"


class PubMedClient:
    """Fetches open-access dental research via NCBI E-utilities, scoped by
    MeSH terms so the corpus stays relevant instead of general-dentistry
    firehose. Reuses the same chunking/embedding/ingestion pipeline as the
    ADA corpus -- tagged doc_type='pubmed' with lower trust weight."""

    def __init__(self, mesh_terms: list[str], max_results: int = 50):
        self._mesh_terms = mesh_terms
        self._max_results = max_results

    async def search_open_access(self) -> list[str]:
        query = " OR ".join(f'"{term}"[MeSH Terms]' for term in self._mesh_terms)
        query = f"({query}) AND open access[filter]"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                ESEARCH_URL,
                params={"db": "pubmed", "term": query, "retmax": self._max_results, "retmode": "json"},
            )
            resp.raise_for_status()
            return resp.json()["esearchresult"]["idlist"]

    async def fetch_documents(self, pmids: list[str]) -> list[PubMedDocument]:
        if not pmids:
            return []
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                EFETCH_URL,
                params={"db": "pubmed", "id": ",".join(pmids), "retmode": "xml", "rettype": "abstract"},
            )
            resp.raise_for_status()
            return self._parse_efetch_xml(resp.text)

    @staticmethod
    def _parse_efetch_xml(xml_text: str) -> list[PubMedDocument]:
        from xml.etree import ElementTree as ET

        root = ET.fromstring(xml_text)
        docs = []
        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            title_el = article.find(".//ArticleTitle")
            abstract_parts = article.findall(".//AbstractText")
            if pmid_el is None or title_el is None:
                continue
            abstract = " ".join(p.text or "" for p in abstract_parts)
            docs.append(
                PubMedDocument(pmid=pmid_el.text or "", title=title_el.text or "", abstract=abstract)
            )
        return docs
