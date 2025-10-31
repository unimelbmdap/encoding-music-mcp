# encoding-music-mcp

Welcome to the documentation for **encoding-music-mcp**, a Model Context Protocol (MCP) server for analyzing MEI (Music Encoding Initiative) files.

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

### ⚡ Efficient Design
- Direct disk access - no token waste
- Fast dataframe-based interval analysis
- Comprehensive test suite

## Quick Links

- [Installation Guide](getting-started/installation.md)
- [Quick Start Tutorial](getting-started/quick-start.md)
- [Tools Overview](tools/index.md)
- [API Reference](api-reference.md)

## What is MCP?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) is an open standard that enables AI assistants to securely access data and tools. This server implements MCP to provide music analysis capabilities to any MCP-compatible client, such as Claude Desktop.

## What is MEI?

The [Music Encoding Initiative (MEI)](https://music-encoding.org/) is a community-driven effort to define a system for encoding musical documents in a machine-readable structure. MEI brings together specialists from various music research communities to provide a comprehensive format for representing musical notation.

## Use Cases

- **Music Analysis**: Analyze harmonic progressions, melodic patterns, and key relationships
- **Comparative Studies**: Compare compositions across different composers and periods
- **Pattern Discovery**: Find recurring melodic or harmonic patterns using n-gram analysis
- **Educational Tools**: Explore musical structure and theory with AI assistance
- **Research Workflows**: Integrate music analysis into computational musicology research

## Getting Started

Ready to begin? Head over to the [Installation Guide](getting-started/installation.md) to set up encoding-music-mcp.

## Support

- **GitHub**: [unimelbmdap/encoding-music-mcp](https://github.com/unimelbmdap/encoding-music-mcp)
- **Issues**: [Report bugs or request features](https://github.com/unimelbmdap/encoding-music-mcp/issues)

## License

This project is licensed under the MIT License.
