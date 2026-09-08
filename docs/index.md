# Encoding Music MCP

Welcome to the documentation for **Encoding Music MCP**, a Model Context Protocol (MCP) server for analyzing MEI (Music Encoding Initiative) files.

## Overview

This MCP server provides a comprehensive suite of tools for analyzing encoded musical scores in MEI format. It enables AI assistants and other MCP clients to extract metadata, analyze musical structure, and understand encoded compositions.

## Key Features

### 🎼 Built-in MEI Collection
- **46 curated MEI files** from three major collections:
    - 15 Bach Two-Part Inventions (BWV 772-786)
    - 19 Bartók Mikrokosmos pieces
    - 12 Morley Canzonets (1595)

### 📊 Analysis Tools
- **Metadata Extraction**: Title, composer, editors, publication details, and copyright information
- **Key Analysis**: Detect musical keys with confidence scores using music21
- **Interval Analysis**: Extract notes, melodic intervals, harmonic intervals, and melodic n-grams using CRIM Intervals
- **File Discovery**: Browse and explore the built-in MEI collection

### 🎵 Notation Display
- **Sheet Music Rendering**: Display MEI files as beautifully engraved notation using Verovio
- **Interactive Pagination**: Navigate multi-page scores with prev/next controls
- **Measure Selection**: View specific measure ranges
- Requires the [MCP Apps extension](https://modelcontextprotocol.io/docs/extensions/apps)

### ⚡ Efficient Design
- Direct disk access - no token waste
- Fast dataframe-based interval analysis
- Comprehensive test suite

## Quick Links

- [Installation Guide](getting-started/installation.md)
- [Quick Start Tutorial](getting-started/quick-start.md)
- [Tools Overview](tools/index.md)
- [API Reference](api-reference.md)

## Project Design

- [Architecture](/docs/architecture.md) — Runtime and software architecture
- [UML Diagrams](/docs/uml.md) — Formal Component, Class, Sequence, and State diagrams
- [Problem Space](/docs/design/problem-space.md) — What the project solves and why
- [Decision Log](/docs/adr/index.md) — Architectural Decision Records (6 accepted, 2 superseded)

## Feature Modules

### Score embeddings [✓] · Review: ✓ 2026-08-25 (4 of 4 features)

Convert complete symbolic scores into validated XML representations and reproducible CLaMP 3 embeddings, retain catalog metadata, encode compatible CLaMP text queries, and store vectors for retrieval.

- [sheet-music-processing](/docs/modules/score-embeddings/sheet-music-processing/) [✓]
- [clamp3-extraction](/docs/modules/score-embeddings/clamp3-extraction/) [✓]
- [sqlite-vector-storage](/docs/modules/score-embeddings/sqlite-vector-storage/) [✓]
- [embedding-pipeline-cli](/docs/modules/score-embeddings/embedding-pipeline-cli/) [✓]
- [gpu-extraction-notebook](/docs/modules/score-embeddings/gpu-extraction-notebook/) [✓]
- [unified-vector-domain](/docs/modules/score-embeddings/unified-vector-domain/) [✓]
- [Module Status](/docs/modules/score-embeddings/module-status.md)

### Semantic axis retrieval [✓] · Review: ⏸

Expose Claude-facing ranking along broad musical semantic contrasts using matched prompt ensembles.

- [semantic-axis-search](/docs/modules/semantic-axis-retrieval/semantic-axis-search/) [✓]
- [Module Status](/docs/modules/semantic-axis-retrieval/module-status.md)

### Prototype retrieval [✓] · Review: ⏸

Expose Claude-facing retrieval for one independent high-level musical concept using a dynamically generated prompt ensemble.

- [dynamic-prototype-search](/docs/modules/prototype-retrieval/dynamic-prototype-search/) [✓]
- [Module Status](/docs/modules/prototype-retrieval/module-status.md)

## What is MCP?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) is an open standard that enables AI assistants to securely access data and tools. This server implements MCP to provide music analysis capabilities to any MCP-compatible client, such as Claude Desktop.

## What is MEI?

The [Music Encoding Initiative (MEI)](https://music-encoding.org/) is a community-driven effort to define a system for encoding musical documents in a machine-readable structure. MEI brings together specialists from various music research communities to provide a comprehensive format for representing musical notation.

## Use Cases

- **Music Analysis**: Analyze harmonic progressions, melodic patterns, and key relationships
- **Comparative Studies**: Compare compositions across different composers and periods
- **Pattern Discovery**: Find recurring melodic or harmonic patterns using n-gram analysis
- **Notation Display**: View rendered sheet music inline during analysis conversations
- **Educational Tools**: Explore musical structure and theory with AI assistance
- **Research Workflows**: Integrate music analysis into computational musicology research

## Getting Started

Ready to begin? Head over to the [Installation Guide](getting-started/installation.md) to set up Encoding Music MCP.

## Support

- **GitHub**: [unimelbmdap/encoding-music-mcp](https://github.com/unimelbmdap/encoding-music-mcp)
- **Issues**: [Report bugs or request features](https://github.com/unimelbmdap/encoding-music-mcp/issues)

## License

This project is licensed under the MIT License.
