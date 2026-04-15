"""
RAG Pipeline
Retrieval-Augmented Generation using Supabase pgvector
"""

import json
import hashlib
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
import numpy as np

from ..config import get_settings

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Production-grade RAG pipeline using Supabase pgvector for vector storage
    and Gemini embeddings for semantic search.
    Falls back to local JSON dataset if Supabase is unavailable.
    """
    
    # Table name for storing clause embeddings
    TABLE_NAME = "clause_embeddings"
    EMBEDDING_DIMENSION = 768  # Gemini embedding dimension
    
    def __init__(self):
        self.settings = get_settings()
        self.supabase = None
        self.genai = None
        self._use_local_fallback = False
        self._local_clauses: List[Dict[str, Any]] = []
        
        # Try to initialize Supabase client
        try:
            from supabase import create_client, Client
            self.supabase: Client = create_client(
                self.settings.SUPABASE_URL,
                self.settings.SUPABASE_ANON_KEY
            )
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.warning(f"Supabase initialization failed: {e}. Using local fallback.")
            self._use_local_fallback = True
            self._load_local_dataset()
        
        # Try to configure Gemini for embeddings
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.settings.GEMINI_API_KEY)
            self.genai = genai
            logger.info("Gemini configured for embeddings")
        except Exception as e:
            logger.warning(f"Gemini embedding initialization failed: {e}")
        
        # Local cache for embeddings
        self.embedding_cache: Dict[str, List[float]] = {}
        self.cache_dir = Path(self.settings.CACHE_DIR) / "embeddings"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema
        self._initialized = False
    
    def _load_local_dataset(self):
        """Load local JSON dataset as fallback"""
        try:
            dataset_path = Path(__file__).parent.parent.parent / "data" / "clause_dataset.json"
            if dataset_path.exists():
                with open(dataset_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._local_clauses = data.get('clauses', [])
                logger.info(f"Loaded {len(self._local_clauses)} clauses from local dataset")
            else:
                logger.warning(f"Local dataset not found at {dataset_path}")
        except Exception as e:
            logger.error(f"Failed to load local dataset: {e}")
    
    async def initialize(self) -> None:
        """Initialize the database schema if not exists"""
        if self._initialized or self._use_local_fallback:
            self._initialized = True
            return
            
        try:
            # Check if table exists by attempting a simple query
            result = self.supabase.table(self.TABLE_NAME).select("id").limit(1).execute()
            logger.info(f"RAG pipeline connected to table: {self.TABLE_NAME}")
            self._initialized = True
        except Exception as e:
            logger.warning(f"Table may not exist, attempting to create: {e}")
            await self._create_table()
            self._initialized = True
    
    async def _create_table(self) -> None:
        """
        Create the clause_embeddings table with pgvector extension.
        Note: This requires the pgvector extension to be enabled in Supabase.
        """
        # SQL to create table - this should be run via Supabase dashboard or migration
        create_sql = """
        -- Enable pgvector extension (run in Supabase SQL editor)
        create extension if not exists vector;
        
        -- Create clause embeddings table
        create table if not exists clause_embeddings (
            id text primary key,
            clause_text text not null,
            clause_type text not null,
            risk_level text not null,
            issue text,
            recommendation text,
            negotiation_hint text,
            embedding vector(768),
            created_at timestamp with time zone default timezone('utc'::text, now())
        );
        
        -- Create index for vector similarity search
        create index if not exists clause_embeddings_embedding_idx 
        on clause_embeddings 
        using ivfflat (embedding vector_cosine_ops)
        with (lists = 100);
        """
        
        logger.info("Table creation SQL prepared. Please run in Supabase SQL editor if table doesn't exist.")
        logger.info(create_sql)
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(text.encode()).hexdigest()
    
    async def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from cache"""
        cache_key = self._get_cache_key(text)
        
        # Check memory cache
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
        
        # Check file cache
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    embedding = json.load(f)
                self.embedding_cache[cache_key] = embedding
                return embedding
            except Exception:
                pass
        
        return None
    
    async def _save_embedding_to_cache(self, text: str, embedding: List[float]) -> None:
        """Save embedding to cache"""
        cache_key = self._get_cache_key(text)
        
        # Memory cache
        self.embedding_cache[cache_key] = embedding
        
        # File cache
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(embedding, f)
        except Exception as e:
            logger.warning(f"Failed to save embedding to cache: {e}")
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text using Gemini.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        # Check cache first
        cached = await self._get_cached_embedding(text)
        if cached:
            return cached
        
        try:
            # Truncate text to reasonable length
            text = text[:8000]  # Gemini has token limits
            
            # Generate embedding using Gemini
            result = await asyncio.to_thread(
                genai.embed_content,
                model=self.settings.EMBEDDING_MODEL,
                content=text,
                task_type="retrieval_document"
            )
            
            embedding = result['embedding']
            
            # Cache the result
            await self._save_embedding_to_cache(text, embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * self.EMBEDDING_DIMENSION
    
    async def embed_texts_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        for text in texts:
            embedding = await self.embed_text(text)
            embeddings.append(embedding)
        
        return embeddings
    
    async def add_clause(
        self,
        clause_text: str,
        clause_type: str,
        risk_level: str,
        issue: str = "",
        recommendation: str = "",
        negotiation_hint: str = "",
        clause_id: str = None
    ) -> str:
        """
        Add a clause to the vector database.
        
        Returns:
            Clause ID
        """
        await self.initialize()
        
        # Generate ID if not provided
        if not clause_id:
            clause_id = self._get_cache_key(clause_text)
        
        # Generate embedding
        embedding = await self.embed_text(clause_text)
        
        # Insert into Supabase
        try:
            data = {
                "id": clause_id,
                "clause_text": clause_text,
                "clause_type": clause_type,
                "risk_level": risk_level,
                "issue": issue,
                "recommendation": recommendation,
                "negotiation_hint": negotiation_hint,
                "embedding": embedding
            }
            
            result = self.supabase.table(self.TABLE_NAME).upsert(data).execute()
            
            logger.info(f"Added clause to RAG database: {clause_id[:16]}...")
            return clause_id
            
        except Exception as e:
            logger.error(f"Failed to add clause to database: {e}")
            raise
    
    async def add_clauses_batch(self, clauses: List[Dict[str, Any]]) -> List[str]:
        """
        Add multiple clauses to the database in batch.
        
        Args:
            clauses: List of clause dictionaries with required fields
            
        Returns:
            List of clause IDs
        """
        await self.initialize()
        
        ids = []
        
        # Generate embeddings for all clauses
        texts = [c.get('clause_text', '') for c in clauses]
        embeddings = await self.embed_texts_batch(texts)
        
        # Prepare batch data
        batch_data = []
        for clause, embedding in zip(clauses, embeddings):
            clause_id = clause.get('id') or self._get_cache_key(clause['clause_text'])
            ids.append(clause_id)
            
            batch_data.append({
                "id": clause_id,
                "clause_text": clause.get('clause_text', ''),
                "clause_type": clause.get('clause_type', 'unknown'),
                "risk_level": clause.get('risk_level', 'medium'),
                "issue": clause.get('issue', ''),
                "recommendation": clause.get('recommendation', ''),
                "negotiation_hint": clause.get('negotiation_hint', ''),
                "embedding": embedding
            })
        
        # Batch insert
        try:
            # Supabase batch insert
            batch_size = 100
            for i in range(0, len(batch_data), batch_size):
                batch = batch_data[i:i + batch_size]
                self.supabase.table(self.TABLE_NAME).upsert(batch).execute()
            
            logger.info(f"Added {len(ids)} clauses to RAG database")
            
        except Exception as e:
            logger.error(f"Failed to batch add clauses: {e}")
            raise
        
        return ids
    
    async def retrieve_similar(
        self,
        query_text: str,
        top_k: int = None,
        threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar clauses using vector similarity search.
        
        Args:
            query_text: Query text to find similar clauses for
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of similar clauses with metadata
        """
        await self.initialize()
        
        top_k = top_k or self.settings.TOP_K_RETRIEVAL
        threshold = threshold or self.settings.SIMILARITY_THRESHOLD
        
        # Use local fallback if Supabase is not available
        if self._use_local_fallback:
            return self._local_keyword_search(query_text, top_k)
        
        # Generate query embedding
        query_embedding = await self.embed_text(query_text)
        
        try:
            # Use Supabase RPC for vector similarity search
            # This requires a function to be created in Supabase
            result = self.supabase.rpc(
                'match_clauses',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': threshold,
                    'match_count': top_k
                }
            ).execute()
            
            if result.data:
                return [
                    {
                        'clause_text': r['clause_text'],
                        'clause_type': r['clause_type'],
                        'risk_level': r['risk_level'],
                        'issue': r['issue'],
                        'recommendation': r['recommendation'],
                        'negotiation_hint': r['negotiation_hint'],
                        'similarity_score': r.get('similarity', 0.0)
                    }
                    for r in result.data
                ]
            
            return []
            
        except Exception as e:
            logger.warning(f"Vector search failed, falling back to text search: {e}")
            return self._local_keyword_search(query_text, top_k)
    
    def _local_keyword_search(
        self,
        query_text: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Search local dataset using keyword matching"""
        if not self._local_clauses:
            return []
        
        query_lower = query_text.lower()
        keywords = query_lower.split()[:10]
        
        scored_results = []
        for clause in self._local_clauses:
            clause_text = clause.get('clause_text', '').lower()
            # Simple keyword matching score
            score = sum(1 for kw in keywords if kw in clause_text)
            if score > 0:
                scored_results.append((score, clause))
        
        # Sort by score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Return top_k results
        return [
            {
                'clause_text': c.get('clause_text', ''),
                'clause_type': c.get('clause_type', 'unknown'),
                'risk_level': c.get('risk_level', 'medium'),
                'issue': c.get('issue', ''),
                'recommendation': c.get('recommendation', ''),
                'negotiation_hint': c.get('negotiation_hint', ''),
                'similarity_score': score / max(len(keywords), 1)
            }
            for score, c in scored_results[:top_k]
        ]
    async def retrieve_for_clauses(
        self,
        clauses: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve similar clauses for multiple input clauses.
        
        Args:
            clauses: List of clauses with 'id' and 'text' fields
            
        Returns:
            Dictionary mapping clause_id to list of similar clauses
        """
        results = {}
        
        for clause in clauses:
            clause_id = clause.get('id', '')
            clause_text = clause.get('text', '')
            
            if clause_text:
                similar = await self.retrieve_similar(clause_text)
                results[clause_id] = similar
        
        return results
    
    async def load_dataset(self, dataset_path: str) -> int:
        """
        Load clause dataset from JSON file into vector database.
        
        Args:
            dataset_path: Path to JSON dataset file
            
        Returns:
            Number of clauses loaded
        """
        try:
            with open(dataset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                clauses = data.get('clauses', [])
            else:
                clauses = data
            
            if clauses:
                await self.add_clauses_batch(clauses)
                logger.info(f"Loaded {len(clauses)} clauses from dataset")
                return len(clauses)
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database"""
        try:
            result = self.supabase.table(self.TABLE_NAME)\
                .select("clause_type, risk_level", count="exact")\
                .execute()
            
            total = result.count or 0
            
            # Count by type
            type_counts = {}
            risk_counts = {}
            
            for row in result.data:
                ct = row.get('clause_type', 'unknown')
                rl = row.get('risk_level', 'unknown')
                type_counts[ct] = type_counts.get(ct, 0) + 1
                risk_counts[rl] = risk_counts.get(rl, 0) + 1
            
            return {
                'total_clauses': total,
                'by_type': type_counts,
                'by_risk': risk_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {'total_clauses': 0, 'by_type': {}, 'by_risk': {}}
