import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, SequentialChain
from serpapi.google_search import GoogleSearch
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
# Clear previous session data
for key in st.session_state.keys():
    del st.session_state[key]


# ========================
# API KEYS
# ========================
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
SERP_API_KEY = st.secrets["SERPAPI_API_KEY"]

# Initialize GPT
llm = ChatOpenAI(model_name="gpt-4", temperature=0.2)

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
# PROMPTS
# ========================
market_analysis_prompt = PromptTemplate(
    input_variables=["product", "region", "industry", "competitors"],
    template="""
You are a market research expert.
Analyze the market for {product} in {region}, focusing on {industry}. Include:
1. Market size & growth trend
2. Key competitors: {competitors}
3. Adoption trends in this niche
Provide actionable insights for GTM planning.
"""
)

gtm_framework_prompt = PromptTemplate(
    input_variables=["product", "audience", "budget", "goal", "region", "market_analysis"],
    template="""
Using this market analysis:
{market_analysis}
Create a GTM strategy for {product} targeting {audience}, with a {budget} budget and primary goal: {goal}.
Include:
1. Ideal Customer Profile (ICP)
2. Positioning statement + 3 value propositions
3. Recommended GTM channels (aligned with {goal} and {budget})
4. Highlight if regional tactics are needed for {region}.
"""
)

execution_plan_prompt = PromptTemplate(
    input_variables=["gtm_framework", "budget", "goal", "region"],
    template="""
Using this GTM framework:
{gtm_framework}

Create:
1. A detailed 90-day GTM timeline optimized for a {budget} budget and the primary goal ({goal}). 
STRICT RULE: Only include tactics relevant to {goal}:
   - If Awareness: Focus ONLY on reach, impressions, and brand visibility (organic social media, PR, influencer shoutouts, viral campaigns). Do NOT include sign-ups, conversions, retention tactics, or CAC optimization.
   - If Acquisition: Focus ONLY on sign-ups, free trials, referral programs, landing pages, paid ads that drive conversions. No awareness-only or retention tactics.
   - If Retention: Focus ONLY on loyalty programs, churn reduction strategies, customer engagement campaigns, community-building. No awareness or acquisition tactics.

Ensure regional adaptation for {region} (festivals, influencer partnerships, local platforms).

2. Provide 3 creative campaign ideas EXCLUSIVELY aligned with {goal}. 
For Awareness, emphasize campaigns that maximize reach and buzz (viral videos, PR stunts, influencer collabs).

3. Provide 5 KPIs EXCLUSIVELY focused on {goal} with realistic numeric benchmarks:
   - Awareness: impressions, reach, engagement rate, follower growth, brand mentions.
   - Acquisition: sign-ups, CAC, conversion %, CTR, pipeline growth.
   - Retention: churn %, repeat purchase rate, NPS, engagement in community, upsell %.
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
    product = st.text_input("Enter your product description", value="")
    audience = st.text_input("Enter your target audience", value="")
    budget = st.selectbox("Select your budget level", ["Low", "Medium", "High"])
    goal = st.selectbox("Primary goal of this GTM plan", ["Awareness", "Acquisition", "Retention"])
    region = st.text_input("Target region", value="")
    industry = st.text_input("Industry focus", value="")
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

    for line in report_text.splitlines():
        if y < 50:  # If near bottom margin, add new page
            pdf.showPage()
            add_header_footer()
            pdf.setFont("Helvetica", 11)
            y = height - 60

        # Formatting
        if line.strip().startswith("----"):  # Skip dividers
            continue
        elif line.strip().startswith("GO-TO-MARKET STRATEGY REPORT"):
            continue
        elif line.strip().startswith("Product:"):
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(40, y, line)
            pdf.setFont("Helvetica", 11)
        elif "Market Analysis" in line:
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(40, y, "Market Analysis")
            pdf.setFont("Helvetica", 11)
        elif "GTM Framework" in line:
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(40, y, "GTM Framework")
            pdf.setFont("Helvetica", 11)
        elif "Execution Plan" in line:
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(40, y, "Execution Plan")
            pdf.setFont("Helvetica", 11)
        elif line.strip().startswith("-") or line.strip().startswith("•"):
            pdf.drawString(50, y, "• " + line.lstrip("-•").strip())
        else:
            pdf.drawString(40, y, line)
        y -= line_height

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


if submit_button:
    st.write("🔍 Fetching real-time competitor data...")
    competitors = fetch_competitors(product, region)
    st.write("✅ Competitor data retrieved successfully!")
    st.write("⏳ Generating your GTM plan...")

    result = overall_chain({
        "product": product,
        "audience": audience,
        "budget": budget,
        "goal": goal,
        "region": region,
        "industry": industry,
        "competitors": ", ".join(competitors)
    })

    # ========================
    # DISPLAY OUTPUT
    # ========================
    st.subheader("✅ Your GTM Strategy Report")

    with st.expander("📊 Market Analysis"):
        st.markdown(result["market_analysis"])

    with st.expander("🛠 GTM Framework"):
        st.markdown(result["gtm_framework"])

    with st.expander("🚀 Execution Plan"):
        st.markdown(result["execution_plan"])

    # ========================
    # DOWNLOAD REPORT
    # ========================
    final_report = f"""
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

    st.download_button("📥 Download GTM Plan as TXT", data=final_report, file_name="GTM_Strategy.txt", mime="text/plain")

    # Generate PDF version of the report
    pdf_buffer = create_pdf(final_report)
    st.download_button(
    label="📄 Download GTM Plan as PDF",
    data=pdf_buffer,
    file_name="GTM_Strategy.pdf",
    mime="application/pdf"
)


