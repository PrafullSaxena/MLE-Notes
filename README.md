# Milvus learning demo

A uv project with a guided Jupyter notebook covering real embeddings, collections, persistent local storage, semantic search, metadata filters, and exact retrieval. Includes explanations of server-only aliases and Attu.

## Start

From this project folder:

```bash
uv sync
uv run jupyter lab notebooks/milvus_demo.ipynb
```

In JupyterLab, choose **Run → Run All Cells**. The first run downloads the embedding model; no API key is required. Use the project's `.venv` interpreter if opening the notebook in an IDE.

The notebook creates `data/milvus_learning.db` and caches the model under `.cache/huggingface/`. Both are ignored by Git. Rerunning updates the same six sample IDs. The final cell closes the connection without deleting the data.

## Requirements

- uv and a compatible Python (the project pins Python 3.12).
- macOS or Linux supported by Milvus Lite; on Windows use WSL2/Linux or a separate Milvus server.
- Internet for initial dependency and model downloads.

`uv.lock` records the resolved dependency versions. This project uses the PyMilvus 2.6 series for the local demo; match your organisation's supported SDK/server versions when connecting remotely.

## Verify from the terminal

```bash
MILVUS_DEMO_DB="$PWD/data/milvus_verification.db" uv run jupyter nbconvert --to notebook --execute notebooks/milvus_demo.ipynb --output milvus_demo.verified --output-dir data --ExecutePreprocessor.timeout=600
```

Terminal verification uses a separate database and saves the executed notebook to `data/milvus_demo.verified.ipynb`, so it does not conflict with your open interactive notebook. Run only one terminal verification at a time.

The notebook checks storage, exact metadata query results, filtered vector search, and a known vector's nearest match. Search scores are similarities, not probabilities.

## Server features

Milvus Lite does not support aliases. The notebook contains non-executable reference code for aliases on a development Milvus server. Attu is a separate management UI for a server deployment.

- [Milvus documentation](https://milvus.io/docs/quickstart.md)
- [Lite limitations](https://milvus.io/docs/milvus_lite.md)
- [Attu](https://github.com/zilliztech/attu)

## Troubleshooting: database is locked

`DataDirLockedError: another process holds the lock` means another notebook kernel or Python process owns that local database. Milvus Lite permits one process per database path.

- To learn interactively, use `uv run jupyter lab notebooks/milvus_demo.ipynb` and run cells there.
- To release an open notebook's database, run its final cleanup cell. If that is unavailable, select **Kernel → Shut Down Kernel** in the notebook that opened the database. Closing a browser tab alone does not stop its kernel.
- To verify from a terminal while Jupyter is open, use the separate-database command above.
- Do not delete the database or lock file to fix an active lock.

The final cleanup cell explicitly stops the embedded server because `client.close()` alone does not release its database lock in the installed version. This cleanup call is specific to the local Milvus Lite demo.

An Angular `ng completion` error during shell startup is unrelated to this notebook. The Jupyter TCP warning is also not the cause of a database lock failure.

## Troubleshooting: collection is released

A collection can be saved on disk but not ready for searching after the local database restarts. The notebook now calls `client.load_collection(...)` whether the collection is new or already exists. Run the connection/collection cell before searching. No data needs to be deleted.

## What you will learn, in simple English

- **Embedding:** turn a sentence into a list of numbers that helps us compare meaning.
- **Model:** `sentence-transformers/all-MiniLM-L6-v2` creates 384 numbers per sentence. It runs on your laptop.
- **Store:** keep those numbers, the original sentence, an ID, and a category in Milvus.
- **Search:** turn your question into numbers with the same model, then ask Milvus for similar articles.
- **Filter:** only consider articles with a chosen category.
- **Load:** make a saved collection ready for searches after reopening the database.
- **Close:** stop the local connection and server when finished, without deleting the data.

The notebook explains each step before its code, including what output to expect.
