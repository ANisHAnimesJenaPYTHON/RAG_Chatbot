"""RAG (Retrieval-Augmented Generation) Pipeline"""

import os
import uuid
from typing import List, Dict, Tuple, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from backend.config import settings


class RAGPipeline:
    """RAG pipeline for document retrieval and answer generation"""
    
    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self.embedding_model = None
        self.openai_client = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the RAG pipeline components"""
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chroma_db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize embedding model
        if settings.use_local_embeddings:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            # Will use OpenAI embeddings
            pass
        
        # Initialize OpenAI client if API key is provided
        if settings.openai_api_key:
            self.openai_client = OpenAI(api_key=settings.openai_api_key)
        else:
            self.openai_client = None
    
    def _get_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text"""
        if settings.use_local_embeddings and self.embedding_model:
            embedding = self.embedding_model.encode(text).tolist()
            return embedding
        elif self.openai_client:
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        else:
            raise Exception("No embedding model available")
    
    def add_document(self, document_id: str, document_name: str, content: str):
        """Add a document to the knowledge base - optimized for speed"""
        print(f"Processing document '{document_name}' ({len(content)} chars)...")
        
        # For small/medium documents, process as single chunk for speed
        # For large documents, use smart chunking
        if len(content) < 3000:
            # Small document - process as single chunk (FASTEST)
            print("Processing as single chunk for speed...")
            chunks = [content] if content.strip() else []
        else:
            # Medium/Large document - quick chunking
            print("Chunking document...")
            chunks = self._chunk_text(content)
            print(f"Split into {len(chunks)} chunks")
        
        if not chunks:
            print("Warning: Document has no content")
            return
        
        # Filter empty chunks
        valid_chunks = [chunk for chunk in chunks if chunk.strip()]
        if not valid_chunks:
            print("Warning: No valid chunks found")
            return
        
        print(f"Generating embeddings for {len(valid_chunks)} chunk(s)...")
        
        try:
            # FAST PATH: Batch encode ALL chunks at once (super fast!)
            if settings.use_local_embeddings and self.embedding_model:
                # Batch encode all chunks simultaneously - much faster!
                print("Batch encoding all chunks...")
                embeddings = self.embedding_model.encode(valid_chunks, show_progress_bar=False, batch_size=32, convert_to_numpy=True)
                if hasattr(embeddings, 'tolist'):
                    embeddings_list = embeddings.tolist()
                else:
                    embeddings_list = [emb.tolist() if hasattr(emb, 'tolist') else emb for emb in embeddings]
            else:
                # Fallback for OpenAI embeddings
                embeddings_list = [self._get_embeddings(chunk) for chunk in valid_chunks]
            
            # Prepare data for ChromaDB
            ids_to_add = [f"{document_id}_{i}" for i in range(len(valid_chunks))]
            metadatas_to_add = [{
                "document_id": document_id,
                "document_name": document_name,
                "chunk_index": i
            } for i in range(len(valid_chunks))]
            
            print(f"Storing {len(embeddings_list)} chunk(s) in vector database...")
            # Batch add to ChromaDB
            self.collection.add(
                embeddings=embeddings_list,
                documents=valid_chunks,
                metadatas=metadatas_to_add,
                ids=ids_to_add
            )
            print(f"✓ Successfully added '{document_name}' with {len(embeddings_list)} chunk(s)")
            
        except Exception as e:
            print(f"Error processing document: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _chunk_text(self, text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks - optimized for speed"""
        if len(text) <= chunk_size:
            return [text]
        
        # Fast chunking: simple split without complex boundary detection
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Simple sentence boundary detection (faster)
            if end < len(text):
                # Quick check for sentence end
                period_pos = text.rfind('. ', start, end)
                if period_pos == -1:
                    period_pos = text.rfind('.\n', start, end)
                if period_pos != -1:
                    end = period_pos + 2
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    def remove_document(self, document_id: str):
        """Remove a document from the knowledge base"""
        # Get all chunks for this document
        results = self.collection.get(
            where={"document_id": document_id}
        )
        
        if results and results['ids']:
            self.collection.delete(ids=results['ids'])
    
    def search(self, query: str, top_k: int = 5) -> Tuple[List[Dict], List[float]]:
        """Search for relevant document chunks"""
        if self.collection.count() == 0:
            return [], []
        
        # Generate query embedding
        query_embedding = self._get_embeddings(query)
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count())
        )
        
        # Extract results
        documents = []
        scores = []
        
        if results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                documents.append({
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else 0.0
                })
                scores.append(results['distances'][0][i] if results['distances'] else 0.0)
        
        return documents, scores
    
    def generate_response(
        self,
        query: str,
        retrieved_contexts: List[Dict],
        found_in_documents: bool
    ) -> str:
        """Generate response using LLM"""
        
        if self.openai_client:
            return self._generate_with_openai(query, retrieved_contexts, found_in_documents)
        else:
            return self._generate_simple_response(query, retrieved_contexts, found_in_documents)
    
    def _generate_with_openai(
        self,
        query: str,
        retrieved_contexts: List[Dict],
        found_in_documents: bool
    ) -> str:
        """Generate response using OpenAI"""
        
        # Build context from retrieved documents
        context_parts = []
        sources = []
        
        for ctx in retrieved_contexts:
            content = ctx['content']
            metadata = ctx.get('metadata', {})
            doc_name = metadata.get('document_name', 'Unknown')
            
            context_parts.append(content)
            if doc_name not in sources:
                sources.append(doc_name)
        
        context = "\n\n".join(context_parts)
        
        # Build prompt
        if found_in_documents and context:
            prompt = f"""You are a helpful assistant that answers questions based on the provided documents.

Context from user's documents:
{context}

Question: {query}

Answer the question based on the context provided. If the context doesn't fully answer the question, say so but provide the best answer you can from the context."""
        else:
            prompt = f"""The user asked: {query}

Note: The answer was not found in the user's documents. Please provide a helpful answer from your general knowledge."""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            # If OpenAI fails, fall back to simple response using retrieved contexts
            print(f"OpenAI API error: {str(e)}, using fallback response")
            return self._generate_simple_response(query, retrieved_contexts, found_in_documents)
    
    def _generate_simple_response(
        self,
        query: str,
        retrieved_contexts: List[Dict],
        found_in_documents: bool
    ) -> str:
        """Simple fallback response generation (without OpenAI)"""
        
        if found_in_documents and retrieved_contexts:
            # Combine multiple relevant contexts for better answer
            context_parts = []
            doc_content_map = {}  # Map doc_name to list of content chunks
            
            # Group content by document
            for ctx in retrieved_contexts[:5]:  # Use top 5 results
                content = ctx.get('content', '').strip()
                metadata = ctx.get('metadata', {})
                doc_name = metadata.get('document_name', 'Document')
                
                if content:
                    # Clean up the content (remove excessive whitespace, fix newlines)
                    content = ' '.join(content.split())
                    # Limit each chunk to avoid showing incomplete sentences
                    if len(content) > 500:
                        # Try to find a sentence break
                        last_period = content[:500].rfind('.')
                        if last_period > 300:
                            content = content[:last_period + 1] + "..."
                        else:
                            content = content[:500] + "..."
                    
                    # Group content by document
                    if doc_name not in doc_content_map:
                        doc_content_map[doc_name] = []
                    doc_content_map[doc_name].append(content)
            
            # Combine content from same document and create formatted sections
            all_content = []
            for doc_name, contents in doc_content_map.items():
                # Combine multiple chunks from same document intelligently
                combined_content = " ".join(contents[:3])  # Take first 3 chunks for better context
                all_content.append(combined_content)
            
            # Create a more natural, AI-like response
            combined_text = " ".join(all_content)
            
            # Clean and format the response to be more natural
            num_docs = len(doc_content_map)
            doc_names = list(doc_content_map.keys())
            
            # Generate a more natural response
            if query.lower().startswith(("what", "tell me", "explain", "describe")):
                if num_docs == 1:
                    response = f"Based on {doc_names[0]}, "
                else:
                    response = f"Based on your documents ({', '.join(doc_names)}), "
                
                # Extract key information and create a natural response
                response += self._create_natural_response(query, combined_text)
            else:
                # For other question types
                if num_docs == 1:
                    response = f"Based on {doc_names[0]}, here's what I found:\n\n"
                else:
                    response = f"Based on your documents, here's what I found:\n\n"
                
                # Limit response length but keep it natural
                if len(combined_text) > 1000:
                    # Find a good stopping point
                    cutoff = combined_text[:1000].rfind('.')
                    if cutoff > 700:
                        response += combined_text[:cutoff+1] + " For more details, please refer to the full documents."
                    else:
                        response += combined_text[:900] + "... For more details, please refer to the full documents."
                else:
                    response += combined_text
        else:
            if retrieved_contexts:
                # We have contexts but they're not very relevant
                best_context = retrieved_contexts[0].get('content', '')
                if best_context:
                    response = f"I found some information in your documents, though it may not directly answer '{query}':\n\n"
                    response += best_context[:600]
                    if len(best_context) > 600:
                        response += "..."
                else:
                    response = f"I couldn't find specific information about '{query}' in your selected documents."
            else:
                response = f"I couldn't find specific information about '{query}' in your selected documents. "
                response += "Please make sure you've added documents to the knowledge base first."
        
        return response
    
    def _create_natural_response(self, query: str, content: str) -> str:
        """Create a more natural, AI-like response from content"""
        # Extract key sentences and create a coherent response
        sentences = content.split('. ')
        
        # Take the most relevant sentences (first few usually have the main info)
        key_sentences = []
        seen_words = set()
        
        query_words = set(query.lower().split())
        
        for sentence in sentences[:15]:  # Check first 15 sentences
            sentence_lower = sentence.lower()
            # Check if sentence relates to query
            sentence_words = set(sentence_lower.split())
            relevance = len(query_words.intersection(sentence_words))
            
            if relevance > 0 or len(key_sentences) < 5:
                # Avoid repetition
                words_in_sentence = tuple(sorted(sentence_words))
                if words_in_sentence not in seen_words or len(key_sentences) < 3:
                    key_sentences.append(sentence.strip())
                    seen_words.add(words_in_sentence)
        
        if not key_sentences:
            # Fallback to first few sentences
            key_sentences = [s.strip() for s in sentences[:5] if s.strip()]
        
        # Combine into natural response
        if len(key_sentences) == 1:
            response = key_sentences[0]
        elif len(key_sentences) <= 3:
            response = ". ".join(key_sentences)
        else:
            response = ". ".join(key_sentences[:3]) + ". " + key_sentences[-1] if len(key_sentences) > 3 else ". ".join(key_sentences)
        
        # Ensure it ends properly
        if not response.endswith(('.', '!', '?')):
            response += "."
        
        # Limit length
        if len(response) > 800:
            cutoff = response[:800].rfind('.')
            if cutoff > 500:
                response = response[:cutoff+1]
            else:
                response = response[:750] + "..."
        
        return response
    
    def clear_all_documents(self):
        """Clear all documents from knowledge base"""
        try:
            if self.collection.count() > 0:
                # Get all IDs and delete
                all_results = self.collection.get()
                if all_results and all_results['ids']:
                    self.collection.delete(ids=all_results['ids'])
                print("Knowledge base cleared")
        except Exception as e:
            print(f"Error clearing knowledge base: {str(e)}")
    
    def get_knowledge_base_documents(self) -> List[Dict[str, str]]:
        """Get list of all documents in knowledge base"""
        if self.collection.count() == 0:
            return []
        
        # Get all unique documents
        all_results = self.collection.get()
        
        documents = {}
        if all_results and all_results['metadatas']:
            for metadata in all_results['metadatas']:
                doc_id = metadata.get('document_id')
                doc_name = metadata.get('document_name', 'Unknown')
                if doc_id and doc_id not in documents:
                    documents[doc_id] = doc_name
        
        return [{"id": doc_id, "name": doc_name} for doc_id, doc_name in documents.items()]

