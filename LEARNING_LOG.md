# Learning Log

Each entry: what we built, why, the code that actually matters, what would break it, and a
checkpoint question you should be able to answer yourself before moving on.

---

## Stage 0 — Environment scaffold (2026-09-15)

**What we built**
- A project folder (`cribs/`) with its own **virtual environment** (`.venv/`) — an isolated
  copy of Python just for this project, so its package versions can't clash with anything
  else on your laptop.
- A git repo (`git init`), so every change from here on is tracked and reversible.
- `app.py` — the smallest possible Streamlit app: it just proves the tool that will host the
  real app (Streamlit) actually works on this machine.
- `requirements.txt` — the exact list of packages the project needs (`streamlit`, `pandas`,
  `scikit-learn`). This is what Streamlit Community Cloud reads to rebuild your environment
  when you deploy — without it, the live app has no idea what to install.
- `.gitignore` — tells git to never track `.venv/` (it's huge and machine-specific; anyone
  cloning the repo rebuilds their own from `requirements.txt`) or Python's cached bytecode.

**The lines that actually matter**

```python
import streamlit as st

st.title("cribs — HK Property Valuation Tool")
st.write("Scaffold is running. Nothing computed yet — this is Stage 0.")
```

- `import streamlit as st` — pulls in the library. Everything Streamlit does on the page is a
  method on `st`.
- `st.title(...)` / `st.write(...)` — each call to `st.something` draws one element on the
  page, top to bottom, in the order you call them. There's no separate "HTML file" — the
  Python script *is* the page layout.

**What would break it**
- Running `python app.py` directly instead of `streamlit run app.py` — Streamlit apps are not
  run like normal scripts; the `streamlit run` command starts a local web server and re-runs
  your script top-to-bottom on every interaction.
- Deleting or mis-naming `requirements.txt` before deploying — the cloud deploy would fail
  because it wouldn't know to install Streamlit.
- Being inside the wrong Python environment (forgetting to `source .venv/bin/activate`) — you'd
  get a `ModuleNotFoundError: No module named 'streamlit'` even though it's installed, because
  it's installed *inside* `.venv`, not system-wide.

**Checkpoint question**
If you ran `streamlit run app.py` on a totally fresh laptop that had Python but had never seen
this project before, what two things would you need to do first, and why, before it would work?
(Hint: think about what `.venv` and `requirements.txt` are each for.)
