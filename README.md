<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <h1>FinCheck</h1>
    <p>This repository contains software designed to verify the authenticity of bank statements. It integrates numerical analysis, machine learning, and outsourced AI vision analysis.</p>

  <h2>Getting Started</h2>

  <h3>1. Clone Repository</h3>
    <pre><code>git clone &lt;repository-url&gt;</code></pre>

  <h3>2. Install Required Libraries</h3>
    <p>Ensure you have Python installed. Navigate to the project folder and install the required libraries:</p>
    <pre><code>pip install -r requirements.txt</code></pre>

  <p><strong>Required Libraries Include:</strong></p>
    <ul>
        <li>openai</li>
        <li>pdf2image</li>
        <li>PyPDF2</li>
        <li>python-dotenv</li>
        <li>streamlit</li>
        <li>matplotlib</li>
        <li>pandas</li>
        <li>numpy</li>
        <li>scikit-learn</li>
        <li>sqlite3</li>
    </ul>
    <p>You may also require the installation of <code>poppler</code> for PDF image conversion:</p>
    <ul>
        <li><strong>Windows:</strong> Download from <a href="http://blog.alivate.com.au/poppler-windows/" target="_blank">here</a> and update paths accordingly.</li>
    </ul>

  <h3>3. Set Up Environment Variables</h3>
    <p>Create a <code>OpenAI.env</code> file in your project directory containing:</p>
    <pre><code>OPENAI_API_KEY="your_openai_api_key_here"</code></pre>

  <h3>4. Configure File Paths</h3>
    <p>Ensure all file paths specified in:</p>
    <ul>
        <li><code>main.py</code></li>
        <li><code>SQLPreper.py</code></li>
        <li><code>MachineLearning.py</code></li>
    </ul>
    <p>point correctly to your local directories. Adjust paths explicitly marked in these scripts.</p>

  <h3>5. Run the Application</h3>
    <p>Open the project folder in VS Code, open a terminal, and execute:</p>
    <pre><code>python main.py</code></pre>
    <p>This will initiate the pipeline for bank statement verification.</p>

  <h2>Additional Usage</h2>
    <p>To utilise the web interface locally, run:</p>
    <pre><code>streamlit run app.py</code></pre>
    <p>Then open your browser to the URL displayed in the terminal.</p>

  <h2>Troubleshooting</h2>
    <ul>
        <li>Ensure the paths to files and the database are correctly set.</li>
        <li>Verify the OpenAI API key is valid and correctly loaded.</li>
    </ul>

  <h2>License</h2>
    <p>This project is for educational and demonstrative purposes only.</p>
</body>
</html>

