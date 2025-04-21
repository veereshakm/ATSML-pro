
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
    keyword_categories = {
        'technical_skills': {
            'weight': 0.3,
            'keywords': ['python', 'java', 'javascript', 'html', 'css', 'sql', 'machine learning',
                         'data analysis', 'aws', 'docker', 'git', 'react', 'node', 'mongodb',
                         'c++', 'numpy', 'pandas', 'tensorflow', 'pytorch', 'spring', 'django']
        },
        'soft_skills': {
            'weight': 0.2,
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

    text = text.lower()
    final_score = 0
    feedback = []

    for category, data in keyword_categories.items():
        match_count = 0
        for keyword in data['keywords']:
            # Use regex for better matching (like 'node', 'nodejs', 'node.js')
            if re.search(rf'\b{re.escape(keyword)}\b', text):
                match_count += 1

        total_keywords = len(data['keywords'])
        category_score = (match_count / total_keywords) * 100
        weighted_score = category_score * data['weight']
        final_score += weighted_score

        if category_score < 40:
            feedback.append(f"Consider adding more {category.replace('_', ' ')} to your resume.")

    return round(final_score, 2), feedback


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Campus Placement Predictor</title>
    <style>
        @keyframes celebrate {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        @keyframes motivate {
            0% { transform: translateX(-5px); }
            50% { transform: translateX(5px); }
            100% { transform: translateX(-5px); }
        }
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
        body { 
            font-family: 'Poppins', sans-serif; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 40px;
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
            min-height: 100vh;
            color: #2d3436;
        }
        .form-group { 
            margin: 20px 0; 
            background: rgba(255, 255, 255, 0.9);
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            transition: transform 0.3s ease;
        }
        .form-group:hover {
            transform: translateY(-5px);
        }
        input { 
            padding: 12px;
            width: 100%;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        input:focus {
            border-color: #4CAF50;
            outline: none;
            box-shadow: 0 0 5px rgba(76,175,80,0.3);
        }
        button { 
            padding: 15px 30px;
            background: #4CAF50;
            color: white;
            border: none;
            cursor: pointer;
            border-radius: 25px;
            font-size: 16px;
            transition: all 0.3s ease;
            width: 100%;
            margin-top: 20px;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(76,175,80,0.4);
        }
        .result { 
            margin-top: 30px;
            padding: 20px;
            border-radius: 10px;
            font-size: 18px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .success { 
            background: #4CAF50;
            color: white;
            animation: celebrate 1s ease infinite;
        }
        .failure { 
            background: #ff6b6b;
            color: white;
            animation: motivate 2s ease infinite;
        }
        .upload-section {
            margin-bottom: 20px;
        }
        .or-divider {
            text-align: center;
            margin: 20px 0;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h2>Campus Placement Predictor</h2>
    <div style="background: #ffeeba; color: #856404; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #ffeeba;">
        <strong>Note:</strong> Please ensure your resume includes your CGPA information (e.g., "CGPA: 8.5" or "GPA: 8.5/10"). If not found, you'll need to enter it manually.
    </div>
    <form method="POST" enctype="multipart/form-data">
        <div class="form-group upload-section">
            <label>Upload Your Resume (PDF or DOCX):</label><br>
            <input type="file" name="resume" accept=".pdf,.docx">
        </div>
        <div class="or-divider">OR</div>
        <div class="form-group">
            <label>CGPA (0-10):</label><br>
            <input type="number" name="cgpa" step="0.01" min="0" max="10" value="{{ cgpa if cgpa else '' }}">
        </div>
        <div class="form-group">
            <label>ATS Score (0-100):</label><br>
            <input type="number" name="ats_score" min="0" max="100" value="{{ ats_score if ats_score else '' }}">
        </div>
        <button type="submit">Predict</button>
        {% if result %}
        <button type="button" onclick="window.location.href='/'" style="background: #ff6b6b; margin-top: 10px;">Reset</button>
        {% endif %}
    </form>
    {% if result %}
    <div class="result {{ 'success' if placed else 'failure' }}">
        {% if uploaded_resume %}
        <p><strong>Resume Analysis:</strong><br>
        Calculated ATS Score: {{ ats_score }}<br>
        {% if extracted_cgpa %}
        Extracted CGPA: {{ extracted_cgpa }}<br>
        {% endif %}
        </p>
        {% endif %}
        <p><strong>Final Scores:</strong><br>
        CGPA: {{ cgpa }}<br>
        ATS Score: {{ ats_score }}</p>
        <p>{{ result }}</p>
        {% if feedback %}
        <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
            <h3>Resume Improvement Suggestions:</h3>
            <ul style="list-style-type: disc; margin-left: 20px;">
                {% for suggestion in feedback %}
                <li>{{ suggestion }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}
    </div>
    {% endif %}
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
