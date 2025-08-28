# simple_indexer.py - A simple in-memory alternative to ChromaDB
import os
import hashlib
from pathlib import Path
from sentence_transformers import SentenceTransformer
from ingest import find_docs
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Simple in-memory storage
class SimpleIndexer:
    def __init__(self):
        self.model = SentenceTransformer("paraphrase-MiniLM-L6-v2")
        self.embeddings = {}
        self.documents = {}
        self.metadatas = {}
        
    def index_repo(self, repo_url: str, repo_path: str):
        """Index documents from a repository."""
        docs = find_docs(repo_path)
        
        if not docs:
            print("[WARN] No documents found to index!")
            return False
            
        print(f"[DEBUG] Indexing repo: {repo_url}")
        print(f"[DEBUG] Found docs: {list(docs.keys())}")
        
        added = 0
        for fname, text in docs.items():
            print(f"[DEBUG] Processing file: {fname}")
            chunks = self.chunk_text(text)
            print(f"[DEBUG] Created {len(chunks)} chunks for {fname}")
            
            for chunk in chunks:
                chunk_id = self.make_chunk_id(repo_url, fname, chunk)
                print(f"[DEBUG] Processing chunk {chunk_id[:8]}... (length: {len(chunk)})")
                
                # Create embedding
                print(f"[DEBUG] Creating embedding for chunk {chunk_id[:8]}...")
                emb = self.model.encode(chunk).tolist()
                print(f"[DEBUG] Embedding created, length: {len(emb)}")
                
                # Store in memory
                self.embeddings[chunk_id] = emb
                self.documents[chunk_id] = chunk
                self.metadatas[chunk_id] = {"repo": repo_url, "path": fname.lower()}
                
                print(f"[DEBUG] Chunk {chunk_id[:8]} stored successfully")
                added += 1
        
        print(f"[DEBUG] Final index count: {len(self.documents)}")
        print(f"[INFO] Indexed {added} chunks for {repo_url}")
        return True
    
    def retrieve_docs(self, repo_url: str, query: str, top_k: int = 4):
        """Retrieve relevant documents for a query."""
        if not self.documents:
            print("[WARN] No documents indexed!")
            return []
        
        print(f"[DEBUG] Index has {len(self.documents)} documents")
        
        # Create query embedding
        query_emb = self.model.encode(query).tolist()
        print(f"[DEBUG] Query embedding length: {len(query_emb)}")
        
        # Calculate similarities
        similarities = []
        for chunk_id, emb in self.embeddings.items():
            # Filter by repository if specified
            if repo_url and self.metadatas[chunk_id]["repo"] != repo_url:
                continue
                
            similarity = cosine_similarity([query_emb], [emb])[0][0]
            similarities.append((similarity, chunk_id))
        
        # Sort by similarity and get top_k
        similarities.sort(reverse=True)
        top_results = similarities[:top_k]
        
        print(f"[DEBUG] Found {len(top_results)} relevant chunks")
        
        results = []
        for similarity, chunk_id in top_results:
            results.append({
                "text": self.documents[chunk_id],
                "metadata": self.metadatas[chunk_id],
                "similarity": float(similarity)
            })
        
        return results
    
    def chunk_text(self, text, max_chars=1000):
        """Split text into chunks."""
        paragraphs = text.split("\n\n")
        chunks, cur = [], ""
        for p in paragraphs:
            if len(cur) + len(p) > max_chars:
                if cur.strip():
                    chunks.append(cur.strip())
                cur = p
            else:
                cur += "\n\n" + p
        if cur.strip():
            chunks.append(cur.strip())
        return chunks
    
    def make_chunk_id(self, repo_url: str, file_path: str, chunk_text: str) -> str:
        """Create a unique ID for a chunk."""
        raw = f"{repo_url}|{file_path}|{chunk_text}".encode("utf-8")
        return hashlib.sha1(raw).hexdigest()

# Global instance
indexer = SimpleIndexer()

