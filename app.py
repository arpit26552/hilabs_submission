# frontend/app.py
import streamlit as st
import pandas as pd
import os
import sys
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime


# Make backend + chatbot folders importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from dedupe_providers import dedupe
    from dashboard import ProviderDataVerifier
    from chatapp import NL2SQLConverter
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

# ===============================
# PAGE CONFIGURATION
# ===============================
st.set_page_config(
    page_title="Provider Data Platform",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===============================
# CSS STYLING
# ===============================
st.markdown("""
<style>
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main header styling */
    .main-header {
        background: linear-gradient(90deg, #1f77b4 0%, #2196F3 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    /* Chat interface */
    .chat-container {
        background: #ffffff;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 2px 15px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
        border: 1px solid #e2e8f0;
        max-height: 600px;
        overflow-y: auto;
    }
    
    .user-message {
        background: #3b82f6;
        color: #ffffff;
        padding: 1rem 1.5rem;
        border-radius: 18px 18px 4px 18px;
        margin: 1rem 0 1rem 20%;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
        font-size: 14px;
        line-height: 1.5;
    }
    
    .bot-response {
        background: #f1f5f9;
        color: #1e293b;
        padding: 1rem 1.5rem;
        border-radius: 18px 18px 18px 4px;
        margin: 1rem 20% 1rem 0;
        border-left: 4px solid #10b981;
        font-size: 14px;
        line-height: 1.5;
    }
    
    .error-message {
        background: #fef2f2;
        color: #dc2626;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #ef4444;
        margin: 0.5rem 20% 0.5rem 0;
    }
    
    .success-message {
        background: #dcfce7;
        color: #166534;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #22c55e;
        margin: 0.5rem 20% 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# HELPER FUNCTIONS
# ===============================
def create_metric_card(title, value, delta=None):
    """Create a metric card component"""
    delta_html = f'<small style="color: #666;">+{delta}</small>' if delta else ""
    return f"""
    <div class="metric-card">
        <h4 style="margin: 0; color: #333; font-size: 14px;">{title}</h4>
        <h2 style="margin: 0.5rem 0 0 0; color: #1f77b4; font-size: 24px;">{value}</h2>
        {delta_html}
    </div>
    """

@st.cache_data
def load_dedup_data():
    """Load deduplication data with caching"""
    try:
        roster_file = "provider_roster_with_errors.csv"
        if not os.path.exists(roster_file):
            return None, None, f"File not found: {roster_file}"
        
        roster = pd.read_csv(roster_file, dtype=str).fillna("")
        pairs_df, roster_out, clusters = dedupe(roster)
        return roster_out, clusters, None
    except Exception as e:
        return None, None, str(e)

@st.cache_data
def load_validation_data():
    """Load validation data with caching"""
    try:
        roster_file = "provider_roster_with_errors.csv"
        ca_file = "ca_medical_license_database.csv"
        ny_file = "ny_medical_license_database.csv"
        
        for file in [roster_file, ca_file, ny_file]:
            if not os.path.exists(file):
                return None, f"File not found: {file}"
        
        verifier = ProviderDataVerifier(roster_file, ca_file, ny_file)
        verifier.load_data()
        verifier.verify_data()
        results = verifier.generate_reports()
        return results, None
    except Exception as e:
        return None, str(e)

def create_dashboard_charts():
    """Create dashboard visualization charts"""
    # Sample data for demonstration
    fig1 = go.Figure(data=[
        go.Bar(name='Valid', x=['NPIs', 'Names', 'Licenses', 'Phones'], y=[450, 480, 400, 420]),
        go.Bar(name='Invalid', x=['NPIs', 'Names', 'Licenses', 'Phones'], y=[50, 20, 100, 80])
    ])
    fig1.update_layout(
        title='Data Validation Summary',
        barmode='stack',
        height=400,
        template='plotly_white'
    )
    
    fig2 = px.bar(
        x=[120, 95, 88, 75, 65],
        y=['CA', 'NY', 'TX', 'FL', 'IL'],
        orientation='h',
        title='Top 5 States by Provider Count',
        color=[120, 95, 88, 75, 65],
        color_continuous_scale='Blues'
    )
    fig2.update_layout(height=400, template='plotly_white')
    
    return fig1, fig2

# ===============================
# MAIN HEADER
# ===============================
st.markdown("""
<div class="main-header">
    <h1 style="margin: 0; font-size: 2.5rem;">🏥 Provider Data Analytics Platform</h1>
    <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">
        Advanced data quality management and analytics for healthcare providers
    </p>
</div>
""", unsafe_allow_html=True)

# ===============================
# SIDEBAR NAVIGATION
# ===============================
with st.sidebar:
    st.markdown("### 🧭 Navigation")
    page = st.radio(
        "Select a section:",
        ["📊 Dashboard", "🔎 Deduplication", "✅ Validation", "💬 AI Assistant"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### 📈 Quick Stats")
    st.markdown(create_metric_card("Total Records", "524"), unsafe_allow_html=True)
    st.markdown(create_metric_card("Active Today", "12"), unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### ℹ️ System Info")
    st.info("Database: SQLite")
    st.info("Last Updated: Today")

# ===============================
# DASHBOARD PAGE
# ===============================
if "Dashboard" in page:
    st.markdown("## 📊 Executive Dashboard")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(create_metric_card("Total Providers", "524", "12"), unsafe_allow_html=True)
    with col2:
        st.markdown(create_metric_card("Active Licenses", "456", "8"), unsafe_allow_html=True)
    with col3:
        st.markdown(create_metric_card("Board Certified", "398", "5"), unsafe_allow_html=True)
    with col4:
        st.markdown(create_metric_card("Data Quality", "87%", "2%"), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    fig1, fig2 = create_dashboard_charts()
    
    with col1:
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        st.plotly_chart(fig2, use_container_width=True)
    
    # Recent activity
    st.markdown("### 📋 Recent Activity")
    activity_data = {
        'Time': ['10:30 AM', '10:15 AM', '09:45 AM', '09:30 AM'],
        'Action': ['Data Validation', 'New Provider Added', 'License Renewed', 'Duplicate Removed'],
        'Status': ['✅ Complete', '✅ Complete', '⚠️ Pending', '✅ Complete']
    }
    st.dataframe(pd.DataFrame(activity_data), use_container_width=True, hide_index=True)

# ===============================
# DEDUPLICATION PAGE
# ===============================
elif "Deduplication" in page:
    st.markdown("## 🔎 Provider Deduplication")
    
    if st.button("🔄 Run Deduplication Analysis", type="primary"):
        with st.spinner("Running deduplication analysis..."):
            roster_out, clusters, error = load_dedup_data()
            
            if error:
                st.error(f"Error: {error}")
            else:
                st.session_state['dedup_results'] = (roster_out, clusters)
                st.success("Deduplication completed successfully!")
    
    # Display results if available
    if 'dedup_results' in st.session_state:
        roster_out, clusters = st.session_state['dedup_results']
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(create_metric_card("Total Records", len(roster_out)), unsafe_allow_html=True)
        with col2:
            unique_clusters = len(roster_out["dedup_cluster_id"].unique())
            st.markdown(create_metric_card("Unique Clusters", unique_clusters), unsafe_allow_html=True)
        with col3:
            duplicate_clusters = sum(roster_out["dedup_cluster_id"].value_counts() > 1)
            st.markdown(create_metric_card("Duplicate Clusters", duplicate_clusters), unsafe_allow_html=True)
        with col4:
            dedup_rate = round((1 - duplicate_clusters / len(roster_out)) * 100, 1)
            st.markdown(create_metric_card("Clean Rate", f"{dedup_rate}%"), unsafe_allow_html=True)
        
        # Tabs for results
        tab1, tab2 = st.tabs(["📋 Deduplicated Data", "🔍 Duplicate Clusters"])
        
        with tab1:
            st.markdown("### Results")
            search_term = st.text_input("🔍 Search providers:")
            
            display_data = roster_out.copy()
            if search_term:
                display_data = display_data[
                    display_data['full_name'].str.contains(search_term, case=False, na=False)
                ]
            
            st.dataframe(display_data.head(100), use_container_width=True, hide_index=True)
            
            # Download
            csv = roster_out.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Results",
                data=csv,
                file_name=f"dedup_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with tab2:
            if clusters and len(clusters) > 0:
                cluster_options = [f"Cluster {i+1} ({len(cluster)} records)" for i, cluster in enumerate(clusters)]
                selected = st.selectbox("Select cluster:", cluster_options)
                
                if selected:
                    cluster_idx = int(selected.split()[1]) - 1
                    cluster_data = roster_out.loc[clusters[cluster_idx]]
                    st.dataframe(cluster_data, use_container_width=True, hide_index=True)
            else:
                st.success("✅ No duplicate clusters found!")

# ===============================
# VALIDATION PAGE
# ===============================
elif "Validation" in page:
    st.markdown("## ✅ Data Validation")
    
    if st.button("🔄 Run Validation", type="primary"):
        with st.spinner("Running validation checks..."):
            results, error = load_validation_data()
            
            if error:
                st.error(f"Error: {error}")
            else:
                st.session_state['validation_results'] = results
                st.success("Validation completed successfully!")
    
    # Display results if available
    if 'validation_results' in st.session_state:
        results = st.session_state['validation_results']
        
        # Summary
        col1, col2 = st.columns(2)
        with col1:
            fig1, _ = create_dashboard_charts()
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            mismatches_df = results.get("mismatches", pd.DataFrame())
            expired_df = results.get("expired", pd.DataFrame())
            
            st.markdown(create_metric_card("Total Issues", len(mismatches_df)), unsafe_allow_html=True)
            st.markdown(create_metric_card("Expired Licenses", len(expired_df)), unsafe_allow_html=True)
        
        # Detailed tabs
        tab1, tab2, tab3 = st.tabs(["❌ Issues", "⏰ Licenses", "🎓 Certifications"])
        
        with tab1:
            if not mismatches_df.empty:
                field_names = mismatches_df['field_name'].unique()
                for field in field_names:
                    with st.expander(f"📋 {field.replace('_', ' ').title()} Issues"):
                        field_data = mismatches_df[mismatches_df['field_name'] == field]
                        st.dataframe(field_data.head(50), use_container_width=True, hide_index=True)
            else:
                st.success("✅ No validation issues found!")
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### ⚠️ Expired")
                expired_df = results.get("expired", pd.DataFrame())
                if not expired_df.empty:
                    st.dataframe(expired_df.head(20), use_container_width=True, hide_index=True)
                else:
                    st.success("✅ No expired licenses")
            
            with col2:
                st.markdown("#### ✅ Active")
                active_df = results.get("active", pd.DataFrame())
                if not active_df.empty:
                    st.dataframe(active_df.head(20), use_container_width=True, hide_index=True)
                else:
                    st.info("ℹ️ No active license data")
        
        with tab3:
            board_df = results.get("board", pd.DataFrame())
            if not board_df.empty:
                st.dataframe(board_df.head(50), use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ No board certification data")

# ===============================
# AI ASSISTANT PAGE
# ===============================
elif "AI Assistant" in page:
    st.markdown("## 💬 AI Data Assistant")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_query" not in st.session_state:
        st.session_state.current_query = None
    
    # Control buttons
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.info("Ask questions about your provider database in natural language")
    with col2:
        if st.button("🗑️ Clear Chat", type="secondary"):
            st.session_state.messages = []
            st.session_state.current_query = None
            # Clear stored results
            for key in list(st.session_state.keys()):
                if key.startswith('query_result_'):
                    del st.session_state[key]
            st.success("Chat cleared!")
            st.rerun()
    with col3:
        if st.button("🔄 Reset", type="secondary"):
            st.session_state.messages = []
            st.session_state.current_query = None
            st.rerun()
    
    # Current query display
    if st.session_state.current_query:
        st.warning(f"🔍 Processing: {st.session_state.current_query}")
    
    # Sample questions
    st.markdown("### 💡 Sample Questions")
    col1, col2, col3 = st.columns(3)
    
    sample_questions = [
        ("📊 Total Count", "How many providers do we have?"),
        ("⚠️ Expired Licenses", "Show expired licenses"),
        ("🏥 Specialists", "Find cardiologists"),
        ("📍 By State", "Providers in California"),
        ("✅ Data Issues", "Show validation errors"),
        ("🎓 Certified", "Board certified doctors")
    ]
    
    for i, (title, question) in enumerate(sample_questions):
        col = [col1, col2, col3][i % 3]
        with col:
            if st.button(title, key=f"sample_{i}"):
                st.session_state.current_query = question
                st.rerun()
    
    # Chat display
    if st.session_state.messages:
        st.markdown("### 💬 Chat")
        
        chat_container = st.container()
        with chat_container:
            for i, message in enumerate(st.session_state.messages):
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="user-message">
                        <strong>You:</strong> {message["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                
                elif message["role"] == "assistant":
                    content = message["content"]
                    if "ERROR:" in content:
                        st.markdown(f"""
                        <div class="error-message">
                            <strong>Assistant:</strong> {content}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="bot-response">
                            <strong>Assistant:</strong> {content}
                        </div>
                        """, unsafe_allow_html=True)
                
                # Show expandable results
                if f'query_result_{i}' in st.session_state:
                    result_df = st.session_state[f'query_result_{i}']
                    with st.expander(f"📊 Results ({len(result_df)} records)"):
                        st.dataframe(result_df.head(50), use_container_width=True, hide_index=True)
                        
                        csv = result_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "📥 Download",
                            data=csv,
                            file_name=f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key=f"download_{i}"
                        )
    
    # Process queries
    if st.session_state.current_query:
        prompt = st.session_state.current_query
        st.session_state.current_query = None
        process_query = True
    else:
        prompt = st.chat_input("Ask about your provider data...")
        process_query = bool(prompt)
    
    if process_query and prompt:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Process query
        with st.spinner("Processing your question..."):
            try:
                # Check if database exists
                db_path = "roster.db"
                if not os.path.exists(db_path):
                    response = "ERROR: Database file 'roster.db' not found. Please ensure the database is properly set up."
                else:
                    converter = NL2SQLConverter(db_path)
                    result, sql_or_error = converter.execute_nl_query(prompt)
                    
                    if result is not None:
                        if isinstance(result, pd.DataFrame):
                            if len(result) > 0:
                                # Store result
                                result_key = f'query_result_{len(st.session_state.messages)}'
                                st.session_state[result_key] = result
                                response = f"Found {len(result)} records. SQL: {sql_or_error}"
                            else:
                                response = f"No records found. SQL: {sql_or_error}"
                        else:
                            response = f"Result: {result}. SQL: {sql_or_error}"
                    else:
                        response = f"ERROR: {sql_or_error}"
                    
                    converter.close()
            
            except Exception as e:
                response = f"ERROR: System error - {str(e)}"
        
        # Add response
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
    
    # Help section
    with st.expander("❓ Help"):
        st.markdown("""
        **Sample Questions:**
        - "How many providers do we have?"
        - "Show providers in California"
        - "Find expired licenses"
        - "List cardiologists"
        - "Count by state"
        
        **Tips:**
        - Use simple, clear questions
        - Refer to common fields like state, city, specialty
        - Try the sample questions first
        """)

# ===============================
# FOOTER
# ===============================
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #666; padding: 1rem;">
    Provider Data Analytics Platform | Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
</div>
""", unsafe_allow_html=True)