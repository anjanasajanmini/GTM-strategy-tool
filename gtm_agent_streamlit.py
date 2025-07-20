import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, SequentialChain
from serpapi.google_search import GoogleSearch
import os
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("ALL_PROXY", None)
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# Background Image
page_bg_img = """
<style>
[data-testid="stAppViewContainer"] {
    background-image: url("https://images.unsplash.com/photo-1615715757462-9ce10a340052?q=80&w=774&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}
/* Dark Overlay for Transparency */
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5); /* Change 0.5 for more or less transparency */
    z-index: -1;
}

/* Your other CSS for container, radio buttons, inputs, and button styling comes here */
</style>
"""
st.markdown(page_bg_img, unsafe_allow_html=True)

custom_css = """
<style>
/* Form Container Styling */
section.main > div:first-child {
    background-color: rgba(0, 0, 0, 0.6) !important;
    padding: 20px !important;
    border-radius: 12px !important;
    max-width: 700px !important;
    margin: 30px auto !important;
    transition: transform 0.4s ease, box-shadow 0.4s ease !important;
}

section.main > div:first-child:hover {
    transform: scale(1.02) !important;
    box-shadow: 0px 8px 30px rgba(0, 0, 0, 0.6) !important;
}

/* Headings */
h1 {
    text-align: center !important;
    color: white !important;
    font-size: 40px !important;
    font-weight: bold !important;
}

/* Labels */
div[data-baseweb="form-control"] > label {
    color: white !important;
    font-size: 18px !important;
    font-weight: 600 !important;
    margin-bottom: 8px !important;
    display: block !important;
}

/* Text Inputs */
.stTextInput input {
    background-color: rgba(255, 255, 255, 0.95) !important;
    color: black !important;
    font-size: 16px !important;
    font-weight: normal !important;
    border-radius: 6px !important;
    padding: 12px !important;
    border: 1px solid #ccc !important;
    width: 100% !important;
}

/* Radio Buttons Styling */
div[role="radiogroup"] {
    display: flex !important;
    gap: 20px !important;
    justify-content: flex-start !important;
    margin-bottom: 15px !important;
}

div[role="radio"] {
    background-color: rgba(255, 255, 255, 0.95) !important;
    color: white !important;
    border-radius: 6px !important;
    padding: 10px 15px !important;
    font-size: 16px !important;
    font-weight: 500 !important;
    border: 1px solid #ccc !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
}

div[role="radio"][aria-checked="true"] {
    background-color: #FF4B4B !important; /* Red highlight when selected */
    color: white !important;
    border: 1px solid #FF4B4B !important;
}


/* Button Styling */
div.stButton > button:first-child {
    background-color: #FF4B4B !important;
    color: white !important;
    font-size: 18px !important;
    border-radius: 10px !important;
    width: 100% !important;
    font-weight: bold !important;
    border: none !important;
    transition: background 0.3s ease, transform 0.2s ease !important;
}

div.stButton > button:first-child:hover {
    background-color: #CC0000 !important;
    transform: translateY(-3px) !important;
}
/* Force all form labels to white */
label, div[data-baseweb="form-control"] label, .stMarkdown p {
    color: white !important;
}
/* Fix radio button text color */
[data-baseweb="radio"] > div > div {
    color: white !important;
    font-size: 16px !important;
    font-weight: normal !important;
}

/* Fix font color for GTM report inside expanders */
div.streamlit-expanderContent, .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown h2, .stMarkdown h3 {
    color: white !important;
}
/* Force Expander Header Titles to White */
[data-testid="stExpander"] button div p {
    color: white !important;
    font-weight: bold !important;
    font-size: 18px !important;
}


</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)



# ========================
# API KEYS
# ========================
import os
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
os.environ["SERPAPI_API_KEY"] = st.secrets["SERPAPI_API_KEY"]


# Initialize GPT
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4o-mini",  # or "gpt-4"
    temperature=0.2
)


# ========================
# Fetch Competitors (SerpAPI)
# ========================
def fetch_competitors(product, region):
    try:
        search = GoogleSearch({
            "q": f"top competitors of {product} in {region}",
            "api_key": SERP_API_KEY
        })
        results = search.get_dict()
        competitors = []
        if "organic_results" in results:
            for res in results["organic_results"][:10]:
                title = res.get("title", "")
                if len(title.split()) <= 4 and "Top" not in title:
                    competitors.append(title)
        return competitors[:5] if competitors else ["Runway ML", "Synthesia", "Pictory"]
    except Exception:
        return ["Runway ML", "Synthesia", "Pictory"]

# ========================
# PROMPTS (Updated for Accuracy)
# ========================

market_analysis_prompt = PromptTemplate(
    input_variables=["product", "region", "industry", "competitors"],
    template="""
You are a market research expert. Analyze the market for {product} in {region}, focusing on {industry}.
Include:
1. Current market size & annual growth rate (with numeric estimates if known)
2. Top 3 emerging trends relevant to this industry
3. Key competitors: {competitors} – highlight 2 strengths & 2 weaknesses for each
4. Barriers to entry and main adoption challenges for new players
Provide concise, actionable insights tailored to GTM planning.
"""
)

gtm_framework_prompt = PromptTemplate(
    input_variables=["product", "audience", "budget", "goal", "region", "market_analysis"],
    template="""
Using this market analysis:
{market_analysis}

Create a Go-To-Market (GTM) strategy for {product} targeting {audience}.
Constraints: Budget = {budget}, Primary Goal = {goal}, Region = {region}.

Include:
1. Ideal Customer Profile (ICP) with at least 3 attributes (demographics, behaviors, pain points)
2. Positioning statement (one line) + 3 unique value propositions
3. Recommended GTM channels that fit both {goal} and {budget}:
   - Awareness: prioritize cost-effective reach (organic, influencer collabs, PR stunts, social campaigns)
   - Acquisition: focus on lead-gen (landing pages, free trials, retargeting ads)
   - Retention: emphasize loyalty (community engagement, churn reduction, upsell)
4. Regional adaptation ideas (festivals, local influencers, language-specific content)
Ensure recommendations feel **practical and resource-conscious** for the given budget.
"""
)

execution_plan_prompt = PromptTemplate(
    input_variables=["gtm_framework", "budget", "goal", "region"],
    template="""
Using this GTM framework:
{gtm_framework}

Create:
1. A detailed **90-day execution plan** for the given budget ({budget}) and primary goal ({goal}):
   - Break down by **Month 1, Month 2, Month 3**
   - List **specific actions with numbers** (e.g., "Launch 3 influencer collabs", "Run 2 viral video campaigns", "Host 1 webinar")
   - Include **ownership suggestion** (e.g., marketing team, freelancer)

STRICT RULE:
- Awareness: focus ONLY on reach/impressions (influencer campaigns, PR, viral content, social ads)
- Acquisition: focus ONLY on sign-ups & conversion (paid ads, referral programs, landing pages)
- Retention: focus ONLY on engagement/churn reduction (community-building, loyalty perks)

2. Provide 3 **creative campaign ideas** that strongly resonate with the audience and align with {goal}.
   - Make them bold, viral-worthy, and niche-relevant (e.g., if targeting filmmakers, tie into film festivals or cinematic storytelling)

3. Provide 5 **SMART KPIs** for {goal}:
   - Awareness: impressions, reach, engagement rate, brand mentions, social shares
   - Acquisition: sign-ups, conversion rate, CTR, CAC, pipeline growth
   - Retention: churn %, repeat purchases, NPS, community engagement, upsell %

For each KPI, include a **realistic benchmark** scaled to the {budget} (e.g., "Impressions: 200K–300K for Low budget").
"""
)

# ========================
# CHAINS
# ========================
market_analysis_chain = LLMChain(llm=llm, prompt=market_analysis_prompt, output_key="market_analysis")
gtm_framework_chain = LLMChain(llm=llm, prompt=gtm_framework_prompt, output_key="gtm_framework")
execution_plan_chain = LLMChain(llm=llm, prompt=execution_plan_prompt, output_key="execution_plan")

overall_chain = SequentialChain(
    chains=[market_analysis_chain, gtm_framework_chain, execution_plan_chain],
    input_variables=["product", "audience", "budget", "goal", "region", "industry", "competitors"],
    output_variables=["market_analysis", "gtm_framework", "execution_plan"],
    verbose=True
)


# ========================
# STREAMLIT UI
# ========================
st.title("GrowthPilot: AI-Powered GTM Strategy Builder")


with st.form("gtm_form"):
    # Input fields with empty defaults

    product = st.text_input("Enter your product description", value="", label_visibility="visible")
    audience = st.text_input("Enter your target audience", value="", label_visibility="visible")
    budget = st.radio("Select your budget level", ["Low", "Medium", "High"], horizontal=True)
    goal = st.radio("Primary goal of this GTM plan", ["Awareness", "Acquisition", "Retention"], horizontal=True)
    region = st.text_input("Target region", value="", label_visibility="visible")
    industry = st.text_input("Industry focus", value="", label_visibility="visible")
    submit_button = st.form_submit_button("Generate GTM Strategy")

def create_pdf(report_text):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    def add_header_footer():
        # Header
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(40, height - 30, "🚀 GrowthPilot: AI-Powered GTM Strategy")
        # Footer
        pdf.setFont("Helvetica-Oblique", 9)
        pdf.drawString(200, 20, "Generated by GrowthPilot")

    add_header_footer()
    pdf.setFont("Helvetica", 11)
    y = height - 60  # Starting position below header
    line_height = 14
    max_width = width - 80  # Left margin = 40, Right margin = 40

    for line in report_text.splitlines():
        if y < 50:  # If near bottom margin, add new page
            pdf.showPage()
            add_header_footer()
            pdf.setFont("Helvetica", 11)
            y = height - 60

        # Wrap text if it exceeds page width
        words = line.split()
        current_line = ""
        for word in words:
            if pdf.stringWidth(current_line + " " + word, "Helvetica", 11) < max_width:
                current_line += " " + word
            else:
                pdf.drawString(40, y, current_line.strip())
                y -= line_height
                current_line = word
        if current_line:
            pdf.drawString(40, y, current_line.strip())
            y -= line_height

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer

if submit_button:
    st.write("✅ Button clicked and logic started")
    if not product or not audience or not region or not industry:
        st.error("⚠️ Please fill in all fields before generating the GTM strategy.")
    else:
        st.success("✅ Form submitted successfully!")
        st.write("🔍 Fetching real-time competitor data...")

        try:
            # Fetch competitors
            competitors = fetch_competitors(product, region)
            st.write("✅ Competitor data retrieved successfully!")
            st.write("⏳ Generating your GTM plan...")

            # Generate GTM strategy using LangChain
            result = overall_chain({
                "product": product,
                "audience": audience,
                "budget": budget,
                "goal": goal,
                "region": region,
                "industry": industry,
                "competitors": ", ".join(competitors)
            })

            # Save result to session state so it persists after download clicks
            st.session_state["gtm_result"] = result
            st.session_state["final_report"] = f"""
GO-TO-MARKET STRATEGY REPORT
============================

Product: {product}
Audience: {audience}
Budget: {budget}
Goal: {goal}
Region: {region}
Industry: {industry}

---- MARKET ANALYSIS ----
{result["market_analysis"]}

---- GTM FRAMEWORK ----
{result["gtm_framework"]}

---- EXECUTION PLAN ----
{result["execution_plan"]}
"""

        except Exception as e:
            st.error(f"❌ Something went wrong: {e}")
# Persisted display after download click
if "gtm_result" in st.session_state:
    result = st.session_state["gtm_result"]
    final_report = st.session_state["final_report"]

    st.subheader("✅ Your GTM Strategy Report")

    with st.expander("📊 Market Analysis"):
        st.markdown(result["market_analysis"])

    with st.expander("🛠 GTM Framework"):
        st.markdown(result["gtm_framework"])

    with st.expander("🚀 Execution Plan"):
        st.markdown(result["execution_plan"])

    # Download buttons
    st.download_button("📥 Download GTM Plan as TXT", data=final_report, file_name="GTM_Strategy.txt", mime="text/plain")

    pdf_buffer = create_pdf(final_report)
    st.download_button(
        label="📄 Download GTM Plan as PDF",
        data=pdf_buffer,
        file_name="GTM_Strategy.pdf",
        mime="application/pdf"
    )

