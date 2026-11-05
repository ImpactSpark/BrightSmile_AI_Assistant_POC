from app.services.rag.pubmed_client import PubMedClient

SAMPLE_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345</PMID>
      <Article>
        <ArticleTitle>Dental caries management outcomes</ArticleTitle>
        <Abstract>
          <AbstractText>Caries lesions respond well to fluoride treatment.</AbstractText>
        </Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""


def test_parse_efetch_xml_extracts_documents():
    docs = PubMedClient._parse_efetch_xml(SAMPLE_XML)
    assert len(docs) == 1
    doc = docs[0]
    assert doc.pmid == "12345"
    assert doc.title == "Dental caries management outcomes"
    assert "fluoride" in doc.abstract
    assert doc.source == "PubMed:12345"
    assert doc.url == "https://pubmed.ncbi.nlm.nih.gov/12345/"


def test_parse_efetch_xml_empty_returns_no_documents():
    docs = PubMedClient._parse_efetch_xml("<PubmedArticleSet></PubmedArticleSet>")
    assert docs == []
