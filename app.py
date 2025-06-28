import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


try:
    gemini_api_key = os.getenv("GEMINI_API_KEY") 
    if not gemini_api_key:
        st.error("Gemini API Key not found. Please set it as an environment variable (`GEMINI_API_KEY`), in a `.env` file, or in Streamlit secrets (`.streamlit/secrets.toml`).")
        st.stop()  # Stop the app if API key is not found
    genai.configure(api_key=gemini_api_key)
except Exception as e:
    st.error(f"Error configuring Gemini API: {e}. Please ensure your API key is correctly set up.")
    st.stop()

# Define the model to use for summarization.
# Using 'gemini-1.5-flash' as it's optimized for speed and cost for summarization.
GEMINI_MODEL_NAME = "gemini-1.5-flash"

# --- Functions ---

def get_youtube_transcript(video_url: str) -> str | None:
    """
    Fetches the transcript for a given YouTube video URL.

    Args:
        video_url (str): The full URL of the YouTube video.

    Returns:
        str | None: The concatenated transcript text if successful, None otherwise.
    """
    try:
        # Extract video ID from the URL
        video_id = video_url.split("v=")[1].split("&")[0]
        
        # Get the transcript, prioritizing common languages
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US', 'es', 'fr', 'de', 'pt', 'hi', 'zh'])

        # Concatenate all transcript entries into a single string
        transcript_text = " ".join([entry['text'] for entry in transcript_list])
        st.success("Transcript fetched successfully.")
        return transcript_text

    except NoTranscriptFound:
        st.error(f"Error: No English or other common language transcript found for this video. This might be due to language availability or the video owner not providing captions.")
        return None
    except TranscriptsDisabled:
        st.error(f"Error: Transcripts are disabled for this video.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching the transcript: {e}")
        return None

def summarize_text_with_gemini(text_to_summarize: str, word_count: int, model_name: str = GEMINI_MODEL_NAME) -> str | None:
    """
    Summarizes the given text using the Gemini API.

    Args:
        text_to_summarize (str): The long text (e.g., transcript) to be summarized.
        word_count (int): The desired word count for the summary.
        model_name (str): The name of the Gemini model to use for summarization.

    Returns:
        str | None: The generated summary if successful, None otherwise.
    """
    try:
        # Initialize the GenerativeModel
        model = genai.GenerativeModel(model_name)

        # Define the prompt for summarization, now including the desired word count
        prompt = f"""You are a YouTube video summarizer. Take the transcript text and provide a detailed summary in bullet points within {word_count} words. Focus on key concepts and structure the output clearly.
        Text:
        {text_to_summarize}

        Summary:
        """
        
        # Generate content with the model
        response = model.generate_content(prompt)

        # Access the generated text
        if response.candidates and response.candidates[0].content.parts:
            summary = response.candidates[0].content.parts[0].text
            st.success("Summary generated successfully!")
            return summary
        else:
            st.warning("Gemini API did not return a valid summary. This could be due to safety filters or an empty response.")
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                st.write("Prompt Feedback:", response.prompt_feedback)
            if hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'finish_reason'):
                        st.write(f"Candidate Finish Reason: {candidate.finish_reason}")
                    if hasattr(candidate, 'safety_ratings'):
                        st.write(f"Candidate Safety Ratings: {candidate.safety_ratings}")
            return None

    except Exception as e:
        st.error(f"An error occurred during Gemini API call: {e}")
        return None

def get_youtube_thumbnail_url(video_url: str) -> str | None:
    """
    Generates the URL for a YouTube video's high-quality thumbnail.

    Args:
        video_url (str): The full URL of the YouTube video.

    Returns:
        str | None: The URL of the thumbnail image, or None if video ID cannot be extracted.
    """
    try:
        video_id = video_url.split("v=")[1].split("&")[0]
        return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    except Exception:
        return None

# --- Streamlit UI ---
st.set_page_config(page_title="YouTube Transcript Summarizer", page_icon="📝")

st.title("YouTube Transcript Summarizer")
st.markdown(
    """
    Enter a YouTube video URL below to get a concise summary of the video.
    """
)

# Input for YouTube URL
youtube_url = st.text_input("Enter YouTube Video URL:", placeholder="e.g., https://www.youtube.com/watch?v=dQw4w9WgXcQ")

# --- NEW FEATURE: Word Count Selection ---
# Add a selectbox for the user to choose the desired word count for the summary.
word_count_options = [250, 400, 600]
selected_word_count = st.selectbox(
    "Select desired summary length (in words):",
    options=word_count_options,
    index=0  # Sets the default value to the first item, 250
)

# Button to trigger summarization
if st.button("Summarize Video"):
    if youtube_url:
        # Display thumbnail if available
        thumbnail_url = get_youtube_thumbnail_url(youtube_url)
        if thumbnail_url:
            st.image(thumbnail_url, caption="Video Thumbnail", use_container_width=True)
        else:
            st.warning("Could not retrieve video thumbnail.")

        with st.spinner("Fetching transcript and generating summary... This might take a moment."):
            # Step 1: Fetch the transcript
            transcript = get_youtube_transcript(youtube_url)

            if transcript:
                # Check if the transcript is excessively long
                if len(transcript.split()) > 10000:
                    st.warning("The transcript is very long. Summarization might be less effective or fail due to context window limits.")

                # Step 2: Summarize the transcript using Gemini with the selected word count
                summary = summarize_text_with_gemini(transcript, selected_word_count)

                if summary:
                    st.subheader("Generated Summary:")
                    st.success(summary)
                    st.markdown("---")
                    st.subheader("Full Transcript (for reference):")
                    # Use st.expander to hide the full transcript
                    with st.expander("Click to view full transcript"):
                        st.write(transcript)
                else:
                    st.error("Failed to generate summary. Please check the video or try a different one.")
            else:
                st.error("Could not retrieve transcript. Please check the URL or try a different video.")
    else:
        st.warning("Please enter a YouTube video URL to summarize.")

st.markdown(
    """
    ---
    *Made with ❤️ by IITP Students.* """
)
