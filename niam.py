import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
from pdf2image import convert_from_path
import pytesseract
from PyPDF2 import PdfReader, PdfWriter
import os
import api
# Google generative AI setup
genai.configure(api.api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# Function to split PDFs
def split_pdf(input_pdf, output_prefix="output"):
    reader = PdfReader(input_pdf)
    if not os.path.exists('output'):
        os.makedirs('output')
    for i in range(len(reader.pages)):
        writer = PdfWriter()
        writer.add_page(reader.pages[i])
        output_filename = f"output/{output_prefix}_page_{i+1}.pdf"
        with open(output_filename, "wb") as output_file:
            writer.write(output_file)

# Streamlit UI for prompt processing
st.title("AI Enhanced Learning App")

# PDF processing section
st.header("Upload your PDF")
uploaded_pdf = st.file_uploader("Upload a PDF", type=["pdf"])
if uploaded_pdf is not None:
    pdf_path = "uploaded_pdf.pdf"
    with open(pdf_path, "wb") as f:
        f.write(uploaded_pdf.read())

    split_pdf(pdf_path)
    st.success("PDF has been split into individual pages.")

    # OCR PDF section with navigation and comparison
    st.header("Pagewise Summary")

    # Initialize session state for page number
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 1

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("Previous Page"):
            if st.session_state.page_number > 1:
                st.session_state.page_number -= 1
    with col2:
        page_input = st.text_input("Enter page number", value=st.session_state.page_number)
        if st.button("Go to Page"):
            try:
                page_number = int(page_input)
                if page_number > 0:
                    st.session_state.page_number = page_number
            except ValueError:
                st.error("Please enter a valid page number.")
    with col3:
        if st.button("Next Page"):
            st.session_state.page_number += 1

    # Display and process the current page
    page_number = st.session_state.page_number
    pdf_page = f"output/output_page_{page_number}.pdf"
    if os.path.exists(pdf_page):
        images = convert_from_path(pdf_page)
        full_text = ""
        for image in images:
            text = pytesseract.image_to_string(image)
            full_text += text + "\n"
        
        prompt = "Summarize this text and ignore headers, unnecessary characters, respond in prettified way with bullet points wherever necessary."
        response = model.generate_content(prompt + full_text)
        output_filename = f"output/output_page_{page_number}.txt"
        
        with open(output_filename, "w") as output_file:
            output_file.write(response.text)
        
        st.subheader("Summary")
        st.write(response.text)
    else:
        st.error(f"Invalid page index: {page_number}")

    # Display PDF as image
    if st.button("Show/Hide PDF"):
        if 'show_pdf' not in st.session_state:
            st.session_state.show_pdf = True
        else:
            st.session_state.show_pdf = not st.session_state.show_pdf

    if 'show_pdf' in st.session_state and st.session_state.show_pdf:
        for image in images:
            st.image(image, caption=f"Page {page_number}", use_column_width=True)

    # Compare OCR text with user input
    st.header("Test your knowledge")
    comparison_text = st.text_area("Enter your understanding of the text:")
    if st.button("Submit"):
        ocr_text_file = f"output/output_page_{page_number}.txt"
        if os.path.exists(ocr_text_file):
            with open(ocr_text_file, "r") as f:
                ocr_text = f.read()
                prompt = ("Compare first text with second text and respond in either "
                          "'all important points covered' or (how much percentage covered) and then 'important points missed are' "
                          "and then proceed to list the missed points/key phrases.")
                response = model.generate_content(prompt + ocr_text + " second text: " + comparison_text)
                st.subheader("Comparison Result")
                st.write(response.text)
        else:
            st.error(f"Invalid page index: {page_number}")

# Run the app locally
# Streamlit apps are typically run using the command: `streamlit run app.py`
