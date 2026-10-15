# Resume Review Agent — Stage 2 Quick Review

Prepare a pasted, PDF, or DOCX resume and a job description, check the prepared
text preview, then select **Analyze Resume**. One CrewAI agent uses Groq to
extract requirements, compare resume evidence, and suggest improvements.
The report shows eight fixed sections, an estimated score, and a Markdown
file download. MKU appears at the upper-right corner. Detailed mode is the
next stage and is not available in this release.

## Run in Codex or locally

Open this project folder in Codex. Use Python 3.11:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
python -m streamlit run app.py
```

On Windows activate with `.venv\Scripts\activate`; copy the example using
File Explorer or your shell. Put your own Groq key in the copied file:

```toml
GROQ_API_KEY = "your-real-key"
GROQ_MODEL = "openai/gpt-oss-120b"
```

Do not commit a real secrets file. GROQ_MODEL is a Groq model ID without the
`groq/` prefix. The app applies the provider prefix itself. The input screen
works without secrets; an API key is required only for analysis.

## Streamlit Community Cloud

Upload the project directory's contents to a GitHub repository. Include
`app.py`, `inputs.py`, `review.py`, `runtime.py`, `requirements.txt`, and the `.streamlit`
directory with config and sample secrets. Select `app.py` as the entrypoint,
choose Python 3.11 in Advanced settings, and add your key/model to the Cloud
Secrets settings. Do not commit a local `.venv` or real `secrets.toml`.

Put the contents of this folder at the repository root, including hidden folders.
The included GitHub Actions workflow assumes this layout. On Community Cloud:

1. Create an app and select the repository and branch.
2. Set the main file path to `app.py`.
3. In Advanced settings explicitly select **Python 3.11** (do not rely on the default).
4. Paste the TOML key/model example above into Secrets, using your real key.
5. Deploy. Prepare a sample resume and job description, then analyze and download.

`pysqlite3-binary` is installed only on Linux. `runtime.py` substitutes it only
when the system SQLite is too old for CrewAI's Chroma dependency. No apt
packages or `packages.txt` are needed. Keep `.streamlit/config.toml` at the
repository root so Cloud applies the upload limit and telemetry preference.

Deployment reference: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
Secrets reference: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management

## Limits, grounding, and score

- PDF/DOCX upload limit: 5 MiB. PDFs have at most 20 pages, with the baseline
  page-content and extracted-text limits preserved. Scans require OCR first.
- Both texts need at least 100 characters. Prepared text is limited to 24,000
  resume characters and 16,000 job characters; truncation warnings and preview
  show what will be sent. Check the extraction reading order.
- DOCX paragraphs and table cells are read; embedded images and text boxes
  are not OCR processed. Headers and footers are not included.
- Analyze sends the prepared texts to Groq. Documents are kept in server/session
  memory, are not written to disk, and are not stored in a shared text cache.
  Results persist on reruns and clear when source text changes or Start over is used.
- The agent has no tools, memory, planning, or delegation. CrewAI telemetry and
  tracing are disabled. Groq requests use temperature 0.2, a timeout, and at most
  three application attempts on rate limits with exponential backoff.
- Requirement rows need source quotations from the job description. Matched and
  Partial rows need verbatim resume quotations (spacing may differ). Unsupported
  job rows are removed; unsupported resume claims are marked Missing with a
  validation note. This verifies quotation presence, not the correctness of every
  semantic judgment. Review suggestions before using them.
- Numeric bullet claims must occur in that same original bullet. Optional
  `[add your % improvement]` placeholders must be filled truthfully. Other factual
  rewrite constraints are prompt instructions; they are not a guarantee.
- Must-have requirements have weight 2, nice-to-have weight 1. Matched earns
  full credit, Partial half, Missing zero. The weighted percentage is an estimate,
  not an ATS score or a prediction of a hiring decision. At most 30 requirements
  are requested. The four-sentence summary is computed from the validated table.

## Verification

```bash
python -m unittest -v
python -m pip check
```

The supplied tests cover baseline PDF validation and preparation, DOCX extraction,
evidence rejection, scoring, report headings, mock CrewAI configuration, retries,
and Streamlit preparation/result invalidation. Provider tests use mocks, not
real Groq calls. See REVIEW.md for checks actually run in this workspace.

Before public release, try a real Quick review using your private Groq key.
The offline suite does not verify provider availability or your account quota.
