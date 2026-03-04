# Architecture Diagram -- 5-Stage Pipeline with Strategy Routing

```mermaid
flowchart TD
    In[Ingestion\nDocumentInput] --> T

    subgraph S1[Stage 1: Triage]
      T[Triage Classifier\nInput: DocumentInput\nOutput: TriageDecision]
      R{Strategy Router}
      T --> R
    end

    subgraph S2[Stage 2: Structure Extraction]
      E1[Fast Text Extractor\npdfplumber/PyMuPDF]
      E2[Layout Extractor\nDocling/MinerU]
      E3[Vision/OCR Extractor\nTesseract]
      E4[Table Extractor\nCamelot]
      Q1{Extraction Quality Check\n(reading order/table/bbox)}
    end

    subgraph S3[Stage 3: Semantic Chunking]
      C[Semantic Chunker\nInput: ExtractionResult\nOutput: ChunkingResult]
      Q2{Chunk Quality Check\n(table integrity/hierarchy)}
    end

    subgraph S4[Stage 4: PageIndex Builder]
      P[PageIndex Builder\nInput: ChunkingResult\nOutput: IndexResult]
      V[(Vector Index\nFAISS optional)]
      L[(Lexical Index\nInverted index)]
      P --> V
      P --> L
    end

    subgraph S5[Stage 5: Query Interface]
      QI[Query Interface\nInput: QueryRequest\nOutput: QueryResponse]
      QE{Query Confidence Gate}
      QI --> QE
    end

    Ledger[(Provenance & Audit Ledger\ntrace_id + bbox + page refs)]

    R -->|Tier A: Fast Text| E1
    R -->|Tier B: Layout Aware| E2
    R -->|Tier C: Vision Augmented| E3
    R -->|Table route| E4

    E1 --> Q1
    E2 --> Q1
    E3 --> Q1
    E4 --> Q1

    Q1 -->|pass| C
    Q1 -->|low confidence escalation| R

    C --> Q2
    Q2 -->|pass| P
    Q2 -->|re-chunk feedback| C

    V --> QI
    L --> QI
    QE -->|low confidence escalation| R

    T -.write.-> Ledger
    E1 -.write.-> Ledger
    E2 -.write.-> Ledger
    E3 -.write.-> Ledger
    E4 -.write.-> Ledger
    C -.write.-> Ledger
    P -.write.-> Ledger
    QI -.write.-> Ledger
```

## Data Structures by Stage

- Triage: `DocumentInput -> TriageDecision`
- Structure Extraction: `TriageDecision + DocumentInput -> ExtractionResult`
- Semantic Chunking: `ExtractionResult -> ChunkingResult`
- PageIndex Builder: `ChunkingResult -> IndexResult`
- Query Interface: `QueryRequest + IndexResult -> QueryResponse`

## Non-Linearity Notes

- Extraction quality gate can reroute to a different strategy tier.
- Chunk quality gate can trigger re-chunk feedback loops.
- Query confidence gate can trigger escalation through Triage/Extraction again.
