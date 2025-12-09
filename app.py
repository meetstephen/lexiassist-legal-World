import streamlit as st
import google.generativeai as genai
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import uuid

# ============================================================
# CONFIGURATION & SETUP
# ============================================================

st.set_page_config(
    page_title="LexiAssist",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
STORAGE_FILE = "lexi_data.json"
CASE_STATUSES = ['active', 'pending', 'completed', 'archived']
CLIENT_TYPES = ['individual', 'corporate', 'government']

# ============================================================
# STATE MANAGEMENT (Persistence)
# ============================================================

def load_data():
    """Loads data from session state or local file."""
    if 'data_loaded' not in st.session_state:
        # Default empty state
        default_data = {
            "cases": [],
            "clients": [],
            "time_entries": [],
            "invoices": [],
            "api_key": ""
        }
        
        # Try to load from local file for persistence
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, "r") as f:
                    saved_data = json.load(f)
                    # Merge saved data with defaults to ensure all keys exist
                    default_data.update(saved_data)
            except Exception as e:
                st.error(f"Error loading data: {e}")

        # Initialize session state
        for key, value in default_data.items():
            st.session_state[key] = value
        
        st.session_state['data_loaded'] = True

def save_data():
    """Saves current session state to local file."""
    data_to_save = {
        "cases": st.session_state.cases,
        "clients": st.session_state.clients,
        "time_entries": st.session_state.time_entries,
        "invoices": st.session_state.invoices,
        "api_key": st.session_state.api_key
    }
    try:
        with open(STORAGE_FILE, "w") as f:
            json.dump(data_to_save, f)
    except Exception as e:
        st.error(f"Error saving data: {e}")

# Load data on start
load_data()

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def generate_id():
    return str(uuid.uuid4())

def call_gemini(prompt, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro') # Using gemini-pro which is generally available
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise Exception(f"Gemini API Error: {str(e)}")

def format_currency(amount):
    return f"₦{amount:,.2f}"

def get_client_name(client_id):
    client = next((c for c in st.session_state.clients if c['id'] == client_id), None)
    return client['name'] if client else "Unknown Client"

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2666/2666505.png", width=50) # Generic Legal Icon
    st.title("LexiAssist")
    st.caption("AI Legal Practice Management")
    
    # Navigation
    selected_tab = st.radio("Navigation", 
        ["AI Assistant", "Legal Research", "Cases", "Calendar", "Templates", "Clients", "Billing"],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # API Key Configuration
    st.subheader("⚙️ Settings")
    api_key_input = st.text_input("Gemini API Key", value=st.session_state.api_key, type="password")
    if api_key_input != st.session_state.api_key:
        st.session_state.api_key = api_key_input
        save_data()
        st.success("API Key updated!")
    
    if not st.session_state.api_key:
        st.warning("Please enter your Google Gemini API Key to use AI features.")
        st.markdown("[Get API Key](https://makersuite.google.com/app/apikey)")

# ============================================================
# PAGES
# ============================================================

# --- 1. AI ASSISTANT ---
if selected_tab == "AI Assistant":
    st.header("🤖 AI Legal Assistant")
    
    task_types = {
        "Drafting": "Contracts, pleadings, applications",
        "Analysis": "Issue spotting, IRAC reasoning",
        "Research": "Case law, statutes, authorities",
        "General": "Ask anything legal-related"
    }
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_task = st.selectbox("Select Task Type", list(task_types.keys()))
        st.info(f"**{selected_task}:** {task_types[selected_task]}")
    
    with col2:
        user_query = st.text_area("Describe your task", height=150, placeholder="E.g., Draft a lease agreement for a property in Lagos...")
        
        if st.button("Generate Response", type="primary"):
            if not st.session_state.api_key:
                st.error("Please configure your API Key in the sidebar.")
            elif not user_query:
                st.warning("Please enter a query.")
            else:
                with st.spinner("LexiAssist is thinking..."):
                    system_prompt = f"""
                    You are LexiAssist, an AI legal assistant for Nigerian lawyers.
                    Context: Nigeria (Laws, Acts, Rules of Court).
                    Task Type: {selected_task}
                    Query: {user_query}
                    
                    Please provide a professional, formatted legal response.
                    Disclaimer: State that this is AI-generated and not final legal advice.
                    """
                    try:
                        response = call_gemini(system_prompt, st.session_state.api_key)
                        st.session_state['last_response'] = response
                    except Exception as e:
                        st.error(f"Error: {e}")

    if 'last_response' in st.session_state:
        st.divider()
        st.subheader("Response")
        st.markdown(st.session_state['last_response'])
        
        st.download_button(
            label="Download as Text",
            data=st.session_state['last_response'],
            file_name="lexi_assist_output.txt",
            mime="text/plain"
        )

# --- 2. LEGAL RESEARCH ---
elif selected_tab == "Legal Research":
    st.header("📚 Legal Research")
    
    research_query = st.text_input("Enter Research Topic", placeholder="E.g., Requirements for winding up a company in Nigeria")
    
    if st.button("Start Research", type="primary"):
        if not st.session_state.api_key:
            st.error("API Key required.")
        elif not research_query:
            st.warning("Enter a topic.")
        else:
            with st.spinner("Researching databases..."):
                prompt = f"""
                Conduct legal research on: {research_query}
                Jurisdiction: Nigeria.
                Structure:
                1. Relevant Statutes
                2. Case Law (Cite specific cases if known, or general principles)
                3. Analysis
                4. Conclusion
                """
                try:
                    res = call_gemini(prompt, st.session_state.api_key)
                    st.markdown(res)
                except Exception as e:
                    st.error(f"Error: {e}")

# --- 3. CASES ---
elif selected_tab == "Cases":
    col1, col2 = st.columns([4, 1])
    col1.header("🗂️ Case Management")
    
    # Add New Case Form (Expander)
    with st.expander("➕ Add New Case"):
        with st.form("add_case_form"):
            c_title = st.text_input("Case Title")
            c1, c2 = st.columns(2)
            c_suit = c1.text_input("Suit No")
            c_court = c2.text_input("Court")
            c_date = st.date_input("Next Hearing", value=None)
            
            # Client Dropdown
            client_opts = {c['id']: c['name'] for c in st.session_state.clients}
            c_client_id = st.selectbox("Client", options=list(client_opts.keys()), format_func=lambda x: client_opts[x]) if client_opts else None
            
            c_status = st.selectbox("Status", CASE_STATUSES)
            c_notes = st.text_area("Notes")
            
            if st.form_submit_button("Save Case"):
                if c_title and c_suit:
                    new_case = {
                        "id": generate_id(),
                        "title": c_title,
                        "suitNo": c_suit,
                        "court": c_court,
                        "nextHearing": str(c_date) if c_date else None,
                        "status": c_status,
                        "notes": c_notes,
                        "clientId": c_client_id,
                        "createdAt": datetime.now().isoformat()
                    }
                    st.session_state.cases.append(new_case)
                    save_data()
                    st.success("Case added!")
                    st.rerun()
                else:
                    st.error("Title and Suit No are required.")

    # Display Cases
    if not st.session_state.cases:
        st.info("No cases found. Add one above.")
    else:
        # Convert to DataFrame for easier display
        df_data = []
        for c in st.session_state.cases:
            client_name = get_client_name(c.get('clientId'))
            df_data.append({
                "Title": c['title'],
                "Suit No": c['suitNo'],
                "Status": c['status'],
                "Hearing": c.get('nextHearing', 'N/A'),
                "Client": client_name,
                "ID": c['id'] # Hidden ID for identification
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df.drop(columns=["ID"]), use_container_width=True)

        # Delete functionality
        st.subheader("Manage Cases")
        case_to_delete = st.selectbox("Select Case to Delete", options=df_data, format_func=lambda x: f"{x['Title']} ({x['Suit No']})")
        if st.button("Delete Selected Case"):
            st.session_state.cases = [c for c in st.session_state.cases if c['id'] != case_to_delete['ID']]
            save_data()
            st.success("Case deleted.")
            st.rerun()

# --- 4. CALENDAR ---
elif selected_tab == "Calendar":
    st.header("📅 Court Calendar")
    
    upcoming = [c for c in st.session_state.cases if c.get('nextHearing') and c['status'] == 'active']
    upcoming.sort(key=lambda x: x['nextHearing'])
    
    if not upcoming:
        st.info("No upcoming hearings scheduled.")
    else:
        for case in upcoming:
            date_obj = datetime.strptime(case['nextHearing'], "%Y-%m-%d").date()
            days_left = (date_obj - datetime.now().date()).days
            
            color = "red" if days_left <= 3 else "orange" if days_left <= 7 else "green"
            
            with st.container():
                c1, c2 = st.columns([1, 4])
                with c1:
                    st.markdown(f"### :{color}[{days_left} Days]")
                    st.caption(f"{case['nextHearing']}")
                with c2:
                    st.subheader(case['title'])
                    st.text(f"Court: {case['court']} | Suit: {case['suitNo']}")
                st.divider()

# --- 5. TEMPLATES ---
elif selected_tab == "Templates":
    st.header("📄 Template Library")
    
    templates = {
        "Employment Contract": "EMPLOYMENT CONTRACT\n\nMade on [DATE] between...",
        "Tenancy Agreement": "TENANCY AGREEMENT\n\nLandlord: [NAME]...",
        "Power of Attorney": "POWER OF ATTORNEY\n\nI, [NAME], hereby appoint...",
        "Affidavit": "IN THE HIGH COURT OF...\nAFFIDAVIT OF FACT...",
    }
    
    selected_temp = st.selectbox("Choose a template", list(templates.keys()))
    
    st.text_area("Template Content (Copy or Edit)", value=templates[selected_temp], height=300)
    
    if st.button("Send to AI Assistant for Customization"):
        # This is a bit tricky in Streamlit, we'll just tell the user to copy it
        st.info("Copy the text above, go to 'AI Assistant', paste it, and ask the AI to fill in the details.")

# --- 6. CLIENTS ---
elif selected_tab == "Clients":
    st.header("👥 Client Management")
    
    with st.expander("➕ Add New Client"):
        with st.form("add_client"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            c_type = st.selectbox("Type", CLIENT_TYPES)
            
            if st.form_submit_button("Save Client"):
                if name:
                    new_client = {
                        "id": generate_id(),
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "type": c_type,
                        "createdAt": datetime.now().isoformat()
                    }
                    st.session_state.clients.append(new_client)
                    save_data()
                    st.success("Client added!")
                    st.rerun()
                else:
                    st.error("Name is required.")

    if st.session_state.clients:
        for client in st.session_state.clients:
            with st.container():
                st.markdown(f"**{client['name']}** ({client['type']})")
                st.caption(f"📧 {client['email']} | 📞 {client['phone']}")
                if st.button("Delete", key=client['id']):
                    st.session_state.clients = [c for c in st.session_state.clients if c['id'] != client['id']]
                    save_data()
                    st.rerun()
                st.divider()
    else:
        st.info("No clients yet.")

# --- 7. BILLING ---
elif selected_tab == "Billing":
    st.header("💰 Billing & Time Tracking")
    
    # Stats
    total_billable = sum(e['amount'] for e in st.session_state.time_entries)
    col1, col2 = st.columns(2)
    col1.metric("Total Billable", format_currency(total_billable))
    col2.metric("Total Hours", f"{sum(e['hours'] for e in st.session_state.time_entries)} hrs")
    
    # Add Entry
    with st.expander("➕ Log Time Entry"):
        with st.form("time_entry"):
            client_opts = {c['id']: c['name'] for c in st.session_state.clients}
            b_client = st.selectbox("Client", options=list(client_opts.keys()), format_func=lambda x: client_opts[x]) if client_opts else None
            
            b_desc = st.text_input("Description")
            c1, c2 = st.columns(2)
            b_hours = c1.number_input("Hours", min_value=0.1, step=0.5)
            b_rate = c2.number_input("Rate (₦)", value=50000)
            
            if st.form_submit_button("Log Time"):
                if b_client and b_hours:
                    entry = {
                        "id": generate_id(),
                        "clientId": b_client,
                        "description": b_desc,
                        "hours": b_hours,
                        "rate": b_rate,
                        "amount": b_hours * b_rate,
                        "date": datetime.now().isoformat()
                    }
                    st.session_state.time_entries.append(entry)
                    save_data()
                    st.success("Time logged!")
                    st.rerun()
                else:
                    st.error("Client and Hours required")

    # Table
    if st.session_state.time_entries:
        bill_data = []
        for e in st.session_state.time_entries:
            bill_data.append({
                "Date": e['date'][:10],
                "Client": get_client_name(e['clientId']),
                "Description": e['description'],
                "Hours": e['hours'],
                "Amount": format_currency(e['amount'])
            })
        st.dataframe(pd.DataFrame(bill_data), use_container_width=True)
    else:
        st.info("No time entries logged.")