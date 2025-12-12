import streamlit as st
from google import genai
import time
import random
from datetime import datetime, timedelta
import json
import hashlib
import base64
from io import BytesIO

# ─── PAGE CONFIGURATION ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="📘 SmartPrep AI Tutor - JAMB Edition",
    layout="centered"
)

# ─── IMPROVED STYLING WITH GAMIFICATION ELEMENTS ─────────────────────────────────
st.markdown("""
<style>
    .main-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .home-button {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1000;
        background: #4f46e5;
        color: white;
        border: none;
        border-radius: 50px;
        padding: 10px 20px;
        font-weight: bold;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
        transition: all 0.3s ease;
    }
    .home-button:hover {
        background: #3730a3;
        box-shadow: 0 6px 16px rgba(79, 70, 229, 0.4);
        transform: translateY(-2px);
    }
    .nav-bar {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 0.75rem;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: white;
    }
    .nav-title {
        font-size: 1.5rem;
        font-weight: bold;
        margin: 0;
    }
    .nav-stats {
        display: flex;
        gap: 1rem;
        font-size: 0.9rem;
    }
    .nav-stats span {
        background: rgba(255, 255, 255, 0.2);
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
    }
    .quiz-container {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 1rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .success-msg {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        text-align: center;
        border-left: 4px solid #28a745;
    }
    .error-msg {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        text-align: center;
        border-left: 4px solid #dc3545;
    }
    .timer {
        background: linear-gradient(135deg, #e2f0fb 0%, #cce7f0 100%);
        color: #0c63e4;
        padding: 0.75rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
        font-size: 1.25rem;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    .timer-warning {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        color: #856404;
    }
    .timer-danger {
        background: linear-gradient(135deg, #f8d7da 0%, #fab1a0 100%);
        color: #721c24;
        animation: pulse 1s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.8; transform: scale(1.02); }
        100% { opacity: 1; transform: scale(1); }
    }
    .subject-badge {
        display: inline-block;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.85rem;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 2px 4px rgba(79, 70, 229, 0.3);
    }
    .stats-card {
        background: linear-gradient(135deg, #f0f8ff 0%, #e6f3ff 100%);
        padding: 1.5rem;
        border-radius: 0.75rem;
        margin-bottom: 1rem;
        border-left: 4px solid #4f46e5;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    .achievement-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1rem;
        border-radius: 0.75rem;
        margin-bottom: 1rem;
        border: 1px solid #dee2e6;
        display: flex;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    .achievement-card:hover {
        transform: translateY(-2px);
    }
    .achievement-locked {
        filter: grayscale(1);
        opacity: 0.7;
    }
    .achievement-icon {
        font-size: 2rem;
        margin-right: 1rem;
        min-width: 2.5rem;
        text-align: center;
    }
    .achievement-content {
        flex-grow: 1;
    }
    .streak-flame {
        color: #ff9800;
        font-size: 1.5rem;
        animation: flicker 1.5s infinite alternate;
    }
    @keyframes flicker {
        0%, 18%, 22%, 25%, 53%, 57%, 100% { opacity: 1; }
        20%, 24%, 55% { opacity: 0.5; }
    }
    .level-badge {
        display: inline-block;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        font-weight: bold;
        width: 2.5rem;
        height: 2.5rem;
        line-height: 2.5rem;
        text-align: center;
        border-radius: 50%;
        margin-right: 0.5rem;
        box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
    }
    .xp-bar {
        height: 0.75rem;
        background: #e9ecef;
        border-radius: 0.375rem;
        margin-top: 0.5rem;
        overflow: hidden;
    }
    .xp-progress {
        height: 100%;
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
        border-radius: 0.375rem;
        transition: width 0.5s ease;
    }
    .mastery-bar {
        height: 0.5rem;
        background: #e9ecef;
        border-radius: 0.25rem;
        margin: 0.5rem 0;
        overflow: hidden;
    }
    .mastery-progress {
        height: 100%;
        background: linear-gradient(90deg, #12b886 0%, #38d9a9 100%);
        border-radius: 0.25rem;
        transition: width 0.5s ease;
    }
    .points-highlight {
        font-weight: bold;
        color: #4f46e5;
    }
    .progress-container {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    .button-primary {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 0.5rem;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
    }
    .button-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4);
    }
    .warning-box {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        color: #856404;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 4px solid #ffc107;
    }
    .info-box {
        background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
        color: #0c5460;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 4px solid #17a2b8;
    }
</style>
""", unsafe_allow_html=True)

# ─── API CLIENT SETUP WITH ERROR HANDLING ───────────────────────────────────────
@st.cache_resource
def initialize_client():
    """Initialize the Gemini client with proper error handling"""
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not api_key:
            st.error("❌ GEMINI_API_KEY not found in secrets. Please add it in your Streamlit app settings.")
            st.stop()
        client = genai.Client(api_key=api_key)
        # Test the connection with a simple call
        test_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"role": "user", "parts": [{"text": "Say 'API working'"}]}]
        )
        return client
    except ImportError:
        st.error("❌ Google GenAI library not installed. Please add 'google-generativeai' to requirements.txt")
        st.stop()
    except Exception as e:
        st.error(f"❌ API Connection Failed: {str(e)}")
        st.error("Please check your API key and internet connection.")
        st.stop()

# ─── EXPANDED JAMB SUBJECTS AND TOPICS ───────────────────────────────────────────
def get_jamb_subjects_and_topics():
    """Return a comprehensive dictionary of JAMB subjects and their topics"""
    return {
        "Mathematics": [
            "Algebra and Equations", "Geometry and Trigonometry", "Statistics and Probability",
            "Calculus", "Vectors", "Matrices", "Number Bases", "Sets and Logic"
        ],
        "Biology": [
            "Cell Biology", "Genetics", "Ecology", "Evolution", "Plant Biology", "Animal Biology",
            "Human Anatomy and Physiology", "Microbiology", "Reproduction", "Nutrition"
        ],
        "English Language": [
            "Comprehension", "Lexis and Structure", "Oral Forms", "Figurative Expressions",
            "Literary Devices", "Registers", "Synonyms and Antonyms", "Grammatical Structures"
        ],
        "Physics": [
            "Mechanics", "Energy", "Waves", "Optics", "Electricity and Magnetism", 
            "Modern Physics", "Heat and Temperature", "Electronics", "Nuclear Physics"
        ],
        "Chemistry": [
            "Atomic Structure", "Chemical Bonding", "Chemical Reactions", "Acids and Bases",
            "Organic Chemistry", "Physical Chemistry", "Inorganic Chemistry", "Electrochemistry"
        ],
        "Government": [
            "Nigerian Constitution", "Nigerian Political System", "Nigerian Federalism", 
            "Political Parties", "Electoral Systems", "Public Administration", 
            "Nigerian Foreign Policy", "International Relations"
        ],
        "Literature in English": [
            "Drama", "Poetry", "Prose", "Literary Terms", "African Literature",
            "Non-African Literature", "Literary Criticism", "Literary History"
        ],
        "Economics": [
            "Microeconomics", "Macroeconomics", "Development Economics", "Public Finance",
            "International Economics", "Monetary Economics", "Nigerian Economy", "Economic Theory"
        ],
        "Geography": [
            "Physical Geography", "Human Geography", "Regional Geography", "Map Reading",
            "Environmental Geography", "Economic Geography", "Population Geography", "Climatology"
        ],
        "Agricultural Science": [
            "Soil Science", "Crop Production", "Animal Production", "Agricultural Economics",
            "Farm Mechanization", "Agricultural Ecology", "Fisheries", "Forestry"
        ],
        "Accounting": [
            "Financial Accounting", "Cost Accounting", "Principles of Accounting", "Bookkeeping",
            "Financial Statements", "Partnership Accounting", "Company Accounting", "Public Sector Accounting"
        ],
        "Commerce": [
            "Trade", "Business Organizations", "Marketing", "Money and Banking",
            "Insurance", "Stock Exchange", "Communication", "Consumer Protection"
        ],
        "Christian Religious Studies": [
            "The Bible", "Old Testament", "New Testament", "Church History", 
            "Christian Ethics", "Christian Doctrines", "Christian Living", "Christian Practices"
        ],
        "Islamic Studies": [
            "Qur'an", "Hadith", "Tawhid", "Fiqh", "Islamic History", 
            "Islamic Ethics", "Islamic Civilization", "Islamic Practices"
        ],
        "Hausa Language": [
            "Grammar", "Comprehension", "Oral Literature", "Written Literature", 
            "Translation", "Culture", "History", "Composition"
        ],
        "Igbo Language": [
            "Grammar", "Comprehension", "Oral Literature", "Written Literature", 
            "Translation", "Culture", "History", "Composition"
        ],
        "Yoruba Language": [
            "Grammar", "Comprehension", "Oral Literature", "Written Literature", 
            "Translation", "Culture", "History", "Composition"
        ],
        "Computer Science": [
            "Computer Fundamentals", "Programming", "Data Processing", "Database",
            "Computer Networks", "Information Systems", "Software Development", "Computer Applications"
        ]
    }

# ─── IMPROVED QUESTION GENERATION FOR JAMB CURRICULUM ───────────────────────────
def generate_jamb_question(client, subject, difficulty, previous_questions=None):
    """Generate a JAMB-style question with topic diversity"""
    try:
        # Get JAMB topics for the selected subject
        jamb_topics = get_jamb_subjects_and_topics()
        subject_topics = jamb_topics.get(subject, ["General"])
        # Choose a topic that hasn't been covered yet
        topic = random.choice(subject_topics)
        if previous_questions:
            # Try to avoid topics that have been used already
            used_topics = [q.get("topic", "") for q in previous_questions]
            available_topics = [t for t in subject_topics if t not in used_topics]
            if available_topics:
                topic = random.choice(available_topics)

        prompt = f"""
        Create a {difficulty.lower()} level multiple choice question for {subject} focused on the topic of {topic}.
        This question should follow the Nigerian JAMB curriculum standards and difficulty level.
        
        The question should:
        1. Be specific to Nigerian context when appropriate
        2. Match the depth expected in JAMB exams
        3. Test deep understanding rather than simple memorization
        4. Be distinct from common or standard questions
        5. Include challenging distractors that test common misconceptions
        
        Format your response EXACTLY like this example:
        Question: What is 2 + 2?
        A) 3
        B) 4
        C) 5
        D) 6
        Answer: B
        Explanation: 2 + 2 equals 4, which is option B.
        Topic: Basic Arithmetic
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        content = response.candidates[0].content.parts[0].text.strip()
        question_data = parse_question_response(content)
        
        if question_data:
            question_data["topic"] = topic
            
            # Check for duplicates or very similar questions
            if previous_questions:
                for prev_q in previous_questions:
                    if similarity_check(question_data["question"], prev_q["question"]):
                        # If too similar, generate a new question recursively
                        return generate_jamb_question(client, subject, difficulty, previous_questions)
            
            return question_data
        return None
    except Exception as e:
        st.error(f"Question generation failed: {str(e)}")
        return None

def similarity_check(question1, question2):
    """Simple check for question similarity to avoid repetition"""
    # Convert to lowercase and remove punctuation for comparison
    q1 = ''.join(c.lower() for c in question1 if c.isalnum() or c.isspace())
    q2 = ''.join(c.lower() for c in question2 if c.isalnum() or c.isspace())
    
    # Check if questions are very similar
    if len(q1) > 0 and len(q2) > 0:
        # If one question is a subset of the other or they're very similar
        if q1 in q2 or q2 in q1 or (len(set(q1.split()) & set(q2.split())) / len(set(q1.split()) | set(q2.split())) > 0.7):
            return True
    
    return False

def parse_question_response(content):
    """Parse the AI response into structured question data"""
    try:
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        question = ""
        options = []
        answer = ""
        explanation = ""
        topic = ""

        for line in lines:
            if line.startswith("Question:"):
                question = line.replace("Question:", "").strip()
            elif line.startswith(("A)", "B)", "C)", "D)")):
                options.append(line)
            elif line.startswith("Answer:"):
                answer = line.replace("Answer:", "").strip()
            elif line.startswith("Explanation:"):
                explanation = line.replace("Explanation:", "").strip()
            elif line.startswith("Topic:"):
                topic = line.replace("Topic:", "").strip()

        if not all([question, len(options) >= 4, answer, explanation]):
            raise ValueError("Incomplete question data")

        return {
            "question": question,
            "options": options,
            "answer": answer,
            "explanation": explanation,
            "topic": topic
        }
    except Exception:
        return None

# ─── GAMIFICATION FUNCTIONS ───────────────────────────────────────────────────────
def calculate_xp(score, time_efficiency, difficulty_level):
    """Calculate experience points based on quiz performance"""
    # Base XP for completing quiz
    base_xp = 100
    
    # XP for correct answers (10-100)
    score_xp = score * 10
    
    # XP bonus for time efficiency (0-50)
    # time_efficiency is a value between 0-1 where 1 is most efficient
    time_bonus = int(time_efficiency * 50)
    
    # Difficulty multiplier
    difficulty_multiplier = 1.0
    if difficulty_level == "Medium":
        difficulty_multiplier = 1.25
    elif difficulty_level == "Hard":
        difficulty_multiplier = 1.5
    
    total_xp = int((base_xp + score_xp + time_bonus) * difficulty_multiplier)
    return total_xp

def calculate_level(total_xp):
    """Calculate user level based on total XP"""
    level = 1 + int(total_xp / 500) # Level up every 500 XP
    return level

def get_xp_progress(total_xp):
    """Calculate progress to next level as percentage"""
    current_level = calculate_level(total_xp)
    xp_for_current_level = (current_level - 1) * 500
    xp_for_next_level = current_level * 500
    
    progress = ((total_xp - xp_for_current_level) / 
                (xp_for_next_level - xp_for_current_level)) * 100
    return int(progress)

def update_streak(last_active_date=None):
    """Update the user's daily streak"""
    today = datetime.now().date()
    
    if not last_active_date:
        return 1, today # First day of streak
    
    # Convert string date to datetime if needed
    if isinstance(last_active_date, str):
        last_active_date = datetime.strptime(last_active_date, "%Y-%m-%d").date()
    
    days_diff = (today - last_active_date).days
    
    if days_diff == 0:
        # Already logged in today
        return st.session_state.streak_count, last_active_date
    elif days_diff == 1:
        # Consecutive day
        return st.session_state.streak_count + 1, today
    else:
        # Streak broken
        return 1, today

def get_subject_mastery(subject_history):
    """Calculate mastery percentage for each topic in a subject"""
    mastery_data = {}
    
    for entry in subject_history:
        topic = entry.get("topic", "General")
        correct = entry.get("correct", False)
        
        if topic not in mastery_data:
            mastery_data[topic] = {"attempts": 0, "correct": 0}
        
        mastery_data[topic]["attempts"] += 1
        if correct:
            mastery_data[topic]["correct"] += 1
    
    # Calculate mastery percentages
    for topic in mastery_data:
        attempts = mastery_data[topic]["attempts"]
        correct = mastery_data[topic]["correct"]
        mastery_data[topic]["mastery"] = int((correct / max(1, attempts)) * 100)
    
    return mastery_data

def check_achievements(user_data):
    """Check and update user achievements"""
    achievements = []
    
    # Quiz completion achievements
    total_quizzes = user_data.get("total_quizzes", 0)
    if total_quizzes >= 1:
        achievements.append({
            "id": "first_quiz",
            "icon": "🎯",
            "title": "First Steps",
            "description": "Completed your first quiz",
            "unlocked": True
        })
    
    if total_quizzes >= 5:
        achievements.append({
            "id": "five_quizzes",
            "icon": "🏅",
            "title": "Quiz Enthusiast",
            "description": "Completed 5 quizzes",
            "unlocked": True
        })
    
    if total_quizzes >= 20:
        achievements.append({
            "id": "twenty_quizzes",
            "icon": "🏆",
            "title": "Quiz Master",
            "description": "Completed 20 quizzes",
            "unlocked": True
        })
    
    # Perfect score achievements
    perfect_scores = user_data.get("perfect_scores", 0)
    if perfect_scores >= 1:
        achievements.append({
            "id": "first_perfect",
            "icon": "💯",
            "title": "Perfect Start",
            "description": "Got your first perfect score",
            "unlocked": True
        })
    
    if perfect_scores >= 5:
        achievements.append({
            "id": "five_perfect",
            "icon": "🌟",
            "title": "Excellence",
            "description": "Achieved 5 perfect scores",
            "unlocked": True
        })
    
    # Streak achievements
    streak = user_data.get("streak_count", 0)
    if streak >= 3:
        achievements.append({
            "id": "three_day_streak",
            "icon": "🔥",
            "title": "On Fire",
            "description": "3-day study streak",
            "unlocked": True
        })
    
    if streak >= 7:
        achievements.append({
            "id": "weekly_streak",
            "icon": "🔥🔥",
            "title": "Weekly Warrior",
            "description": "7-day study streak",
            "unlocked": True
        })
    
    if streak >= 30:
        achievements.append({
            "id": "monthly_streak",
            "icon": "🔥🔥🔥",
            "title": "Dedication",
            "description": "30-day study streak",
            "unlocked": True
        })
    
    # Add locked achievements
    all_achievements = [
        {"id": "first_quiz", "icon": "🎯", "title": "First Steps", "description": "Complete your first quiz"},
        {"id": "five_quizzes", "icon": "🏅", "title": "Quiz Enthusiast", "description": "Complete 5 quizzes"},
        {"id": "twenty_quizzes", "icon": "🏆", "title": "Quiz Master", "description": "Complete 20 quizzes"},
        {"id": "first_perfect", "icon": "💯", "title": "Perfect Start", "description": "Get a perfect score"},
        {"id": "five_perfect", "icon": "🌟", "title": "Excellence", "description": "Achieve 5 perfect scores"},
        {"id": "three_day_streak", "icon": "🔥", "title": "On Fire", "description": "Maintain a 3-day study streak"},
        {"id": "weekly_streak", "icon": "🔥🔥", "title": "Weekly Warrior", "description": "Maintain a 7-day study streak"},
        {"id": "monthly_streak", "icon": "🔥🔥🔥", "title": "Dedication", "description": "Maintain a 30-day study streak"}
    ]
    
    # Add locked versions of achievements not yet earned
    unlocked_ids = [a["id"] for a in achievements]
    for achievement in all_achievements:
        if achievement["id"] not in unlocked_ids:
            locked_achievement = achievement.copy()
            locked_achievement["unlocked"] = False
            achievements.append(locked_achievement)
    
    return sorted(achievements, key=lambda x: (not x["unlocked"], x["title"]))

# ─── TIMER FUNCTIONS ───────────────────────────────────────────────────────────
def format_time_remaining(seconds):
    """Format the remaining time in minutes:seconds"""
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"

def get_timer_class(seconds_left):
    """Return the appropriate CSS class for the timer based on time remaining"""
    if seconds_left < 30:
        return "timer timer-danger"
    elif seconds_left < 60:
        return "timer timer-warning"
    else:
        return "timer"

# ─── HOME NAVIGATION FUNCTIONS ──────────────────────────────────────────────────
def show_home_button():
    """Display the home button if not on setup screen"""
    if st.session_state.app_stage != "setup":
        if st.button("🏠 Home", key="home_btn", help="Return to subject selection"):
            # Show confirmation dialog
            st.session_state.show_home_confirm = True

def handle_home_navigation():
    """Handle home navigation with confirmation"""
    if st.session_state.get("show_home_confirm", False):
        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
        st.warning("⚠️ **Are you sure you want to go home?**")
        st.write("Your current progress will be saved, but the active quiz will be reset.")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("✅ Yes, Go Home", type="primary"):
                go_home()
        with col2:
            if st.button("❌ Cancel"):
                st.session_state.show_home_confirm = False
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def go_home():
    """Navigate to home screen and reset quiz state"""
    # Reset quiz-specific session state but preserve user progress
    st.session_state.app_stage = "setup"
    st.session_state.current_question = None
    st.session_state.previous_questions = []
    st.session_state.score = 0
    st.session_state.question_count = 0
    st.session_state.show_answer = False
    st.session_state.user_choice = None
    st.session_state.timer_start = None
    st.session_state.total_time_used = 0
    st.session_state.timer_expired = False
    st.session_state.show_home_confirm = False
    st.rerun()

def show_navigation_bar():
    """Display the enhanced navigation bar with user stats"""
    current_level = calculate_level(st.session_state.total_xp)
    
    nav_html = f"""
    <div class="nav-bar">
        <div class="nav-title">📘 SmartPrep AI Tutor</div>
        <div class="nav-stats">
            <span>Level {current_level}</span>
            <span>{st.session_state.total_xp} XP</span>
            <span>🔥 {st.session_state.streak_count}</span>
            <span>📊 {st.session_state.total_quizzes} Quizzes</span>
        </div>
    </div>
    """
    st.markdown(nav_html, unsafe_allow_html=True)

# ─── SESSION STATE INITIALIZATION ───────────────────────────────────────────────
def initialize_session_state():
    """Initialize session state with default values"""
    if "app_stage" not in st.session_state:
        st.session_state.app_stage = "setup"
    if "current_tab" not in st.session_state:
        st.session_state.current_tab = "quiz"
    if "subject" not in st.session_state:
        st.session_state.subject = "Mathematics"
    if "difficulty" not in st.session_state:
        st.session_state.difficulty = "Medium"
    if "current_question" not in st.session_state:
        st.session_state.current_question = None
    if "previous_questions" not in st.session_state:
        st.session_state.previous_questions = []
    if "score" not in st.session_state:
        st.session_state.score = 0
    if "question_count" not in st.session_state:
        st.session_state.question_count = 0
    if "show_answer" not in st.session_state:
        st.session_state.show_answer = False
    if "user_choice" not in st.session_state:
        st.session_state.user_choice = None
    if "timer_start" not in st.session_state:
        st.session_state.timer_start = None
    if "time_per_question" not in st.session_state:
        st.session_state.time_per_question = 120 # Default: 2 minutes per question
    if "total_time_used" not in st.session_state:
        st.session_state.total_time_used = 0
    if "timer_expired" not in st.session_state:
        st.session_state.timer_expired = False
    if "show_home_confirm" not in st.session_state:
        st.session_state.show_home_confirm = False
    
    # User data persistence
    if "user_name" not in st.session_state:
        st.session_state.user_name = "Student"
    if "total_xp" not in st.session_state:
        st.session_state.total_xp = 0
    if "total_quizzes" not in st.session_state:
        st.session_state.total_quizzes = 0
    if "perfect_scores" not in st.session_state:
        st.session_state.perfect_scores = 0
    if "last_active_date" not in st.session_state:
        st.session_state.last_active_date = datetime.now().date().isoformat()
    if "streak_count" not in st.session_state:
        st.session_state.streak_count = 1
    if "subject_history" not in st.session_state:
        st.session_state.subject_history = {}
    if "achievements" not in st.session_state:
        st.session_state.achievements = []

# ─── ENHANCED USER PROFILE FUNCTIONS ────────────────────────────────────────────
def show_user_stats():
    """Display comprehensive user statistics"""
    current_level = calculate_level(st.session_state.total_xp)
    xp_progress = get_xp_progress(st.session_state.total_xp)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="stats-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="level-badge">{current_level}</div> **Level {current_level}**', unsafe_allow_html=True)
        st.markdown(f"**{st.session_state.total_xp} XP** total")
        st.markdown(f'<div class="xp-bar"><div class="xp-progress" style="width: {xp_progress}%"></div></div>', unsafe_allow_html=True)
        st.markdown(f"**{xp_progress}%** to next level")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="stats-card">', unsafe_allow_html=True)
        st.markdown("**📊 Quiz Statistics**")
        st.markdown(f"Total Quizzes: **{st.session_state.total_quizzes}**")
        st.markdown(f"Perfect Scores: **{st.session_state.perfect_scores}**")
        if st.session_state.total_quizzes > 0:
            accuracy = (st.session_state.perfect_scores / st.session_state.total_quizzes) * 100
            st.markdown(f"Perfect Rate: **{accuracy:.1f}%**")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="stats-card">', unsafe_allow_html=True)
        st.markdown("**🔥 Study Streak**")
        if st.session_state.streak_count > 1:
            st.markdown(f'<span class="streak-flame">🔥</span> **{st.session_state.streak_count} days**', unsafe_allow_html=True)
        else:
            st.markdown("**1 day** - Keep it up!")
        st.markdown(f"Last active: {st.session_state.last_active_date}")
        st.markdown('</div>', unsafe_allow_html=True)

def show_subject_progress():
    """Display progress across all subjects"""
    if st.session_state.subject_history:
        st.markdown("### 📚 Subject Progress")
        
        for subject, history in st.session_state.subject_history.items():
            mastery_data = get_subject_mastery(history)
            if mastery_data:
                st.markdown(f'<span class="subject-badge">{subject}</span>', unsafe_allow_html=True)
                
                # Calculate overall subject mastery
                total_attempts = sum(data["attempts"] for data in mastery_data.values())
                total_correct = sum(data["correct"] for data in mastery_data.values())
                overall_mastery = int((total_correct / max(1, total_attempts)) * 100)
                
                st.markdown(f"**Overall Mastery: {overall_mastery}%** ({total_correct}/{total_attempts})")
                st.markdown(f'<div class="mastery-bar"><div class="mastery-progress" style="width: {overall_mastery}%"></div></div>', unsafe_allow_html=True)
                
                # Show topic breakdown
                with st.expander(f"View {subject} topic breakdown"):
                    for topic, data in mastery_data.items():
                        mastery_percent = data["mastery"]
                        st.markdown(f"**{topic}:** {mastery_percent}% ({data['correct']}/{data['attempts']})")
                        st.markdown(f'<div class="mastery-bar"><div class="mastery-progress" style="width: {mastery_percent}%"></div></div>', unsafe_allow_html=True)

# ─── MAIN APPLICATION ───────────────────────────────────────────────────────────
def main():
    # Initialize session state
    initialize_session_state()
    
    # Initialize API client
    client = initialize_client()
    
    # Show navigation bar (except on setup screen)
    if st.session_state.app_stage != "setup":
        show_navigation_bar()
    
    # Handle home navigation confirmation
    handle_home_navigation()
    
    # Show home button
    show_home_button()
    
    # Main header (only show on setup screen)
    if st.session_state.app_stage == "setup":
        st.markdown("""
        <div class="main-header">
            <h1 style="color: #4f46e5; font-size: 2.5rem;">📘 SmartPrep AI Tutor - JAMB Edition</h1>
            <p style="color: #6b7280;">Your comprehensive AI-powered guide for JAMB exam success</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Main application flow
    if st.session_state.app_stage == "setup":
        show_setup_screen(client)
    elif st.session_state.app_stage == "quiz":
        show_quiz_screen(client)
    elif st.session_state.app_stage == "results":
        show_results_screen()

def show_setup_screen(client):
    """Display the enhanced setup screen with user stats and subject selection"""
    # Show user stats if they have progress
    if st.session_state.total_quizzes > 0:
        show_user_stats()
        show_subject_progress()
    
    # Show achievements
    user_data = {
        "total_quizzes": st.session_state.total_quizzes,
        "perfect_scores": st.session_state.perfect_scores,
        "streak_count": st.session_state.streak_count,
        "subject_history": st.session_state.subject_history
    }
    
    achievements = check_achievements(user_data)
    unlocked_achievements = [a for a in achievements if a["unlocked"]]
    
    if unlocked_achievements:
        st.markdown("### 🏆 Your Achievements")
        cols = st.columns(min(3, len(unlocked_achievements)))
        for i, achievement in enumerate(unlocked_achievements[:3]): # Show first 3
            with cols[i]:
                st.markdown(f'<div class="achievement-card"><div class="achievement-icon">{achievement["icon"]}</div><div class="achievement-content"><strong>{achievement["title"]}</strong><br>{achievement["description"]}</div></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="quiz-container">', unsafe_allow_html=True)
    st.subheader("🚀 Start a New Quiz!")
    
    # Enhanced subject selection with descriptions
    st.markdown("### Select Your Subject")
    subjects_info = {
        "Mathematics": "🔢 Algebra, Geometry, Statistics, and more",
        "Biology": "🧬 Life sciences, genetics, and human anatomy",
        "English Language": "📝 Grammar, comprehension, and language skills",
        "Physics": "⚛️ Mechanics, waves, electricity, and modern physics",
        "Chemistry": "🧪 Atoms, bonds, reactions, and organic chemistry",
        "Government": "🏛️ Nigerian politics, constitution, and governance",
        "Literature in English": "📚 Drama, poetry, prose, and literary analysis",
        "Economics": "💰 Micro/macro economics and Nigerian economy",
        "Geography": "🌍 Physical and human geography",
        "Agricultural Science": "🌾 Crop production, soil science, and farming",
        "Accounting": "📊 Financial accounting and bookkeeping",
        "Commerce": "🏢 Trade, marketing, and business organizations",
        "Christian Religious Studies": "✝️ Bible study and Christian teachings",
        "Islamic Studies": "☪️ Qur'an, Hadith, and Islamic principles",
        "Computer Science": "💻 Programming, databases, and IT systems"
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        subject = st.selectbox(
            "Choose a subject:",
            list(subjects_info.keys()),
            index=0,
            format_func=lambda x: f"{x}"
        )
    
        # Show subject description
        st.markdown(f'<div class="info-box">{subjects_info[subject]}</div>', unsafe_allow_html=True)
    
    with col2:
        difficulty = st.selectbox(
            "Select difficulty level:",
            ["Easy", "Medium", "Hard"],
            index=1,
            help="Easy: Basic concepts | Medium: Standard JAMB level | Hard: Advanced concepts"
        )
    
        # Show difficulty info
        difficulty_info = {
            "Easy": "✅ Perfect for beginners and concept review",
            "Medium": "⚖️ Standard JAMB exam difficulty level", 
            "Hard": "🎯 Challenging questions for advanced preparation"
        }
        st.markdown(f'<div class="info-box">{difficulty_info[difficulty]}</div>', unsafe_allow_html=True)
    
    # Quiz settings
    st.markdown("### ⚙️ Quiz Settings")
    time_options = {
        "60 seconds": 60,
        "90 seconds": 90, 
        "2 minutes (Recommended)": 120,
        "3 minutes": 180,
        "No time limit": None
    }
    
    time_choice = st.selectbox(
        "Time per question:",
        list(time_options.keys()),
        index=2
    )
    
    if st.button("🚀 Start Quiz", type="primary", use_container_width=True):
        with st.spinner("🔄 Generating your first question..."):
            # Update session state
            st.session_state.subject = subject
            st.session_state.difficulty = difficulty
            st.session_state.time_per_question = time_options[time_choice]
            
            # Generate first question
            question = generate_jamb_question(client, subject, difficulty)
            
            if question:
                st.session_state.current_question = question
                st.session_state.previous_questions = [question]
                st.session_state.app_stage = "quiz"
                st.session_state.question_count = 1
                st.session_state.timer_start = time.time() if time_options[time_choice] else None
                st.success("✅ Question generated successfully!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to generate question. Please try again.")
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_quiz_screen(client):
    """Display the enhanced quiz screen with current question"""
    if not st.session_state.current_question:
        st.error("No question available. Returning to setup...")
        st.session_state.app_stage = "setup"
        st.rerun()
        return
    
    question = st.session_state.current_question
    
    # Timer display (only if timer is enabled)
    if st.session_state.timer_start and st.session_state.time_per_question and not st.session_state.show_answer:
        elapsed_time = time.time() - st.session_state.timer_start
        time_left = max(0, st.session_state.time_per_question - elapsed_time)
        
        timer_class = get_timer_class(time_left)
        st.markdown(f'<div class="{timer_class}">⏱️ Time Remaining: {format_time_remaining(int(time_left))}</div>', unsafe_allow_html=True)
        
        # Auto-submit if time expires
        if time_left <= 0 and not st.session_state.timer_expired:
            st.session_state.timer_expired = True
            st.session_state.show_answer = True
            st.session_state.user_choice = "Time Expired"
            st.rerun()
    
    # Enhanced progress indicator
    progress = st.session_state.question_count / 10
    st.markdown('<div class="progress-container">', unsafe_allow_html=True)
    st.markdown(f"**Progress: Question {st.session_state.question_count} of 10** ({int(progress * 100)}%)")
    st.progress(progress)
    st.markdown(f"**Current Score: {st.session_state.score}/{st.session_state.question_count - (1 if not st.session_state.show_answer else 0)}**")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="quiz-container">', unsafe_allow_html=True)
    
    # Question header with subject and topic badges
    st.markdown(f'<span class="subject-badge">{st.session_state.subject}</span>', unsafe_allow_html=True)
    st.markdown(f"**Topic: {question.get('topic', 'General')}** | **Difficulty: {st.session_state.difficulty}**")
    st.markdown("---")
    
    # Question text
    st.markdown(f"### {question['question']}")
    
    # Answer options (only show if answer not revealed)
    if not st.session_state.show_answer:
        choice = st.radio(
            "Select your answer:",
            question['options'],
            key=f"q_{st.session_state.question_count}"
        )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("✅ Submit Answer", type="primary", use_container_width=True):
                st.session_state.user_choice = choice
                st.session_state.show_answer = True
                
                # Calculate time used for this question
                if st.session_state.timer_start:
                    time_used = time.time() - st.session_state.timer_start
                    st.session_state.total_time_used += time_used
                
                # Check if correct and record in history
                is_correct = choice.startswith(question['answer'])
                if is_correct:
                    st.session_state.score += 1
                
                # Record question in subject history
                if st.session_state.subject not in st.session_state.subject_history:
                    st.session_state.subject_history[st.session_state.subject] = []
                
                st.session_state.subject_history[st.session_state.subject].append({
                    "topic": question.get("topic", "General"),
                    "correct": is_correct,
                    "date": datetime.now().isoformat(),
                    "difficulty": st.session_state.difficulty
                })
                
                st.rerun()
    
    # Show feedback if answer submitted
    if st.session_state.show_answer:
        user_answer = st.session_state.user_choice
        correct_answer = question['answer']
        
        # Show result with enhanced styling
        if user_answer == "Time Expired":
            st.markdown('<div class="error-msg">⏰ **Time Expired!** The correct answer was <strong>' + correct_answer + '</strong>.</div>', unsafe_allow_html=True)
        elif user_answer.startswith(correct_answer):
            st.markdown('<div class="success-msg">✅ **Correct!** Excellent work! 🎉</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="error-msg">❌ **Incorrect.** The correct answer was <strong>{correct_answer}</strong>.</div>', unsafe_allow_html=True)
        
        # Show explanation with better formatting
        st.markdown("### 💡 Detailed Explanation")
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.markdown(question['explanation'])
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Next question or finish
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.session_state.question_count >= 10:
                if st.button("🎯 View Results", type="primary", use_container_width=True):
                    st.session_state.app_stage = "results"
                    st.rerun()
            else:
                if st.button("➡️ Next Question", type="primary", use_container_width=True):
                    with st.spinner("🔄 Generating next question..."):
                        next_question = generate_jamb_question(
                            client, 
                            st.session_state.subject, 
                            st.session_state.difficulty,
                            st.session_state.previous_questions
                        )
                        
                        if next_question:
                            st.session_state.current_question = next_question
                            st.session_state.previous_questions.append(next_question)
                            st.session_state.question_count += 1
                            st.session_state.show_answer = False
                            st.session_state.user_choice = None
                            st.session_state.timer_start = time.time() if st.session_state.time_per_question else None
                            st.session_state.timer_expired = False
                            st.rerun()
                        else:
                            st.error("Failed to generate next question. Please try again.")
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_results_screen():
    """Display the enhanced final results screen"""
    st.balloons()
    
    # Calculate results
    score_percentage = (st.session_state.score / 10) * 100
    total_time_minutes = st.session_state.total_time_used / 60
    time_efficiency = max(0, (1200 - st.session_state.total_time_used) / 1200) if st.session_state.total_time_used > 0 else 1
    
    # Calculate XP earned
    xp_earned = calculate_xp(st.session_state.score, time_efficiency, st.session_state.difficulty)
    old_xp = st.session_state.total_xp
    old_level = calculate_level(old_xp)
    
    # Update user stats
    st.session_state.total_xp += xp_earned
    st.session_state.total_quizzes += 1
    
    if st.session_state.score == 10:
        st.session_state.perfect_scores += 1
    
    # Check for level up
    new_level = calculate_level(st.session_state.total_xp)
    level_up = new_level > old_level
    
    # Update streak
    st.session_state.streak_count, st.session_state.last_active_date = update_streak(
        st.session_state.last_active_date
    )
    
    st.markdown('<div class="quiz-container">', unsafe_allow_html=True)
    
    # Level up notification
    if level_up:
        st.markdown(f'<div class="success-msg">🎉 **LEVEL UP!** You reached Level {new_level}! 🚀</div>', unsafe_allow_html=True)
    
    st.markdown("## 🎉 Quiz Complete!")
    st.markdown("---")
    
    # Enhanced score display
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("### 📊 Your Score")
        st.markdown(f"**{st.session_state.score} / 10**")
        st.markdown(f"**{score_percentage:.0f}%**")
    
    with col2:
        st.markdown("### ⏱️ Time Used")
        if st.session_state.total_time_used > 0:
            st.markdown(f"**{total_time_minutes:.1f} min**")
            st.markdown(f"Avg: {total_time_minutes*6:.0f}s/q")
        else:
            st.markdown("**No time limit**")
    
    with col3:
        st.markdown("### ⭐ XP Earned")
        st.markdown(f"**+{xp_earned} XP**")
        st.markdown(f"Total: {st.session_state.total_xp}")
    
    with col4:
        st.markdown("### 🎯 Level")
        st.markdown(f'<div class="level-badge">{new_level}</div>', unsafe_allow_html=True)
        if level_up:
            st.markdown("**NEW!** 🎉")
    
    # Performance feedback with personalized messages
    if score_percentage == 100:
        st.markdown('<div class="success-msg">🌟 **PERFECT SCORE!** Outstanding performance! You\'re absolutely ready for JAMB! 🏆</div>', unsafe_allow_html=True)
    elif score_percentage >= 80:
        st.markdown('<div class="success-msg">🌟 **Excellent work!** You\'re well-prepared for JAMB. Keep up the great work! 👏</div>', unsafe_allow_html=True)
    elif score_percentage >= 60:
        st.markdown('<div class="info-box">👍 **Good job!** You\'re on the right track. A few more practice sessions and you\'ll be ready! 💪</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="warning-box">📚 **Keep studying!** Focus on the explanations and try more practice quizzes. You\'ve got this! 🎯</div>', unsafe_allow_html=True)
    
    # XP Progress display
    xp_progress = get_xp_progress(st.session_state.total_xp)
    st.markdown("### 🚀 Your Progress")
    st.markdown(f'<div class="level-badge">{new_level}</div> **Level {new_level}** - {st.session_state.total_xp} XP total', unsafe_allow_html=True)
    st.markdown(f'<div class="xp-bar"><div class="xp-progress" style="width: {xp_progress}%"></div></div>', unsafe_allow_html=True)
    st.markdown(f"**{xp_progress}%** to Level {new_level + 1}")
    
    # Streak display
    if st.session_state.streak_count > 1:
        st.markdown(f'**Study Streak:** <span class="streak-flame">🔥</span> {st.session_state.streak_count} days! Keep it going!', unsafe_allow_html=True)
    
    # Achievements check
    user_data = {
        "total_quizzes": st.session_state.total_quizzes,
        "perfect_scores": st.session_state.perfect_scores,
        "streak_count": st.session_state.streak_count,
        "subject_history": st.session_state.subject_history
    }
    
    achievements = check_achievements(user_data)
    new_achievements = [a for a in achievements if a["unlocked"] and a["id"] not in st.session_state.achievements]
    
    if new_achievements:
        st.markdown("### 🏆 New Achievements Unlocked!")
        for achievement in new_achievements:
            st.markdown(f'<div class="achievement-card"><div class="achievement-icon">{achievement["icon"]}</div><div class="achievement-content"><strong>{achievement["title"]}</strong><br>{achievement["description"]}</div></div>', unsafe_allow_html=True)
            st.session_state.achievements.append(achievement["id"])
    
    # Subject mastery for this quiz
    if st.session_state.subject in st.session_state.subject_history:
        recent_history = st.session_state.subject_history[st.session_state.subject][-10:] # Last 10 questions
        mastery_data = get_subject_mastery(recent_history)
        if mastery_data:
            st.markdown(f"### 📈 {st.session_state.subject} - Topic Performance")
            for topic, data in mastery_data.items():
                mastery_percent = data["mastery"]
                st.markdown(f"**{topic}:** {mastery_percent}% mastery ({data['correct']}/{data['attempts']} correct)")
                st.markdown(f'<div class="mastery-bar"><div class="mastery-progress" style="width: {mastery_percent}%"></div></div>', unsafe_allow_html=True)
    
    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Take Another Quiz", type="primary", use_container_width=True):
            go_home()
    
    with col2:
        if st.button("📊 View My Progress", use_container_width=True):
            go_home()
    
    st.markdown('</div>', unsafe_allow_html=True)

# ─── RUN APPLICATION ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
