"""Resume Review Agent — Stage 2: prepared inputs and one-agent Quick review."""
from __future__ import annotations

from runtime import configure_runtime

configure_runtime()

import hashlib
import streamlit as st
from inputs import (
    MAX_RESUME_CHARS, MAX_JOB_CHARS, extract_pdf_text, extract_docx_text,
    validate_text, trim_text,
)
from review import ReviewError, review_quick

st.set_page_config(page_title='Resume Review Agent', page_icon='📄')


def limit_text(text: str, limit: int, label: str) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    head = trim_text(text, limit)
    st.warning(f'{label} is long. Only the first {len(head):,} of {len(text):,} '
               'characters will be prepared. Put the most relevant details first.')
    return head


def get_llm_settings() -> tuple[str, str]:
    try:
        key = str(st.secrets['GROQ_API_KEY']).strip()
        model = str(st.secrets.get('GROQ_MODEL', 'openai/gpt-oss-120b')).strip()
    except (KeyError, FileNotFoundError):
        raise ReviewError('Missing GROQ_API_KEY. Locally create .streamlit/secrets.toml '
                          'with GROQ_API_KEY = "your-real-key". On Streamlit Cloud, '
                          'add that line in App settings → Secrets.') from None
    if not key:
        raise ReviewError('GROQ_API_KEY is empty. Enter your key in Streamlit secrets.')
    if not model or model.startswith('groq/'):
        raise ReviewError('Set GROQ_MODEL to a Groq model ID without the groq/ prefix.')
    return key, model


# UI
st.markdown("<div style='position:fixed;top:3.5rem;right:1.5rem;z-index:999;"
            "font-weight:800;font-size:1.4rem;pointer-events:none'>MKU</div>",
            unsafe_allow_html=True)
st.title('Resume Review Agent')
st.caption('Stage 2 · Quick review with one CrewAI agent. Detailed mode comes next.')
st.info('Prepare and check the text first. Analyze Resume sends the prepared text to Groq.')
st.caption('Inputs stay in server/session memory and are not saved to disk. '
           'Remove unnecessary personal details before analysis.')
paste_tab, pdf_tab = st.tabs(['Paste text', 'Upload PDF or DOCX'])
with paste_tab:
    pasted_resume = st.text_area('Resume text', height=240, key='pasted_resume',
                                placeholder='Paste your resume here')
with pdf_tab:
    uploaded = st.file_uploader('PDF or DOCX (5 MB; PDFs: 20 pages maximum)',
                               type=['pdf', 'docx'], max_upload_size=5, key='resume_upload')
source = st.radio('Resume source to prepare', ['Paste text', 'Upload PDF or DOCX'], horizontal=True)
file_error = None
resume = pasted_resume if source == 'Paste text' else ''
if source == 'Upload PDF or DOCX' and uploaded is not None:
    try:
        extractor = extract_docx_text if uploaded.name.lower().endswith('.docx') else extract_pdf_text
        resume = extractor(uploaded.getvalue())
        st.success(f'Extracted {len(resume):,} characters from the file.')
    except ValueError as exc:
        file_error = str(exc)
        st.error(file_error)
job = st.text_area('Job description', height=220, key='job_description')
problems = validate_text(resume, job)
if source == 'Upload PDF or DOCX' and uploaded is None:
    problems.insert(0, 'Upload a PDF/DOCX or choose Paste text.')
if file_error:
    problems.insert(0, file_error)
if problems:
    st.warning('To prepare inputs, complete both fields. ' + ' '.join(problems))

fingerprint = hashlib.sha256((source + '\0' + resume + '\0' + job).encode()).hexdigest()
if st.session_state.get('prepared_fingerprint') != fingerprint:
    st.session_state.pop('prepared_inputs', None)
    st.session_state.pop('review_result', None)

if st.button('Prepare inputs', type='primary', disabled=bool(problems), key='prepare'):
    prepared_resume = limit_text(resume, MAX_RESUME_CHARS, 'Resume')
    prepared_job = limit_text(job, MAX_JOB_CHARS, 'Job description')
    st.session_state['prepared_inputs'] = (prepared_resume, prepared_job)
    st.session_state['prepared_fingerprint'] = fingerprint
    st.session_state.pop('review_result', None)

prepared = st.session_state.get('prepared_inputs')
if prepared:
    prepared_resume, prepared_job = prepared
    st.success('Inputs prepared. Check the preview before analysis.')
    st.caption(f'Resume: {len(prepared_resume):,} characters · Job description: {len(prepared_job):,} characters')
    with st.expander('Preview prepared text'):
        st.text('RESUME\n' + prepared_resume + '\n\nJOB DESCRIPTION\n' + prepared_job)
else:
    st.caption('Prepare valid inputs to enable Analyze Resume.')

if st.button('Analyze Resume', disabled=prepared is None or bool(problems), key='analyze'):
    st.session_state.pop('review_result', None)
    try:
        api_key, model_name = get_llm_settings()
        with st.spinner('Checking requirements and resume evidence. Please wait…'):
            st.session_state['review_result'] = review_quick(*prepared, api_key, model_name)
    except ReviewError as exc:
        st.error(str(exc))
        if exc.technical_type:
            with st.expander('Technical details'):
                st.code(exc.technical_type)
    except Exception as exc:
        st.error('The review could not finish. Please try again.')
        with st.expander('Technical details'):
            st.code(type(exc).__name__)

result = st.session_state.get('review_result')
if result:
    st.metric('Estimated match', f"{result['score']}/100")
    st.markdown(result['markdown'])
    st.download_button('Download report', result['markdown'], 'resume_review.md', 'text/markdown')
if st.button('Start over', key='start_over'):
    st.session_state.clear()
    st.rerun()
