import streamlit as st
import requests
import time
import os

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# Use session state for token
if 'token' not in st.session_state:
    st.session_state.token = None

st.set_page_config(page_title="Adam Alpha Pro", layout="wide")
st.title("Adam Alpha Pro v5")

# Sidebar login
with st.sidebar:
    user = st.text_input("Username", value=os.getenv("API_USER", ""))
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        resp = requests.post(f"{API_BASE}/login", json={"username": user, "password": pwd})
        if resp.ok:
            st.session_state.token = resp.json()["access_token"]
            st.success("Logged in")
            st.experimental_rerun()
        else:
            st.session_state.token = None
            st.error("Login failed")

if st.session_state.token:
    st.sidebar.success("Logged in successfully!")
    symbol = st.text_input("Symbol:")
    if st.button("Analyze") and symbol:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        job = requests.post(f"{API_BASE}/analyze", json={"symbol": symbol}, headers=headers).json().get("job_id")
        status = st.empty()
        while time.time() - start_time < max_wait_time:
            time.sleep(1)
            result_resp = requests.get(f"{API_BASE}/results/{job}", headers=headers)
            if not result_resp.ok:
                status.error(f"Error fetching results: {result_resp.status_code}")
                break
            result = result_resp.json()
            if result.get("status") == "PENDING":
            else:
                break
        st.metric("Final Verdict", result["brain"]["verdict"], delta=f"Score: {result['brain']['final_score']}")
        st.bar_chart(result["brain"]["category_breakdown"])
        for k, v in result.items():
            if k not in ("brain", "symbol", "status"):
                with st.expander(k):
                    st.json(v)
