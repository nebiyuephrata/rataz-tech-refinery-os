# Architecture Diagram

```mermaid
flowchart LR
    A[Document Input\nPDF/TXT/Upload] --> B{Extraction Triage\nConfig-Driven}
    B -->|OCR signal| C[Tesseract Adapter]
    B -->|Table signal| D[Camelot Adapter]
    B -->|Layout signal| E[Docling/MinerU Adapter]
    B -->|Default| F[Plain Text]

    C --> G[Extraction Result\nPydantic + Provenance]
    D --> G
    E --> G
    F --> G

    G --> H[Normalization\nRule-Based]
    H --> I[Chunking\nSemantic-friendly windows]
    I --> J[Indexing\nInverted + optional vector]
    J --> K[Query Engine\nDeterministic hybrid]

    K --> L[Query Response\nPydantic + trace_id]
    J --> M[(SQLite Audit Store)]
    L --> M

    N[FastAPI] -->|/ingest| G
    N -->|/query| K
    N -->|/audit/requests| M
```

## Separation Of Concerns

- extraction: strategy routing + source parsing
- normalization: deterministic text cleanup
- chunking: provenance-preserving text segmentation
- indexing: lexical/vector index management
- querying: deterministic retrieval + configurable escalation
