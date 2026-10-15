"""Resume Review Agent — Stage 3: Quick and Detailed resume review."""
from __future__ import annotations

from runtime import configure_runtime

configure_runtime()

import hashlib
import streamlit as st
from inputs import (
    MAX_RESUME_CHARS, MAX_JOB_CHARS, extract_pdf_text, extract_docx_text,
    validate_text, trim_text,
)
from review import ReviewError, review_quick, review_detailed

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
st.caption('Quick review or Detailed review with three agents working in sequence.')
st.info('Prepare and check the text first. Analyze Resume sends the prepared text to Groq.')
st.caption('Inputs stay in server/session memory and are not saved to disk. '
           'Remove unnecessary personal details before analysis.')
# One source selector controls exactly which input is displayed and read.
def read_uploaded_text(upload, label: str) -> str:
    if upload.name.lower().endswith('.docx'):
        return extract_docx_text(upload.getvalue())
    if upload.name.lower().endswith('.pdf'):
        return extract_pdf_text(upload.getvalue())
    raise ValueError(f'{label}: choose a PDF or DOCX file.')


def reset_session():
    generation = st.session_state.get('upload_generation', 0) + 1
    st.session_state.clear()
    st.session_state['upload_generation'] = generation


st.caption('To paste: click inside a text box, press ⌘+V on Mac or Ctrl+V on Windows, '
           'then click outside the box to apply the text.')
generation = st.session_state.get('upload_generation', 0)
file_errors = []
st.subheader('1. Resume')
source = st.radio('Resume input method', ['Paste text', 'Upload PDF or DOCX'],
                  horizontal=True, key='resume_source')
resume = ''
if source == 'Paste text':
    resume = st.text_area('Resume text', height=240, key='pasted_resume',
                          placeholder='Click here, then paste your resume.')
else:
    uploaded = st.file_uploader('Upload resume (5 MB; PDFs: 20 pages maximum)',
                               type=['pdf', 'docx'], max_upload_size=5,
                               key=f'resume_upload_{generation}')
    if uploaded is None:
        file_errors.append('Upload a resume file or choose Paste text.')
    else:
        try:
            resume = read_uploaded_text(uploaded, 'Resume')
            st.success(f'Resume file read: {len(resume):,} characters.')
        except ValueError as exc:
            file_errors.append(str(exc))
            st.error(str(exc))
st.caption(f'Resume text received: {len(resume.strip()):,} characters.')

st.subheader('2. Job description')
job_source = st.radio('Job-description input method', ['Paste text', 'Upload PDF or DOCX'],
                      horizontal=True, key='job_source')
job = ''
if job_source == 'Paste text':
    job = st.text_area('Job description', height=220, key='job_description',
                       placeholder='Click here, then paste the full job description.')
else:
    job_file = st.file_uploader('Upload job description (5 MB; PDFs: 20 pages maximum)',
                               type=['pdf', 'docx'], max_upload_size=5,
                               key=f'job_upload_{generation}')
    if job_file is None:
        file_errors.append('Upload a job-description file or choose Paste text.')
    else:
        try:
            job = read_uploaded_text(job_file, 'Job description')
            st.success(f'Job-description file read: {len(job):,} characters.')
        except ValueError as exc:
            file_errors.append(str(exc))
            st.error(str(exc))
st.caption(f'Job-description text received: {len(job.strip()):,} characters.')
problems = validate_text(resume, job)
problems = file_errors + problems
if problems:
    st.warning('To prepare inputs, complete both fields. ' + ' '.join(problems))

fingerprint = hashlib.sha256((source + '\0' + job_source + '\0' + resume + '\0' + job).encode()).hexdigest()
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

mode = st.radio('Review mode', ['Quick', 'Detailed'], horizontal=True, key='review_mode')
st.caption('Quick uses one agent. Detailed uses three sequential agents and uses more tokens.')
if st.session_state.get('review_result_mode') != mode:
    st.session_state.pop('review_result', None)

if st.button('Analyze Resume', disabled=prepared is None or bool(problems), key='analyze'):
    st.session_state.pop('review_result', None)
    try:
        api_key, model_name = get_llm_settings()
        with st.spinner(f'{mode} review: checking requirements and resume evidence. Please wait…'):
            reviewer = review_detailed if mode == 'Detailed' else review_quick
            st.session_state['review_result'] = reviewer(*prepared, api_key, model_name)
            st.session_state['review_result_mode'] = mode
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
    st.caption(f'{mode} review completed')
    st.metric('Estimated match', f"{result['score']}/100")
    st.markdown(result['markdown'])
    st.download_button('Download report', result['markdown'], 'resume_review.md', 'text/markdown')
st.button('Start over', key='start_over', on_click=reset_session)
