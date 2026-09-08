# UML Diagrams — Encoding Music MCP

This document provides formal Unified Modeling Language (UML) specifications for the **Encoding Music MCP** architecture, covering package components, domain classes, sequence interactions, and pipeline lifecycle states.

---

## 1. System Component Diagram

The component diagram illustrates the high-level architecture of Encoding Music MCP, partitioning the system into the MCP Application Layer, Symbolic Analysis Subsystem, Semantic Vector Retrieval Subsystem, and External Storage/Engines.

```mermaid
graph TB
    subgraph ClientLayer["MCP Client Layer"]
        Claude["Claude Desktop / MCP Client"]
    end

    subgraph FastMCPLayer["MCP Application Layer (encoding_music_mcp)"]
        Server["server.py (FastMCP)"]
        ToolReg["tools/registry.py"]
        ResourceReg["resources/registry.py"]
        PromptReg["prompts/registry.py"]
        Server --> ToolReg
        Server --> ResourceReg
        Server --> PromptReg
    end

    subgraph RetrievalSubsystem["Semantic Vector Retrieval Subsystem"]
        CombTool["combined_retrieval.py"]
        ProtoTool["prototype_retrieval.py"]
        AxisTool["semantic_axis_retrieval.py"]
        RetService["score_embeddings/retrieval.py<br/>(RetrievalService)"]
        DomainModel["Domain Models<br/>(ComposedQuery, PrototypeVector, SemanticAxisVector)"]

        CombTool --> RetService
        ProtoTool --> RetService
        AxisTool --> RetService
        CombTool --> DomainModel
        ProtoTool --> DomainModel
        AxisTool --> DomainModel
        RetService --> DomainModel
    end

    subgraph SymbolicSubsystem["Symbolic Analysis Subsystem"]
        IntervalsTool["tools/intervals.py<br/>(notes, intervals, n-grams, cadences)"]
        KeyTool["tools/key_analysis.py<br/>(analyze_key)"]
        MetaTool["tools/metadata.py<br/>(get_mei_metadata)"]
        NotationTool["tools/notation.py<br/>(show_notation)"]
        DiscTool["tools/discovery.py<br/>(list_available_mei_files)"]
        VisualTool["tools/visualisation/<br/>(voice_ranges, heatmaps, progress)"]
    end

    subgraph StorageSubsystem["Domain Storage & Extraction Subsystem"]
        Repo["score_embeddings/storage.py<br/>(EmbeddingRepository)"]
        Encoder["score_embeddings/clamp_extractor.py<br/>(TextEncoder)"]
        Processor["score_embeddings/music_processing.py<br/>(standardize, export, validate)"]
        Pipeline["score_embeddings/pipeline.py<br/>(Batch Pipeline Orchestrator)"]

        RetService --> Repo
        RetService --> Encoder
        Pipeline --> Processor
        Pipeline --> Repo
    end

    subgraph ExternalServices["External Engines & Storage"]
        SQLiteDB[("SQLite + sqlite-vec<br/>score-embeddings.sqlite3")]
        CLaMPWorker["Pinned CLaMP 3 Model Cache & Runtime"]
        VerovioEngine["Verovio Engraving Engine"]
        Music21Lib["music21 Library"]
        CRIMLib["crim-intervals Library"]
        MEIFiles[("MEI Corpus Files<br/>(Bach, Bartók, Morley)")]

        Repo --> SQLiteDB
        Encoder --> CLaMPWorker
        NotationTool --> VerovioEngine
        KeyTool --> Music21Lib
        Processor --> Music21Lib
        IntervalsTool --> CRIMLib
        ResourceReg --> MEIFiles
        DiscTool --> MEIFiles
    end

    Claude <==>|"MCP Protocol (stdio / SSE / HTTP)"| Server
    ToolReg --> CombTool
    ToolReg --> ProtoTool
    ToolReg --> AxisTool
    ToolReg --> IntervalsTool
    ToolReg --> KeyTool
    ToolReg --> MetaTool
    ToolReg --> NotationTool
    ToolReg --> DiscTool
    ToolReg --> VisualTool
```

---

## 2. Unified Vector Domain Class Diagram

This class diagram models the object-oriented structure of the unified vector retrieval domain under **ADR-0008**, **ADR-0006**, and **ADR-0005**, including vector hierarchies, query composition, storage repositories, and retrieval services.

```mermaid
classDiagram
    class QueryVector {
        +ndarray values
        +int dimension
        +float raw_norm
        +str query_type
        +EmbeddingModelIdentity model_identity
        +unit_direction() ndarray
    }

    class PrototypeVector {
        +str concept
        +tuple_str prompts
        +float centroid_norm
        +build(concept: str, prompts: Sequence, prompt_embeddings: ndarray, model_identity: EmbeddingModelIdentity)$ PrototypeVector
    }

    class SemanticAxisVector {
        +tuple_str positive_prompts
        +tuple_str negative_prompts
        +build(positive_prompts: Sequence, negative_prompts: Sequence, positive_embeddings: ndarray, negative_embeddings: ndarray, model_identity: EmbeddingModelIdentity)$ SemanticAxisVector
    }

    class WeightedQuery {
        +QueryVector query
        +float weight
        +float mean
        +float std
        +effective_weight() float
        +scaled_vector() ndarray
    }

    class ComposedQuery {
        +list_WeightedQuery queries
        +list_str query_names
        +add_query(query: QueryVector, weight: float, name: str)
        +is_empty() bool
        +synthesize_vector() tuple
        +recover_z_scores(raw_scores: ndarray) ndarray
    }

    class SearchResult {
        +int rank
        +float score
        +str title
        +str song_title
        +str artist
        +str work_created_date
        +str score_id
        +int embedding_id
        +dict component_scores
        +str score_definition
        +to_dict() dict
    }

    class EmbeddingRepository {
        +Path database_path
        +Connection connection
        +open() EmbeddingRepository
        +close()
        +upsert(record: EmbeddingRecord)
        +get_dataset_baseline(query: QueryVector, model_identity: EmbeddingModelIdentity) tuple
        +search_knn(query: QueryVector, limit: int, model_identity: EmbeddingModelIdentity) list
    }

    class TextEncoder {
        +encode_batch(texts: Sequence, config: ClampRuntimeConfig) TextEmbeddingBatch
    }

    class RetrievalService {
        +EmbeddingRepository repository
        +TextEncoder encoder
        +search_composed(composed_query: ComposedQuery, limit: int, model_identity: EmbeddingModelIdentity) list_SearchResult
    }

    class EmbeddingModelIdentity {
        <<interface>>
        +str model_commit
        +str model_revision
        +str model_weight_sha256
        +int dimension
        +matches(other: EmbeddingModelIdentity) bool
    }

    class ClampModelIdentity {
        +str model_commit
        +str model_revision
        +str model_weight_sha256
        +int dimension
    }

    class EmbeddingRecord {
        +str score_id
        +str source_path
        +str source_sha256
        +str processing_fingerprint
        +dict validation
        +str model_commit
        +str model_revision
        +str model_weight_sha256
        +ndarray raw_embedding
        +ndarray normalized_embedding
        +str title
        +str artist
        +str work_created_date
    }

    QueryVector <|-- PrototypeVector : specializes
    QueryVector <|-- SemanticAxisVector : specializes
    EmbeddingModelIdentity <|.. ClampModelIdentity : implements

    QueryVector o-- EmbeddingModelIdentity : tagged with
    WeightedQuery *-- QueryVector : wraps
    ComposedQuery *-- WeightedQuery : aggregates

    RetrievalService --> ComposedQuery : evaluates
    RetrievalService --> EmbeddingRepository : executes KNN
    RetrievalService --> TextEncoder : encodes prompts
    RetrievalService ..> SearchResult : produces

    EmbeddingRepository ..> EmbeddingRecord : stores & queries
```

---

## 3. Composed Vector Retrieval Sequence Diagram

This sequence diagram depicts the end-to-end execution of `search_songs_by_combined_criteria` under **ADR-0008**, illustrating prompt consensus, single-batch text encoding, single-vector synthesis, and exact $z$-index score recovery.

```mermaid
sequenceDiagram
    autonumber
    actor Claude as Claude / MCP Client
    participant FastMCP as FastMCP Server
    participant Tool as combined_retrieval.py
    participant Service as RetrievalService
    participant Encoder as TextEncoder (CLaMP 3)
    participant Repo as EmbeddingRepository (SQLite)

    Claude->>FastMCP: Call search_songs_by_combined_criteria(prototypes, axes, limit)
    FastMCP->>Tool: search_songs_by_combined_criteria(...)
    
    Note over Tool: 1. Parse & validate sub-queries<br/>2. Deduplicate prompt texts across all sub-queries
    Tool->>Encoder: encode_batch(deduplicated_prompts, clamp_config)
    Encoder-->>Tool: TextEmbeddingBatch (unit prompt vectors, model_identity)

    Note over Tool: 3. Construct domain vectors:<br/>- PrototypeVector.build(...)<br/>- SemanticAxisVector.build(...)<br/>4. Assemble ComposedQuery
    
    Tool->>Repo: open()
    Tool->>Service: search_composed(composed_query, limit, model_identity)

    loop For each sub-query in ComposedQuery
        Service->>Repo: get_dataset_baseline(sub_query, model_identity)
        Repo-->>Service: (mean_similarity, std_similarity)
        Note over Service: Calibrate WeightedQuery with baseline mean & std
    end

    Note over Service: 5. Synthesize composite direction vector V_composed<br/>and scalar offset C_composed (ADR-0008)
    
    Service->>Repo: search_knn(composite_query_vector, limit, model_identity)
    Repo-->>Service: Raw KNN matches (cosine distances d_i, metadata)

    Note over Service: 6. Recover exact standardized z-indices:<br/>z_i = ||V_composed|| * (1 - d_i) - C_composed<br/>7. Assemble SearchResult objects with component scores

    Service-->>Tool: list[SearchResult]
    Tool->>Repo: close()
    Tool-->>FastMCP: JSON List of Results (scores in z-index units)
    FastMCP-->>Claude: Tool Result Payload

    Note over Claude: Claude stipulates to user that individual results<br/>might be incorrect, but results are usually correct on average.
```

---

## 4. Symbolic Analysis & Notation Sequence Diagram

This sequence diagram illustrates the execution flow for symbolic analysis (`intervals.py`, `key_analysis.py`) and dynamic sheet music notation rendering (`notation.py`).

```mermaid
sequenceDiagram
    autonumber
    actor Claude as Claude / MCP Client
    participant FastMCP as FastMCP Server
    participant Helpers as tools/helpers.py
    participant Tool as Tool Implementation<br/>(intervals / notation / key_analysis)
    participant Engine as Engine<br/>(CRIM / music21 / Verovio)
    participant Disk as MEI Corpus Storage

    alt Musical Analysis (e.g., get_melodic_ngrams)
        Claude->>FastMCP: Call get_melodic_ngrams(filename="Bach_BWV_0772.mei", n=3)
        FastMCP->>Tool: get_melodic_ngrams(...)
        Tool->>Helpers: resolve_mei_path(filename)
        Helpers->>Disk: Check existence in mei_files/
        Helpers-->>Tool: Absolute Path
        Tool->>Engine: CRIM Intervals parse & n-gram extraction
        Engine-->>Tool: pandas DataFrame of n-gram sequences
        Tool-->>FastMCP: JSON Table / Summary of Patterns
        FastMCP-->>Claude: Melodic N-Grams Result

    else Notation Rendering (show_notation)
        Claude->>FastMCP: Call show_notation(filename="Bach_BWV_0772.mei", page=1)
        FastMCP->>Tool: show_notation(...)
        Tool->>Helpers: resolve_mei_path(filename)
        Helpers-->>Tool: Absolute Path
        Tool->>Disk: Read MEI XML content
        Tool->>Engine: verovio.toolkit.renderToSVG(page=1)
        Engine-->>Tool: Raw SVG XML String
        Tool-->>FastMCP: Rendered SVG (with pagination controls)
        FastMCP-->>Claude: Interactive Sheet Music Display (MCP Apps UI)
    end
```

---

## 5. Ingestion Pipeline State Diagram

This state diagram depicts the lifecycle of a symbolic score processed by the standalone whole-score embedding pipeline (`score_embeddings/`).

```mermaid
stateDiagram-v2
    [*] --> Discovered: File identified (*.mei, *.musicxml, *.mxl)
    
    Discovered --> Standardizing: Deep-copy stream & apply default tempo/velocity
    Standardizing --> MusicXMLExported: Deterministic MusicXML (.xml) written to workspace
    
    MusicXMLExported --> Validating: Reparse with music21 & compare NoteEvents
    
    state Validating {
        [*] --> NoteEventCheck
        NoteEventCheck --> ExactMatch: Pitch & duration agree 100%
        NoteEventCheck --> QualifiedMatch: Minor discrepancies within tolerance
        NoteEventCheck --> Mismatch: Note drop or pitch disagreement
    }

    ExactMatch --> ValidatedPass: PASS
    QualifiedMatch --> ValidatedWarning: PASS WITH WARNINGS
    Mismatch --> ValidationFailed: FAIL

    ValidationFailed --> Excluded: Excluded from CLaMP inference; failure logged in DB
    Excluded --> [*]

    ValidatedPass --> FeatureExtraction: Pass validated XML to CLaMP subprocess
    ValidatedWarning --> FeatureExtraction: Pass validated XML to CLaMP subprocess

    FeatureExtraction --> RawEmbeddingProduced: Subprocess outputs 768-dim raw .npy vector
    RawEmbeddingProduced --> L2Normalizing: Validate finite floats & normalize to unit vector
    
    L2Normalizing --> RelationalStorage: Upsert metadata & raw vector into score_embeddings table
    RelationalStorage --> VectorIndexed: Insert unit vector into sqlite-vec virtual table
    
    VectorIndexed --> WorkspaceCleanup: Purge temporary XML workspace files
    WorkspaceCleanup --> ReadyForRetrieval: Score available for KNN search
    ReadyForRetrieval --> [*]
```
