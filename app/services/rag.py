# app/services/rag.py - Updated for chromadb 0.4.22 compatibility
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict
import logging
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)

class PolicyStore:
    """Vector database for classification policies"""
    
    def __init__(self):
        # ChromaDB 0.4.22 uses PersistentClient
        self.client = chromadb.PersistentClient(path="./chroma_db")
        
        # Use appropriate embedding function
        if settings.llm_provider == "openai":
            self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=settings.openai_api_key,
                model_name="text-embedding-ada-002"
            )
        else:
            # For Ollama, create custom embedding function using a dedicated embedding model
            self.embedding_fn = self._create_ollama_embedding_function()
        
        # Get or create collection (chromadb 0.4.22 syntax)
        self.collection = self.client.get_or_create_collection(
            name="policies",
            embedding_function=self.embedding_fn
        )
        
        # Initialize with policies if empty
        if self.collection.count() == 0:
            self._initialize_policies()
    
    def _create_ollama_embedding_function(self):
        """Create embedding function for Ollama using dedicated embedding model"""
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
                        logger.error(f"Ollama embedding failed for model {self.model}: {e}")
                        # Fallback to dummy embedding
                        import hashlib
                        hash_val = hashlib.md5(text.encode()).hexdigest()
                        emb = [int(hash_val[i:i+2], 16) / 255.0 for i in range(0, min(20, len(hash_val)), 2)]
                        embeddings.append(emb)
                return embeddings
        
        return OllamaEmbeddingFunction(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embedding_model  # Use dedicated model like nomic-embed-text
        )
    
    def _initialize_policies(self):
        """Load policy documents from markdown file"""
        policy_path = Path(__file__).parent.parent / "policies" / "classification_policies.md"
        
        if not policy_path.exists():
            logger.warning(f"Policy file not found at {policy_path}")
            return
        
        with open(policy_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into sections
        sections = self._split_policy_sections(content)
        
        for i, section in enumerate(sections):
            # Create chunks
            chunks = self._create_retrieval_units(section['text'], section['title'])
            
            for j, chunk in enumerate(chunks):
                chunk_id = f"policy_{i}_{j}_{settings.llm_provider}"
                self.collection.add(
                    documents=[chunk],
                    ids=[chunk_id],
                    metadatas=[{
                        "section": section['title'],
                        "category": self._extract_category(section['title']),
                        "chunk_index": j,
                        "provider": settings.llm_provider
                    }]
                )
        
        logger.info(f"Initialized policy store with {self.collection.count()} chunks using {settings.llm_provider}")
    
    def _split_policy_sections(self, content: str) -> List[Dict]:
        """Split markdown into sections"""
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
        """Create retrieval units"""
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
        """Extract policy category"""
        title_lower = title.lower()
        
        categories = ['cashback', 'adult', 'gambling', 'agency', 'scam', 'legitimate', 'ecommerce']
        
        for category in categories:
            if category in title_lower:
                return category
        
        return 'general'
    
    def retrieve_relevant_policies(self, query: str, top_k: int = None) -> tuple[str, List[Dict]]:
        """Retrieve relevant policies"""
        top_k = top_k or settings.top_k_policies
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            policies = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    policies.append({
                        "text": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "relevance_score": 1 - results['distances'][0][i] if results['distances'] else 0.5
                    })
            
            # Format policies
            formatted = []
            for p in policies:
                category = p['metadata'].get('category', 'general')
                formatted.append(f"[{category}]\n{p['text']}")
            
            return "\n\n---\n\n".join(formatted), policies
            
        except Exception as e:
            logger.error(f"Error retrieving policies: {e}")
            return "", []
