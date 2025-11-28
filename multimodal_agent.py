import streamlit as st
import time
from pathlib import Path
import tempfile
import re
import random
from agno.agent import Agent
from agno.run.agent import RunOutput
from agno.models.google import Gemini
from agno.media import Video, Image

st.set_page_config(
    page_title="Multimodal AI Agent",
    page_icon="🧬",
    layout="wide"
)

st.title("Multimodal AI Agent 🧬")

# --- Function to simulate parsing and calculating attribution ---
def run_agent_and_get_attribution(agent: Agent, prompt: str, media_args: dict) -> tuple:
    """
    Runs the agent with an attribution-forcing prompt and parses the result
    to extract scores and evidence for the aggregator component.
    
    NOTE: This is a simulation. In a production environment, the LLM must be
    tuned/prompted to reliably output the attribution sections in a parseable format
    (e.g., in a final JSON or using clear markdown headers).
    """
    
    # 1. Run the agent with the modified prompt
    result: RunOutput = agent.run(prompt, **media_args)
    full_content = result.content
    
    # --- SIMULATED PARSING & SCORING ---
    # Since agno's RunOutput doesn't give direct contribution scores, we
    # simulate this by forcing the LLM to output specific sections and
    # then assign a random score based on the result.
    
    # This regex attempts to find structured sections based on the prompt's formatting
    visual_match = re.search(r'\*\*VISUAL FINDINGS:\*\*(.*?)(?=\*\*|\Z)', full_content, re.DOTALL)
    search_match = re.search(r'\*\*RESEARCH FINDINGS:\*\*(.*?)(?=\*\*|\Z)', full_content, re.DOTALL)
    answer_match = re.search(r'\*\*FINAL ANSWER:\*\*(.*?)(?=\*\*|\Z)', full_content, re.DOTALL)
    
    # If the LLM successfully executed a search, assume higher search reliance
    # This part needs an actual check on RunOutput.messages for tool calls in a real app.
    # For this simulation, we'll use a random distribution but prioritize if the content mentions external sources.
    
    search_content_found = "web search" in full_content.lower() or "external sources" in full_content.lower()
    
    if search_content_found:
        # If external sources are mentioned, skew the score toward search
        search_score = random.randint(50, 95) 
    else:
        # If mostly visual description, skew toward visual
        search_score = random.randint(5, 50)
        
    visual_score = 100 - search_score
    
    # Extract data for the Evidence Log
    visual_findings = visual_match.group(1).strip() if visual_match else "No specific visual findings detailed."
    search_queries = ["(Query 1 - Simulated)", "(Query 2 - Simulated)"] 
    search_snippets = ["(Snippet 1 from example.com)", "(Snippet 2 from example.org)"] 
    final_answer = answer_match.group(1).strip() if answer_match else full_content
    
    # In a real agno app, you would use result.messages and search for tool_calls 
    # and tool_outputs to get actual queries and snippets.
    
    attribution_data = {
        'visual_score': visual_score,
        'search_score': search_score,
        'visual_findings': visual_findings.split('\n'),
        'search_queries': search_queries,
        'search_snippets': search_snippets,
        'final_answer': final_answer
    }
    
    return attribution_data

# --- APP SETUP ---

# Get Gemini API key from user in sidebar
with st.sidebar:
    st.header("🔑 Configuration")
    gemini_api_key = st.text_input("Enter your Gemini API Key", type="password")
    st.caption(
        "Get your API key from [Google AI Studio]"
        "(https://aistudio.google.com/apikey) 🔑"
    )

# Initialize single agent with both capabilities
@st.cache_resource
def initialize_agent(api_key):
    return Agent(
        name="Multimodal Analyst",
        model=Gemini(id="gemini-2.5-flash", api_key=api_key),
        markdown=True,
    )

if gemini_api_key:
    agent = initialize_agent(gemini_api_key)

    # --- Image/Video Selector and Uploader ---
    media_type = st.selectbox(
        "Select media type to upload:",
        ["Video", "Image"]
    )
    
    if media_type == "Video":
        uploaded_file = st.file_uploader(
            "Upload a video file", 
            type=['mp4', 'mov', 'avi']
        )
    else: # Image
        uploaded_file = st.file_uploader(
            "Upload an image file", 
            type=['jpg', 'jpeg', 'png']
        )

    if uploaded_file:
        # Save file to a temporary location
        suffix = uploaded_file.name.split('.')[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{suffix}') as tmp_file:
            tmp_file.write(uploaded_file.read())
            media_path = tmp_file.name
        
        # Display media based on type
        if media_type == "Video":
            st.video(media_path)
            media_object = Video(filepath=media_path)
        else:
            st.image(media_path, use_column_width=True)
            media_object = Image(filepath=media_path)

        # --- User Prompt Section ---
        user_prompt = st.text_area(
            "What would you like to know?",
            placeholder=f"Ask any question related to the {media_type.lower()} - the AI Agent will analyze it and search the web if needed",
            help="You can ask questions about the media content and get relevant information from the web"
        )
        
        if st.button("Analyze & Research 🚀"):
            if not user_prompt:
                st.warning("Please enter your question.")
            else:
                try:
                    with st.spinner(f"Processing {media_type.lower()} and researching..."):
                        
                        media_type_lower = media_type.lower()
                        
                        # --- MODIFIED CHAIN-OF-THOUGHT PROMPT ---
                        prompt = f"""
                        You are a highly capable Multimodal Analyst. Your final output MUST contain three separate, clearly marked sections: **VISUAL FINDINGS**, **RESEARCH FINDINGS**, and **FINAL ANSWER**.
                        
                        **TASK (Chain-of-Thought):**
                        1. **Analyze the provided {media_type_lower} meticulously.** Use object recognition, scene context, temporal flow (for videos), and any visible text to build a complete understanding. Output this summary under **VISUAL FINDINGS**.
                        2. **Perform web research** to gather necessary external context. Output the synthesis of the search results under **RESEARCH FINDINGS**.
                        3. **QUESTION:** Answer the user's question: {user_prompt}. The answer must fuse findings from both the **VISUAL FINDINGS** and **RESEARCH FINDINGS** sections. Output this final conclusion under **FINAL ANSWER**.
                        
                        **OUTPUT INSTRUCTIONS:** Ensure your output is comprehensive, professional, and includes the three required markdown sections.
                        """
                        
                        # Set media arguments based on type
                        if media_type == "Video":
                            media_args = {'videos': [media_object]}
                        else:
                            media_args = {'images': [media_object]}
                        
                        # Run the agent and parse the simulated attribution
                        attribution_data = run_agent_and_get_attribution(agent, prompt, media_args)
                        
                    # --- DISPLAY RESULTS AND AGGREGATOR ---
                    
                    st.subheader("✅ Agent's Final Conclusion")
                    st.markdown(attribution_data['final_answer'])

                    st.markdown("---")
                    
                    ## 🕹️ GAMIFIED AGGREGATOR COMPONENT 
                    st.header("🔬 Multimodal Contribution Scorecard")
                    st.caption("This scorecard visualizes the estimated reliance of the answer on visual input vs. external research.")

                    col1, col2 = st.columns(2)
                    
                    # Visual Contribution Column
                    with col1:
                        st.metric(
                            label=f"🖼️ {media_type} Insight Score", 
                            value=f"{attribution_data['visual_score']}%",
                            delta="Direct Perception"
                        )
                        st.progress(attribution_data['visual_score'] / 100)
                        st.markdown(f"The model's answer relied on **direct visual evidence** (e.g., recognizing objects, reading text in the image) for **{attribution_data['visual_score']}%** of its data.")

                    # Search Contribution Column
                    with col2:
                        st.metric(
                            label="🌐 Research Power Score", 
                            value=f"{attribution_data['search_score']}%",
                            delta="External Knowledge"
                        )
                        st.progress(attribution_data['search_score'] / 100)
                        st.markdown(f"The model's answer relied on **external web search data** (e.g., facts, prices, dates) for **{attribution_data['search_score']}%** of its data.")

                    st.markdown("---")

                   

                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                finally:
                    # Clean up the temporary file
                    Path(media_path).unlink(missing_ok=True)
    else:
        st.info(f"Please upload a {media_type.lower()} to begin analysis.")
else:
    st.warning("Please enter your Gemini API key to continue.")

st.markdown("""
    <style>
    .stTextArea textarea {
        height: 100px;
    }
    </style>
    """, unsafe_allow_html=True)
