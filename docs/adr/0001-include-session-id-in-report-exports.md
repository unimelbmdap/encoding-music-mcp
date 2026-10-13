# Include the raw session ID in report exports

Conversation report exports include the source session's raw ID so a future replay workflow can associate the exported calls with their originating session. A session ID can grant access to live session state, so exports are treated as sensitive: the ID remains inside the JSONL metadata and is omitted from filenames and ordinary status text. A non-reusable fingerprint was considered but rejected because it would not preserve the requested session identity.
