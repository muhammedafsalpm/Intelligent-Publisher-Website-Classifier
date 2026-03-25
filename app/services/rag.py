import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict
import json
import logging
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)

class PolicyStore:
    """Vector database for classification policies with provider support"""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        
        # Use appropriate embedding function based on provider
        if settings.llm_provider == "openai":
            self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=settings.openai_api_key,
                model_name="text-embedding-ada-002"
            )
        else:
            # For Ollama, we'll use a custom embedding function
            self.embedding_fn = self._create_ollama_embedding_function()
        
        self.collection = self.client.get_or_create_collection(
            name="policies",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize with policies if empty
        if self.collection.count() == 0:
            self._initialize_policies()
    
    def _create_ollama_embedding_function(self):
        """Create embedding function for Ollama"""
        class OllamaEmbeddingFunction:
            def __init__(self, base_url, model):
                self.base_url = base_url
                self.model = model
                import httpx
                self.client = httpx.Client(timeout=30.0)
            
            def __call__(self, input):
                """Generate embeddings for input texts"""
                embeddings = []
                for text in input:
                    try:
                        response = self.client.post(
                            f"{self.base_url}/api/embeddings",
                            json={"model": self.model, "prompt": text}
                        )
                        result = response.json()
                        embeddings.append(result.get("embedding", []))
                    except Exception as e:
                        logger.error(f"Ollama embedding failed: {e}")
                        # Fallback to dummy embedding
                        import hashlib
                        hash_val = hashlib.md5(text.encode()).hexdigest()
                        emb = [int(hash_val[i:i+2], 16) / 255.0 for i in range(0, min(20, len(hash_val)), 2)]
                        embeddings.append(emb)
                return embeddings
        
        return OllamaEmbeddingFunction(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model
        )
    
    def _initialize_policies(self):
        """Load policy documents from markdown file"""
        policy_path = Path(__file__).parent.parent / "policies" / "classification_policies.md"
        
        if not policy_path.exists():
            logger.error(f"Policy file not found at {policy_path}")
            return

        with open(policy_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        sections = self._split_policy_sections(content)
        
        for i, section in enumerate(sections):
            chunks = self._create_retrieval_units(section['text'], section['title'])
            
            for j, chunk in enumerate(chunks):
                chunk_id = f"policy_{i}_{j}"
                self.collection.add(
                    documents=[chunk],
                    ids=[chunk_id],
                    metadatas=[{
                        "section": section['title'],
                        "category": self._extract_category(section['title']),
                        "chunk_index": j,
                        "total_chunks": len(chunks),
                        "provider": settings.llm_provider
                    }]
                )
        
        logger.info(f"Initialized policy store with {self.collection.count()} retrieval units using {settings.llm_provider}")
    
    def _split_policy_sections(self, content: str) -> List[Dict]:
        """Split markdown into semantic sections"""
        sections = []
        current_section = {"title": "General Guidelines", "text": ""}
        
        for line in content.split('\n'):
            if line.startswith('## '):
                if current_section['text'].strip():
                    sections.append(current_section)
                current_section = {
                    "title": line[3:].strip(),
                    "text": ""
                }
            else:
                current_section['text'] += line + '\n'
        
        if current_section['text'].strip():
            sections.append(current_section)
        
        return sections
    
    def _create_retrieval_units(self, text: str, section_title: str) -> List[str]:
        """Create optimal retrieval units"""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        retrieval_units = []
        current_unit = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            
            if current_length + para_length > settings.chunk_size and current_unit:
                retrieval_units.append('\n\n'.join(current_unit))
                current_unit = [para]
                current_length = para_length
            else:
                current_unit.append(para)
                current_length += para_length
        
        if current_unit:
            retrieval_units.append('\n\n'.join(current_unit))
        
        # Add context
        units_with_context = []
        for unit in retrieval_units:
            contextualized = f"[SECTION: {section_title}]\n\n{unit}"
            units_with_context.append(contextualized)
        
        return units_with_context
    
    def _extract_category(self, title: str) -> str:
        """Extract policy category from section title"""
        title_lower = title.lower()
        
        categories = [
            'cashback', 'adult', 'gambling', 'agency', 'scam',
            'legitimate', 'ecommerce', 'blog', 'news'
        ]
        
        for category in categories:
            if category in title_lower:
                return category
        
        return 'general'
    
    def retrieve_relevant_policies(self, query: str, top_k: int = None) -> tuple[str, List[Dict]]:
        """Retrieve relevant policy units"""
        top_k = top_k or settings.top_k_policies
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            policies = []
            for i, doc in enumerate(results['documents'][0]):
                policies.append({
                    "text": doc,
                    "metadata": results['metadatas'][0][i],
                    "relevance_score": 1 - results['distances'][0][i]
                })
            
            formatted = []
            for p in policies:
                formatted.append(
                    f"[{p['metadata']['section']}] "
                    f"(relevance: {p['relevance_score']:.2f})\n"
                    f"{p['text']}"
                )
            
            return "\n\n---\n\n".join(formatted), policies
            
        except Exception as e:
            logger.error(f"Error retrieving policies: {e}")
            return "", []
    
    def add_policy(self, section_title: str, policy_text: str):
        """Dynamically add new policy"""
        chunks = self._create_retrieval_units(policy_text, section_title)
        
        for j, chunk in enumerate(chunks):
            chunk_id = f"custom_{section_title}_{j}_{hash(chunk)}"
            self.collection.add(
                documents=[chunk],
                ids=[chunk_id],
                metadatas=[{
                    "section": section_title,
                    "category": self._extract_category(section_title),
                    "custom": True,
                    "provider": settings.llm_provider
                }]
            )
        
        logger.info(f"Added new policy section: {section_title}")
