# Skill: rag-knowledge-base

## Objective
Implement a Retrieval Augmented Generation (RAG) system to allow the AI to answer questions based on a custom knowledge base (e.g., financial docs, user's history).

## Context
Used to enhance the AI Assistant's knowledge of the user's specific context and general financial rules.

## Prerequisites
- Embedding model (e.g., OpenAI embeddings, HuggingFace).
- Vector Database (e.g., Pinecone, Chroma, pgvector).

## Execution Procedure
1. **Indexing**:
    - Chunk documents into manageable pieces.
    - Generate embeddings for each chunk.
    - Store embeddings and metadata in the vector DB.
2. **Retrieval**:
    - Embed the user's query.
    - Search the vector DB for the top-K most similar chunks.
3. **Augmentation**: Append the retrieved context to the prompt.
4. **Generation**: The LLM generates an answer based on the provided context.
5. **Evaluation**: Use a "Faithfulness" metric to ensure the answer is derived from the context.

## Technical Patterns
- Vector Search (Cosine Similarity).
- Hybrid Search (Keyword + Semantic).
- Reranking.

## Examples
- AI answering "What is my strategy for the emergency reserve?" by retrieving the user's "Planning Goals" document.

## Validation Criteria
- Relevant context is retrieved for relevant queries.
- AI cites the source of the information.
- Low hallucination rate for knowledge-base questions.

## Common Errors
- Poor chunking strategy leading to fragmented context.
- Using an embedding model that doesn't handle Portuguese financial terms well.

## Security Rules
- Ensure strict multi-tenancy: User A cannot retrieve chunks from User B's vector space.

## Deliverables
- Vector DB Configuration.
- Indexing Pipeline.
- Retrieval Logic.
