import streamlit as st
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import time
from random import randint


# Function to get user's country based on IP
def get_user_country():
    try:
        response = requests.get("https://ipinfo.io/json")
        data = response.json()
        return data.get("country", "")
    except Exception as e:
        print(f"Error in get_user_country: {e}")
        return None


# Normalize URLs for comparison
def normalize_netloc(link):
    parsed = urlparse(link)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


# Validate API key (optional, improves UX)
def validate_api_key(api_key):
    try:
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        payload = {"q": "test", "gl": "in", "hl": "en", "num": 1}
        r = requests.post("https://google.serper.dev/search", headers=headers, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Error in validate_api_key: {e}")
        return False


# Modify check_domain_ranking to handle 429 errors and log better results
def check_domain_ranking(api_key, keyword, gl, domain, google_domain=None, hl=None,
                         location="India", device="desktop", search_type="search", strict=False):
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    payload = {
        "q": keyword,
        "gl": gl,
        "hl": hl,
        "num": 100,
        "location": location,
        "device": device,
        "searchType": search_type
    }

    if google_domain:
        payload["google_domain"] = google_domain

    retries = 5  # Number of retry attempts
    delay = 5  # Starting delay in seconds

    for attempt in range(retries):
        try:
            print(f"Requesting for keyword: {keyword} (Attempt {attempt + 1})")
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            # Log the status code and the response content for debugging
            print(f"Attempt {attempt + 1} - Status Code: {response.status_code}")

            if response.status_code == 403:
                print(f"Invalid API key (403) for keyword: {keyword}")
                return keyword, location, "❌ Invalid API key (403)", None
            elif response.status_code == 429:  # Rate limit exceeded
                wait_time = delay * (2 ** attempt) + randint(0, 3)  # Exponential backoff
                print(f"Rate limit hit. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)  # Wait before retrying
                continue  # Retry the request
            elif response.status_code != 200:
                print(f"API Error {response.status_code} for keyword: {keyword}")
                return keyword, location, f"❌ API Error {response.status_code}", None

            # If the response is successful, proceed with parsing the results
            data = response.json()
            organic_results = data.get("organic") or data.get("organic_results") or []

            normalized_domain = domain.lower().replace("www.", "").strip()

            # Loop through results and check if the domain matches
            for i, item in enumerate(organic_results, 1):
                link = item.get("link") or item.get("url") or ""
                if not link:
                    continue

                netloc = normalize_netloc(link)
                if (strict and netloc == normalized_domain) or (not strict and normalized_domain in netloc):
                    print(f"Found {keyword} at position {i}: {link}")
                    return keyword, location, i, link

            print(f"{keyword} not found in top 100 results.")
            return keyword, location, "Not in Top 100", None

        except Exception as e:
            print(f"Error during request for keyword '{keyword}': {e}")
            return keyword, location, f"Error: {e}", None

    # After retries are exhausted, return an error message
    print(f"Max retries exceeded for keyword: {keyword}")
    return keyword, location, "❌ Rate limit exceeded. Please try again later.", None


# ------------------------ Streamlit App ------------------------

st.sidebar.title("️SYU Rank Tracker")
api_key = st.sidebar.text_input("🔑 Enter your Serper.dev API Key", type="password")
st.sidebar.markdown("[Get your API key at Serper.dev](https://serper.dev)")

st.title("SYU Rank Tracker (with Location + Device Options)")

# Hardcoded country info for India
COUNTRY_MAP = {
    "India": {"gl": "in", "google_domain": "google.co.in", "hl": "en"},
}

user_country = get_user_country()
if user_country != "IN":
    st.warning("⚠ Your IP location is not detected as India. Defaulting to India for ranking results.")

with st.form("serp_form"):
    keywords = st.text_area("📝 Enter up to 500 keywords (one per line)", placeholder="Enter keywords...")
    domain = st.text_input("🔗 Your Website Domain", placeholder="example.com")

    st.markdown("### 🧩 Optional Settings")
    device = st.selectbox("💻 Device Type", ["desktop", "mobile"])
    search_type = st.selectbox("🔎 Search Type", ["search", "news", "images", "videos"])
    strict_match = st.checkbox("🎯 Use strict domain matching", value=False)

    submitted = st.form_submit_button("🔎 Check Rankings")

# Run Ranking Check
if submitted:
    if not api_key:
        st.error("⚠ Please enter your Serper.dev API key")
    elif not validate_api_key(api_key):
        st.error("❌ Invalid or unauthorized Serper.dev API key (403). Please check your key.")
    elif not keywords.strip():
        st.error("⚠ Please enter at least one keyword")
    elif not domain.strip():
        st.error("⚠ Please enter your website domain")
    else:
        keyword_list = [k.strip() for k in keywords.strip().split("\n") if k.strip()][:500]
        st.subheader("🔍 Checking rankings... (Location: India)")
        progress_bar = st.progress(0)
        total = len(keyword_list)
        results = []

        mapping = COUNTRY_MAP["India"]
        gl, google_domain, hl = mapping["gl"], mapping["google_domain"], mapping["hl"]

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(
                    check_domain_ranking,
                    api_key, kw, gl, domain,
                    google_domain, hl,
                    location="India",
                    device=device,
                    search_type=search_type,
                    strict=strict_match
                ): kw for kw in keyword_list
            }

            completed = 0
            for future in as_completed(futures):
                completed += 1
                result = future.result()
                results.append(result)

                # REMOVE or COMMENT OUT this line to prevent individual results from being shown
                # st.write(f"Result for {result[0]}: {result[2]} - {result[3]}")

                progress_bar.progress(completed / total)

        # Filter out keywords that are not in the top 100
        ranked_results = [result for result in results if result[2] != "Not in Top 100"]

        if ranked_results:
            st.subheader("📊 Domain Ranking Results (India) - Keywords in Top 100")
            df = pd.DataFrame(ranked_results, columns=["Keyword", "Location", "Ranking", "URL"])
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("⚠ No keywords found in the top 100.")

        st.download_button("⬇ Download CSV",
                           data=pd.DataFrame(results, columns=["Keyword", "Location", "Ranking", "URL"]).to_csv(
                               index=False), file_name="rankings.csv", mime="text/csv")

        if any("403" in str(r[2]) for r in results):
            st.warning("⚠ Some keywords returned a 403 error. Please check your API key quota or plan.")
