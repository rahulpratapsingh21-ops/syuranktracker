import streamlit as st
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Select Your university Rank Tracker", layout="wide")

# Sidebar
st.sidebar.title("️SYU Rank Tracker")
st.sidebar.markdown("Check your website's ranking in Google (Top 100) using **Serper.dev API**.")

# API Key input
api_key = st.sidebar.text_input("🔑 Enter your Serper.dev API Key", type="password")
st.sidebar.markdown("[Get your API key at Serper.dev](https://serper.dev)")

# Main Title
st.title("SYU Rank Tracker")

# Input form
with st.form("serp_form"):
    keywords = st.text_area("📝 Enter up to 1000 keywords (one per line)", placeholder="Enter keywords here...")
    country = st.selectbox("🌍 Select Country",
                           ["India", "United States", "United Kingdom", "Indonesia", "Australia", "Canada"], index=0)
    domain = st.text_input("🔗 Your Website Domain (Required, e.g., example.com)", placeholder="example.com")
    submitted = st.form_submit_button("🔎 Check Rankings")


# Function to check ranking
def check_domain_ranking(api_key, keyword, country, domain):
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "q": keyword,
        "gl": country.lower(),
        "num": 100
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            organic_results = data.get("organic", [])
            for i, item in enumerate(organic_results, 1):
                link = item.get("link", "")
                if domain in link:
                    return keyword, i, link
            return keyword, "Not in Top 100", None
        else:
            return keyword, "Error", None
    except:
        return keyword, "Error", None


# Run search
if submitted:
    if not api_key:
        st.error("⚠ Please enter your Serper.dev API key")
    elif not keywords.strip():
        st.error("⚠ Please enter at least one keyword")
    elif not domain.strip():
        st.error("⚠ Please enter your website domain")
    else:
        keyword_list = keywords.strip().split("\n")[:1000]  # limit 1000
        results = []

        st.subheader("🔎 Checking rankings... This may take a few seconds...")
        progress_bar = st.progress(0)
        total = len(keyword_list)

        # Parallel requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_kw = {executor.submit(check_domain_ranking, api_key, kw, country, domain): kw for kw in
                            keyword_list}
            for i, future in enumerate(as_completed(future_to_kw), 1):
                results.append(future.result())
                progress_bar.progress(i / total)

        # Convert to DataFrame
        df = pd.DataFrame(results, columns=["Keyword", "Ranking", "URL"])

        st.subheader("📊 Domain Ranking Results")
        st.dataframe(df, use_container_width=True)
