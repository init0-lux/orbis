from fastapi import FastAPI, Request
from pydantic import BaseModel
import google.generativeai as genai
import uvicorn
import os
from fastapi import File, UploadFile
from PIL import Image
import io
from pdf2image import convert_from_path
import pytesseract
from PyPDF2 import PdfReader, PdfWriter
import api

app = FastAPI()

genai.configure(api.api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

class PromptRequest(BaseModel):
    prompt: str

def split_pdf(input_pdf, output_prefix="output"):
    reader = PdfReader(input_pdf)
    for i in range(len(reader.pages)):
        writer = PdfWriter()
        writer.add_page(reader.pages[i])
        
        output_filename = f"output/{output_prefix}_page_{i+1}.pdf"
        with open(output_filename, "wb") as output_file:
            writer.write(output_file)
        print(f"Created: {output_filename}")

@app.post("/prompt/")
async def process_prompt(request: PromptRequest):
    response = model.generate_content(request.prompt)
    return {"response": "This is a response : " + response.text}

@app.post("/parse-image/")
async def parse_image(file: UploadFile = File(...)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))

    # Assuming genai has a method to parse images
    response = model.generate_content(image)
    
    return {"response": response.text}

@app.post("/parse-pdf/")
async def parse_pdf(file: UploadFile = File(...)):
    contents = await file.read()
    pdf_path = "reference.pdf"
    
    with open(pdf_path, "wb") as f:
        f.write(contents)
    split_pdf(pdf_path)
    return "PDF has been split into pages"


@app.post("/ocr-pdf/")
async def ocr_pdf(request: int):
    print(f"Received request with integer: {request}")
    if os.path.exists(f"output/output_page_{request}.pdf"):

        images = convert_from_path(f"output/output_page_{request}.pdf")
        full_text = ""
        for image in images:
            text = pytesseract.image_to_string(image)
            full_text += text + "\n"

        prompt="Summarize this text and ignore headers,unnecessary characters,respond in plain text"
        response=model.generate_content(prompt+full_text)
        output_filename = f"output/output_page_{request}.txt"
        with open(output_filename, "w") as output_file:
            output_file.write(response.text)
        print(f"Created: {output_filename}")
        return response.text

    else:
        return "invalid page index",f"output/output_page_{request}.pdf"
    
@app.post("/ocr-pdf-answer/")

async def ocr_pdf_answer(page_number: int, comparison_text: str):
    print(f"Received request with page number: {page_number} and comparison text: {comparison_text}")
    if os.path.exists(f"output/output_page_{page_number}.txt"):
        with open(f"output/output_page_{page_number}.txt", "r") as f:
            full_text = "OG text  " + f.read()
            prompt = "compare first text with second text and respond in either 'all important points covered' or 'important points missed are' and then proceed to list the missed points/key phrases"
            response = model.generate_content(prompt + full_text + " second text " + comparison_text)
            return response.text
    else:
        return "Invalid page index", f"output/output_page_{page_number}.txt"
    

if __name__ == "__main__":
    uvicorn.run(app, host="192.168.148.5", port=80)