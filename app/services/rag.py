# app/services/rag.py
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict
import json
import logging
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)

class PolicyStore:
    """Vector database for classification policies - dynamically updatable"""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name="text-embedding-ada-002"
        )
        
        self.collection = self.client.get_or_create_collection(
            name="policies",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize with policies if empty
        if self.collection.count() == 0:
            self._initialize_policies()
    
    def _initialize_policies(self):
        """Load policy documents from markdown file"""
        policy_path = Path(__file__).parent.parent / "policies" / "classification_policies.md"
        
        with open(policy_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into policy sections
        sections = self._split_policy_sections(content)
        
        for i, section in enumerate(sections):
            # Create multiple retrieval units per section
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
                        "total_chunks": len(chunks)
                    }]
                )
        
        logger.info(f"Initialized policy store with {self.collection.count()} retrieval units")
    
    def _split_policy_sections(self, content: str) -> List[Dict]:
        """Split markdown into semantic sections"""
        sections = []
        current_section = {"title": "General Guidelines", "text": ""}
        
        for line in content.split('\n'):
            if line.startswith('## '):  # Major section header
                if current_section['text'].strip():
                    sections.append(current_section)
                current_section = {
                    "title": line[3:].strip(),
                    "text": ""
                }
            elif line.startswith('### '):  # Subsection
                # Keep as part of parent section
                current_section['text'] += line + '\n'
            else:
                current_section['text'] += line + '\n'
        
        if current_section['text'].strip():
            sections.append(current_section)
        
        return sections
    
    def _create_retrieval_units(self, text: str, section_title: str) -> List[str]:
        """Create optimal retrieval units - each self-contained and meaningful"""
        
        # Split by paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        retrieval_units = []
        current_unit = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            
            # If this paragraph would make unit too large, save current and start new
            if current_length + para_length > settings.chunk_size and current_unit:
                retrieval_units.append('\n\n'.join(current_unit))
                current_unit = [para]
                current_length = para_length
            else:
                current_unit.append(para)
                current_length += para_length
        
        # Add the last unit
        if current_unit:
            retrieval_units.append('\n\n'.join(current_unit))
        
        # Ensure each unit has context about its section
        units_with_context = []
        for unit in retrieval_units:
            contextualized = f"[SECTION: {section_title}]\n\n{unit}"
            units_with_context.append(contextualized)
        
        return units_with_context
    
    def _extract_category(self, title: str) -> str:
        """Extract policy category from section title"""
        title_lower = title.lower()
        
        # Dynamic category detection - no hardcoded mapping
        categories = [
            'cashback', 'adult', 'gambling', 'agency', 'scam',
            'legitimate', 'ecommerce', 'blog', 'news'
        ]
        
        for category in categories:
            if category in title_lower:
                return category
        
        return 'general'
    
    def retrieve_relevant_policies(self, query: str, top_k: int = None) -> tuple[str, List[Dict]]:
        """Retrieve relevant policy units for a given query"""
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
            
            # Format policies with context
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
        """Dynamically add new policy to store"""
        chunks = self._create_retrieval_units(policy_text, section_title)
        
        for j, chunk in enumerate(chunks):
            chunk_id = f"custom_{section_title}_{j}_{hash(chunk)}"
            self.collection.add(
                documents=[chunk],
                ids=[chunk_id],
                metadatas=[{
                    "section": section_title,
                    "category": self._extract_category(section_title),
                    "custom": True
                }]
            )
        
        logger.info(f"Added new policy section: {section_title}")
