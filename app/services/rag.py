# app/services/rag.py
import chromadb
from typing import List, Dict, Optional
import logging
import hashlib
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)

# Lazy load sentence-transformers for better startup performance
try:
    from sentence_transformers import SentenceTransformer
    USE_LOCAL_EMBEDDINGS = True
except ImportError:
    USE_LOCAL_EMBEDDINGS = False
    logger.warning("sentence-transformers not found - the RAG layer will use fallback hashing")

class PolicyStore:
    """Intelligent Policy Store using local sentence-transformer embeddings (no API dependency)"""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.model: Optional['SentenceTransformer'] = None
        
        if USE_LOCAL_EMBEDDINGS:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Local embedding model 'all-MiniLM-L6-v2' active")
            except Exception as e:
                logger.error(f"Failed to load sentence-transformers: {e}")
        
        # Create robust embedding wrapper
        class UniversalEmbeddingFunction:
            def __init__(self, parent):
                self.parent = parent
            
            def __call__(self, input: List[str]) -> List[List[float]]:
                if self.parent.model:
                    # High quality local embeddings
                    embeddings = self.parent.model.encode(input)
                    return embeddings.tolist()
                else:
                    # Determinstic hashing fallback
                    return [self.parent._hash_embedding(text) for text in input]
        
        self.collection = self.client.get_or_create_collection(
            name="policies",
            embedding_function=UniversalEmbeddingFunction(self)
        )
        
        count = self.collection.count()
        if count < 3:
            # Either brand new or a stale/partial previous initialization — reload policies
            if count > 0:
                logger.warning(f"Stale policy store detected ({count} chunks) — clearing and re-initializing")
                self.client.delete_collection("policies")
                self.collection = self.client.get_or_create_collection(
                    name="policies",
                    embedding_function=UniversalEmbeddingFunction(self)
                )
            self._initialize_policies()
        
        # In-memory cache for repeated identical queries
        self._query_cache: dict = {}
    
    def _hash_embedding(self, text: str, dim: int = 384) -> List[float]:
        """Generate static embedding from SHA-256 hash for deterministic retrieval without a model"""
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        embedding = []
        for i in range(dim):
            byte_val = hash_bytes[i % len(hash_bytes)]
            embedding.append(float(byte_val) / 255.0)
        
        return embedding
    
    def _initialize_policies(self):
        """Index classification policy documents"""
        policy_path = Path(__file__).parent.parent / "policies" / "classification_policies.md"
        
        if not policy_path.exists():
            logger.warning(f"No policy document found at {policy_path}")
            return
        
        try:
            with open(policy_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            sections = self._split_policy_blocks(content)
            for i, section in enumerate(sections):
                chunks = self._create_retrieval_units(section['text'], section['title'])
                for j, chunk in enumerate(chunks):
                    self.collection.add(
                        documents=[chunk],
                        ids=[f"p_{i}_{j}"],
                        metadatas=[{
                            "section": section['title'],
                            "category": self._infer_category(section['title']),
                            "chunk_id": j
                        }]
                    )
            
            logger.info(f"Policy store initialized with {self.collection.count()} chunks")
        except Exception as e:
            logger.error(f"Failed to bootstrap policy store: {e}")
    
    def _split_policy_blocks(self, content: str) -> List[Dict]:
        """Divide policy MD into titled blocks"""
        sections = []
        current = {"title": "General", "text": ""}
        for line in content.split('\n'):
            if line.startswith('## '):
                if current['text'].strip(): sections.append(current)
                current = {"title": line[3:].strip(), "text": ""}
            else:
                current['text'] += line + '\n'
        if current['text'].strip(): sections.append(current)
        return sections
    
    def _create_retrieval_units(self, text: str, title: str) -> List[str]:
        """Chunk policies with configurable overlap"""
        paras = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        if not paras:
            return []
        
        units = []
        i = 0
        
        while i < len(paras):
            current = []
            current_len = 0
            start_idx = i
            
            # Add overlap from previous chunk if configured
            overlap_text = ""
            if i > 0 and settings.chunk_overlap > 0 and units:
                # Get previous chunk content
                prev_chunk = units[-1]
                if ']\n' in prev_chunk:
                    prev_content = prev_chunk.split(']\n', 1)[1]
                else:
                    prev_content = prev_chunk
                
                # Take last chunk_overlap characters
                overlap_chars = min(settings.chunk_overlap, len(prev_content))
                if overlap_chars > 0:
                    overlap_text = prev_content[-overlap_chars:]
                    # Optional: trim to last paragraph for cleaner overlap
                    last_break = overlap_text.rfind('\n\n')
                    if last_break > len(overlap_text) // 2:
                        overlap_text = overlap_text[last_break + 2:]
                    
                    if overlap_text.strip():
                        current.append(overlap_text.strip())
                        current_len += len(overlap_text)
            
            # Add new paragraphs
            for j in range(start_idx, len(paras)):
                para_len = len(paras[j])
                if current_len + para_len > settings.chunk_size and current:
                    break
                current.append(paras[j])
                current_len += para_len
            
            if current:
                units.append(f"[{title}]\n" + "\n\n".join(current))
            
            # Move forward by number of new paragraphs (not overlap paragraphs)
            # Count only paragraphs that were NOT part of the overlap
            new_paras_added = len([p for p in current if p not in ([overlap_text.strip()] if overlap_text.strip() else [])])
            i += max(1, new_paras_added)
        
        return units
    
    def _infer_category(self, title: str) -> str:
        t = title.lower()
        for cat in ['cashback', 'adult', 'gambling', 'agency', 'scam', 'ecommerce']:
            if cat in t: return cat
        return 'general'
    
    def retrieve_relevant_policies(self, query: str, top_k: int = None) -> tuple[str, List[Dict]]:
        """Perform semantic search for policies relevant to the classification query"""
        top_k = top_k or settings.top_k_policies
        
        # Check in-memory cache first for speed
        cache_key = f"{query[:80]}_{top_k}"
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            payloads = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    payloads.append({
                        "text": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "relevance": 1 - results['distances'][0][i] if results['distances'] else 0
                    })
            
            # Limit each policy chunk to 500 chars to keep LLM context lean
            formatted = "\n\n---\n\n".join([f"[{p['metadata'].get('section')}]\n{p['text'][:500]}" for p in payloads])
            result = (formatted, payloads)
            
            # Cache (LRU-style: evict oldest when over 50 entries)
            if len(self._query_cache) > 50:
                self._query_cache.pop(next(iter(self._query_cache)))
            self._query_cache[cache_key] = result
            
            return result
        except Exception as e:
            logger.error(f"RAG retrieval failure: {e}")
            return "", []
    
    def add_policy(self, section_title: str, policy_text: str) -> int:
        """Dynamically add a new policy chunk to the store and clear the query cache"""
        chunks = self._create_retrieval_units(policy_text, section_title)
        current_count = self.collection.count()
        
        for j, chunk in enumerate(chunks):
            chunk_id = f"dynamic_{current_count}_{j}"
            self.collection.add(
                documents=[chunk],
                ids=[chunk_id],
                metadatas=[{
                    "section": section_title,
                    "category": self._infer_category(section_title),
                    "chunk_id": j,
                    "source": "dynamic"
                }]
            )
        
        self._query_cache.clear()  # Invalidate cache so new policy is picked up
        logger.info(f"Added {len(chunks)} chunks for section '{section_title}'")
        return self.collection.count()
    
    def force_reload(self) -> int:
        """Wipe existing collection and reload from the markdown policy file"""
        try:
            self.client.delete_collection("policies")
        except Exception:
            pass
        
        from sentence_transformers import SentenceTransformer as _ST
        
        class _EF:
            def __init__(self, parent):
                self.parent = parent
            def __call__(self, input):
                if self.parent.model:
                    return self.parent.model.encode(input).tolist()
                return [self.parent._hash_embedding(t) for t in input]
        
        self.collection = self.client.get_or_create_collection(
            name="policies",
            embedding_function=_EF(self)
        )
        self._query_cache.clear()
        self._initialize_policies()
        logger.info(f"Force-reloaded policy store: {self.collection.count()} chunks")
        return self.collection.count()
    
    def clear_cache(self):
        """Flush the in-memory query cache"""
        self._query_cache.clear()

