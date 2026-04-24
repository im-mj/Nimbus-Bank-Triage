# Hugging Face Deployment Steps

## Important

Hugging Face Spaces expects the Space repository root to contain the `Dockerfile` and `README.md`.

That means you should use the **contents of this folder** as the root of a separate Hugging Face Space repo.

## Steps

1. Create a new Hugging Face Space.
2. Choose **Docker** as the Space SDK.
3. Upload or push all files from this folder to the Space repo root.
4. In the Space settings, add the secret:
   - `ANTHROPIC_API_KEY`
5. Optionally add:
   - `LANGSMITH_API_KEY`
6. Wait for the build to complete.
7. Open the public Space URL and test the sample tickets from the UI.

## What Is Included Here

- `Dockerfile` - container build for Hugging Face Docker Space
- `README.md` - Space metadata and landing page
- `.streamlit/config.toml` - Streamlit server config
- `src/` - application code
- `data/chroma/` - prebuilt Chroma vector index
- `requirements.txt` - Python dependencies

## What Not To Upload

- Do not upload your local `.env`
- Do not upload local virtual environments
- Do not upload local logs unless you want them in the Space repo

## If You Change App Code Later

This folder is a deployment snapshot. If the main project changes, copy the updated `src/`, `data/`, `.streamlit/`, and `requirements.txt` into this folder again before redeploying.
