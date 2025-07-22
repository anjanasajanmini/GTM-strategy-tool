import os
os.environ["STREAMLIT_WATCHDOG"] = "false"
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, SequentialChain
from serpapi.google_search import GoogleSearch
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import textwrap

## ========================
# API KEYS
# ========================
# Set environment variables for both keys
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
os.environ["SERPAPI_API_KEY"] = st.secrets["SERPAPI_API_KEY"]

# Assign variables for convenience
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
SERPAPI_API_KEY = st.secrets["SERPAPI_API_KEY"]

# Initialize GPT (explicitly pass the key)
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    api_key=OPENAI_API_KEY  # ✅ Correct
)


# ========================
# Background Styling
# ========================
page_bg_img = """<style>[data-testid="stAppViewContainer"] {
background-image: url("https://images.unsplash.com/photo-1615715757462-9ce10a340052?q=80&w=774");
background-size: cover; background-position: center; background-attachment: fixed;}
[data-testid="stAppViewContainer"]::before {
content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
background-color: rgba(0, 0, 0, 0.5); z-index: -1;}</style>"""
st.markdown(page_bg_img, unsafe_allow_html=True)

# ========================
# Fetch Market Data
# ========================
def fetch_market_data(product, region, industry):
    try:
        query = f"{industry} {product} market size 2024-2025 CAGR {region} site:statista.com OR site:marketsandmarkets.com OR site:grandviewresearch.com"
        search = GoogleSearch({"q": query, "api_key": SERP_API_KEY})
        results = search.get_dict()
        snippets = []
        if "organic_results" in results:
            for res in results["organic_results"][:3]:
                snippet = res.get("snippet", "")
                link = res.get("link", "")
                if snippet:
                    snippets.append(f"{snippet} (Source: {link})")
        return "\n".join(snippets) if snippets else "Recent numeric insights not directly found, providing best estimates."
    except Exception as e:
        return f"Error fetching data: {e}"

# ========================
# Fetch Competitors
# ========================
def fetch_competitors(product, region):
    try:
        search = GoogleSearch({"q": f"top competitors of {product} in {region}", "api_key": SERP_API_KEY})
        results = search.get_dict()
        competitors = []
        if "organic_results" in results:
            for res in results["organic_results"][:10]:
                title = res.get("title", "")
                if len(title.split()) <= 6 and not title.lower().startswith("top"):
                    competitors.append(title)
        if competitors:
            return competitors[:5]
    except:
        pass
    try:
        response = llm.predict(f"List 5 major competitors for {product} in {region}, comma-separated.")
        return [c.strip() for c in response.split(",")[:5]]
    except:
        return ["Adobe", "Runway", "Pika Labs", "Descript", "Veed.io"]

# ========================
# PROMPTS
# ========================
market_analysis_prompt = PromptTemplate(
    input_variables=["product", "region", "industry", "competitors", "market_data"],
    template="""
Analyze the {product} market in {region} ({industry} sector).
Use this latest data:
{market_data}

Include:
1. 2025 market size estimate and CAGR (%).
2. 3 emerging trends shaping this industry NOW (not older than 2024).
3. Competitors: {competitors} – 2 strengths & 2 weaknesses for each.
4. Barriers to entry and adoption challenges.
Provide numeric estimates where possible. Avoid math formulas or code-like text.
"""
)

gtm_framework_prompt = PromptTemplate(
    input_variables=["product", "audience", "budget", "goal", "region", "market_analysis"],
    template="""
Using this market analysis:
{market_analysis}

Create a GTM strategy for {product}, targeting {audience}, budget={budget}, goal={goal}, region={region}.
Include:
1. ICP with 3 traits (demographics, behaviors, pain points).
2. Positioning + 3 value propositions.
3. Channels for {goal} & {budget}.
4. Region-specific tactics (festivals, local influencers).
Keep it realistic and actionable.
"""
)

execution_plan_prompt = PromptTemplate(
    input_variables=["gtm_framework", "budget", "goal", "region"],
    template="""
Based on this GTM framework:
{gtm_framework}

Provide:
1. 90-day roadmap with clear numeric actions.
2. 3 bold campaign ideas that can trend.
3. 5 SMART KPIs tied to {budget} with numeric benchmarks.
"""
)

# ========================
# Chains
# ========================
market_analysis_chain = LLMChain(llm=llm, prompt=market_analysis_prompt, output_key="market_analysis")
gtm_framework_chain = LLMChain(llm=llm, prompt=gtm_framework_prompt, output_key="gtm_framework")
execution_plan_chain = LLMChain(llm=llm, prompt=execution_plan_prompt, output_key="execution_plan")

overall_chain = SequentialChain(
    chains=[market_analysis_chain, gtm_framework_chain, execution_plan_chain],
    input_variables=["product", "audience", "budget", "goal", "region", "industry", "competitors", "market_data"],
    output_variables=["market_analysis", "gtm_framework", "execution_plan"],
    verbose=True
)

# ========================
# Streamlit UI
# ========================
st.title("GrowthPilot: AI-Powered GTM Strategy Builder")

with st.form("gtm_form"):
    product = st.text_input("Enter your product")
    audience = st.text_input("Enter your target audience")
    budget = st.radio("Budget Level", ["Low", "Medium", "High"], horizontal=True)
    goal = st.radio("Primary Goal", ["Awareness", "Acquisition", "Retention"], horizontal=True)
    region = st.text_input("Target region")
    industry = st.text_input("Industry")
    submit_button = st.form_submit_button("Generate GTM Strategy")

# ========================
# PDF Generator (Fixed Wrapping)
# ========================
def create_pdf(report_text):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Fonts and spacing
    pdf.setFont("Helvetica", 11)
    y = height - 50
    line_height = 16
    max_width = width - 80  # 40px margin on both sides

    # Clean the text: Remove '#' and extra markdown characters
    clean_text = report_text.replace("###", "").replace("##", "").replace("#", "").strip()

    # Split text into lines
    lines = clean_text.splitlines()

    # Add proper heading styles
    def draw_line(text, bold=False):
        nonlocal y
        if bold:
            pdf.setFont("Helvetica-Bold", 13)
        else:
            pdf.setFont("Helvetica", 11)

        # Wrap text if it exceeds page width
        words = text.split()
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

    # Loop through lines and apply formatting
    for line in lines:
        if y < 50:  # New page if too low
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = height - 50

        if line.strip() == "":
            y -= line_height
            continue
        elif line.upper() == line and len(line.split()) < 6:  # Treat short all-caps as heading
            draw_line(line, bold=True)
        elif line.startswith("----"):  # Skip divider lines
            continue
        else:
            draw_line(line)

    pdf.save()
    buffer.seek(0)
    return buffer


if submit_button:
    if not product or not audience or not region or not industry:
        st.error("⚠️ Please fill in all fields before generating the GTM strategy.")
    else:
        st.write("🔍 Fetching real-time data...")
        try:
            competitors = fetch_competitors(product, region)
            market_data = fetch_market_data(product, region, industry)
            st.write("✅ Data retrieved! Generating GTM plan...")

            result = overall_chain({
                "product": product,
                "audience": audience,
                "budget": budget,
                "goal": goal,
                "region": region,
                "industry": industry,
                "competitors": ", ".join(competitors),
                "market_data": market_data
            })

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
            st.session_state["gtm_result"] = result
            st.session_state["final_report"] = final_report

        except Exception as e:
            st.error(f"❌ Something went wrong: {e}")

if "gtm_result" in st.session_state:
    result = st.session_state["gtm_result"]
    final_report = st.session_state["final_report"]
    st.subheader("✅ Your GTM Strategy Report")
    with st.expander("📊 Market Analysis"): st.markdown(result["market_analysis"])
    with st.expander("🛠 GTM Framework"): st.markdown(result["gtm_framework"])
    with st.expander("🚀 Execution Plan"): st.markdown(result["execution_plan"])
    st.download_button("📥 Download as TXT", data=final_report, file_name="GTM_Strategy.txt")
    st.download_button("📄 Download as PDF", data=create_pdf(final_report), file_name="GTM_Strategy.pdf")
