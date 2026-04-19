from rank_bm25 import BM25Okapi
from ..db.neo4j_driver import get_neo4j_driver as get_driver
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import string

# Download necessary NLTK data
try:
    stopwords.words('english')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')

class KeywordSearch:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KeywordSearch, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.initialized = True
        self.documents = []
        self.bm25 = None
        self.stop_words = set(stopwords.words('english'))
        self.punctuation = set(string.punctuation)

    def _preprocess_text(self, text):
        if not text:
            return []
        # Tokenize, remove stop words and punctuation, and lowercase
        tokens = word_tokenize(text.lower())
        return [token for token in tokens if token not in self.stop_words and token not in self.punctuation]

    async def index_documents(self):
        """
        Fetches documents from Neo4j and builds the BM25 index.
        A document is the combined text of a symbol's name, docstring, and code.
        """
        driver = get_driver()
        async with driver.session() as session:
            # Fetch functions and classes from the graph
            result = await session.run("""
                MATCH (s:Function)
                RETURN s.name AS name, s.docstring AS docstring, s.code_content AS code
                UNION
                MATCH (s:Class)
                RETURN s.name AS name, s.docstring AS docstring, s.code_content AS code
            """)
            
            records = await result.data()
            
        self.documents = [
            {
                "name": record["name"],
                "docstring": record["docstring"],
                "code": record["code"],
                "combined_text": f"{record['name']} {record.get('docstring', '')} {record.get('code', '')}"
            }
            for record in records
        ]
        
        tokenized_corpus = [self._preprocess_text(doc["combined_text"]) for doc in self.documents]
        
        if not tokenized_corpus:
            self.bm25 = None
            return

        self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, limit: int = 10):
        """
        Performs a keyword search against the indexed documents.
        """
        if not self.bm25:
            return []
            
        tokenized_query = self._preprocess_text(query)
        doc_scores = self.bm25.get_scores(tokenized_query)
        
        # Get top N document indices
        top_n_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)[:limit]
        
        results = []
        for i in top_n_indices:
            results.append({
                "name": self.documents[i]["name"],
                "score": doc_scores[i],
                "docstring": self.documents[i]["docstring"],
            })
            
        return results

# Singleton instance
keyword_search_instance = KeywordSearch()
