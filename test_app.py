import unittest
from unittest.mock import patch
from io import BytesIO
from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from streamlit.testing.v1 import AppTest
from inputs import extract_pdf_text, validate_text, trim_text, MAX_PDF_BYTES


def pdf_bytes(text=None, pages=1, encrypted=False):
    writer = PdfWriter()
    for _ in range(pages):
        page = writer.add_blank_page(width=612, height=792)
        if text:
            font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
            page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):
                DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
            stream = DecodedStreamObject()
            stream.set_data(f'BT /F1 12 Tf 72 720 Td ({text}) Tj ET'.encode())
            page[NameObject('/Contents')] = writer._add_object(stream)
    if encrypted:
        writer.encrypt('password')
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class InputTests(unittest.TestCase):
    def test_selectable_pdf(self):
        self.assertEqual(extract_pdf_text(pdf_bytes('Resume evidence')), 'Resume evidence')

    def test_invalid_pdfs(self):
        cases = [(b'not a pdf', 'does not appear'), (b'%PDF- broken', 'could not be read'),
                 (pdf_bytes(), 'No selectable'), (pdf_bytes(encrypted=True), 'password'),
                 (pdf_bytes(pages=21), '20 pages'), (b'%PDF-' + b'x' * MAX_PDF_BYTES, 'over 5 MB')]
        for data, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                extract_pdf_text(data)

    def test_validation_and_truncation(self):
        self.assertEqual(len(validate_text('  ', 'short')), 2)
        self.assertEqual(validate_text('r' * 100, 'j' * 100), [])
        self.assertEqual(trim_text(' hello ', 10), 'hello')
        self.assertLessEqual(len(trim_text('a word ' * 30, 100)), 100)


class UITests(unittest.TestCase):
    def test_prepare_and_invalidate(self):
        app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.button[0].disabled)
        app.text_area(key='pasted_resume').set_value('Resume experience ' * 20)
        app.text_area(key='job_description').set_value('Required experience ' * 20)
        app.run()
        self.assertFalse(app.button[0].disabled)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertIn('prepared_inputs', app.session_state)
        app.run()
        self.assertTrue(app.success)
        app.text_area(key='job_description').set_value('Changed requirements ' * 20).run()
        self.assertNotIn('prepared_inputs', app.session_state)
        app.radio[0].set_value('Upload PDF or DOCX').run()
        self.assertTrue(app.button[0].disabled)

    def test_missing_secrets_and_reset(self):
        app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run()
        app.text_area(key='pasted_resume').set_value('Resume experience ' * 20)
        app.text_area(key='job_description').set_value('Required experience ' * 20).run()
        app.button(key='prepare').click().run()
        with patch('review.review_quick') as mocked:
            app.button(key='analyze').click().run()
            mocked.assert_not_called()
        self.assertFalse(app.exception)
        self.assertIn('GROQ_API_KEY', app.error[0].value)
        app.button(key='start_over').click().run()
        self.assertFalse(app.exception)
        self.assertNotIn('prepared_inputs', app.session_state)
        self.assertEqual(app.text_area(key='pasted_resume').value, '')
        self.assertTrue(app.button(key='analyze').disabled)

    def test_long_input(self):
        app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run()
        app.text_area(key='pasted_resume').set_value('resume ' * 4000)
        app.text_area(key='job_description').set_value('job ' * 5000).run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        resume, job = app.session_state['prepared_inputs']
        self.assertLessEqual(len(resume), 24000)
        self.assertLessEqual(len(job), 16000)
        self.assertEqual(len(app.warning), 2)

    def test_quick_result_and_stale_clearing(self):
        app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run()
        app.secrets['GROQ_API_KEY'] = 'test-key'
        app.text_area(key='pasted_resume').set_value('Resume experience ' * 20)
        app.text_area(key='job_description').set_value('Required experience ' * 20).run()
        app.button(key='prepare').click().run()
        with patch('review.review_quick', return_value={'score': 70, 'markdown': 'Test report'}) as mocked:
            app.button(key='analyze').click().run()
            self.assertEqual(mocked.call_count, 1)
        self.assertFalse(app.exception)
        self.assertIn('review_result', app.session_state)
        app.run()
        self.assertIn('review_result', app.session_state)
        app.text_area(key='job_description').set_value('Changed requirements ' * 20).run()
        self.assertNotIn('review_result', app.session_state)

if __name__ == '__main__':
    unittest.main()
