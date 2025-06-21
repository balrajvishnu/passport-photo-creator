import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import streamlit as st
import openai
from serpapi import GoogleSearch

# --- Configuration ---
# Securely fetch secrets
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    SERP_API_KEY = st.secrets["SERP_API_KEY"]
except KeyError:
    st.error("Error: Missing API keys. Please add OPENAI_API_KEY and SERP_API_KEY to your secrets.")
    st.stop()

# Configure the APIs
openai.api_key = OPENAI_API_KEY

# --- Core Functions ---

def search_book_reviews(book_title):
    """Searches for book reviews and summaries using SerpApi."""
    # Clean the book title for a better search query
    cleaned_title = book_title.strip().rstrip(':.!?,;')
    st.info(f"🔎 Searching for reviews of '{cleaned_title}'...")
    try:
        params = {
            "engine": "google",
            "q": f'reviews and summary of the book "{cleaned_title}"',
            "api_key": SERP_API_KEY,
            "num": 10  # Request more results to get a better overview
        }
        search = GoogleSearch(params)
        results = search.get_dict()

        # Check for an error from the API
        if "error" in results:
            st.error(f"SerpApi Error: {results['error']}. Please check that your SERP_API_KEY is correct in your secrets file.")
            return None

        # Extract relevant text snippets from the search results
        snippets = []
        if "organic_results" in results:
            for result in results["organic_results"]:
                if "snippet" in result:
                    snippets.append(result["snippet"])
        
        if not snippets:
            st.warning("Could not find enough review information online. The analysis might be limited.")
            return None

        return " ".join(snippets)
    except Exception as e:
        st.error(f"Failed to search for book reviews: {e}")
        return None

def analyze_book_reviews(book_title, reviews_text):
    """Analyzes book reviews using GPT-4o to generate a summary, sentiment, rating, and recommendation."""
    st.info("🤖 Analyzing reviews with GPT-4o...")
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        prompt_messages = [
            {"role": "system", "content": "You are a highly intelligent book review analyst. Based on the provided snippets from web search results, you will analyze the book. Your output must be in markdown format and strictly follow this structure:\n\n**Book Summary:**\n[A concise, high-level summary of the book's plot and main themes.]\n\n**Review Analysis:**\n[An analysis of the overall sentiment of the reviews (e.g., overwhelmingly positive, mixed, generally negative). Mention key points of praise or criticism.]\n\n**Rating:**\n[A rating out of 10, e.g., 8.5/10.]\n\n**Recommendation:**\n[A clear recommendation, e.g., 'Highly Recommended', 'Recommended for fans of the genre', 'Not Recommended'.]"},
            {"role": "user", "content": f"Here are the review snippets for the book '{book_title}':\n\n{reviews_text}"}
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=prompt_messages,
            temperature=0.7,
            max_tokens=800
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Failed to analyze book reviews with OpenAI: {e}")
        return None

# --- Password Protection ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

# --- Streamlit UI ---
st.set_page_config(page_title="AI Book Reviewer & Recommender", layout="centered")

if check_password():
    st.title("📚 AI Book Reviewer & Recommender")
    st.write("Enter a book title, and let AI provide a summary, review analysis, and recommendation.")

    book_title_prompt = st.text_input("Enter the title of the book", key="book_title_input")
    analyze_button = st.button("Analyze Book")

    if analyze_button and book_title_prompt:
        with st.spinner(f"Compiling a report for '{book_title_prompt}'... This may take a moment."):
            # Step 1: Search for reviews
            review_snippets = search_book_reviews(book_title_prompt)
            
            if review_snippets:
                # Step 2: Analyze the reviews with AI
                analysis_result = analyze_book_reviews(book_title_prompt, review_snippets)

                if analysis_result:
                    st.success("Analysis Complete!")
                    st.markdown(analysis_result)

    elif analyze_button and not book_title_prompt:
        st.warning("Please enter a book title first.") 