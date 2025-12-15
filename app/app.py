import streamlit as st
import requests
import pandas as pd
import time

# ================= CONFIG =================
FASTAPI_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Agentic Data Prep",
    page_icon="🤖",
    layout="wide"
)

# ================= CUSTOM CSS =================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #020617, #0f172a);
    color: white;
}
[data-testid="stSidebar"] {
    background: #020617;
}
h1, h2, h3 {
    color: #22d3ee;
}
.stButton>button {
    background: linear-gradient(90deg, #22d3ee, #3b82f6);
    color: black;
    font-weight: bold;
    border-radius: 10px;
    padding: 0.6rem 1.3rem;
    transition: 0.3s;
}
.stButton>button:hover {
    transform: scale(1.05);
}
.card {
    background: #020617;
    padding: 16px;
    border-radius: 14px;
    border: 1px solid #1e293b;
    margin-bottom: 12px;
}
.badge-ai {
    background: #16a34a;
    padding: 6px 14px;
    border-radius: 20px;
    font-weight: bold;
}
.badge-fallback {
    background: #facc15;
    padding: 6px 14px;
    border-radius: 20px;
    font-weight: bold;
    color: black;
}
</style>
""", unsafe_allow_html=True)

# ================= HERO =================
st.markdown("""
<h1 style="text-align:center;">🤖 Agentic Data Prep</h1>
<p style="text-align:center; font-size:17px; opacity:0.85;">
An Automated AI-Powered Data Cleaning and Preprocessing System
</p>
""", unsafe_allow_html=True)

# ================= SIDEBAR =================
st.sidebar.header("📌 Choose Input Method")

data_source = st.sidebar.radio(
    "Select data source",
    ["📁 Upload CSV / Excel", "🗄️ Database Query", "🌐 External API"]
)

# ---------- Sidebar Explanation ----------
st.sidebar.markdown("---")
st.sidebar.subheader("ℹ️ What does this do?")

if data_source == "📁 Upload CSV / Excel":
    st.sidebar.markdown("""
    **Upload CSV / Excel**

    Upload datasets directly from your system.

    **Agent Workflow:**
    - Detects missing values & duplicates  
    - Fixes data types and normalizes values  
    - Enhances cleaning using AI when available  
    - Falls back to traditional methods if AI fails  

    📥 Output: Cleaned, model-ready dataset
    """)

elif data_source == "🗄️ Database Query":
    st.sidebar.markdown("""
    **Database Query**

    Fetch raw data directly from PostgreSQL or MySQL databases.

    **Agent Workflow:**
    - Executes the provided SQL query  
    - Cleans the fetched data automatically  
    - Applies AI enhancement when available  
    - Guarantees output via fallback system  

    📥 Output: Cleaned query results
    """)

elif data_source == "🌐 External API":
    st.sidebar.markdown("""
    **External API**

    Fetch raw JSON data from REST APIs.

    **Agent Workflow:**
    - Converts JSON to structured tabular data  
    - Handles inconsistencies and missing fields  
    - Uses AI for intelligent formatting  
    - Ensures valid output even without AI  

    📥 Output: Cleaned structured dataset
    """)

# ================= HELPER =================
def show_agent_status(ai_enhanced, message):
    if ai_enhanced:
        st.markdown(f"""
        <div class="card">
            <span class="badge-ai">🤖 AI AGENT ENHANCED</span>
            <p>{message}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="card">
            <span class="badge-fallback">⚠️ FALLBACK MODE</span>
            <p>{message}</p>
        </div>
        """, unsafe_allow_html=True)

# ================= CSV / EXCEL =================
if data_source == "📁 Upload CSV / Excel":
    st.subheader("📁 Upload Dataset")

    uploaded_file = st.file_uploader(
        "Supported formats: CSV, Excel",
        type=["csv", "xlsx", "xls"]
    )

    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)

        st.subheader("🔍 Raw Data Preview")
        st.dataframe(df.head(10), use_container_width=True)

        col1, col2, col3 = st.columns(3)
        col1.metric("Rows", df.shape[0])
        col2.metric("Columns", df.shape[1])
        col3.metric("Missing Values", df.isnull().sum().sum())

        if st.button("🚀 Run Agentic Data Cleaning"):
            progress = st.progress(0)
            for i in range(70):
                time.sleep(0.01)
                progress.progress(i + 1)

            response = requests.post(
                f"{FASTAPI_URL}/cleandata/",
                files={"file": (uploaded_file.name, uploaded_file.getvalue())}
            )

            if response.status_code == 200:
                result = response.json()
                cleaned_df = pd.DataFrame(result.get("cleaned_data", []))

                show_agent_status(
                    result.get("ai_enhanced", False),
                    result.get("message", "")
                )

                tab1, tab2 = st.tabs(["📊 Cleaned Data", "📈 Statistical Summary"])
                with tab1:
                    st.dataframe(cleaned_df, use_container_width=True)
                with tab2:
                    st.write(cleaned_df.describe())

                st.download_button(
                    "📥 Download Cleaned Dataset",
                    cleaned_df.to_csv(index=False),
                    "cleaned_data.csv",
                    "text/csv"
                )
            else:
                st.error("❌ Backend not reachable. Ensure FastAPI is running.")

# ================= DATABASE =================
elif data_source == "🗄️ Database Query":
    st.subheader("🗄️ Database Ingestion")

    db_url = st.text_input(
        "Database Connection URL",
        "postgresql://user:password@localhost:5432/db"
    )
    query = st.text_area("SQL Query", "SELECT * FROM my_table;")

    if st.button("🚀 Fetch & Run Agent"):
        with st.spinner("Invoking Agentic Data Prep pipeline..."):
            response = requests.post(
                f"{FASTAPI_URL}/clean-db/",
                json={"db_url": db_url, "query": query}
            )

        if response.status_code == 200:
            result = response.json()
            cleaned_df = pd.DataFrame(result.get("cleaned_data", []))

            show_agent_status(result.get("ai_enhanced", False), result.get("message", ""))
            st.dataframe(cleaned_df, use_container_width=True)

            st.download_button(
                "📥 Download Cleaned Dataset",
                cleaned_df.to_csv(index=False),
                "cleaned_data.csv",
                "text/csv"
            )
        else:
            st.error("❌ Database cleaning failed")

# ================= API =================
elif data_source == "🌐 External API":
    st.subheader("🌐 API Data Fetching")

    api_url = st.text_input(
        "API Endpoint",
        "https://jsonplaceholder.typicode.com/posts"
    )

    if st.button("🚀 Fetch & Run Agent"):
        with st.spinner("Agent analyzing API data..."):
            response = requests.post(
                f"{FASTAPI_URL}/clean-api/",
                json={"api_url": api_url}
            )

        if response.status_code == 200:
            result = response.json()
            cleaned_df = pd.DataFrame(result.get("cleaned_data", []))

            show_agent_status(result.get("ai_enhanced", False), result.get("message", ""))
            st.dataframe(cleaned_df, use_container_width=True)

            st.download_button(
                "📥 Download Cleaned Dataset",
                cleaned_df.to_csv(index=False),
                "cleaned_data.csv",
                "text/csv"
            )
        else:
            st.error("❌ API cleaning failed")

# ================= FOOTER =================
st.markdown("""
<hr>
<p style="text-align:center; opacity:0.7;">
<b>Agentic Data Prep</b> — An Automated AI-Powered Data Cleaning and Preprocessing System<br>
Built using Streamlit · FastAPI · Groq AI · LangGraph
</p>
""", unsafe_allow_html=True)

