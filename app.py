
from flask import Flask, request, render_template_string, flash
import PyPDF2
from docx import Document
import re
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Required for flashing messages

def extract_text_from_pdf(file):
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return ""

def extract_text_from_docx(file):
    doc = Document(file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def extract_cgpa(text):
    # More comprehensive patterns for CGPA extraction
    # Updated CGPA regex pattern
    cgpa_patterns = [
        r'(?:cgpa|gpa)[\s:]*([0-9]{1,2}(?:\.[0-9]{1,2})?)',
        r'(?:cgpa|gpa)[\s:]*([0-9]{1,2}(?:\.[0-9]{1,2})?)\s*/\s*10',
        r'(?:aggregate|score)[\s:]*([0-9]{1,2}(?:\.[0-9]{1,2})?)',
        r'grade point average[\s:]*([0-9]{1,2}(?:\.[0-9]{1,2})?)',
        r'cumulative grade point average[\s:]*([0-9]{1,2}(?:\.[0-9]{1,2})?)'
    ]

    
    text_lower = text.lower()
    for pattern in cgpa_patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                cgpa = float(match.group(1))
                if 0 <= cgpa <= 10:  # Validate CGPA range
                    return cgpa
            except ValueError:
                continue
    return None

def calculate_ats_score(text, cgpa=None):
    import nltk
    from nltk.stem import PorterStemmer
    nltk.download('punkt', quiet=True)
    
    ps = PorterStemmer()
    tokens = nltk.word_tokenize(text.lower())
    stemmed_text = [ps.stem(word) for word in tokens]

    keyword_categories = {
        'technical_skills': {
            'weight': 0.35,
            'keywords': ['python', 'java', 'javascript', 'html', 'css', 'sql', 'machine learning',
                         'data analysis', 'aws', 'docker', 'git', 'react', 'node', 'mongodb',
                         'c++', 'numpy', 'pandas', 'tensorflow', 'pytorch', 'spring', 'django']
        },
        'soft_skills': {
            'weight': 0.25,
            'keywords': ['leadership', 'teamwork', 'communication', 'problem solving', 
                         'analytical', 'initiative', 'project management']
        },
        'education': {
            'weight': 0.2,
            'keywords': ['bachelor', 'master', 'phd', 'degree', 'university', 'college']
        },
        'experience': {
            'weight': 0.2,
            'keywords': ['experience', 'internship', 'project', 'developed', 'implemented',
                         'managed', 'led', 'created', 'achieved']
        }
    }

    final_score = 0
    feedback = []

    for category, data in keyword_categories.items():
        match_count = 0
        for keyword in data['keywords']:
            stemmed_keyword = ps.stem(keyword)
            if stemmed_keyword in stemmed_text:
                match_count += 1

        total_keywords = len(data['keywords'])
        match_ratio = match_count / total_keywords
        category_score = match_ratio * 100
        weighted_score = category_score * data['weight']
        final_score += weighted_score

        if match_ratio < 0.4:
            feedback.append(f"Consider adding more {category.replace('_', ' ')} to your resume.")

    # Calibration boost to bring raw score in line with real-world ATS
    calibrated_score = min(round(final_score * 1.15, 2), 100.0)
    return calibrated_score, feedback



HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Campus Placement Predictor</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <!-- Google Fonts for a clean, modern look -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(to right, #f5f7fa, #c3cfe2);
            margin: 0;
            padding: 0;
            color: #2c3e50;
        }

        .container {
            max-width: 900px;
            margin: 50px auto;
            background: #ffffff;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
        }

        h1 {
            text-align: center;
            font-size: 2.4rem;
            margin-bottom: 30px;
            color: #34495e;
        }

        label {
            font-weight: 600;
            display: block;
            margin-top: 20px;
            margin-bottom: 8px;
        }

        input[type="file"],
        input[type="number"] {
            width: 100%;
            padding: 12px;
            border: 1px solid #dfe6e9;
            border-radius: 8px;
            font-size: 1rem;
        }

        input[type="file"] {
            padding: 10px 12px;
            background-color: #ecf0f1;
        }

        button {
            margin-top: 30px;
            width: 100%;
            background-color: #3498db;
            color: white;
            padding: 14px;
            border: none;
            border-radius: 10px;
            font-size: 1.1rem;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }

        button:hover {
            background-color: #2980b9;
        }

        .result-box {
            margin-top: 40px;
            padding: 20px;
            background-color: #f1f2f6;
            border-left: 5px solid #3498db;
            border-radius: 10px;
        }

        .result-box h2 {
            margin-top: 0;
            font-size: 1.5rem;
            color: #2d3436;
        }

        .suggestions {
            margin-top: 20px;
            list-style: disc inside;
        }

        @media (max-width: 600px) {
            .container {
                padding: 20px;
                margin: 20px;
            }

            h1 {
                font-size: 2rem;
            }

            button {
                font-size: 1rem;
            }
        }
    </style>
</head>
<body>

<div class="container">
    <h1>Campus Placement Predictor</h1>
    <form method="POST" enctype="multipart/form-data">
        <label for="resume">Upload Resume (PDF/DOCX):</label>
        <input type="file" id="resume" name="resume" accept=".pdf,.docx" required>

        <label for="cgpa">Enter your CGPA (0-10):</label>
        <input type="number" id="cgpa" name="cgpa" step="0.01" min="0" max="10" required>

        <label for="ats_score">Enter your ATS Score (0-100):</label>
        <input type="number" id="ats_score" name="ats_score" min="0" max="100" required>

        <button type="submit">Predict Placement Chance</button>
    </form>

    {% if result %}
    <div class="result-box">
        <h2>Prediction Result</h2>
        <p><strong>CGPA:</strong> {{ cgpa }}</p>
        <p><strong>ATS Score:</strong> {{ ats_score }}</p>
        <p><strong>Prediction:</strong> {{ result }}</p>

        {% if feedback %}
        <h3>Suggestions to Improve Your Chances:</h3>
        <ul class="suggestions">
            {% for suggestion in feedback %}
            <li>{{ suggestion }}</li>
            {% endfor %}
        </ul>
        {% endif %}
    </div>
    {% endif %}
</div>

</body>
</html>

'''

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    placed = False
    cgpa = None
    ats_score = None
    uploaded_resume = False
    extracted_cgpa = None
    
    if request.method == "POST":
        if 'resume' in request.files and request.files['resume'].filename:
            file = request.files['resume']
            uploaded_resume = True
            
            # Extract text from resume
            if file.filename.endswith('.pdf'):
                text = extract_text_from_pdf(file)
            elif file.filename.endswith('.docx'):
                text = extract_text_from_docx(file)
            else:
                return "Invalid file format. Please upload PDF or DOCX files only."
            
            # Calculate ATS score, feedback and extract CGPA
            ats_score, feedback = calculate_ats_score(text)
            
            # Extract CGPA using the dedicated function
            extracted_cgpa = extract_cgpa(text)
            
            # Use extracted CGPA if available, otherwise use manual input
            if extracted_cgpa is not None:
                cgpa = extracted_cgpa
            else:
                cgpa_input = request.form.get("cgpa", "")
                if not cgpa_input:
                    return "Please enter your CGPA since it couldn't be extracted from the resume"
                try:
                    cgpa = float(cgpa_input)
                except ValueError:
                    return "Please enter a valid CGPA number"
        else:
            # Manual input with validation
            cgpa_input = request.form.get("cgpa", "")
            ats_score_input = request.form.get("ats_score", "")
            
            if not cgpa_input or not ats_score_input:
                return "Please fill in both CGPA and ATS score"
                
            try:
                cgpa = float(cgpa_input)
                ats_score = float(ats_score_input)
            except ValueError:
                return "Please enter valid numerical values for CGPA and ATS score"
        
        # Prediction logic
        # Prediction logic
        if cgpa >= 9.0 and ats_score >= 75:
            result = "Excellent profile! You're highly competitive for campus placements!"
            placed = True
        elif cgpa >= 7.0 and ats_score >= 60:
            result = "Good chance! Keep your resume sharp and prepare for interviews."
            placed = True
        else:
            result = "You can improve! Boost your resume and gain more experience to stand out."
            placed = False

    
    return render_template_string(
        HTML_TEMPLATE,
        result=result,
        placed=placed,
        cgpa=cgpa,
        ats_score=ats_score,
        uploaded_resume=uploaded_resume,
        extracted_cgpa=extracted_cgpa
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
