import streamlit as st
import google.generativeai as genai
from urllib.parse import urlparse, parse_qs, quote_plus
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import requests
from gtts import gTTS
from fpdf import FPDF
import os
import tempfile
from streamlit_lottie import st_lottie

# --- Page Config ---
st.set_page_config(page_title="YouTube Video Summarizer", page_icon="📝", layout="centered")

# --- CSS Styling ---
st.markdown("""
    <style>
    body {
        background-color: #0e1117;
        color: white;
    }
    # .glow-title {
    #     font-size: 2.5rem;
    #     font-weight: 700;
    #     color: #FFFFFF;
    #     text-align: center;
    #     margin-top: 0.5em;
    #     letter-spacing: 1px;
    }
   
   .glow-title {
    font-size: 2.5rem;
    font-weight: bold;
    color: #4facfe; /* Fallback color */
    background-image: linear-gradient(to right, #4facfe 0%, #00f2fe 100%);
    background-clip: text;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-top: 0.5em;
}

    .badge {
        display: inline-block;
        margin: 0.3em;
        padding: 0.4em 0.7em;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: 600;
        background: #2b2d31;
        color: #00f9ff;
        border: 1px solid #00f9ff55;
    }
    button[kind="primary"] {
        background: linear-gradient(to right, #00f9ff, #00fcb2);
        border: none !important;
        color: black !important;
        font-weight: bold;
        box-shadow: 0 0 10px #00f9ff;
        transition: all 0.3s ease-in-out;
    }
    button[kind="primary"]:hover {
        box-shadow: 0 0 20px #00fcb2;
        transform: scale(1.05);
    }
    </style>
""", unsafe_allow_html=True)

# --- Load Lottie Animation ---
def load_lottie_url(url):
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    return None


# --- Lottie ---
hero_lottie = load_lottie_url("https://assets10.lottiefiles.com/packages/lf20_x62chJ.json")


# --- Gemini Setup ---
try:
    # recommended to use st.secrets for API keys
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_MODEL_NAME = "gemini-1.5-flash"
except KeyError:
    st.error("Gemini API Key not found. Please add GEMINI_API_KEY to your Streamlit secrets.")
    st.stop()


# Header Section 
st.markdown('<div class="glow-title">✨ YT Video Summarizer ✨</div>', unsafe_allow_html=True)
col1, col2 = st.columns([1, 2])
with col1:
    st_lottie(hero_lottie, height=200, key="hero-animation")
with col2:
    st.markdown('<div class="hero-box">', unsafe_allow_html=True)
    st.markdown("*Quickly turn long YouTube videos into summarized insights.*")
    st.markdown("✅ Powered by Google Gemini 1.5 Flash")
    st.markdown("📑 Transcript ➝ Summary ➝ PDF/Audio")
    st.markdown("🔊 Listen to summary narration")
    st.markdown('<span class="badge">Gemini AI</span> <span class="badge">Audio Export</span> <span class="badge">PDF Summary</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Helper Functions 
def extract_video_id(url: str) -> str | None:
    query = urlparse(url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            return parse_qs(query.query).get('v', [None])[0]
        if query.path.startswith(('/embed/', '/v/')):
            return query.path.split('/')[2]
    return None

def get_transcript(video_id: str) -> str | None:
    try:
        # Fetches from a list of preferred languages
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US', 'hi'])
        return " ".join([entry['text'] for entry in transcript_list])
    except TranscriptsDisabled:
        st.error("Transcripts are disabled for this video.")
    except NoTranscriptFound:
        st.warning("No English transcript could be found for this video.")
    except Exception as e:
        st.error(f"An error occurred while fetching the transcript: {e}")
    return None

def summarize_text_gemini(text: str, word_count: int) -> str | None:
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        prompt = f"Summarize the following YouTube transcript into concise bullet points, aiming for a total of around {word_count} words:\n\n{text}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"An error occurred during summarization: {e}")
        return None

def generate_tts(summary: str, lang='en') -> str | None:
    try:
        tts = gTTS(summary, lang=lang)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tts.save(tmp_file.name)
            return tmp_file.name
    except Exception as e:
        st.error(f"Failed to generate audio: {e}")
        return None

def create_pdf(summary: str) -> str | None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    # Encode summary to latin-1, replacing characters that Arial can't handle
    encoded_summary = summary.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, encoded_summary)
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdf.output(tmp_file.name)
            return tmp_file.name
    except Exception as e:
        st.error(f"Failed to create PDF: {e}")
        return None

def get_youtube_thumbnail_url(video_id: str) -> str:
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

# Sidebar
st.sidebar.title("🔧 Options")
st.sidebar.info("Customize your summary output below 👇")
selected_word_count = st.sidebar.selectbox("📝 Summary Length (approx. words):", [250, 400, 600])

# Main Input
youtube_url = st.text_input("🔗 Enter YouTube Video URL:", placeholder="e.g. https://www.youtube.com/watch?v=dQw4w9WgXcQ")

# Button Trigger
if st.button("🚀 Generate Summary", type="primary"):
    if youtube_url:
        video_id = extract_video_id(youtube_url)
        if video_id:
            with st.spinner("Fetching transcript..."):
                st.image(get_youtube_thumbnail_url(video_id), caption="🎞 Video Thumbnail", use_container_width=True)
                transcript = get_transcript(video_id)

            if transcript:
                progress_bar = st.progress(0, "Summarizing...")
                summary = summarize_text_gemini(transcript, selected_word_count)
                progress_bar.progress(100, "✅ Summary Ready")

                if summary:
                    st.markdown("### 📝 Summary")
                    st.markdown(summary)

                    # Comparison
                    st.markdown("### 🔍 Transcript vs Summary")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_area("📜 Full Transcript", value=transcript, height=300)
                    with col2:
                        st.text_area("📝 Summary", value=summary, height=300)

                    # Downloads
                    st.markdown("### 📥 Download Options")
                    pdf_path = create_pdf(summary)
                    if pdf_path:
                        with open(pdf_path, "rb") as pdf_file:
                            st.download_button("📄 Download as PDF", data=pdf_file, file_name="summary.pdf", mime="application/pdf")

                    tts_path = generate_tts(summary)
                    if tts_path:
                        st.audio(tts_path, format="audio/mp3")

                    # Sharing
                    share_url = f"https://api.whatsapp.com/send?text={quote_plus(summary)}"
                    st.markdown(f"[📤 Share on WhatsApp]({share_url})")
        else:
            st.error("Invalid YouTube URL. Please enter a valid URL.")
    else:
        st.warning("Please enter a YouTube video URL.")

# --- Footer ---
st.markdown("---")
st.caption("Made with ❤ by IITP Students!!!")
