import streamlit as st
import google.generativeai as genai
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import requests

# --- Configuration ---

st.set_page_config(page_title="YouTube Video Summarizer", page_icon="📝", layout="centered")

# --- API Key and Model Configuration ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_MODEL_NAME = "gemini-1.5-flash"
except (KeyError, FileNotFoundError):
    st.error("Gemini API Key not found. Please add GEMINI_API_KEY to your Streamlit secrets.")
    st.stop()

# --- Helper Functions ---

def extract_video_id(url: str) -> str | None:
    if not url:
        return None
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
    Fetches the transcript using ScraperAPI proxy (you still use transcript API, not raw HTML).
    """
    try:
        SCRAPERAPI_KEY = st.secrets["SCRAPERAPI_KEY"]
        # Test if ScraperAPI can access the video page — not strictly needed
        target_url = f"https://www.youtube.com/watch?v={video_id}"
        proxy_url = f"http://api.scraperapi.com/?api_key={SCRAPERAPI_KEY}&url={target_url}"
        test_response = requests.get(proxy_url)
        if test_response.status_code != 200:
            st.warning(f"ScraperAPI could not access video (status code: {test_response.status_code})")

        # Still fetch transcript directly
        languages_to_try = ['hi', 'en', 'en-US', 'es', 'fr', 'de', 'pt']
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=languages_to_try)
        full_transcript = " ".join([entry['text'] for entry in transcript_list])
        st.success("Transcript fetched successfully!")
        return full_transcript

    except TranscriptsDisabled:
        st.error("Transcripts are disabled for this video by the owner.")
        return None
    except NoTranscriptFound:
        st.warning("No suitable transcript found in supported languages.")
        return None
    except Exception as e:
        st.error(f"Transcript fetch failed: {e}")
        return None

def summarize_text_with_gemini(text_to_summarize: str, word_count: int) -> str | None:
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
        st.error(f"Gemini API error: {e}")
        return None

def get_youtube_thumbnail_url(video_id: str) -> str:
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
                st.image(get_youtube_thumbnail_url(video_id), caption="Video Thumbnail", use_container_width=True)
                transcript = get_transcript_with_scraperapi(video_id)
                if transcript:
                    summary = summarize_text_with_gemini(transcript, selected_word_count)
                    if summary:
                        st.subheader("Generated Summary:")
                        st.markdown(summary)
                        with st.expander("Click to view full transcript"):
                            st.text_area(label="Full Transcript", value=transcript, height=250)
        else:
            st.error("Invalid YouTube URL. Please enter a valid video link.")
    else:
        st.warning("Please enter a YouTube video URL to summarize.")

st.markdown("---")
st.markdown("Made with ❤ by IITP Students.")
