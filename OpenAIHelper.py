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
        Analyze images of potential bank statements and extract structured data.
        Returns JSON-formatted response with page analysis.
        """
        # System message content for the AI
        system_content = (
            "You are a data extraction AI. "
            "Your task is to analyse each page image to see if it's a business bank statement or something else. "
            "For each page: "
            " 1) Determine 'classification' as 'bank_statement' or 'other'. "
            " 2) If it's a bank_statement, extract as many of these fields as possible; if unknown, use 'unknown': "
            "    - business_name "
            "    - business_address "
            "    - bank_name "
            "    - opening_balance "
            "    - closing_balance "
            "    - transaction_count "
            "    - page_text (the entire text you can read/infer from the page) "
            "Produce an array of objects, one per page. "
            "Use this JSON format exactly (no extra commentary): "
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
            "      \"page_text\": \"string or unknown\" "
            "    } "
            "  ] "
            "}. "
            "Return valid JSON only. Do not include extra text."
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

        # Add images to the user content
        for img in images:
            try:
                base64_image = self.encode_image(img)
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                })
            except Exception as e: #  Handle image encoding errors
                print(f"Error encoding image: {e}")
                continue

        # Call the OpenAI API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=2000,  # Increase if AI JSON response is too short
                response_format={"type": "json_object"}  # Ensure JSON output
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return None
