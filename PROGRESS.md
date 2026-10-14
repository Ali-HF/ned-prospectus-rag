# Project Progress

## Done
- Set up Python 3.12 virtual environment in `.venv` with required packages.
- Migrated provider to Google Gemini (`langchain-google-genai`, `google-genai`) and pinned in `requirements.txt`.
- Downloaded and verified local embedding model `BAAI/bge-small-en-v1.5` (vector dimension 384).
- Created configuration in `config.py` with all tunable RAG/LLM parameters and dynamic PDF path resolution.
- Created `system_prompt.txt`, `fallback.txt`, `.env.example`, `.env`, and `.gitignore`.
- Placed target prospectus `UGProspectus2025.pdf` in `data/`.
- Verified setup via `check_setup.py`.
- Created `SPEC.md` and `PROGRESS.md`.
- Initialized local Git repository on `main` and created initial commit.

## In progress
- Awaiting remote repository URL to configure `git remote` and enable continuous pushes.

## Decisions
- Switched LLM provider to Google Gemini per user instruction to use `ChatGoogleGenerativeAI` and free-tier access.
- Implemented dynamic PDF path discovery in `config.py` to seamlessly handle `UGProspectus2025.pdf`, `manual.pdf`, or other prospectus naming conventions.
- Maintained `TEMPERATURE = None` and `MAX_TOKENS = 1500` per Gemini 3 recommendations in `SPEC.md`.
- Initialized local git repo tracking clean project state while strictly ignoring `.env`, `.venv`, and `chroma_db`.

## Known issues
- Free-tier rate limits on `gemini-3.8-flash` require retry logic (wait 2s, up to 2 retries) and fallback handling when quota is exhausted.
- Git remote not configured yet; awaiting user repository URL or credentials to push.

## Next step
- Add remote repository URL (`git remote add origin <url>`) and push `main`.
- Proceed with `ingest.py` implementation.
