from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_bcrypt import Bcrypt
import sqlite3
import os
import re
from collections import Counter
import math
from dotenv import load_dotenv
import requests

load_dotenv()

try:
    from ml_models import predict_domain, match_mentors_ml, calculate_risk_score
    ML_AVAILABLE = True
    print("✅ ML Models loaded successfully!")
except ImportError:
    ML_AVAILABLE = False
    print("⚠️ ML models not available. Using basic algorithms. Install: pip install scikit-learn")

# HuggingFace Free API
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
HF_AVAILABLE = bool(HF_API_KEY)
if HF_AVAILABLE:
    print("✅ HuggingFace AI connected (FREE)!")
else:
    print("⚠️ HuggingFace not configured. Using rule-based chatbot.")

try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    OPENAI_AVAILABLE = True
    print("✅ OpenAI connected successfully!")
except:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI not available.")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "startup_secret")

bcrypt = Bcrypt(app)

# ---------- DATABASE ----------
DB_PATH = os.path.join(os.path.dirname(__file__), "startupconnect.db")

# Initialize DB on startup
with app.app_context():
    pass  # init_db() called below

# ---------- AI HELPER FUNCTIONS ----------
def classify_domain(description):
    """Domain classification - uses ML if available, otherwise keyword-based"""
    if ML_AVAILABLE:
        try:
            result = predict_domain(description)
            print(f"🤖 AI Domain Classification: {result}")
            return result
        except Exception as e:
            print(f"⚠️ ML classification failed: {e}, using fallback")
    
    # Fallback to keyword-based
    description_lower = description.lower()
    
    domains = {
        'AgriTech': ['agriculture', 'farming', 'crop', 'soil', 'harvest', 'agri', 'farm'],
        'FinTech': ['finance', 'payment', 'banking', 'money', 'transaction', 'wallet', 'loan'],
        'EdTech': ['education', 'learning', 'student', 'course', 'teaching', 'school', 'college'],
        'HealthTech': ['health', 'medical', 'hospital', 'doctor', 'patient', 'medicine', 'healthcare'],
        'E-Commerce': ['ecommerce', 'shopping', 'retail', 'marketplace', 'store', 'buy', 'sell']
    }
    
    scores = {}
    for domain, keywords in domains.items():
        score = sum(1 for keyword in keywords if keyword in description_lower)
        scores[domain] = score
    
    result = max(scores, key=scores.get) if max(scores.values()) > 0 else 'Other'
    print(f"🔑 Keyword-based Classification: {result}")
    return result

def calculate_text_similarity(text1, text2):
    """Calculate cosine similarity between two texts"""
    def get_word_freq(text):
        words = re.findall(r'\w+', text.lower())
        return Counter(words)
    
    freq1 = get_word_freq(text1)
    freq2 = get_word_freq(text2)
    
    all_words = set(freq1.keys()) | set(freq2.keys())
    
    vec1 = [freq1.get(word, 0) for word in all_words]
    vec2 = [freq2.get(word, 0) for word in all_words]
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0
    
    return dot_product / (magnitude1 * magnitude2)

def recommend_schemes(domain, stage):
    """Recommend government schemes based on domain and stage"""
    db = get_db()
    cur = db.cursor()
    
    # Match schemes by domain and stage
    cur.execute("""
        SELECT * FROM schemes 
        WHERE (domain LIKE ? OR domain = 'All') 
        AND (stage LIKE ? OR stage LIKE ?)
        LIMIT 3
    """, (f'%{domain}%', f'%{stage}%', '%All%'))
    
    schemes = cur.fetchall()
    cur.close()
    db.close()
    
    return schemes

def get_db():
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS startups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            startup_name TEXT NOT NULL,
            idea_description TEXT NOT NULL,
            domain TEXT,
            stage TEXT,
            team_size INTEGER,
            revenue_model TEXT,
            prototype_status TEXT,
            market_validation TEXT,
            readiness_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schemes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheme_name TEXT NOT NULL,
            domain TEXT,
            stage TEXT,
            funding_type TEXT,
            description TEXT,
            eligibility TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS mentor_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            mentor_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users(id),
            FOREIGN KEY (mentor_id) REFERENCES users(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS investor_interests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            investor_id INTEGER NOT NULL,
            startup_id INTEGER NOT NULL,
            status TEXT DEFAULT 'interested',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (investor_id) REFERENCES users(id),
            FOREIGN KEY (startup_id) REFERENCES startups(id)
        )
        """
    )
    
    # Add sample government schemes
    cur.execute("SELECT COUNT(*) FROM schemes")
    count = cur.fetchone()[0]
    if count == 0:
        schemes = [
            ("Startup India Seed Fund Scheme", "All", "Idea,Prototype", "Grant", 
             "Financial assistance to startups for proof of concept, prototype development, product trials, market entry and commercialization.",
             "DPIIT recognized startups incorporated within 2 years"),
            ("NIDHI-PRAYAS", "All", "Idea,Prototype", "Grant", 
             "Proof of concept grant up to Rs 10 lakhs for young innovators to translate their ideas into prototypes.",
             "Students, faculty, and startups in early stage"),
            ("Atal Innovation Mission", "EdTech,All", "Idea", "Incubation", 
             "Promotes innovation and entrepreneurship through Atal Tinkering Labs and incubation centers.",
             "Students and early-stage startups"),
            ("NABARD Startup Scheme", "AgriTech", "Prototype,MVP", "Loan", 
             "Financial support for agri-startups focusing on rural development and agriculture innovation.",
             "AgriTech startups with working prototype"),
            ("Credit Guarantee Scheme", "All", "MVP,Growth", "Guarantee", 
             "Collateral-free credit to startups through CGTMSE.",
             "Registered startups with business plan"),
            ("Stand-Up India", "All", "Growth", "Loan", 
             "Bank loans between Rs 10 lakh to Rs 1 crore for SC/ST and women entrepreneurs.",
             "Women and SC/ST entrepreneurs"),
            ("MSME Innovation Scheme", "All", "Prototype,MVP", "Grant", 
             "Support for innovative MSMEs in product development and commercialization.",
             "Registered MSMEs with innovative products"),
            ("Digital India Startup Hub", "EdTech,FinTech", "All", "Mentorship", 
             "Platform connecting startups with investors, mentors, and government schemes.",
             "All tech startups")
        ]
        cur.executemany("""
            INSERT INTO schemes (scheme_name, domain, stage, funding_type, description, eligibility)
            VALUES (?, ?, ?, ?, ?, ?)
        """, schemes)
    
    conn.commit()
    cur.close()
    conn.close()

# ---------- HOME ----------
@app.route("/")
def home():
    return render_template("home.html", show_footer=True)

# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        role = request.form["role"]
        password = request.form["password"]

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

        try:
            db = get_db()
            cur = db.cursor()
        except Exception:
            flash("Database connection error. Please check your database settings.", "danger")
            return render_template("register.html", show_footer=False)

        cur.execute("SELECT id FROM users WHERE email=?", (email,))
        if cur.fetchone():
            flash("Email already exists", "danger")
            cur.close()
            db.close()
            return redirect(url_for("register"))

        cur.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, hashed_pw, role)
        )

        db.commit()
        cur.close()
        db.close()

        flash("Registration successful!", "success")
        return redirect(url_for("login"))

    return render_template("register.html", show_footer=False)

# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        try:
            db = get_db()
            cur = db.cursor()
        except Exception:
            flash("Database connection error. Please check your database settings.", "danger")
            return render_template("login.html", show_footer=False)

        cur.execute("SELECT id, password, role FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        cur.close()
        db.close()

        if user and bcrypt.check_password_hash(user[1], password):
            session["user_id"] = user[0]
            session["role"] = user[2]
            return redirect(url_for("dashboard"))

        flash("Invalid credentials", "danger")

    return render_template("login.html", show_footer=False)

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    role = session.get("role")
    if role == "student":
        return redirect(url_for("student_dashboard"))
    elif role == "investor":
        return redirect(url_for("investor_dashboard"))
    elif role == "mentor":
        return redirect(url_for("mentor_dashboard"))
    else:
        return redirect(url_for("home"))

# ---------- STUDENT DASHBOARD ----------
@app.route("/student/dashboard")
@app.route("/student/dashboard/<section>")
def student_dashboard(section="overview"):
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("login"))
    
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT name FROM users WHERE id=?", (session["user_id"],))
    user = cur.fetchone()
    
    data = {}
    
    if section == "submit_idea":
        pass
    elif section == "my_ideas":
        cur.execute("SELECT * FROM startups WHERE student_id=?", (session["user_id"],))
        data["startups"] = cur.fetchall()
    elif section == "mentors":
        cur.execute("SELECT id, name, email FROM users WHERE role='mentor'")
        data["mentors"] = cur.fetchall()
    elif section == "investors":
        cur.execute("SELECT id, name, email FROM users WHERE role='investor'")
        data["investors"] = cur.fetchall()
    elif section == "schemes":
        cur.execute("SELECT * FROM schemes")
        data["schemes"] = cur.fetchall()
    elif section == "messages":
        cur.execute("""
            SELECT m.*, u.name as sender_name FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.receiver_id=? OR m.sender_id=?
            ORDER BY m.created_at DESC
        """, (session["user_id"], session["user_id"]))
        data["messages"] = cur.fetchall()
        cur.execute("SELECT id, name, email FROM users WHERE role='mentor'")
        data["mentors"] = cur.fetchall()
        cur.execute("SELECT id, name, email FROM users WHERE role='investor'")
        data["investors"] = cur.fetchall()
    elif section == "progress":
        cur.execute("SELECT * FROM startups WHERE student_id=?", (session["user_id"],))
        data["startups"] = cur.fetchall()
    
    cur.close()
    db.close()
    
    return render_template("student_dashboard.html", name=user[0], section=section, data=data, show_footer=False)

@app.route("/student/submit_idea", methods=["POST"])
def submit_idea():
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("login"))
    
    startup_name = request.form["startup_name"]
    idea_description = request.form["idea_description"]
    domain = request.form["domain"]
    stage = request.form["stage"]
    team_size = request.form["team_size"]
    revenue_model = request.form["revenue_model"]
    prototype_status = request.form["prototype_status"]
    market_validation = request.form["market_validation"]
    
    # AI Domain Classification (if user didn't select or selected 'Other')
    if not domain or domain == "Other":
        domain = classify_domain(idea_description)
        print(f"✨ Auto-classified domain: {domain}")
    
    # AI Readiness score calculation
    score = 0
    if market_validation == "yes": score += 25
    if revenue_model: score += 20
    if prototype_status == "completed": score += 25
    elif prototype_status == "in_progress": score += 15
    if int(team_size) >= 3: score += 20
    else: score += 10
    score += 10  # Base score
    
    print(f"📊 Readiness Score Calculated: {score}/100")
    print(f"   - Market Validation: {market_validation}")
    print(f"   - Revenue Model: {'Yes' if revenue_model else 'No'}")
    print(f"   - Prototype: {prototype_status}")
    print(f"   - Team Size: {team_size}")
    
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO startups (student_id, startup_name, idea_description, domain, stage, 
                            team_size, revenue_model, prototype_status, market_validation, readiness_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (session["user_id"], startup_name, idea_description, domain, stage, 
           team_size, revenue_model, prototype_status, market_validation, score))
    
    startup_id = cur.lastrowid
    
    # AI Scheme Recommendation
    recommended = recommend_schemes(domain, stage)
    print(f"🏛️ Recommended {len(recommended)} government schemes for {domain} at {stage} stage")
    
    db.commit()
    cur.close()
    db.close()
    
    print(f"✅ Startup '{startup_name}' submitted successfully!\n")
    flash("Startup idea submitted successfully!", "success")
    return redirect(url_for("student_dashboard", section="my_ideas"))

@app.route("/student/send_message", methods=["POST"])
def student_send_message():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    receiver_id = request.form["receiver_id"]
    message = request.form["message"]
    
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
                (session["user_id"], receiver_id, message))
    db.commit()
    cur.close()
    db.close()
    
    flash("Message sent successfully!", "success")
    role = session.get("role")
    if role == "student":
        return redirect(url_for("student_dashboard", section="messages"))
    elif role == "investor":
        return redirect(url_for("investor_dashboard", section="messages"))
    elif role == "mentor":
        return redirect(url_for("mentor_dashboard", section="messages"))
    return redirect(url_for("dashboard"))

@app.route("/connect_mentor/<int:mentor_id>")
def connect_mentor(mentor_id):
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("login"))
    
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO mentor_requests (student_id, mentor_id) VALUES (?, ?)",
                (session["user_id"], mentor_id))
    db.commit()
    cur.close()
    db.close()
    
    flash("Connection request sent to mentor!", "success")
    return redirect(url_for("student_dashboard", section="mentors"))

# ---------- INVESTOR DASHBOARD ----------
@app.route("/investor/dashboard")
@app.route("/investor/dashboard/<section>")
def investor_dashboard(section="overview"):
    if "user_id" not in session or session.get("role") != "investor":
        return redirect(url_for("login"))
    
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT name FROM users WHERE id=?", (session["user_id"],))
    user = cur.fetchone()
    
    data = {}
    
    if section == "startups":
        cur.execute("""
            SELECT s.*, u.name as student_name FROM startups s
            JOIN users u ON s.student_id = u.id
            ORDER BY s.readiness_score DESC
        """)
        data["startups"] = cur.fetchall()
    elif section == "shortlisted":
        cur.execute("""
            SELECT s.*, u.name as student_name FROM startups s
            JOIN users u ON s.student_id = u.id
            JOIN investor_interests ii ON s.id = ii.startup_id
            WHERE ii.investor_id = ?
        """, (session["user_id"],))
        data["startups"] = cur.fetchall()
    elif section == "messages":
        cur.execute("""
            SELECT m.*, u.name as sender_name FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.receiver_id=? OR m.sender_id=?
            ORDER BY m.created_at DESC
        """, (session["user_id"], session["user_id"]))
        data["messages"] = cur.fetchall()
        cur.execute("SELECT id, name, email FROM users WHERE role='student'")
        data["students"] = cur.fetchall()
        cur.execute("SELECT id, name, email FROM users WHERE role='mentor'")
        data["mentors"] = cur.fetchall()
    elif section == "revenue":
        cur.execute("""
            SELECT s.startup_name, s.revenue_model, s.readiness_score, u.name as student_name
            FROM startups s
            JOIN users u ON s.student_id = u.id
            JOIN investor_interests ii ON s.id = ii.startup_id
            WHERE ii.investor_id = ?
        """, (session["user_id"],))
        data["startups"] = cur.fetchall()
    elif section == "risk":
        cur.execute("""
            SELECT s.startup_name, s.stage, s.market_validation, s.prototype_status, s.readiness_score, u.name as student_name
            FROM startups s
            JOIN users u ON s.student_id = u.id
            JOIN investor_interests ii ON s.id = ii.startup_id
            WHERE ii.investor_id = ?
        """, (session["user_id"],))
        data["startups"] = cur.fetchall()
    elif section == "growth":
        cur.execute("""
            SELECT s.startup_name, s.stage, s.team_size, s.readiness_score, s.created_at, u.name as student_name
            FROM startups s
            JOIN users u ON s.student_id = u.id
            JOIN investor_interests ii ON s.id = ii.startup_id
            WHERE ii.investor_id = ?
        """, (session["user_id"],))
        data["startups"] = cur.fetchall()
    elif section == "analytics":
        cur.execute("SELECT domain, COUNT(*) as count FROM startups GROUP BY domain")
        data["domain_stats"] = cur.fetchall()
    
    cur.close()
    db.close()
    
    return render_template("investor_dashboard.html", name=user[0], section=section, data=data, show_footer=False)

@app.route("/investor/shortlist/<int:startup_id>")
def shortlist_startup(startup_id):
    if "user_id" not in session or session.get("role") != "investor":
        return redirect(url_for("login"))
    
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO investor_interests (investor_id, startup_id) VALUES (?, ?)",
                (session["user_id"], startup_id))
    db.commit()
    cur.close()
    db.close()
    
    flash("Startup shortlisted successfully!", "success")
    return redirect(url_for("investor_dashboard", section="startups"))

# ---------- MENTOR DASHBOARD ----------
@app.route("/mentor/dashboard")
@app.route("/mentor/dashboard/<section>")
def mentor_dashboard(section="overview"):
    if "user_id" not in session or session.get("role") != "mentor":
        return redirect(url_for("login"))
    
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT name FROM users WHERE id=?", (session["user_id"],))
    user = cur.fetchone()
    
    data = {}
    
    if section == "students":
        cur.execute("""
            SELECT s.*, u.name as student_name FROM startups s
            JOIN users u ON s.student_id = u.id
            ORDER BY s.created_at DESC
        """)
        data["startups"] = cur.fetchall()
    elif section == "mentees":
        cur.execute("""
            SELECT u.id, u.name, u.email FROM users u
            JOIN mentor_requests mr ON u.id = mr.student_id
            WHERE mr.mentor_id = ? AND mr.status = 'accepted'
        """, (session["user_id"],))
        data["mentees"] = cur.fetchall()
    elif section == "requests":
        cur.execute("""
            SELECT mr.*, u.name as student_name FROM mentor_requests mr
            JOIN users u ON mr.student_id = u.id
            WHERE mr.mentor_id = ? AND mr.status = 'pending'
        """, (session["user_id"],))
        data["requests"] = cur.fetchall()
    elif section == "schemes":
        cur.execute("SELECT * FROM schemes")
        data["schemes"] = cur.fetchall()
    elif section == "messages":
        cur.execute("""
            SELECT m.*, u.name as sender_name FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.receiver_id=? OR m.sender_id=?
            ORDER BY m.created_at DESC
        """, (session["user_id"], session["user_id"]))
        data["messages"] = cur.fetchall()
        cur.execute("SELECT id, name, email FROM users WHERE role='student'")
        data["students"] = cur.fetchall()
        cur.execute("SELECT id, name, email FROM users WHERE role='investor'")
        data["investors"] = cur.fetchall()
    
    cur.close()
    db.close()
    
    return render_template("mentor_dashboard.html", name=user[0], section=section, data=data, show_footer=False)

@app.route("/mentor/accept_request/<int:request_id>")
def accept_mentor_request(request_id):
    if "user_id" not in session or session.get("role") != "mentor":
        return redirect(url_for("login"))
    
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE mentor_requests SET status='accepted' WHERE id=?", (request_id,))
    db.commit()
    cur.close()
    db.close()
    
    flash("Mentor request accepted!", "success")
    return redirect(url_for("mentor_dashboard", section="requests"))

# ---------- CHATBOT ----------
@app.route("/chatbot", methods=["POST"])
def chatbot():
    if "user_id" not in session:
        return jsonify({"response": "Please login to use the chatbot."})
    
    user_question = request.json.get("question", "")
    role = session.get("role")
    
    db = get_db()
    cur = db.cursor()
    
    # Gather context from database
    cur.execute("SELECT COUNT(*) FROM startups")
    startup_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE role='mentor'")
    mentor_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE role='investor'")
    investor_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM schemes")
    scheme_count = cur.fetchone()[0]
    
    context = f"""You are an AI assistant for StartupConnect TN. Platform has {startup_count} startups, {mentor_count} mentors, {investor_count} investors, {scheme_count} schemes. User role: {role}. Answer questions about startups, mentors, investors, schemes, and business advice."""
    
    cur.close()
    db.close()
    
    # Try HuggingFace (FREE)
    if HF_AVAILABLE:
        try:
            API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-large"
            headers = {"Authorization": f"Bearer {HF_API_KEY}"}
            payload = {"inputs": f"{context}\n\nQuestion: {user_question}\nAnswer:"}
            
            hf_response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
            if hf_response.status_code == 200:
                result = hf_response.json()
                if isinstance(result, list) and len(result) > 0:
                    return jsonify({"response": result[0].get("generated_text", "I'm here to help!")})
        except Exception as e:
            print(f"HuggingFace Error: {e}")
    
    # Try OpenAI (PAID)
    if OPENAI_AVAILABLE:
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": context},
                    {"role": "user", "content": user_question}
                ],
                max_tokens=200,
                temperature=0.7
            )
            return jsonify({"response": response.choices[0].message.content})
        except Exception as e:
            print(f"OpenAI Error: {e}")
    
    # Fallback to rule-based (FREE)
    user_question_lower = user_question.lower()
    
    if any(word in user_question_lower for word in ["startup", "idea", "business"]):
        response = f"We have {startup_count} startups registered. Students can submit ideas, get AI domain classification, and receive readiness scores to attract investors."
    elif any(word in user_question_lower for word in ["mentor", "mentorship", "guide"]):
        response = f"We have {mentor_count} mentors available. Mentors provide guidance, feedback, and industry connections. Connect from the Find Mentors section."
    elif any(word in user_question_lower for word in ["investor", "investment", "funding"]):
        response = f"We have {investor_count} investors. They look for high-potential startups with good readiness scores. Build your prototype and validate your market."
    elif any(word in user_question_lower for word in ["scheme", "government", "grant", "loan"]):
        response = f"We have {scheme_count} government schemes including grants, loans, and incubation support. Check Govt Schemes section for matches."
    elif any(word in user_question_lower for word in ["readiness", "score"]):
        response = "Readiness Score (0-100): Market Validation (25pts), Revenue Model (20pts), Prototype Status (25pts), Team Size (20pts). Higher scores attract investors."
    elif any(word in user_question_lower for word in ["domain", "agritech", "fintech", "edtech"]):
        response = "Domains: AgriTech, FinTech, EdTech, HealthTech, E-Commerce. Our AI auto-classifies your startup based on description."
    elif "help" in user_question_lower:
        response = "I can help with: Startup info, Mentor/Investor details, Government schemes, Readiness scores, Platform features, and business advice!"
    else:
        response = "I'm your startup assistant! Ask me about startups, mentors, investors, schemes, readiness scores, or platform features."
    
    return jsonify({"response": response})


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/test_modal")
def test_modal():
    return render_template("test_modal.html")

# ---------- RUN ----------
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
else:
    # Called by gunicorn on Render
    init_db()