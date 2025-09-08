import streamlit as st
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

st.set_page_config(page_title="Select Your university Rank Tracker", layout="wide")

# Sidebar
st.sidebar.title("️SYU Rank Tracker")
api_key = st.sidebar.text_input("🔑 Enter your Serper.dev API Key", type="password")
st.sidebar.markdown("[Get your API key at Serper.dev](https://serper.dev)")

st.title("SYU Rank Tracker (Multi-Location)")

COUNTRY_MAP = {
    "India": {"gl": "in", "google_domain": "google.co.in", "hl": "en"},
    "United States": {"gl": "us", "google_domain": "google.com", "hl": "en"},
    "United Kingdom": {"gl": "uk", "google_domain": "google.co.uk", "hl": "en"},
    "Indonesia": {"gl": "id", "google_domain": "google.co.id", "hl": "id"},
    "Australia": {"gl": "au", "google_domain": "google.com.au", "hl": "en"},
    "Canada": {"gl": "ca", "google_domain": "google.ca", "hl": "en"},
}

with st.form("serp_form"):
    keywords = st.text_area("📝 Enter up to 500 keywords (one per line)", placeholder="Enter keywords...")
    country = st.selectbox("🌍 Select Country", list(COUNTRY_MAP.keys()), index=0)
    locations = st.text_area("📍 Enter Locations (one per line)",
                             placeholder="e.g.\nMumbai, India\nDelhi, India\nNew York, NY")
    domain = st.text_input("🔗 Your Website Domain", placeholder="example.com")
    submitted = st.form_submit_button("🔎 Check Rankings")


def normalize_netloc(link):
    parsed = urlparse(link)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc

def check_domain_ranking(api_key, keyword, gl, domain, google_domain=None, hl=None, location=None):
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": keyword, "gl": gl, "num": 100}
    if google_domain: payload["google_domain"] = google_domain
    if hl: payload["hl"] = hl
    if location: payload["location"] = location

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            return keyword, location, f"Error {response.status_code}", None
        data = response.json()
        organic_results = data.get("organic") or data.get("organic_results") or []
        for i, item in enumerate(organic_results, 1):
            link = item.get("link") or item.get("url") or ""
            if not link: continue
            if normalize_netloc(link).endswith(domain.lower()):
                return keyword, location or "N/A", i, link
        return keyword, location or "N/A", "Not in Top 100", None
    except Exception as e:
        return keyword, location or "N/A", f"Error: {e}", None


if submitted:
    if not api_key:
        st.error("⚠ Please enter your Serper.dev API key")
    elif not keywords.strip():
        st.error("⚠ Please enter at least one keyword")
    elif not domain.strip():
        st.error("⚠ Please enter your website domain")
    else:
        keyword_list = [k.strip() for k in keywords.strip().split("\n") if k.strip()][:500]
        location_list = [l.strip() for l in locations.strip().split("\n") if l.strip()] or [None]

        st.subheader("🔎 Checking rankings... (multi-location)")
        progress_bar = st.progress(0)
        total = len(keyword_list) * len(location_list)
        results = []

        mapping = COUNTRY_MAP.get(country, {})
        gl, google_domain, hl = mapping.get("gl"), mapping.get("google_domain"), mapping.get("hl")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(check_domain_ranking, api_key, kw, gl, domain, google_domain, hl, loc): (kw, loc)
                for kw in keyword_list for loc in location_list
            }
            completed = 0
            for future in as_completed(futures):
                completed += 1
                results.append(future.result())
                progress_bar.progress(completed / total)

        df = pd.DataFrame(results, columns=["Keyword", "Location", "Ranking", "URL"])
        st.subheader("📊 Domain Ranking Results (Multi-Location)")
        st.dataframe(df, use_container_width=True)
        st.download_button("⬇ Download CSV", data=df.to_csv(index=False), file_name="rankings.csv", mime="text/csv")
