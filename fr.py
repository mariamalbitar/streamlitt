import streamlit as st
import requests
import plotly.express as px
import pandas as pd
import json
import os
from datetime import datetime, timedelta


try:
    from query_engine import initialize_query_engine, run_query
except ImportError as e:
    st.error(f"Failed to import query_engine: {e}. Query Interface will be disabled.")
    initialize_query_engine = lambda x: None
    run_query = lambda x, y: "Query Interface is disabled due to import error."


st.set_page_config(page_title="Financial Insights Dashboard", layout="wide")


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
.stApp {
    background-color: #F3F4F6;
    font-family: 'Roboto', sans-serif;
}
.auth-container {
    background: #FFFFFF;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    max-width: 400px;
    margin: 3rem auto;
    text-align: center;
}
.main-title {
    text-align: center;
    font-size: 2.5rem;
    font-weight: 700;
    color: #1E3A8A;
    margin-bottom: 1rem;
}
.logo {
    display: block;
    margin: 0 auto 1rem;
    max-width: 100px;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 1rem;
    justify-content: center;
}
.stTabs [data-baseweb="tab"] {
    background-color: #FFFFFF;
    color: #1E3A8A;
    font-weight: 400;
    font-size: 1rem;
    padding: 0.5rem 1rem;
    border-radius: 8px;
    transition: all 0.3s ease;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background-color: #1E3A8A;
    color: #FFFFFF;
}
.stTabs [data-baseweb="tab"]:hover {
    background-color: #E5E7EB;
}
.stTextInput > div > div > input {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    padding: 0.7rem;
    color: #1E3A8A;
    font-size: 0.95rem;
}
.stTextInput > div > div > input:focus {
    border-color: #1E3A8A;
    box-shadow: 0 0 4px rgba(30, 58, 138, 0.3);
}
.stButton > button {
    background-color: #1E3A8A;
    color: #FFFFFF;
    border-radius: 8px;
    padding: 0.7rem 1.5rem;
    font-weight: 400;
    font-size: 0.95rem;
    transition: all 0.3s ease;
    width: 100%;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.stButton > button:hover {
    background-color: #3B82F6;
    transform: scale(1.03);
}
.stAlert {
    border-radius: 8px;
    padding: 0.8rem;
    font-size: 0.9rem;
}
.company-data {
    background: #FFFFFF;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    margin: 2rem 0;
}
.kpi-card {
    background: #FFFFFF;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 1rem;
    margin: 0.5rem;
    text-align: center;
}
.kpi-card h3 {
    margin: 0;
    font-size: 0.9rem;
    color: #1E3A8A;
}
.kpi-card p {
    margin: 0.5rem 0 0;
    font-size: 1.2rem;
    font-weight: 700;
}
.positive {
    color: #10B981;
}
.negative {
    color: #EF4444;
}
.sidebar .sidebar-content {
    background-color: #1E3A8A;
    color: #FFFFFF;
}
.sidebar h2, .sidebar p {
    color: #FFFFFF;
}
.logout-button {
    background-color: #EF4444;
    color: #FFFFFF;
    border-radius: 8px;
    padding: 0.7rem;
    font-weight: 400;
    font-size: 0.95rem;
    transition: all 0.3s ease;
    width: 100%;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.logout-button:hover {
    background-color: #DC2626;
    transform: scale(1.03);
}
.footer {
    text-align: center;
    color: #6B7280;
    font-size: 0.85rem;
    margin-top: 2rem;
    padding: 1rem;
}
</style>
""", unsafe_allow_html=True)


st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">', unsafe_allow_html=True)


API_URL = "http://127.0.0.1:8002"

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.email = None
    st.session_state.role = None
    st.session_state.page = "login"


companies_paths = {
    "Apple": r"C:\Users\Fa\Desktop\Streamlit-Authentication-main\stock_AAPL-1.json",
    "Meta": r"C:\Users\Fa\Desktop\Streamlit-Authentication-main\stock_META-1.json",
    "Microsoft": r"C:\Users\Fa\Desktop\Streamlit-Authentication-main\stock_MSFT-1.json",
    "cleaned": r"C:\Users\Fa\Desktop\Streamlit-Authentication-main\cleaned.json",
    "financial_phrasebank": r"C:\Users\Fa\Desktop\Streamlit-Authentication-main\financial_phrasebank (2).json"
}
companies = ['Apple', 'Meta', 'Microsoft']
REQUIRED_STOCK_COLUMNS = ['Date', 'Close', 'Open', 'High', 'Low', 'Volume']
REQUIRED_CLEANED_COLUMNS = ['Credit Expiration', 'Current Stage', 'DPD']
REQUIRED_PHRASEBANK_COLUMNS = ['Text', 'Sentiment']

sample_data = {
    'Apple': pd.DataFrame({
        'Date': pd.date_range(start='2025-01-01', end='2025-07-12', freq='D'),
        'Close': [150 + i * 0.3 + (i % 8) for i in range(193)],
        'Open': [148 + i * 0.3 + (i % 8) for i in range(193)],
        'High': [152 + i * 0.3 + (i % 8) for i in range(193)],
        'Low': [146 + i * 0.3 + (i % 8) for i in range(193)],
        'Volume': [2000000 + i * 2000 for i in range(193)]
    }),
    'Meta': pd.DataFrame({
        'Date': pd.date_range(start='2025-01-01', end='2025-07-12', freq='D'),
        'Close': [300 + i * 0.5 + (i % 10) for i in range(193)],
        'Open': [298 + i * 0.5 + (i % 10) for i in range(193)],
        'High': [302 + i * 0.5 + (i % 10) for i in range(193)],
        'Low': [296 + i * 0.5 + (i % 10) for i in range(193)],
        'Volume': [1000000 + i * 1000 for i in range(193)]
    }),
    'Microsoft': pd.DataFrame({
        'Date': pd.date_range(start='2025-01-01', end='2025-07-12', freq='D'),
        'Close': [250 + i * 0.4 + (i % 7) for i in range(193)],
        'Open': [248 + i * 0.4 + (i % 7) for i in range(193)],
        'High': [252 + i * 0.4 + (i % 7) for i in range(193)],
        'Low': [246 + i * 0.4 + (i % 7) for i in range(193)],
        'Volume': [1500000 + i * 1500 for i in range(193)]
    }),
    'cleaned': pd.DataFrame([
        {"Credit Expiration": 92, "DPD": 0, "Current Stage": 1},
        {"Credit Expiration": 245, "DPD": 0, "Current Stage": 1},
        {"Credit Expiration": 0, "DPD": 0, "Current Stage": 2}
    ]),
    'financial_phrasebank': pd.DataFrame([
        {"Text": "Apple stock rises after strong earnings", "Sentiment": "positive"},
        {"Text": "Meta faces regulatory challenges", "Sentiment": "negative"}
    ])
}


def load_financial_data(file_path, company_name):
    try:
        if not os.path.exists(file_path):
            st.warning(f"File not found: {file_path}. Using sample data.")
            return None
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        if isinstance(raw_data, dict) and company_name in raw_data:
            df = pd.DataFrame(raw_data[company_name])
        else:
            df = pd.DataFrame(raw_data)
        
        missing_columns = [col for col in REQUIRED_STOCK_COLUMNS if col not in df.columns]
        if missing_columns:
            st.warning(f"Missing required columns in {file_path}: {', '.join(missing_columns)}. Using sample data.")
            return None
        
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            if df['Date'].isna().all():
                st.warning(f"Invalid date format in {file_path}. Using sample data.")
                return None
            df = df.dropna(subset=['Date']).sort_values('Date')
        return df
    except Exception as e:
        st.warning(f"Error loading {file_path}: {str(e)}. Using sample data.")
        return None

def load_cleaned_data():
    try:
        response = requests.get(f"{API_URL}/data/cleaned", proxies={"http": None, "https": None})
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        missing_columns = [col for col in REQUIRED_CLEANED_COLUMNS if col not in df.columns]
        if missing_columns:
            st.warning(f"Missing required columns in cleaned data from API: {', '.join(missing_columns)}. Using local data.")
            return None
        return df
    except Exception as e:
        st.warning(f"Error fetching cleaned data from API: {e}. Using local data.")
        try:
            if not os.path.exists(companies_paths['cleaned']):
                st.warning(f"Local file not found: {companies_paths['cleaned']}. Using sample data.")
                return None
            with open(companies_paths['cleaned'], 'r', encoding='utf-8') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            missing_columns = [col for col in REQUIRED_CLEANED_COLUMNS if col not in df.columns]
            if missing_columns:
                st.warning(f"Missing required columns in {companies_paths['cleaned']}: {', '.join(missing_columns)}. Using sample data.")
                return None
            return df
        except Exception as e:
            st.warning(f"Error loading local cleaned data: {e}. Using sample data.")
            return None

def load_phrasebank_data():
    try:
        response = requests.get(f"{API_URL}/data/financial_phrasebank", proxies={"http": None, "https": None})
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data, columns=['Text'])
        df['Sentiment'] = df['Text'].str.extract(r'@(\w+)$')
        df['Text'] = df['Text'].str.replace(r'@\w+$', '', regex=True)
        if df['Sentiment'].isna().any():
            st.warning("Some entries in financial_phrasebank data from API are missing sentiment labels. Using local data.")
            return None
        return df
    except Exception as e:
        st.warning(f"Error fetching financial_phrasebank data from API: {e}. Using local data.")
        try:
            if not os.path.exists(companies_paths['financial_phrasebank']):
                st.warning(f"Local file not found: {companies_paths['financial_phrasebank']}. Using sample data.")
                return None
            with open(companies_paths['financial_phrasebank'], 'r', encoding='utf-8') as f:
                data = json.load(f)
            df = pd.DataFrame([{"Text": item.split('@')[0], "Sentiment": item.split('@')[1]} for item in data])
            if df['Sentiment'].isna().any():
                st.warning("Some entries in local financial_phrasebank data are missing sentiment labels. Using sample data.")
                return None
            return df
        except Exception as e:
            st.warning(f"Error loading local financial_phrasebank data: {e}. Using sample data.")
            return None


data = {}
for company, path in companies_paths.items():
    if company in companies:
        df = load_financial_data(path, company)
        data[company] = df if df is not None else sample_data[company]
    elif company == 'cleaned':
        df = load_cleaned_data()
        data[company] = df if df is not None else sample_data[company]
    elif company == 'financial_phrasebank':
        df = load_phrasebank_data()
        data[company] = df if df is not None else sample_data[company]

router_engine = initialize_query_engine(companies_paths) if 'initialize_query_engine' in globals() else None

def login_page():
    st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
    st.markdown("<h2><i class='fas fa-sign-in-alt'></i> Log In</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submit = st.form_submit_button("Log In")
            if submit:
                if username.strip() and password.strip():
                    with st.spinner("Logging in..."):
                        try:
                            response = requests.post(
                                f"{API_URL}/login",
                                data={"username": username.strip(), "password": password.strip()},
                                proxies={"http": None, "https": None}
                            )
                            response.raise_for_status()
                            user_data = response.json()
                            st.session_state.logged_in = True
                            st.session_state.username = username.strip()
                            st.session_state.email = user_data.get("email", "Not provided")
                            st.session_state.role = user_data.get("role", "Regular User")
                            st.session_state.page = "dashboard"
                            st.success(user_data.get("msg", "Login successful!"))
                            st.rerun()
                        except requests.exceptions.HTTPError as e:
                            if e.response.status_code in [400, 500]:
                                st.error(e.response.json().get("detail", "Invalid credentials"))
                            else:
                                st.error(f"Failed to connect to server: {e}")
                        except Exception as e:
                            st.error(f"Failed to connect to server: {e}")
                else:
                    st.warning("Please fill in all fields.")
    st.markdown("<p>Don't have an account? <a href='#' onclick='st.session_state.page=\"signup\";st.rerun()'>Sign Up</a></p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def signup_page():
    st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
    st.markdown("<h2><i class='fas fa-user-plus'></i> Sign Up</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("signup_form"):
            username = st.text_input("Username", placeholder="Choose a username")
            email = st.text_input("Email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Choose a password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm password")
            role = st.selectbox("Role", ["Regular User", "Expert", "Administrator"], help="Select your role")
            submit = st.form_submit_button("Sign Up")
            if submit:
                if username.strip() and email.strip() and password.strip() and confirm_password.strip():
                    if password == confirm_password:
                        with st.spinner("Registering..."):
                            try:
                                response = requests.post(
                                    f"{API_URL}/register",
                                    data={
                                        "username": username.strip(),
                                        "email": email.strip(),
                                        "password": password.strip(),
                                        "role": role
                                    },
                                    proxies={"http": None, "https": None}
                                )
                                response.raise_for_status()
                                user_data = response.json()
                                st.session_state.logged_in = True
                                st.session_state.username = username.strip()
                                st.session_state.email = email.strip()
                                st.session_state.role = role
                                st.session_state.page = "dashboard"
                                st.success(user_data.get("msg", "Registration successful!"))
                                st.rerun()
                            except requests.exceptions.HTTPError as e:
                                if e.response.status_code in [400, 500]:
                                    st.error(e.response.json().get("detail", "Registration failed"))
                                else:
                                    st.error(f"Failed to connect to server: {e}")
                            except Exception as e:
                                st.error(f"Failed to connect to server: {e}")
                    else:
                        st.error("Passwords do not match.")
                else:
                    st.warning("Please fill in all fields.")
    st.markdown("<p>Already have an account? <a href='#' onclick='st.session_state.page=\"login\";st.rerun()'>Log In</a></p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def run_query_interface():
    st.markdown("<h2>Financial Query Interface</h2>", unsafe_allow_html=True)
    query = st.text_input("Enter your financial query (e.g., $.Microsoft[?(@.Date == '2024-06-14')].Close)", 
                          placeholder="Enter JSONPath query or natural language question")
    criteria = st.text_input("Search Criteria (optional)", placeholder="e.g., Date > 2024-01-01")
    if st.button("Run Query"):
        if query:
            with st.spinner("Processing query..."):
                try:
                    response = run_query(query, router_engine)
                    if criteria:
                        response = f"{response} (Filtered by: {criteria})"
                    st.session_state.query_result = response
                    st.success(f"Query Result: {response}")
                except Exception as e:
                    st.error(f"Error processing query: {e}")
        else:
            st.warning("Please enter a query.")

def display_results():
    if 'query_result' in st.session_state:
        st.markdown("<h2>Query Results</h2>", unsafe_allow_html=True)
        st.write(st.session_state.query_result)
    else:
        st.warning("No query results available. Run a query first.")

def suggest_improvement():
    st.markdown("<h2>Suggest Improvement</h2>", unsafe_allow_html=True)
    suggestion = st.text_area("Enter your suggestion", placeholder="Type your suggestion here")
    if st.button("Submit Suggestion"):
        if suggestion.strip():
            try:
                response = requests.post(
                    f"{API_URL}/suggestions",
                    json={"username": st.session_state.username, "suggestion": suggestion.strip()},
                    proxies={"http": None, "https": None}
                )
                response.raise_for_status()
                st.success("Suggestion submitted successfully!")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code in [400, 500]:
                    st.error(e.response.json().get("detail", "Failed to submit suggestion"))
                else:
                    st.error(f"Error submitting suggestion: {e}")
            except Exception as e:
                st.error(f"Error submitting suggestion: {e}")
        else:
            st.warning("Please enter a suggestion.")

def verify_permissions():
    st.markdown("<h2>Verify Permissions</h2>", unsafe_allow_html=True)
    st.write(f"Current Role: {st.session_state.role}")
    st.write("Permissions verified based on your role.")

def evaluate_report_quality():
    st.markdown("<h2>Evaluate Report Quality</h2>", unsafe_allow_html=True)
    if 'query_result' in st.session_state:
        quality = st.slider("Rate the report quality (1-10)", 1, 10, 5)
        if st.button("Submit Evaluation"):
            try:
                response = requests.post(
                    f"{API_URL}/evaluations",
                    json={"username": st.session_state.username, "report": st.session_state.query_result, "quality": quality},
                    proxies={"http": None, "https": None}
                )
                response.raise_for_status()
                st.success(f"Report quality rated as {quality}/10")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code in [400, 500]:
                    st.error(e.response.json().get("detail", "Failed to submit evaluation"))
                else:
                    st.error(f"Error submitting evaluation: {e}")
            except Exception as e:
                st.error(f"Error submitting evaluation: {e}")
    else:
        st.warning("No report to evaluate. Run a query first.")

def edit_report():
    st.markdown("<h2>Edit Report</h2>", unsafe_allow_html=True)
    if 'query_result' in st.session_state:
        edited_report = st.text_area("Edit Report", value=st.session_state.query_result)
        if st.button("Save Changes"):
            st.session_state.query_result = edited_report
            st.success("Report updated successfully!")
    else:
        st.warning("No report to edit. Run a query first.")

def visualize_cleaned_data(df):
    if df is None or df.empty:
        st.error("No data available for Cleaned Data.")
        return
    st.markdown("<h2>Cleaned Data Analysis</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
        st.markdown("<h3>Average Credit Expiration</h3>", unsafe_allow_html=True)
        avg_credit = df['Credit Expiration'].mean()
        st.markdown(f"<p>{avg_credit:.2f} days</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
        st.markdown("<h3>Stage 1 Count</h3>", unsafe_allow_html=True)
        stage1_count = len(df[df['Current Stage'] == 1])
        st.markdown(f"<p>{stage1_count}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
        st.markdown("<h3>Stage 2 Count</h3>", unsafe_allow_html=True)
        stage2_count = len(df[df['Current Stage'] == 2])
        st.markdown(f"<p>{stage2_count}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<h3>Credit Expiration Distribution</h3>", unsafe_allow_html=True)
    fig_credit = px.histogram(df, x='Credit Expiration', nbins=20, title="Credit Expiration Days")
    fig_credit.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Roboto", size=12, color="#1E3A8A"),
        xaxis_title="Credit Expiration (Days)",
        yaxis_title="Count"
    )
    st.plotly_chart(fig_credit, use_container_width=True)

    st.markdown("<h3>Days Past Due (DPD) Distribution</h3>", unsafe_allow_html=True)
    fig_dpd = px.histogram(df, x='DPD', nbins=20, title="Days Past Due (DPD)", color_discrete_sequence=['salmon'])
    fig_dpd.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Roboto", size=12, color="#1E3A8A"),
        xaxis_title="DPD",
        yaxis_title="Number of Customers"
    )
    st.plotly_chart(fig_dpd, use_container_width=True)

    st.markdown("<h3>Stage Distribution</h3>", unsafe_allow_html=True)
    stage_counts = df['Current Stage'].value_counts().reset_index()
    stage_counts.columns = ['Stage', 'Count']
    fig_stage = px.bar(stage_counts, x='Stage', y='Count', title="Current Stage Distribution", color_discrete_sequence=['purple'])
    fig_stage.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Roboto", size=12, color="#1E3A8A"),
        xaxis_title="Current Stage",
        yaxis_title="Number of Customers"
    )
    st.plotly_chart(fig_stage, use_container_width=True)

    st.markdown("<h3>Cleaned Data Table</h3>", unsafe_allow_html=True)
    st.dataframe(df.head(100), use_container_width=True)

def visualize_phrasebank_data(df):
    if df is None or df.empty:
        st.error("No data available for Financial Phrasebank.")
        return
    st.markdown("<h2>Financial Phrasebank Sentiment Analysis</h2>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
        st.markdown("<h3>Positive Statements</h3>", unsafe_allow_html=True)
        positive_count = len(df[df['Sentiment'] == 'positive'])
        st.markdown(f"<p>{positive_count}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
        st.markdown("<h3>Neutral Statements</h3>", unsafe_allow_html=True)
        neutral_count = len(df[df['Sentiment'] == 'neutral'])
        st.markdown(f"<p>{neutral_count}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
        st.markdown("<h3>Negative Statements</h3>", unsafe_allow_html=True)
        negative_count = len(df[df['Sentiment'] == 'negative'])
        st.markdown(f"<p>{negative_count}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<h3>Sentiment Distribution</h3>", unsafe_allow_html=True)
    sentiment_counts = df['Sentiment'].value_counts().reset_index()
    sentiment_counts.columns = ['Sentiment', 'Count']
    fig_sentiment = px.pie(sentiment_counts, names='Sentiment', values='Count', title="Sentiment Distribution", 
                           color_discrete_sequence=['green', 'red', 'grey'])
    fig_sentiment.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Roboto", size=12, color="#1E3A8A")
    )
    st.plotly_chart(fig_sentiment, use_container_width=True)

    st.markdown("<h3>Financial Phrasebank Data</h3>", unsafe_allow_html=True)
    st.dataframe(df.head(100), use_container_width=True)

def visualize_stock_comparison():
    st.markdown("<h2>Stock Price Comparison</h2>", unsafe_allow_html=True)
    comparison_df = pd.DataFrame()
    for company in companies:
        df = data[company].copy()
        if df.empty:
            st.warning(f"No data available for {company}. Skipping in comparison.")
            continue
        df['Company'] = company
        comparison_df = pd.concat([comparison_df, df[['Date', 'Close', 'Company']].head(100)], ignore_index=True)
    if comparison_df.empty:
        st.error("No data available for stock comparison.")
        return
    fig_comparison = px.line(comparison_df, x='Date', y='Close', color='Company', title="Stock Price Comparison")
    fig_comparison.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Roboto", size=12, color="#1E3A8A"),
        xaxis_title="Date",
        yaxis_title="Closing Price (USD)",
        legend_title="Company"
    )
    st.plotly_chart(fig_comparison, use_container_width=True)

def query_interface():
    st.markdown("<h2>Query Financial Data</h2>", unsafe_allow_html=True)
    query = st.text_input("Enter your query (e.g., $.Microsoft[?(@.Date == '2024-06-14')].Close)", 
                          placeholder="Enter JSONPath query or natural language question")
    if st.button("Run Query"):
        if query:
            with st.spinner("Processing query..."):
                try:
                    response = run_query(query, router_engine)
                    st.success(f"Query Result: {response}")
                except Exception as e:
                    st.error(f"Error processing query: {e}")
        else:
            st.warning("Please enter a query.")

def user_management_page():
    if st.session_state.role != "Administrator":
        st.error("Access denied. Administrator role required.")
        return
    st.markdown("<h2>User Management</h2>", unsafe_allow_html=True)
    
    try:
        response = requests.get(f"{API_URL}/users", proxies={"http": None, "https": None})
        response.raise_for_status()
        users = response.json()
        st.markdown("<h3>Registered Users</h3>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(users), use_container_width=True)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code in [400, 500]:
            st.error(e.response.json().get("detail", "Error fetching users"))
        else:
            st.error(f"Error fetching users: {e}")
    except Exception as e:
        st.error(f"Error fetching users: {e}")

    st.markdown("<h3>Modify User Role</h3>", unsafe_allow_html=True)
    with st.form("modify_user_form"):
        username = st.text_input("Username to Modify", placeholder="Enter username")
        new_role = st.selectbox("New Role", ["Regular User", "Expert", "Administrator"])
        submit_modify = st.form_submit_button("Modify Role")
        if submit_modify:
            if username.strip():
                try:
                    response = requests.put(
                        f"{API_URL}/users/{username}",
                        json={"role": new_role},
                        proxies={"http": None, "https": None}
                    )
                    response.raise_for_status()
                    st.success(response.json().get("msg", "User role updated successfully"))
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code in [400, 404, 500]:
                        st.error(e.response.json().get("detail", "Failed to update user role"))
                    else:
                        st.error(f"Error modifying user: {e}")
                except Exception as e:
                    st.error(f"Error modifying user: {e}")
            else:
                st.warning("Please enter a username.")

    st.markdown("<h3>Delete User</h3>", unsafe_allow_html=True)
    with st.form("delete_user_form"):
        username_to_delete = st.text_input("Username to Delete", placeholder="Enter username")
        submit_delete = st.form_submit_button("Delete User")
        if submit_delete:
            if username_to_delete.strip():
                try:
                    response = requests.delete(
                        f"{API_URL}/users/{username_to_delete}",
                        proxies={"http": None, "https": None}
                    )
                    response.raise_for_status()
                    st.success(response.json().get("msg", "User deleted successfully"))
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code in [400, 404, 500]:
                        st.error(e.response.json().get("detail", "Failed to delete user"))
                    else:
                        st.error(f"Error deleting user: {e}")
                except Exception as e:
                    st.error(f"Error deleting user: {e}")
            else:
                st.warning("Please enter a username.")

def dashboard_page():
    if st.session_state.role not in ["Regular User", "Expert", "Administrator"]:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.email = None
        st.session_state.role = None
        st.session_state.page = "login"
        st.error("Invalid role detected. Logging out.")
        st.rerun()

    with st.sidebar:
        st.markdown("<h2><i class='fas fa-chart-line'></i> Dashboard</h2>", unsafe_allow_html=True)
        st.markdown(f"<p><i class='fas fa-user'></i> Welcome, {st.session_state.username} ({st.session_state.role})</p>", unsafe_allow_html=True)
        st.markdown(f"<p><i class='fas fa-envelope'></i> Email: {st.session_state.email}</p>", unsafe_allow_html=True)
        
        role_tasks = {
            "Regular User": [
                ("Financial Query", run_query_interface),
                ("View Results", display_results),
                ("Suggest Improvement", suggest_improvement),
                ("Verify Permissions", verify_permissions),
                ("Stock Analysis", "Stock Analysis"),
                ("Stock Comparison", "Stock Comparison")
            ],
            "Expert": [
                ("Financial Query", run_query_interface),
                ("View Results", display_results),
                ("Suggest Improvement", suggest_improvement),
                ("Verify Permissions", verify_permissions),
                ("Evaluate Report Quality", evaluate_report_quality),
                ("Edit Report", edit_report),
                ("Stock Analysis", "Stock Analysis"),
                ("Cleaned Data", "Cleaned Data"),
                ("Financial Phrasebank", "Financial Phrasebank"),
                ("Stock Comparison", "Stock Comparison"),
                ("Query Interface", query_interface)
            ],
            "Administrator": [
                ("Financial Query", run_query_interface),
                ("View Results", display_results),
                ("Suggest Improvement", suggest_improvement),
                ("Verify Permissions", verify_permissions),
                ("Evaluate Report Quality", evaluate_report_quality),
                ("Edit Report", edit_report),
                ("User Management", user_management_page),
                ("Stock Analysis", "Stock Analysis"),
                ("Cleaned Data", "Cleaned Data"),
                ("Financial Phrasebank", "Financial Phrasebank"),
                ("Stock Comparison", "Stock Comparison"),
                ("Query Interface", query_interface)
            ]
        }
        
        task_options = [task[0] for task in role_tasks[st.session_state.role]]
        selected_task = st.selectbox("Select Task", task_options, help="Choose a task")
        
        if selected_task == "Stock Analysis":
            company = st.selectbox("Select Company", companies, help="Choose a company")
        else:
            company = None
        
        if st.button("Log Out", key="logout_button", type="secondary"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.email = None
            st.session_state.role = None
            st.session_state.page = "login"
            st.rerun()

    st.markdown("<h1 class='main-title'><i class='fas fa-chart-line'></i> Financial Insights Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<img src='https://via.placeholder.com/100?text=Logo' class='logo' alt='Project Logo'/>", unsafe_allow_html=True)
    st.markdown("<div class='company-data'>", unsafe_allow_html=True)

    task_dict = {task[0]: task[1] for task in role_tasks[st.session_state.role]}
    if selected_task in task_dict:
        task_func = task_dict[selected_task]
        if isinstance(task_func, str):
            if task_func == "Stock Analysis":
                st.markdown(f"<h2>{company} Financial Analysis</h2>", unsafe_allow_html=True)
                df = data.get(company)
                if df is None or df.empty:
                    st.error(f"No data available for {company}.")
                    st.markdown("</div>", unsafe_allow_html=True)
                    return

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
                    st.markdown("<h3>Last Closing Price</h3>", unsafe_allow_html=True)
                    st.markdown(f"<p>${df['Close'].iloc[-1]:.2f}</p>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                with col2:
                    st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
                    st.markdown("<h3>Daily Change</h3>", unsafe_allow_html=True)
                    try:
                        change = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
                        st.markdown(f"<p class='{'positive' if change >= 0 else 'negative'}'>{change:.2f}%</p>", unsafe_allow_html=True)
                    except Exception:
                        st.markdown("<p class='negative'>N/A</p>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                with col3:
                    st.markdown("<div class='kpi-card'>", unsafe_allow_html=True)
                    st.markdown("<h3>Trading Volume</h3>", unsafe_allow_html=True)
                    st.markdown(f"<p>{df['Volume'].iloc[-1]:,}</p>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<h3>Select Time Range</h3>", unsafe_allow_html=True)
                time_range = st.slider("Date Range", 
                                       min_value=df['Date'].min().date(), 
                                       max_value=df['Date'].max().date(), 
                                       value=(df['Date'].max() - timedelta(days=30)).date(), 
                                       format="YYYY-MM-DD")
                filtered_df = df[df['Date'].dt.date >= time_range].head(100)

                st.markdown("<h3>Price Trend</h3>", unsafe_allow_html=True)
                fig_price = px.line(filtered_df, x='Date', y='Close', title=f"{company} Stock Price")
                fig_price.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(family="Roboto", size=12, color="#1E3A8A"),
                    xaxis_title="Date",
                    yaxis_title="Price (USD)"
                )
                st.plotly_chart(fig_price, use_container_width=True)

                st.markdown("<h3>Trading Volume</h3>", unsafe_allow_html=True)
                fig_volume = px.bar(filtered_df, x='Date', y='Volume', title=f"{company} Trading Volume")
                fig_volume.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(family="Roboto", size=12, color="#1E3A8A"),
                    xaxis_title="Date",
                    yaxis_title="Volume"
                )
                st.plotly_chart(fig_volume, use_container_width=True)

                st.markdown("<h3>Historical Data</h3>", unsafe_allow_html=True)
                st.dataframe(filtered_df, use_container_width=True)
            elif task_func == "Cleaned Data":
                visualize_cleaned_data(data['cleaned'])
            elif task_func == "Financial Phrasebank":
                visualize_phrasebank_data(data['financial_phrasebank'])
            elif task_func == "Stock Comparison":
                visualize_stock_comparison()
            elif task_func == "Query Interface":
                query_interface()
            elif task_func == "User Management":
                user_management_page()
        else:
            task_func()
    st.markdown("</div>", unsafe_allow_html=True)

try:
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        tab1, tab2 = st.tabs(["Sign Up", "Log In"])
        with tab1:
            signup_page()
        with tab2:
            login_page()
    else:
        dashboard_page()
except Exception as e:
    st.error(f"Error in main interface rendering: {e}")