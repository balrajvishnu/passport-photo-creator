# AI Book Reviewer & Recommender

This Streamlit application provides an AI-powered analysis of any book. Simply enter a book title, and the app will search for reviews online, analyze them using GPT-4o, and generate a concise report including a summary, sentiment analysis, a rating, and a final recommendation.

## ✨ Features

-   **Real-time Review Search**: Uses SerpApi to find current book reviews and summaries from Google search results.
-   **AI-Powered Analysis**: Leverages OpenAI's `gpt-4o` to understand and summarize the collected reviews.
-   **Secure**: Protects access with a password and securely manages API keys using Streamlit's built-in secrets management.
-   **Easy to Deploy**: Ready to be deployed on Streamlit Community Cloud in just a few steps.

## 🚀 How to Run Locally

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/balrajvishnu/book-reviewer-app.git
    cd book-reviewer-app
    ```

2.  **Create your secrets file:**
    -   Create a directory named `.streamlit`.
    -   Inside that directory, create a new file named `secrets.toml`.

3.  **Add your credentials to `.streamlit/secrets.toml`:**
    ```toml
    # Your chosen password for the app
    password = "your_secret_password"

    # Your API keys
    OPENAI_API_KEY = "your_openai_api_key_here"
    SERP_API_KEY = "your_serp_api_key_here"
    ```

4.  **Install the required libraries:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Run the Streamlit app:**
    ```bash
    streamlit run book_reviewer_app.py
    ```

## ☁️ Deployment

This app is ready to be deployed on [Streamlit Community Cloud](https://share.streamlit.io/).

1.  Push this repository to your GitHub account.
2.  On the Streamlit Cloud dashboard, click "**New app**" and select this repository.
3.  Before deploying, go to the "**Advanced settings...**" section.
4.  Copy the entire contents of your local `.streamlit/secrets.toml` file (the one with your real password and API keys) and paste it into the "**Secrets**" text box.
5.  Click "**Deploy!**" 