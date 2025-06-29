import streamlit as st
import google.generativeai as genai
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

# --- Configuration ---

# Set the page configuration for the Streamlit app
st.set_page_config(page_title="YouTube Video Summarizer", page_icon="📝", layout="centered")

# --- API Key and Model Configuration ---

# Configure the Gemini API from Streamlit secrets
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_MODEL_NAME = "gemini-1.5-flash"
except (KeyError, FileNotFoundError):
    st.error("Gemini API Key not found. Please add `GEMINI_API_KEY` to your Streamlit secrets.")
    st.stop()

# --- Helper and Core Functions ---

def extract_video_id(url: str) -> str | None:
    """Extracts the YouTube video ID from various YouTube URL formats."""
    if not url:
        return None
    # Standard URL: https://www.youtube.com/watch?v=VIDEO_ID
    # Shortened URL: https://youtu.be/VIDEO_ID
    query = urlparse(url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            p = parse_qs(query.query)
            return p.get('v', [None])[0]
        if query.path[:7] == '/embed/':
            return query.path.split('/')[2]
        if query.path[:3] == '/v/':
            return query.path.split('/')[2]
    return None

def get_transcript_with_proxy(video_id: str) -> str | None:
    """
    Fetches the transcript for a video in a list of preferred languages,
    using a proxy to avoid IP blocking.
    """
    proxies = {}
    try:
        # Build proxy URL from secrets if they exist
        proxy_url = (
            f"http://{st.secrets['PROXY_USER']}:{st.secrets['PROXY_PASS']}"
            f"@{st.secrets['PROXY_HOST']}:{st.secrets['PROXY_PORT']}"
        )
        proxies = {'http': proxy_url, 'https': proxy_url}
    except KeyError:
        # Run without proxy if secrets are not set
        st.info("Proxy credentials not found. Running directly.", icon="⚠️")

    try:
        # Define the list of languages to try
        # This will find the first available transcript from this list
        languages_to_try = ['hi', 'en', 'en-US', 'es', 'fr', 'de', 'pt']
        
        # Get the transcript using your proven logic, but with proxies added
        transcript_list = YouTubeTranscriptApi.get_transcript(
            video_id, 
            languages=languages_to_try,
            proxies=proxies or None
        )

        # Concatenate all transcript entries into a single string
        full_transcript = " ".join([entry['text'] for entry in transcript_list])
        
        st.success("Transcript fetched successfully!")
        return full_transcript

    except TranscriptsDisabled:
        st.error("Transcripts are disabled for this video by the owner.")
        return None
    except NoTranscriptFound:
        st.warning("No suitable transcript could be found in the supported languages for this video.")
        return None
    except Exception as e:
        st.error(f"An error occurred while fetching the transcript: {e}")
        return None


def summarize_text_with_gemini(text_to_summarize: str, word_count: int) -> str | None:
    """Summarizes the given text using the Gemini API."""
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        prompt = f"""You are a YouTube video summarizer. Take the following transcript and provide a detailed summary in bullet points within approximately {word_count} words. Focus on key concepts, important arguments, and conclusions.
        Transcript:
        {text_to_summarize}
        Summary:
        """
        response = model.generate_content(prompt)
        summary = response.candidates[0].content.parts[0].text
        st.success("Summary generated successfully!")
        return summary
    except Exception as e:
        st.error(f"An error occurred during Gemini API call: {e}")
        return None

def get_youtube_thumbnail_url(video_id: str) -> str:
    """Generates the URL for a YouTube video's high-quality thumbnail."""
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

# --- Streamlit UI ---

st.title("YouTube Video Summarizer 📝")
st.markdown("Enter a YouTube video URL to get a concise, AI-generated summary.")

youtube_url = st.text_input("Enter YouTube Video URL:", placeholder="e.g., https://www.youtube.com/watch?v=dQw4w9WgXcQ")
selected_word_count = st.selectbox("Select summary length (approx words):", [250, 400, 600])

if st.button("Summarize Video", type="primary"):
    if youtube_url:
        video_id = extract_video_id(youtube_url)
        if video_id:
            with st.spinner("Fetching transcript and generating summary..."):
                thumbnail_url = get_youtube_thumbnail_url(video_id)
                st.image(thumbnail_url, caption="Video Thumbnail", use_container_width=True)
                transcript = get_transcript_with_proxy(video_id)
                if transcript:
                    summary = summarize_text_with_gemini(transcript, selected_word_count)
                    if summary:
                        st.subheader("Generated Summary:")
                        st.markdown(summary)
                        with st.expander("Click to view full transcript"):
                            st.text_area(label="Full Transcript", value=transcript, height=250)
        else:
            st.error("Invalid YouTube URL. Please enter a valid video URL.")
    else:
        st.warning("Please enter a YouTube video URL to summarize.")

st.markdown("---")
st.markdown("*Made with ❤️ by IITP Students.*")
