from dotenv import load_dotenv
import pdf2image
import sys
from pathlib import Path
import os
from openai import OpenAI
import base64
from io import BytesIO
from PyPDF2 import PdfReader
import tkinter as tk
from tkinter import filedialog

def encode_image(image):
    """Convert a PIL Image to base64 string."""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def get_completion(prompt, images=[], model="gpt-4o"):
    """Make a request to OpenAI's API with optional image input."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    client = OpenAI(api_key=api_key)  # Pass API key explicitly
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt}
            ]
        }
    ]
    
    # Add images to the message if provided
    for img in images:
        try:
            base64_image = encode_image(img)
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }
            })
        except Exception as e:
            print(f"Error encoding image: {e}")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1000,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error making OpenAI API request: {e}")
        return None

def get_pdf_metadata(pdf_path):
    """Extract metadata from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        metadata = reader.metadata or {}
        
        info = {
            "Pages": len(reader.pages),
            "Title": metadata.get("/Title", "Not available"),
            "Author": metadata.get("/Author", "Not available"),
            "Creator": metadata.get("/Creator", "Not available"),
            "Producer": metadata.get("/Producer", "Not available"),
            "Creation Date": metadata.get("/CreationDate", "Not available"),
            "Modification Date": metadata.get("/ModDate", "Not available")
        }
        return info
    except Exception as e:
        print(f"Error extracting metadata: {e}")
        return {}

def main():
    # Load the .env file from your specified path
    env_path = r"C:\Users\rokas\Documents\FinCheck\OpenAI.env"
    load_dotenv(env_path)

    # Verify that the API key has loaded successfully
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found. Check your .env file location and content.")
        sys.exit(1)
    else:
        print("API key loaded successfully from .env file.\n")

    # Use a file picker (Tkinter) to select the PDF
    root = tk.Tk()
    root.withdraw()  # Hide the main tkinter window
    pdf_file = filedialog.askopenfilename(
        title="Select a PDF File",
        filetypes=[("PDF Files", "*.pdf")]
    )

    # Handle 'no selection' scenario
    if not pdf_file:
        print("No file selected. Exiting.")
        sys.exit(1)

    pdf_path = Path(pdf_file)

    # Check if the selected file exists
    if not pdf_path.exists():
        print(f"Error: File '{pdf_path}' does not exist")
        sys.exit(1)

    # Get and display PDF metadata
    print("PDF Metadata:")
    metadata = get_pdf_metadata(pdf_path)
    for key, value in metadata.items():
        print(f"{key}: {value}")

    # Convert PDF to images
    try:
        images = pdf2image.convert_from_path(pdf_path)
        print(f"\nFound {len(images)} pages in PDF.")
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        sys.exit(1)

    # Limit to first 20 pages
    max_pages = 20
    images = images[:max_pages] if len(images) > max_pages else images

    # Generate analysis using OpenAI
    prompt = "What do you see in these images? Please analyse each page in order, numbering your analysis for each page."
    response = get_completion(prompt, images)
    if response:
        print("\nComplete PDF analysis:", response)

if __name__ == "__main__":
    main()
