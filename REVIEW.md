# Deployment review — 14 October 2026

## Result

Prepared for Streamlit Community Cloud using Python 3.11. Upload this folder's
contents at the GitHub repository root, select app.py, and add GROQ_API_KEY in
Cloud Secrets. README.md includes the full deployment steps.

## Changes

- Added Linux-only pysqlite3-binary==0.5.4. The previous SQLite fallback imported
  an undeclared package, so it could not work when the host SQLite was too old.
- Centralized startup configuration in runtime.py, applied by both app.py and
  review.py. Direct use of review.py now gets the same SQLite and telemetry setup.
- Added an Ubuntu/Python 3.11 GitHub Actions workflow for dependency installation,
  pip check, and the complete test suite.
- Added regressions for missing secrets, Start over, the old SQLite fallback,
  and real CrewAI construction, which was previously tested only with mocks.
- Expanded deployment instructions and replaced the previous incomplete validation
  report with the checks performed for this release.

## Verified in this workspace

- Clean Python 3.11.9 virtual environment installed all application dependencies.
- python -m pip check: no broken requirements.
- python -m unittest -v: 19 tests passed, including Streamlit AppTest.
- Real CrewAI agent, LLM, task and crew constructed with a dummy key; no kickoff
  or provider request. Test support files are isolated in a temporary directory
  because the workspace restricts writes to the default user support folders.
- Linux CPython 3.11 x86_64 wheel for pysqlite3-binary==0.5.4 downloaded successfully.
- Streamlit launched on 127.0.0.1:8501; /_stcore/health returned ok.
- Browser inspection confirmed the initial input screen renders correctly.

## Remaining limitations

No real Groq API key was provided, so live model output, account quota, and report
quality were not tested. No Cloud account deployment was performed. Installation
and runtime tests ran on macOS ARM64; the included Ubuntu CI workflow should be
run on GitHub to validate the full Linux dependency stack before release.

Quotation checks establish that a quote occurs in the source, not that it supports
the model's judgment. Rewrites block new numbers but other factual changes rely
on model instructions and user review. The score is an estimate, not a hiring
prediction. PDF stream limits are checked after decompression, so the app's
upload limits do not guarantee a strict peak memory limit for hostile files.
CrewAI has a substantial dependency footprint despite memory=False; watch Cloud
resource usage after deployment. The application does not save resume text, but
CrewAI may create framework support/configuration files in its user data directory.
