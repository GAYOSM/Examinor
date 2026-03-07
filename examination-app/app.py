import streamlit as st

st.set_page_config(
    page_title="Examination System",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📋 Examination System Home")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ## 🛡️ Admin Interface
    
    Manage your examination:
    - Upload questions from DOCX files
    - View student responses
    - Generate marks summaries
    - Export results
    
    [→ Go to Admin Interface](Admin_Interface)
    """)

with col2:
    st.markdown("""
    ## 🎓 Student Interface
    
    Take your examination:
    - Register with your details
    - Answer questions
    - Submit your responses
    
    [→ Go to Student Interface](Student_Interface)
    """)

st.markdown("---")
st.info("👆 Select a page above to get started!")
