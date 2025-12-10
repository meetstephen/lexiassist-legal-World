# ================= IMPORTS =================
import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, List, Dict, Any
import uuid
import io

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="LexiAssist - Legal Practice Management",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/meetstephen/lexiassist-legal-World.git',
        'Report a bug': 'https://github.com/meetstephen/lexi-assist/issues',
        'About': '# LexiAssist\nAI-Powered Legal Practice Management System for Nigerian Lawyers'
    }
)

# ============================================================
# CUSTOM CSS STYLING
# ============================================================
st.markdown("""
<style>
/* Main container styling */
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

/* Header styling */
.main-header {
    background: linear-gradient(135deg, #059669 0%, #0d9488 100%);
    padding: 1.5rem 2rem;
    border-radius: 1rem;
    margin-bottom: 2rem;
    color: white;
    box-shadow: 0 10px 40px rgba(5, 150, 105, 0.3);
}
.main-header h1 {
    margin: 0;
    font-size: 2.5rem;
    font-weight: 700;
}
.main-header p {
    margin: 0.5rem 0 0 0;
    opacity: 0.9;
    font-size: 1rem;
}

/* Card styling */
.custom-card {
    background: white;
    border-radius: 1rem;
    padding: 1.5rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    border: 1px solid #e2e8f0;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
}
.custom-card:hover {
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
    transform: translateY(-2px);
}

/* Stat card styling */
.stat-card {
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
    border-radius: 1rem;
    padding: 1.5rem;
    text-align: center;
    border: 1px solid #bbf7d0;
}
.stat-card.blue {
    background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    border: 1px solid #bfdbfe;
}
.stat-card.purple {
    background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
    border: 1px solid #e9d5ff;
}
.stat-card.amber {
    background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
    border: 1px solid #fde68a;
}
.stat-value {
    font-size: 2rem;
    font-weight: 700;
    color: #059669;
}
.stat-card.blue .stat-value {
    color: #2563eb;
}
.stat-card.purple .stat-value {
    color: #7c3aed;
}
.stat-card.amber .stat-value {
    color: #d97706;
}
.stat-label {
    font-size: 0.875rem;
    color: #64748b;
    margin-top: 0.25rem;
}

/* Badge styling */
.badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
}
.badge-success {
    background: #dcfce7;
    color: #166534;
}
.badge-warning {
    background: #fef3c7;
    color: #92400e;
}
.badge-info {
    background: #dbeafe;
    color: #1e40af;
}
.badge-danger {
    background: #fee2e2;
    color: #991b1b;
}

/* Response box styling */
.response-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 0.75rem;
    padding: 1.5rem;
    margin: 1rem 0;
    white-space: pre-wrap;
    font-family: 'Georgia', serif;
    line-height: 1.8;
}

/* Disclaimer styling */
.disclaimer {
    background: #fef3c7;
    border-left: 4px solid #f59e0b;
    padding: 1rem;
    border-radius: 0 0.5rem 0.5rem 0;
    margin-top: 1rem;
    font-size: 0.875rem;
}

/* Task type buttons */
.task-type-btn {
    background: white;
    border: 2px solid #e2e8f0;
    border-radius: 0.75rem;
    padding: 1rem;
    text-align: left;
    transition: all 0.2s ease;
    cursor: pointer;
    width: 100%;
    margin-bottom: 0.5rem;
}
.task-type-btn:hover {
    border-color: #059669;
    box-shadow: 0 4px 12px rgba(5, 150, 105, 0.15);
}
.task-type-btn.selected {
    border-color: #059669;
    background: #f0fdf4;
}

/* Sidebar styling */
.css-1d391kg {
    background: #f8fafc;
}

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 0.5rem;
    padding: 0.5rem 1rem;
    font-weight: 600;
}

/* Calendar event styling */
.calendar-event {
    padding: 1rem;
    border-radius: 0.75rem;
    margin-bottom: 0.75rem;
    border-left: 4px solid;
}
.calendar-event.urgent {
    background: #fee2e2;
    border-color: #ef4444;
}
.calendar-event.warning {
    background: #fef3c7;
    border-color: #f59e0b;
}
.calendar-event.normal {
    background: #f0fdf4;
    border-color: #10b981;
}

/* Template card */
.template-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 0.75rem;
    padding: 1rem;
    margin-bottom: 1rem;
    transition: all 0.2s ease;
}
.template-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# CONSTANTS & TEMPLATES
# ============================================================
TASK_TYPES = {
    "drafting": {
        "label": "📄 Document Drafting",
        "description": "Contracts, pleadings, applications, affidavits",
        "icon": "📄"
    },
    "analysis": {
        "label": "🔍 Legal Analysis",
        "description": "Issue spotting, IRAC/FILAC reasoning",
        "icon": "🔍"
    },
    "research": {
        "label": "📚 Legal Research",
        "description": "Case law, statutes, authorities",
        "icon": "📚"
    },
    "procedure": {
        "label": "📋 Procedural Guidance",
        "description": "Court filing, evidence rules",
        "icon": "📋"
    },
    "interpretation": {
        "label": "⚖️ Statutory Interpretation",
        "description": "Analyze and explain legislation",
        "icon": "⚖️"
    },
    "general": {
        "label": "💬 General Query",
        "description": "Ask anything legal-related",
        "icon": "💬"
    }
}

DEFAULT_TEMPLATES = [
    {
        "id": "1",
        "name": "Employment Contract",
        "category": "Corporate",
        "content": """EMPLOYMENT CONTRACT

This Employment Contract is made on [DATE] between:

1. [EMPLOYER NAME] (hereinafter called "the Employer")
Address: [EMPLOYER ADDRESS]
RC Number: [REGISTRATION NUMBER]

2. [EMPLOYEE NAME] (hereinafter called "the Employee")
Address: [EMPLOYEE ADDRESS]

TERMS AND CONDITIONS:

1. POSITION AND DUTIES
The Employee is employed as [JOB TITLE] and shall perform such duties as may be assigned.

2. COMMENCEMENT DATE
Employment shall commence on [START DATE].

3. PROBATION PERIOD
The Employee shall be on probation for a period of [PERIOD] months.

4. REMUNERATION
The Employee shall receive a monthly salary of N[AMOUNT] payable on [DATE] of each month.

5. WORKING HOURS
Normal working hours shall be [HOURS] per week, Monday to Friday.

6. LEAVE ENTITLEMENT
The Employee shall be entitled to [NUMBER] working days annual leave.

7. TERMINATION
Either party may terminate this contract by giving [NOTICE PERIOD] notice in writing.

8. CONFIDENTIALITY
The Employee agrees to maintain confidentiality of all company information.

9. GOVERNING LAW
This contract shall be governed by the Labour Act of Nigeria and other applicable laws.

SIGNED:
_____________________ _____________________
Employer Employee
Date: Date:
"""
    },
    {
        "id": "2",
        "name": "Tenancy Agreement",
        "category": "Property",
        "content": """TENANCY AGREEMENT

This Agreement is made on [DATE] BETWEEN:

[LANDLORD NAME] of [LANDLORD ADDRESS] (hereinafter called "the Landlord")

AND

[TENANT NAME] of [TENANT ADDRESS] (hereinafter called "the Tenant")

WHEREBY IT IS AGREED AS FOLLOWS:

1. PREMISES
The Landlord agrees to let and the Tenant agrees to take the property known as: [PROPERTY ADDRESS]

2. TERM
The tenancy shall be for a period of [DURATION] commencing from [START DATE].

3. RENT
The rent shall be N[AMOUNT] per [PERIOD], payable in advance on [DATE].

4. SECURITY DEPOSIT
The Tenant shall pay a security deposit of N[AMOUNT] refundable at the end of tenancy.

5. USE OF PREMISES
The premises shall be used solely for [residential/commercial] purposes.

6. MAINTENANCE
The Tenant shall keep the premises in good and tenantable condition.

7. ALTERATIONS
No structural alterations shall be made without the Landlord's written consent.

8. ASSIGNMENT
The Tenant shall not assign or sublet without the Landlord's written consent.

9. TERMINATION
Either party may terminate by giving [NOTICE PERIOD] notice in writing.

10. GOVERNING LAW
This agreement shall be governed by the Lagos State Tenancy Law (or applicable state law).

SIGNED:
_____________________ _____________________
Landlord Tenant
Date: Date:

WITNESS:
Name: _____________________
Address: __________________
Signature: ________________
"""
    },
    {
        "id": "3",
        "name": "Power of Attorney",
        "category": "Litigation",
        "content": """GENERAL POWER OF ATTORNEY

KNOW ALL MEN BY THESE PRESENTS:

I, [GRANTOR NAME], of [ADDRESS], [OCCUPATION], do hereby appoint [ATTORNEY NAME] of [ATTORNEY ADDRESS] as my true and lawful Attorney to act for me and on my behalf in the following matters:

POWERS GRANTED:

1. To demand, sue for, recover, collect, and receive all sums of money, debts, dues, and demands whatsoever which are now or shall hereafter become due.

2. To sign, execute, and deliver all contracts, agreements, and documents.

3. To appear before any court, tribunal, or authority and to institute, prosecute, defend, or settle any legal proceedings.

4. To operate my bank accounts and perform banking transactions.

5. To manage my properties and collect rents.

6. To execute and register any deed or document.

AND I HEREBY DECLARE that this Power of Attorney shall remain in force until revoked by me in writing.

IN WITNESS WHEREOF, I have hereunto set my hand this [DATE].

_____________________
[GRANTOR NAME]

SIGNED AND DELIVERED by the above named in the presence of:

Name: _____________________
Address: __________________
Occupation: _______________
Signature: ________________
"""
    },
    {
        "id": "4",
        "name": "Written Address",
        "category": "Litigation",
        "content": """IN THE [COURT NAME]
IN THE [JUDICIAL DIVISION]
HOLDEN AT [LOCATION]

SUIT NO: [NUMBER]

BETWEEN:

[PLAINTIFF NAME] ........................... PLAINTIFF/APPLICANT

AND

[DEFENDANT NAME] ........................... DEFENDANT/RESPONDENT

WRITTEN ADDRESS OF THE [PLAINTIFF/DEFENDANT]

MAY IT PLEASE THIS HONOURABLE COURT:

1.0 INTRODUCTION

1.1 This Written Address is filed pursuant to the Rules of this Honourable Court.

1.2 [Brief background of the matter]

2.0 FACTS OF THE CASE

2.1 [Detailed facts]

2.2 [Chronological narration]

3.0 ISSUES FOR DETERMINATION

3.1 Whether [First Issue]

3.2 Whether [Second Issue]

4.0 ARGUMENTS

4.1 ON ISSUE ONE
[Detailed legal arguments with authorities]

4.2 ON ISSUE TWO
[Detailed legal arguments with authorities]

5.0 CONCLUSION

5.1 Based on the foregoing submissions, it is humbly urged that this Honourable Court:
(a) [Prayer 1]
(b) [Prayer 2]
(c) [Any other order]

Dated this [DATE]

_____________________
[COUNSEL NAME]
[Law Firm Name]
[Address]
[Phone Number]
[Email]

Counsel to the [Plaintiff/Defendant]
"""
    },
    {
        "id": "5",
        "name": "Affidavit",
        "category": "Litigation",
        "content": """IN THE [COURT NAME]
IN THE [JUDICIAL DIVISION]
HOLDEN AT [LOCATION]

SUIT NO: [NUMBER]

BETWEEN:

[PLAINTIFF NAME] ........................... PLAINTIFF/APPLICANT

AND

[DEFENDANT NAME] ........................... DEFENDANT/RESPONDENT

AFFIDAVIT IN SUPPORT OF [MOTION/APPLICATION]

I, [DEPONENT NAME], [Gender], [Religion], Nigerian citizen, of [ADDRESS], [OCCUPATION], do hereby make oath and state as follows:

1. That I am the [Plaintiff/Defendant/Applicant] in this suit and by virtue of my position, I am familiar with the facts of this case.

2. That I have the authority and consent of the [Party] to depose to this Affidavit.

3. That [State first fact].

4. That [State second fact].

5. That [Continue with numbered paragraphs].

6. That I make this Affidavit in good faith and in support of the [Motion/Application].

7. That I verily believe the facts stated herein to be true and correct to the best of my knowledge, information, and belief.

_____________________
DEPONENT

SWORN TO at the [Court Registry] at [Location] this [DATE]

BEFORE ME:
_____________________
COMMISSIONER FOR OATHS
"""
    },
    {
        "id": "6",
        "name": "Legal Opinion",
        "category": "Corporate",
        "content": """LEGAL OPINION

PRIVATE AND CONFIDENTIAL
PRIVILEGED COMMUNICATION

TO: [CLIENT NAME]
[CLIENT ADDRESS]

FROM: [LAW FIRM NAME]
[LAW FIRM ADDRESS]

DATE: [DATE]

RE: [SUBJECT MATTER]

1.0 INTRODUCTION

We have been instructed to provide a legal opinion on [subject matter]. This opinion is based on the facts and documents provided to us and the applicable laws of the Federal Republic of Nigeria.

2.0 BACKGROUND FACTS

[Detailed background of the matter]

3.0 ISSUES FOR CONSIDERATION

3.1 [First Issue]

3.2 [Second Issue]

3.3 [Third Issue]

4.0 APPLICABLE LEGAL FRAMEWORK

4.1 [Relevant Statutes]

4.2 [Relevant Regulations]

4.3 [Relevant Case Law]

5.0 ANALYSIS

5.1 On the First Issue
[Detailed legal analysis]

5.2 On the Second Issue
[Detailed legal analysis]

5.3 On the Third Issue
[Detailed legal analysis]

6.0 CONCLUSION AND RECOMMENDATIONS

Based on our analysis:

6.1 [First Conclusion]

6.2 [Second Conclusion]

6.3 [Recommendations]

7.0 CAVEATS

This opinion is:
- Based solely on Nigerian law as at the date hereof
- Based on the facts and documents provided to us
- For the sole use of the addressee
- Not to be relied upon by any third party

Yours faithfully,

_____________________
[PARTNER NAME]
For: [LAW FIRM NAME]
"""
    },
    {
        "id": "7",
        "name": "Demand Letter",
        "category": "Litigation",
        "content": """[LAW FIRM LETTERHEAD]

[DATE]

BY HAND/REGISTERED POST/EMAIL

[RECIPIENT NAME]
[RECIPIENT ADDRESS]

Dear Sir/Madam,

RE: DEMAND FOR PAYMENT OF THE SUM OF N[AMOUNT] BEING [DESCRIPTION OF DEBT]

OUR CLIENT: [CLIENT NAME]

We are Solicitors to [CLIENT NAME] (hereinafter referred to as "our Client") on whose behalf and instruction we write you this letter.

Our Client has instructed us on the following facts:

1. [State the background facts]

2. [State the obligation/agreement]

3. [State the breach/default]

By virtue of the foregoing, you are indebted to our Client in the sum of N[AMOUNT] being [description].

Despite several demands, you have failed, refused, and/or neglected to pay the said sum.

TAKE NOTICE that unless you pay the sum of N[AMOUNT] to our Client within SEVEN (7) DAYS of your receipt of this letter, we shall have no option but to institute legal proceedings against you without further notice.

Please be advised that in addition to the principal sum, our Client shall seek:
(a) Interest at [RATE]% per annum
(b) Cost of legal proceedings
(c) General damages

Govern yourself accordingly.

Yours faithfully,

_____________________
[COUNSEL NAME]
For: [LAW FIRM NAME]

c.c: Our Client
"""
    },
    {
        "id": "8",
        "name": "Board Resolution",
        "category": "Corporate",
        "content": """CERTIFIED TRUE COPY OF RESOLUTION PASSED AT A MEETING OF THE BOARD OF DIRECTORS OF [COMPANY NAME] (RC: [REGISTRATION NUMBER]) HELD AT [VENUE] ON [DATE] AT [TIME]

PRESENT:
1. [NAME] - Chairman
2. [NAME] - Director
3. [NAME] - Director
[Add more as applicable]

IN ATTENDANCE:
[NAME] - Company Secretary

RESOLUTION [NUMBER]

[TITLE OF RESOLUTION]

WHEREAS:
A. [Recital/Background]
B. [Reason for Resolution]

IT WAS RESOLVED THAT:
1. [First Resolution]
2. [Second Resolution]
3. That any Director of the Company be and is hereby authorized to execute all documents and do all things necessary to give effect to this Resolution.
4. That the Company Secretary be and is hereby directed to file the necessary returns with the Corporate Affairs Commission.

CERTIFIED TRUE COPY

_____________________
[NAME]
Company Secretary

Date: [DATE]

Company Seal:
"""
    }
]

CASE_STATUSES = ["Active", "Pending", "Completed", "Archived"]
CLIENT_TYPES = ["Individual", "Corporate", "Government"]

# ============================================================
# HELPER FUNCTIONS
# ============================================================

# ============================================================
# GENERATE_ID FUNCTION
# ============================================================
def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())[:8]

# ============================================================
# FORMAT_CURRENCY FUNCTION
# ============================================================
def format_currency(amount: float) -> str:
    """Format amount as Nigerian Naira."""
    return f"₦{amount:,.2f}"

# ============================================================
# FORMAT_DATE FUNCTION
# ============================================================
def format_date(date_str: str) -> str:
    """Format date string to readable format."""
    try:
        date_obj = datetime.fromisoformat(date_str)
        return date_obj.strftime("%B %d, %Y")
    except:
        return date_str

# ============================================================
# GET_DAYS_UNTIL FUNCTION
# ============================================================
def get_days_until(date_str: str) -> int:
    """Calculate days until a given date."""
    try:
        target_date = datetime.fromisoformat(date_str).date()
        today = datetime.now().date()
        return (target_date - today).days
    except:
        return 999

# ============================================================
# GET_RELATIVE_DATE FUNCTION
# ============================================================
def get_relative_date(date_str: str) -> str:
    """Get relative date description."""
    days = get_days_until(date_str)
    if days == 0:
        return "Today"
    elif days == 1:
        return "Tomorrow"
    elif days == -1:
        return "Yesterday"
    elif 0 < days <= 7:
        return f"In {days} days"
    elif -7 <= days < 0:
        return f"{abs(days)} days ago"
    else:
        return format_date(date_str)

# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

# ============================================================
# INIT_SESSION_STATE FUNCTION
# ============================================================
def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        'api_key': '',
        'api_configured': False,
        'cases': [],
        'clients': [],
        'time_entries': [],
        'invoices': [],
        'current_tab': 'AI Assistant',
        'chat_history': [],
        'last_response': '',
        'selected_task_type': 'general'
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

init_session_state()

# ============================================================
# GEMINI API FUNCTIONS
# ============================================================

# ============================================================
# CONFIGURE_GEMINI FUNCTION
# ============================================================
def configure_gemini(api_key: str) -> bool:
    """Configure the Gemini API."""
    try:
        genai.configure(api_key=api_key)
        # Test the configuration
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("Say 'API configured successfully' in one line.")
        st.session_state.api_configured = True
        st.session_state.api_key = api_key
        return True
    except Exception as e:
        st.error(f"Failed to configure API: {str(e)}")
        return False

def generate_legal_response(prompt: str, task_type: str) -> str:
    """Generate a legal response using Gemini."""
    if not st.session_state.api_configured:
        return "Please configure your Gemini API key first."
    
    system_prompt = f"""You are LexiAssist, an advanced AI-powered legal assistant designed specifically for Nigerian lawyers. You perform high-level legal reasoning, draft documents, interpret statutes, assist with legal research, and support litigation and corporate practice workflows.

CORE PRINCIPLES:
1. Default jurisdiction: Nigeria (Constitution, Acts, subsidiary legislation, Rules of Court, case law)
2. Use step-by-step reasoning (IRAC/FILAC methods where applicable)
3. Provide legal information and analysis, NOT definitive legal conclusions
4. Never hallucinate cases, laws, or authorities - state uncertainty clearly if unsure
5. Professional tone suitable for legal practice
6. Always include relevant statutory/case references when available
7. Format responses clearly with headings and numbered points where appropriate

OUTPUT FORMAT:
1. Restate the user request briefly
2. List key assumptions (if needed)
3. Provide detailed analysis or draft
4. Include relevant legal authorities
5. Add any caveats or recommendations

Task Type: {TASK_TYPES.get(task_type, {}).get('label', 'General Query')}
User Request: {prompt}"""
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            system_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
            )
        )
        return response.text
    except Exception as e:
        return f"Error generating response: {str(e)}"

def conduct_legal_research(query: str) -> str:
    """Conduct legal research using Gemini."""
    if not st.session_state.api_configured:
        return "Please configure your Gemini API key first."
    
    research_prompt = f"""You are LexiAssist conducting comprehensive legal research for Nigerian lawyers.

Research Query: {query}

Please provide detailed legal research including:

1. RELEVANT NIGERIAN STATUTES AND PROVISIONS
- List all applicable laws, acts, and their specific sections
- Include relevant regulations and subsidiary legislation
- Note any recent amendments

2. KEY CASE LAW
- Cite relevant Nigerian court decisions
- Include case names, citations (where known), and key holdings
- Distinguish between Supreme Court, Court of Appeal, and High Court decisions
- Note any landmark or leading cases

3. LEGAL PRINCIPLES AND DOCTRINES
- Explain the fundamental legal principles involved
- Discuss how these principles have been interpreted by Nigerian courts
- Note any conflicting authorities

4. PRACTICAL APPLICATION
- How these laws/principles apply to the query
- Procedural requirements
- Limitation periods
- Jurisdictional considerations

5. PRACTICAL GUIDANCE FOR NIGERIAN LEGAL PRACTICE
- Court procedures and requirements
- Filing fees and timelines
- Common pitfalls to avoid
- Strategic considerations

6. ADDITIONAL CONSIDERATIONS
- Recent legal developments
- Pending legislation
- Alternative dispute resolution options
- Comparative law perspectives (where relevant)

Format your response with clear headings and subheadings. If you are uncertain about specific case citations or statute numbers, clearly state this and provide the general principle instead."""
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            research_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
            )
        )
        return response.text
    except Exception as e:
        return f"Error conducting research: {str(e)}"

# ============================================================
# DATA MANAGEMENT FUNCTIONS
# ============================================================

# ============================================================
# ADD_CASE FUNCTION
# ============================================================
def add_case(case_data: dict):
    """Add a new case."""
    case_data['id'] = generate_id()
    case_data['created_at'] = datetime.now().isoformat()
    st.session_state.cases.append(case_data)
    return case_data

# ============================================================
# UPDATE_CASE FUNCTION
# ============================================================
def update_case(case_id: str, updates: dict):
    """Update an existing case."""
    for i, case in enumerate(st.session_state.cases):
        if case['id'] == case_id:
            st.session_state.cases[i].update(updates)
            st.session_state.cases[i]['updated_at'] = datetime.now().isoformat()
            return True
    return False

# ============================================================
# DELETE_CASE FUNCTION
# ============================================================
def delete_case(case_id: str):
    """Delete a case."""
    st.session_state.cases = [c for c in st.session_state.cases if c['id'] != case_id]

# ============================================================
# ADD_CLIENT FUNCTION
# ============================================================
def add_client(client_data: dict):
    """Add a new client."""
    client_data['id'] = generate_id()
    client_data['created_at'] = datetime.now().isoformat()
    st.session_state.clients.append(client_data)
    return client_data

# ============================================================
# DELETE_CLIENT FUNCTION
# ============================================================
def delete_client(client_id: str):
    """Delete a client."""
    st.session_state.clients = [c for c in st.session_state.clients if c['id'] != client_id]

# ============================================================
# GET_CLIENT_NAME FUNCTION
# ============================================================
def get_client_name(client_id: str) -> str:
    """Get client name by ID."""
    for client in st.session_state.clients:
        if client['id'] == client_id:
            return client['name']
    return "Unknown Client"

# ============================================================
# ADD_TIME_ENTRY FUNCTION
# ============================================================
def add_time_entry(entry_data: dict):
    """Add a new time entry."""
    entry_data['id'] = generate_id()
    entry_data['created_at'] = datetime.now().isoformat()
    entry_data['amount'] = entry_data['hours'] * entry_data['rate']
    st.session_state.time_entries.append(entry_data)
    return entry_data

# ============================================================
# DELETE_TIME_ENTRY FUNCTION
# ============================================================
def delete_time_entry(entry_id: str):
    """Delete a time entry."""
    st.session_state.time_entries = [e for e in st.session_state.time_entries if e['id'] != entry_id]

# ============================================================
# GENERATE_INVOICE FUNCTION
# ============================================================
def generate_invoice(client_id: str):
    """Generate an invoice for a client."""
    client_entries = [e for e in st.session_state.time_entries if e.get('client_id') == client_id]
    if not client_entries:
        return None
    client_name = get_client_name(client_id)
    total = sum(e['amount'] for e in client_entries)
    invoice = {
        'id': generate_id(),
        'invoice_no': f"INV-{datetime.now().strftime('%Y%m%d')}-{generate_id()[:4].upper()}",
        'client_id': client_id,
        'client_name': client_name,
        'entries': client_entries,
        'total': total,
        'date': datetime.now().isoformat(),
        'status': 'Draft'
    }
    st.session_state.invoices.append(invoice)
    return invoice

def get_total_billable() -> float:
    """Calculate total billable amount."""
    return sum(e.get('amount', 0) for e in st.session_state.time_entries)

def get_total_hours() -> float:
    """Calculate total hours logged."""
    return sum(e.get('hours', 0) for e in st.session_state.time_entries)

def get_client_billable(client_id: str) -> float:
    """Get total billable for a client."""
    return sum(e.get('amount', 0) for e in st.session_state.time_entries if e.get('client_id') == client_id)

def get_client_case_count(client_id: str) -> int:
    """Get number of cases for a client."""
    return len([c for c in st.session_state.cases if c.get('client_id') == client_id])

def get_upcoming_hearings() -> list:
    """Get upcoming hearings sorted by date."""
    hearings = []
    for case in st.session_state.cases:
        if case.get('next_hearing') and case.get('status') == 'Active':
            hearings.append({
                'case_id': case['id'],
                'case_title': case['title'],
                'date': case['next_hearing'],
                'court': case.get('court', ''),
                'suit_no': case.get('suit_no', '')
            })
    hearings.sort(key=lambda x: x['date'])
    return hearings[:10]

# ============================================================
# UI COMPONENTS
# ============================================================

# ============================================================
# RENDER_HEADER FUNCTION
# ============================================================
def render_header():
    """Render the main header."""
    st.markdown("""
    <div class="main-header">
        <h1>⚖️ LexiAssist</h1>
        <p>AI-Powered Legal Practice Management System for Nigerian Lawyers | Powered by Google Gemini</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# RENDER_STATS FUNCTION
# ============================================================
def render_stats():
    """Render statistics cards."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{len(st.session_state.cases)}</div>
            <div class="stat-label">📁 Active Cases</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card blue">
            <div class="stat-value">{len(st.session_state.clients)}</div>
            <div class="stat-label">👥 Clients</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-card purple">
            <div class="stat-value">{format_currency(get_total_billable())}</div>
            <div class="stat-label">💰 Billable</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        upcoming = len(get_upcoming_hearings())
        st.markdown(f"""
        <div class="stat-card amber">
            <div class="stat-value">{upcoming}</div>
            <div class="stat-label">📅 Upcoming Hearings</div>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# RENDER_SIDEBAR FUNCTION
# ============================================================
def render_sidebar():
    """Render the sidebar."""
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        # API Key Configuration
        st.markdown("#### 🔑 Gemini API Key")
        api_key = st.text_input(
            "Enter your API key",
            type="password",
            value=st.session_state.api_key,
            help="Get your API key from https://makersuite.google.com/app/apikey"
        )
        if st.button("Configure API", type="primary"):
            if api_key:
                with st.spinner("Configuring API..."):
                    if configure_gemini(api_key):
                        st.success("✅ API configured successfully!")
                    else:
                        st.error("❌ Failed to configure API")
            else:
                st.warning("Please enter an API key")
        if st.session_state.api_configured:
            st.success("✅ API is configured")
        else:
            st.warning("⚠️ API not configured")
        # ============================================================
        # CUSTOM CSS STYLING
        # ============================================================
        st.markdown("""
        **Get your free API key:**
        1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
        2. Sign in with Google
        3. Create an API key
        4. Paste it above
        """)
        st.divider()
        # Data Export/Import
        st.markdown("#### 💾 Data Management")
        # Export data
        if st.button("📥 Export All Data"):
            data = {
                'cases': st.session_state.cases,
                'clients': st.session_state.clients,
                'time_entries': st.session_state.time_entries,
                'invoices': st.session_state.invoices,
                'exported_at': datetime.now().isoformat()
            }
            json_str = json.dumps(data, indent=2)
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name=f"lexiassist_backup_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
        # Import data
        uploaded_file = st.file_uploader("📤 Import Data", type=['json'])
        if uploaded_file:
            try:
                data = json.load(uploaded_file)
                st.session_state.cases = data.get('cases', [])
                st.session_state.clients = data.get('clients', [])
                st.session_state.time_entries = data.get('time_entries', [])
                st.session_state.invoices = data.get('invoices', [])
                st.success("Data imported successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error importing data: {str(e)}")
        st.divider()
        # Quick Actions
        st.markdown("#### ⚡ Quick Actions")
        if st.button("➕ New Case", use_container_width=True):
            st.session_state.current_tab = "Cases"
            st.rerun()
        if st.button("👤 New Client", use_container_width=True):
            st.session_state.current_tab = "Clients"
            st.rerun()
        if st.button("⏱️ Log Time", use_container_width=True):
            st.session_state.current_tab = "Billing"
            st.rerun()
        st.divider()
        # About
        st.markdown("#### ℹ️ About")
        st.markdown("""
        **LexiAssist v1.0**
        AI-Powered Legal Practice Management System designed for Nigerian Lawyers.
        
        Built with:
        - 🤖 Google Gemini AI
        - 🎈 Streamlit
        - 🐍 Python
        
        © 2024 LexiAssist
        """)

# ============================================================
# MAIN TAB CONTENT FUNCTIONS
# ============================================================

# ============================================================
# RENDER_AI_ASSISTANT FUNCTION
# ============================================================
def render_ai_assistant():
    """Render the AI Assistant tab."""
    st.markdown("### 🤖 AI Legal Assistant")
    st.markdown("Get AI-powered assistance with legal drafting, analysis, and research.")
    # Task Type Selection
    st.markdown("#### Select Task Type")
    cols = st.columns(3)
    for i, (key, task) in enumerate(TASK_TYPES.items()):
        with cols[i % 3]:
            selected = st.session_state.selected_task_type == key
            if st.button(
                f"{task['icon']} {task['label'].split(' ', 1)[1]}\n\n{task['description']}",
                key=f"task_{key}",
                use_container_width=True,
                type="primary" if selected else "secondary"
            ):
                st.session_state.selected_task_type = key
                st.rerun()
    st.markdown("---")
    # Input Section
    st.markdown("#### Describe Your Legal Task or Query")
    user_input = st.text_area(
        "Enter your query",
        height=200,
        placeholder="Example: Draft a lease agreement for commercial property in Lagos with 2-year term and rent review clause...",
        label_visibility="collapsed"
    )
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("✨ Generate Legal Response", type="primary", use_container_width=True, disabled=not st.session_state.api_configured):
            if user_input:
                with st.spinner("🔄 Generating response..."):
                    response = generate_legal_response(user_input, st.session_state.selected_task_type)
                    st.session_state.last_response = response
            else:
                st.warning("Please enter your legal query or task")
    with col2:
        if st.button("📋 Use Template", use_container_width=True):
            st.session_state.current_tab = "Templates"
            st.rerun()
    if not st.session_state.api_configured:
        st.info("⚠️ Please configure your Gemini API key in the sidebar to use the AI assistant.")
    # Response Display
    if st.session_state.last_response:
        st.markdown("---")
        st.markdown("#### 📄 LexiAssist Response")
        # Export buttons
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            st.download_button(
                label="📥 TXT",
                data=st.session_state.last_response,
                file_name=f"LexiAssist_Response_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain"
            )
        with col2:
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>LexiAssist Legal Document</title>
    <style>
        body {{
            font-family: Georgia, serif;
            line-height: 1.8;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
        }}
        h1 {{
            color: #059669;
            border-bottom: 3px solid #059669;
            padding-bottom: 12px;
        }}
        .content {{
            white-space: pre-wrap;
        }}
        .disclaimer {{
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 16px;
            margin-top: 32px;
        }}
        .footer {{
            text-align: center;
            margin-top: 32px;
            color: #64748b;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <h1>⚖️ LexiAssist Legal Document</h1>
    <div class="content">{st.session_state.last_response}</div>
    <div class="disclaimer">
        <strong>⚖️ Professional Disclaimer:</strong> This document is generated for informational purposes only and does not constitute legal advice.
    </div>
    <div class="footer">
        <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        <p>LexiAssist - AI-Powered Legal Practice Management</p>
    </div>
</body>
</html>"""
            st.download_button(
                label="📥 HTML",
                data=html_content,
                file_name=f"LexiAssist_Response_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                mime="text/html"
            )
        # Display response
        st.markdown(f"""
        <div class="response-box">
            {st.session_state.last_response}
        </div>
        """, unsafe_allow_html=True)
        # Disclaimer
        st.markdown("""
        <div class="disclaimer">
            <strong>⚖️ Professional Disclaimer:</strong> This response is for informational purposes only and does not constitute legal advice. All legal work should be reviewed by a qualified Nigerian lawyer.
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# RENDER_RESEARCH FUNCTION
# ============================================================
def render_research():
    """Render the Legal Research tab."""
    st.markdown("### 📚 Legal Research")
    st.markdown("AI-powered legal research for Nigerian law.")
    # Search Input
    query = st.text_input(
        "Research Query",
        placeholder="E.g., 'breach of contract remedies Nigeria' or 'landlord tenant rights Lagos'",
        label_visibility="collapsed"
    )
    if st.button("🔍 Conduct Research", type="primary", disabled=not st.session_state.api_configured):
        if query:
            with st.spinner("🔄 Conducting research..."):
                results = conduct_legal_research(query)
                st.session_state.research_results = results
        else:
            st.warning("Please enter a research query")
    if not st.session_state.api_configured:
        st.info("⚠️ Please configure your Gemini API key in the sidebar to use legal research.")
    # Display Results
    if 'research_results' in st.session_state and st.session_state.research_results:
        st.markdown("---")
        st.markdown("#### 📋 Research Results")
        col1, col2 = st.columns([1, 5])
        with col1:
            st.download_button(
                label="📥 Export",
                data=st.session_state.research_results,
                file_name=f"Legal_Research_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain"
            )
        st.markdown(f"""
        <div class="response-box">
            {st.session_state.research_results}
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# RENDER_CASES FUNCTION
# ============================================================
def render_cases():
    """Render the Case Management tab."""
    st.markdown("### 📁 Case Management")
    # Add Case Form
    with st.expander("➕ Add New Case", expanded=False):
        with st.form("add_case_form"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Case Title *", placeholder="E.g., John Doe v. State")
                suit_no = st.text_input("Suit Number *", placeholder="E.g., FHC/L/CS/123/2024")
                court = st.text_input("Court", placeholder="E.g., Federal High Court, Lagos")
            with col2:
                next_hearing = st.date_input("Next Hearing Date")
                status = st.selectbox("Status", CASE_STATUSES)
                client_options = ["Select Client"] + [c['name'] for c in st.session_state.clients]
                client_id_idx = st.selectbox("Client", range(len(client_options)), format_func=lambda x: client_options[x])
            notes = st.text_area("Notes", placeholder="Additional case notes...")
            if st.form_submit_button("Save Case", type="primary"):
                if title and suit_no:
                    client_id = None
                    if client_id_idx > 0:
                        client_id = st.session_state.clients[client_id_idx - 1]['id']
                    case_data = {
                        'title': title,
                        'suit_no': suit_no,
                        'court': court,
                        'next_hearing': next_hearing.isoformat() if next_hearing else None,
                        'status': status,
                        'client_id': client_id,
                        'notes': notes
                    }
                    add_case(case_data)
                    st.success("✅ Case added successfully!")
                    st.rerun()
                else:
                    st.error("Please fill in required fields (Title and Suit Number)")
    # Filter Cases
    st.markdown("#### 🔍 Filter Cases")
    filter_status = st.selectbox("Filter by Status", ["All"] + CASE_STATUSES)
    # Display Cases
    filtered_cases = st.session_state.cases
    if filter_status != "All":
        filtered_cases = [c for c in filtered_cases if c.get('status') == filter_status]
    if filtered_cases:
        for case in filtered_cases:
            with st.container():
                col1, col2 = st.columns([5, 1])
                with col1:
                    status_color = {
                        'Active': 'success',
                        'Pending': 'warning',
                        'Completed': 'info',
                        'Archived': ''
                    }.get(case.get('status', ''), '')
                    st.markdown(f"""
                    <div class="custom-card">
                        <h4>{case['title']} <span class="badge badge-{status_color}">{case.get('status', 'Unknown')}</span></h4>
                        <p><strong>Suit No:</strong> {case.get('suit_no', 'N/A')}</p>
                        <p><strong>Court:</strong> {case.get('court', 'N/A')}</p>
                        <p><strong>Client:</strong> {get_client_name(case.get('client_id', ''))}</p>
                        {f"<p><strong>Next Hearing:</strong> {format_date(case['next_hearing'])} ({get_relative_date(case['next_hearing'])})</p>" if case.get('next_hearing') else ""}
                        {f"<p><em>{case['notes']}</em></p>" if case.get('notes') else ""}
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    new_status = st.selectbox(
                        "Status",
                        CASE_STATUSES,
                        index=CASE_STATUSES.index(case.get('status', 'Active')) if case.get('status') in CASE_STATUSES else 0,
                        key=f"status_{case['id']}",
                        label_visibility="collapsed"
                    )
                    if new_status != case.get('status'):
                        update_case(case['id'], {'status': new_status})
                        st.rerun()
                    if st.button("🗑️", key=f"delete_{case['id']}", help="Delete case"):
                        delete_case(case['id'])
                        st.rerun()
    else:
        st.info("📁 No cases found. Add your first case above!")

# ============================================================
# RENDER_CALENDAR FUNCTION
# ============================================================
def render_calendar():
    """Render the Calendar tab."""
    st.markdown("### 📅 Court Calendar")
    st.markdown("View upcoming hearings and important dates.")
    hearings = get_upcoming_hearings()
    if hearings:
        st.markdown("#### Upcoming Hearings")
        for hearing in hearings:
            days_until = get_days_until(hearing['date'])
            if days_until <= 3:
                urgency = "urgent"
                urgency_badge = "danger"
            elif days_until <= 7:
                urgency = "warning"
                urgency_badge = "warning"
            else:
                urgency = "normal"
                urgency_badge = "success"
            st.markdown(f"""
            <div class="calendar-event {urgency}">
                <h4>{hearing['case_title']}</h4>
                <p><strong>Suit No:</strong> {hearing['suit_no']}</p>
                <p><strong>Court:</strong> {hearing['court']}</p>
                <p><strong>Date:</strong> {format_date(hearing['date'])} <span class="badge badge-{urgency_badge}">{get_relative_date(hearing['date'])}</span></p>
            </div>
            """, unsafe_allow_html=True)
    # Calendar View
    st.markdown("---")
    st.markdown("#### 📊 Calendar Overview")
    # Create calendar data
    cal_data = []
    for hearing in hearings:
        cal_data.append({
            'Case': hearing['case_title'],
            'Date': hearing['date'],
            'Days Until': get_days_until(hearing['date'])
        })
    if cal_data:
        df = pd.DataFrame(cal_data)
        fig = px.timeline(
            df,
            x_start='Date',
            x_end='Date',
            y='Case',
            title='Upcoming Hearings Timeline'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📅 No upcoming hearings. Add hearing dates to your cases to see them here.")
    # Tips
    st.markdown("---")
    st.markdown("""
    <div class="custom-card">
        <h4>📌 Calendar Tips</h4>
        <ul>
            <li><span class="badge badge-danger">Red</span> - Hearing within 3 days (urgent)</li>
            <li><span class="badge badge-warning">Yellow</span> - Hearing within 7 days (upcoming)</li>
            <li><span class="badge badge-success">Green</span> - Future hearings</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# RENDER_TEMPLATES FUNCTION
# ============================================================
def render_templates():
    """Render the Templates tab."""
    st.markdown("### 📋 Document Templates")
    st.markdown("Legal document templates for Nigerian practice.")
    # Filter by category
    categories = list(set(t['category'] for t in DEFAULT_TEMPLATES))
    selected_category = st.selectbox("Filter by Category", ["All"] + categories)
    # Display templates
    templates = DEFAULT_TEMPLATES
    if selected_category != "All":
        templates = [t for t in templates if t['category'] == selected_category]
    cols = st.columns(2)
    for i, template in enumerate(templates):
        with cols[i % 2]:
            with st.container():
                st.markdown(f"""
                <div class="template-card">
                    <h4>📄 {template['name']}</h4>
                    <span class="badge badge-success">{template['category']}</span>
                    <p style="margin-top: 0.5rem; color: #64748b; font-size: 0.875rem;">
                        {template['content'][:100]}...
                    </p>
                </div>
                """, unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📋 Use", key=f"use_{template['id']}", use_container_width=True):
                        st.session_state.template_content = template['content']
                        st.session_state.current_tab = "AI Assistant"
                        st.success(f"Template '{template['name']}' loaded!")
                        st.rerun()
                with col2:
                    if st.button("👁️ Preview", key=f"preview_{template['id']}", use_container_width=True):
                        st.session_state.preview_template = template
    # Template Preview Modal
    if 'preview_template' in st.session_state and st.session_state.preview_template:
        template = st.session_state.preview_template
        st.markdown("---")
        st.markdown(f"### Preview: {template['name']}")
        st.code(template['content'], language=None)
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Close Preview"):
                del st.session_state.preview_template
                st.rerun()
        with col2:
            st.download_button(
                label="📥 Download Template",
                data=template['content'],
                file_name=f"{template['name'].replace(' ', '_')}.txt",
                mime="text/plain"
            )

# ============================================================
# RENDER_CLIENTS FUNCTION
# ============================================================
def render_clients():
    """Render the Clients tab."""
    st.markdown("### 👥 Client Management")
    # Add Client Form
    with st.expander("➕ Add New Client", expanded=False):
        with st.form("add_client_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Client Name *", placeholder="Full Name or Company")
                email = st.text_input("Email", placeholder="email@example.com")
                phone = st.text_input("Phone", placeholder="+234 xxx xxx xxxx")
            with col2:
                client_type = st.selectbox("Client Type", CLIENT_TYPES)
                address = st.text_input("Address", placeholder="Physical Address")
                notes = st.text_area("Notes", placeholder="Additional information...")
            if st.form_submit_button("Save Client", type="primary"):
                if name:
                    client_data = {
                        'name': name,
                        'email': email,
                        'phone': phone,
                        'type': client_type,
                        'address': address,
                        'notes': notes
                    }
                    add_client(client_data)
                    st.success("✅ Client added successfully!")
                    st.rerun()
                else:
                    st.error("Please enter client name")
    # Display Clients
    if st.session_state.clients:
        cols = st.columns(2)
        for i, client in enumerate(st.session_state.clients):
            with cols[i % 2]:
                case_count = get_client_case_count(client['id'])
                billable = get_client_billable(client['id'])
                st.markdown(f"""
                <div class="custom-card">
                    <h4>{client['name']} <span class="badge badge-info">{client.get('type', 'Individual')}</span></h4>
                    {f"<p>📧 {client['email']}</p>" if client.get('email') else ""}
                    {f"<p>📱 {client['phone']}</p>" if client.get('phone') else ""}
                    {f"<p>📍 {client['address']}</p>" if client.get('address') else ""}
                    <hr style="margin: 1rem 0;">
                    <div style="display: flex; justify-content: space-around; text-align: center;">
                        <div>
                            <div style="font-size: 1.5rem; font-weight: bold; color: #059669;">{case_count}</div>
                            <div style="font-size: 0.75rem; color: #64748b;">Cases</div>
                        </div>
                        <div>
                            <div style="font-size: 1.5rem; font-weight: bold; color: #7c3aed;">{format_currency(billable)}</div>
                            <div style="font-size: 0.75rem; color: #64748b;">Billable</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    if billable > 0:
                        if st.button("📄 Invoice", key=f"invoice_{client['id']}", use_container_width=True):
                            invoice = generate_invoice(client['id'])
                            if invoice:
                                st.success(f"Invoice {invoice['invoice_no']} generated!")
                                st.rerun()
                with col2:
                    if st.button("🗑️ Delete", key=f"del_client_{client['id']}", use_container_width=True):
                        delete_client(client['id'])
                        st.rerun()
    else:
        st.info("👥 No clients yet. Add your first client above!")

# ============================================================
# RENDER_BILLING FUNCTION
# ============================================================
def render_billing():
    """Render the Billing tab."""
    st.markdown("### 💰 Billing & Time Tracking")
    # Summary Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{format_currency(get_total_billable())}</div>
            <div class="stat-label">💰 Total Billable</div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.5rem;">
                {len(st.session_state.time_entries)} entries
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card blue">
            <div class="stat-value">{get_total_hours():.1f}h</div>
            <div class="stat-label">⏱️ Total Hours</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-card purple">
            <div class="stat-value">{len(st.session_state.invoices)}</div>
            <div class="stat-label">📄 Invoices</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("---")
    # Add Time Entry Form
    with st.expander("⏱️ Log Time Entry", expanded=False):
        with st.form("add_time_form"):
            col1, col2 = st.columns(2)
            with col1:
                client_options = ["Select Client"] + [c['name'] for c in st.session_state.clients]
                client_idx = st.selectbox("Client *", range(len(client_options)), format_func=lambda x: client_options[x])
                case_options = ["Select Case (Optional)"] + [c['title'] for c in st.session_state.cases]
                case_idx = st.selectbox("Case", range(len(case_options)), format_func=lambda x: case_options[x])
                date = st.date_input("Date", value=datetime.now())
            with col2:
                hours = st.number_input("Hours *", min_value=0.25, step=0.25, value=1.0)
                rate = st.number_input("Hourly Rate (₦) *", min_value=0, value=50000, step=5000)
                # Show calculated amount
                amount = hours * rate
                st.markdown(f"**Total Amount:** {format_currency(amount)}")
            description = st.text_area("Description *", placeholder="Describe the work performed...")
            if st.form_submit_button("Save Entry", type="primary"):
                if client_idx > 0 and description:
                    client_id = st.session_state.clients[client_idx - 1]['id']
                    case_id = st.session_state.cases[case_idx - 1]['id'] if case_idx > 0 else None
                    entry_data = {
                        'client_id': client_id,
                        'case_id': case_id,
                        'date': date.isoformat(),
                        'hours': hours,
                        'rate': rate,
                        'description': description
                    }
                    add_time_entry(entry_data)
                    st.success("✅ Time entry logged!")
                    st.rerun()
                else:
                    st.error("Please select a client and enter a description")
    # Time Entries Table
    st.markdown("#### 📋 Time Entries")
    if st.session_state.time_entries:
        # Create DataFrame
        entries_data = []
        for entry in reversed(st.session_state.time_entries):
            entries_data.append({
                'Date': format_date(entry['date']),
                'Client': get_client_name(entry.get('client_id', '')),
                'Description': entry['description'][:50] + '...' if len(entry['description']) > 50 else entry['description'],
                'Hours': f"{entry['hours']}h",
                'Rate': format_currency(entry['rate']),
                'Amount': format_currency(entry['amount']),
                'ID': entry['id']
            })
        df = pd.DataFrame(entries_data)
        # Display as table
        st.dataframe(
            df.drop('ID', axis=1),
            use_container_width=True,
            hide_index=True
        )
        # Delete entries
        entry_to_delete = st.selectbox(
            "Select entry to delete",
            ["None"] + [f"{e['Date']} - {e['Client']} - {e['Description']}" for e in entries_data],
            key="delete_entry_select"
        )
        if entry_to_delete != "None" and st.button("🗑️ Delete Selected Entry"):
            idx = [f"{e['Date']} - {e['Client']} - {e['Description']}" for e in entries_data].index(entry_to_delete)
            delete_time_entry(entries_data[idx]['ID'])
            st.success("Entry deleted!")
            st.rerun()
        # Chart
        if len(entries_data) > 1:
            st.markdown("---")
            st.markdown("#### 📊 Billing Overview")
            # Billable by client
            client_billable = {}
            for entry in st.session_state.time_entries:
                client = get_client_name(entry.get('client_id', ''))
                client_billable[client] = client_billable.get(client, 0) + entry['amount']
            fig = px.pie(
                values=list(client_billable.values()),
                names=list(client_billable.keys()),
                title='Billable Amount by Client'
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("⏱️ No time entries yet. Log your first entry above!")
    # Invoices Section
    if st.session_state.invoices:
        st.markdown("---")
        st.markdown("#### 📄 Generated Invoices")
        for invoice in reversed(st.session_state.invoices):
            with st.expander(f"📄 {invoice['invoice_no']} - {invoice['client_name']} - {format_currency(invoice['total'])}"):
                st.markdown(f"""
                **Invoice Number:** {invoice['invoice_no']}
                **Client:** {invoice['client_name']}
                **Date:** {format_date(invoice['date'])}
                **Status:** {invoice['status']}
                **Total:** {format_currency(invoice['total'])}
                """)
                # Generate downloadable invoice
                invoice_content = f"""{'='*60}
INVOICE
{'='*60}

Invoice Number: {invoice['invoice_no']}
Date: {format_date(invoice['date'])}
Status: {invoice['status']}

BILL TO: {invoice['client_name']}

{'-'*60}
TIME ENTRIES
{'-'*60}
"""
                for i, entry in enumerate(invoice['entries'], 1):
                    invoice_content += f"""
{i}. Date: {format_date(entry['date'])}
    Description: {entry['description']}
    Hours: {entry['hours']} @ {format_currency(entry['rate'])}/hr
    Amount: {format_currency(entry['amount'])}
"""
                invoice_content += f"""
{'-'*60}
TOTAL AMOUNT DUE: {format_currency(invoice['total'])}
{'-'*60}

Payment Terms: Due upon receipt
Thank you for your business.

{'='*60}
Generated by LexiAssist Legal Practice Management System
{'='*60}
"""
                st.download_button(
                    label="📥 Download Invoice",
                    data=invoice_content,
                    file_name=f"{invoice['invoice_no']}.txt",
                    mime="text/plain"
                )

# ============================================================
# MAIN APPLICATION
# ============================================================

# ============================================================
# MAIN FUNCTION
# ============================================================
def main():
    """Main application function."""
    render_header()
    render_sidebar()
    render_stats()
    st.markdown("---")
    # Main Navigation Tabs
    tabs = st.tabs([
        "🤖 AI Assistant",
        "📚 Research",
        "📁 Cases",
        "📅 Calendar",
        "📋 Templates",
        "👥 Clients",
        "💰 Billing"
    ])
    with tabs[0]:
        render_ai_assistant()
    with tabs[1]:
        render_research()
    with tabs[2]:
        render_cases()
    with tabs[3]:
        render_calendar()
    with tabs[4]:
        render_templates()
    with tabs[5]:
        render_clients()
    with tabs[6]:
        render_billing()
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #64748b; font-size: 0.875rem;">
        <p>⚖️ <strong>LexiAssist</strong> - AI-Powered Legal Practice Management System</p>
        <p>Designed for Nigerian Lawyers | Powered by Google Gemini</p>
        <p>© 2024 LexiAssist. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# MAIN EXECUTION
# ============================================================
if __name__ == "__main__":
    main()


