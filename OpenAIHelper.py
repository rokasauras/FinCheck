from openai import OpenAI
import os
import base64
from io import BytesIO

class OpenAIHelper:
    """
    Handles communication with the OpenAI API for image analysis.
    """

    def __init__(self, model="gpt-4o"):
        self.model = model
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = OpenAI(api_key=api_key)

    def encode_image(self, image):
        """Convert a PIL Image to base64 string."""
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def analyse_bank_statements(self, images):
        """
        Analyse a set of images to determine if they are bank statements,
        and extract key information if they are.
        """
        # System message content for the AI
        system_content = (
            "You are a precise OCR data extraction AI. "
            "We have multiple page images of a PDF. Produce a JSON object with a 'pages' array, "
            "where each element corresponds to one page. For the FIRST page only, include the following fields: "
            "  - \"classification\" : \"bank_statement\" or \"other\" "
            "  - \"business_name\" : string or \"unknown\" "
            "  - \"business_address\" : string or \"unknown\" "
            "  - \"bank_name\" : string or \"unknown\" "
            "On ALL pages (including the first page), include: "
            "  - \"page_number\" : integer "
            "  - \"opening_balance\" : float or \"unknown\" "
            "  - \"closing_balance\" : float or \"unknown\" "
            "  - \"transaction_count\" : int or \"unknown\" "
            "  - \"transactions\" : an array of objects, each having "
            "       { \"date\": \"YYYY-MM-DD or unknown\", \"amount\": \"+300\" or \"-200\" or \"unknown\" } "
            "    If no transactions are found, use \"unknown\". "
            "  - \"page_text\" : EVERY piece of visible text, including fine print, footnotes, headers, footers, marginal notes, disclaimers, watermarks, faint or faded text, and text at extreme edges or corners. Omit nothing. "
            "Additionally, include at the END of the JSON object an \"ai_tampering_check\" object containing: "
            "{ "
            "  \"tampered\": true or false, "
            "  \"explanation\": \"Clear explanation if tampering is suspected or 'No obvious tampering detected.'\" "
            "}. "
            "Use the exact JSON format below (no extra commentary): "
            "{ "
            "  \"pages\": [ "
            "    { "
            "      \"page_number\": 1, "
            "      \"classification\": \"bank_statement\" or \"other\", "
            "      \"business_name\": \"string or unknown\", "
            "      \"business_address\": \"string or unknown\", "
            "      \"bank_name\": \"string or unknown\", "
            "      \"opening_balance\": \"float or unknown\", "
            "      \"closing_balance\": \"float or unknown\", "
            "      \"transaction_count\": \"int or unknown\", "
            "      \"transactions\": [ "
            "          { "
            "            \"date\": \"YYYY-MM-DD\" or \"unknown\", "
            "            \"amount\": \"+300\" or \"-200\" or \"unknown\" "
            "          } "
            "       ] or \"unknown\", "
            "      \"page_text\": \"string or unknown\" "
            "    } "
            "  ], "
            "  \"ai_tampering_check\": { "
            "      \"tampered\": true or false, "
            "      \"explanation\": \"Clear explanation if tampering is suspected or 'No obvious tampering detected.'\" "
            "  } "
            "}. "
            "If a page is NOT the first page, do NOT output \"classification\", \"business_name\", \"business_address\", "
            "or \"bank_name\" for that page (leave them out entirely). "
            "Return strictly valid JSON and nothing else."
        )

        # Prepare the messages for the AI
        messages = [
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user",
                "content": []
            }
        ]

        # Add images to the user message content
        for img in images:
            try:
                base64_image = self.encode_image(img)
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                })
            except Exception as e:
                print(f"Error encoding image: {e}")
                continue
        
        # Call the OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=10000,  # Increased for JSON output
                response_format={"type": "json_object"}  # Ensure JSON output
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return None
