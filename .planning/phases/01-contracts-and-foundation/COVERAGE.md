# API Coverage — Phase 1: Contracts and Foundation

No external API integration: Phase 1 consumes no third-party service; the only HTTP traffic is the first-party health page calling the first-party backend, both bound to 127.0.0.1.

Scope notes (not declarations, for the human reader):

- The FastAPI skeleton exposes one local surface, `GET /health`, on loopback only.
- The Next.js page fetches that same local surface; no browser call leaves the machine.
- PostgreSQL is a repo-local database over a local socket/port, not an API integration.
- Provider APIs (MT5, market data vendors) and model runtimes (Ollama) arrive in later phases and will each get their own coverage rows there.
