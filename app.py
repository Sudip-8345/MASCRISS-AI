"""
MASCRISS-AI — Streamlit Dashboard
Streaming agent output + auto-email of crisis report.
"""

import os
import sys
import io
import smtplib
import sqlite3
import threading
import time
import warnings
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


import streamlit as st
from dotenv import load_dotenv, set_key

load_dotenv()
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")
os.environ.setdefault("AGENT_MAX_ITER", "3")
DB_PATH = Path("src/mcp_servers/logistics.db")

# ── Page config ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="MASCRISS-AI",
    page_icon="🛡️",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.1rem;
        font-weight: 800;
        margin-bottom: 0;
    }
    .sub-title {
        text-align: center;
        color: #888;
        font-size: 1rem;
        margin-top: -10px;
        margin-bottom: 30px;
    }
    .stream-box {
        background: #0e1117;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 16px;
        font-family: 'Fira Code', monospace;
        font-size: 0.82rem;
        line-height: 1.5;
        max-height: 500px;
        overflow-y: auto;
        white-space: pre-wrap;
        word-break: break-word;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">MASCRISS-AI</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-title">Multi-Agent Supply Chain Risk Intelligence &amp; Surveillance Sentinel</p>',
    unsafe_allow_html=True,
)


# ── Helper: capture stdout in real-time ──────────────────────────────
class StreamCapture(io.StringIO):
    """Wraps stdout to capture crew output while still printing it."""

    def __init__(self):
        super().__init__()
        self._original = sys.stdout
        self.lock = threading.Lock()

    def write(self, text):
        with self.lock:
            super().write(text)
            self._original.write(text)  # keep terminal output too

    def flush(self):
        self._original.flush()

    def get_text(self):
        with self.lock:
            return self.getvalue()


def run_crew(capture: StreamCapture, result_holder: dict):
    """Run the CrewAI pipeline in a background thread."""
    old_stdout = sys.stdout
    sys.stdout = capture
    try:
        from src.crew import SupplyChainCrew

        inputs = {"current_year": str(datetime.now().year)}
        result = SupplyChainCrew().crew().kickoff(inputs=inputs)
        result_holder["result"] = str(result)
        result_holder["done"] = True
    except Exception as exc:
        result_holder["error"] = str(exc)
        result_holder["done"] = True
    finally:
        sys.stdout = old_stdout


# ── Helper: send email ───────────────────────────────────────────────
def send_email(recipient: str, report_text: str) -> str:
    """Send the crisis report via Gmail SMTP. Returns status message."""
    sender = os.getenv("EMAIL", "")
    password = os.getenv("EMAIL_PASSWORD", "")

    if not sender or not password:
        return "❌ EMAIL or EMAIL_PASSWORD not set in .env"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🛡️ MASCRISS-AI Crisis Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    msg["From"] = sender
    msg["To"] = recipient

    # Plain-text part
    msg.attach(MIMEText(report_text, "plain"))
    # HTML part (wrap in <pre> to keep markdown formatting)
    html = f"<html><body><pre style='font-family:monospace;white-space:pre-wrap'>{report_text}</pre></body></html>"
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        return f"✅ Report emailed to **{recipient}**"
    except Exception as exc:
        return f"❌ Email failed: {exc}"


def add_shipment(
    shipment_id: str,
    supplier_name: str,
    origin_port: str,
    destination_port: str,
    status: str,
    eta: str,
) -> str:
    """Insert a shipment row into logistics.db."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS shipments (
                shipment_id      TEXT PRIMARY KEY,
                supplier_name    TEXT NOT NULL,
                origin_port      TEXT NOT NULL,
                destination_port TEXT NOT NULL,
                status           TEXT NOT NULL,
                eta              TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            INSERT INTO shipments (
                shipment_id, supplier_name, origin_port,
                destination_port, status, eta
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                shipment_id.strip(),
                supplier_name.strip(),
                origin_port.strip(),
                destination_port.strip(),
                status.strip(),
                eta.strip(),
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return f"❌ Shipment ID '{shipment_id}' already exists."
    except Exception as exc:
        return f"❌ Failed to add shipment: {exc}"
    finally:
        conn.close()
    return f"✅ Shipment '{shipment_id}' added to logistics.db"



# ── Sidebar: API Keys & Email ────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Run Control")
    max_iter_input = st.number_input(
        "Agent max iterations",
        min_value=1,
        max_value=20,
        value=int(os.getenv("AGENT_MAX_ITER", "3")),
        step=1,
        help="Each agent can think/tool-call up to this many iterations per run.",
    )
    os.environ["AGENT_MAX_ITER"] = str(int(max_iter_input))

    st.divider()
    st.header("📦 Add Shipment")
    with st.form("add_shipment_form", clear_on_submit=True):
        shipment_id = st.text_input("Shipment ID", placeholder="SH-013")
        supplier_name = st.text_input("Supplier Name", placeholder="Acme Components")
        origin_port = st.text_input("Origin Port", placeholder="Shanghai")
        destination_port = st.text_input("Destination Port", placeholder="Rotterdam")
        status = st.selectbox("Status", ["In Transit", "Loading", "Delayed"])
        eta = st.date_input("ETA")
        add_shipment_submit = st.form_submit_button("Add Shipment")

        if add_shipment_submit:
            if not all(
                [
                    shipment_id.strip(),
                    supplier_name.strip(),
                    origin_port.strip(),
                    destination_port.strip(),
                ]
            ):
                st.warning("Please fill all shipment fields.")
            else:
                result_msg = add_shipment(
                    shipment_id=shipment_id,
                    supplier_name=supplier_name,
                    origin_port=origin_port,
                    destination_port=destination_port,
                    status=status,
                    eta=eta.isoformat(),
                )
                if result_msg.startswith("✅"):
                    st.success(result_msg)
                else:
                    st.error(result_msg)

    st.divider()
    st.header("📧 Auto-Mail Settings")
    recipient_email = st.text_input(
        "Recipient email",
        placeholder="team@company.com",
        help="The crisis report will be emailed here after generation.",
        key="recipient_email_input",
    )
    auto_mail = st.checkbox("Auto-send report after generation", value=False)

    st.divider()
    st.header("🔑 Required API Keys")
    st.caption("If agent fails due to missing/invalid key, enter your key(s) below and retry.")

    def update_env_var(var, value):
        os.environ[var] = value
        # Optionally update .env file (warn user)
        env_path = Path(".env")
        if env_path.exists():
            try:
                set_key(str(env_path), var, value)
            except Exception:
                pass

    api_keys = {
        "OPENROUTER_API_KEY": "OpenRouter (LLM)",
        "SERPER_API_KEY": "Serper (News)",
        "OPENWEATHER_API_KEY": "OpenWeatherMap (Weather)",
        "SERPAPI_API_KEY": "SerpAPI (Maps)",
        "EMAIL": "Gmail address (auto-mail)",
        "EMAIL_PASSWORD": "Gmail app password",
    }
    for var, label in api_keys.items():
        val = st.text_input(
            f"{label}",
            value="",
            placeholder="Enter only if you want to override env/secrets",
            type="password",
            key=f"api_{var}",
        )
        if val:
            update_env_var(var, val)

    st.divider()
    st.caption("**Sender**: from sidebar or `.env` → `EMAIL`")
    st.caption("**LLM**: DeepSeek V3 via OpenRouter")
    st.caption("**Agents**: Sentinel → Analyst → Strategist")

# ── Main area ────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    run_button = st.button("🚀 Run Crisis Detection Pipeline", use_container_width=True, type="primary")

# ── Session state init ───────────────────────────────────────────────
if "report" not in st.session_state:
    st.session_state.report = None

# ── Run pipeline ─────────────────────────────────────────────────────
if run_button:
    st.session_state.report = None

    capture = StreamCapture()
    result_holder = {"done": False}
    thread = threading.Thread(target=run_crew, args=(capture, result_holder), daemon=True)

    stream_container = st.empty()
    status_bar = st.status("🔄 Running agents…", expanded=True)

    thread.start()

    # ── Streaming loop ───────────────────────────────────────────────
    while not result_holder.get("done"):
        current_text = capture.get_text()
        if current_text:
            status_bar.markdown(
                f'<div class="stream-box">{current_text[-8000:]}</div>',
                unsafe_allow_html=True,
            )
        time.sleep(0.5)

    thread.join()

    # ── Final update ─────────────────────────────────────────────────
    if "error" in result_holder:
        status_bar.update(label="❌ Pipeline failed", state="error", expanded=True)
        err = result_holder["error"]
        st.error(err)
        # If error looks like missing/invalid API key, show extra help
        api_hint = [
            "api key",
            "API key",
            "Invalid key",
            "No API key",
            "401",
            "403",
            "Unauthorized",
        ]
        if any(hint in err for hint in api_hint):
            st.warning("Check your API keys in the sidebar and retry.")
    else:
        status_bar.update(label="✅ Pipeline complete!", state="complete", expanded=False)

        # Read generated report from file
        report_path = Path("output/crisis_report.md")
        if report_path.exists():
            report_text = report_path.read_text(encoding="utf-8")
        else:
            report_text = result_holder.get("result", "No output captured.")

        st.session_state.report = report_text

# ── Display report ───────────────────────────────────────────────────
if st.session_state.report:
    st.divider()
    st.subheader("📋 Crisis Response Report")

    tab_rendered, tab_raw = st.tabs(["Rendered", "Raw Markdown"])
    with tab_rendered:
        st.markdown(st.session_state.report)
    with tab_raw:
        st.code(st.session_state.report, language="markdown")

    # ── Download button ──────────────────────────────────────────────
    st.download_button(
        label="⬇️ Download Report",
        data=st.session_state.report,
        file_name=f"crisis_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
    )

    # ── Auto-mail ────────────────────────────────────────────────────
    if auto_mail and recipient_email:
        with st.spinner("Sending email…"):
            mail_status = send_email(recipient_email, st.session_state.report)
        st.info(mail_status)
    elif auto_mail and not recipient_email:
        st.warning("Enter a recipient email in the sidebar to enable auto-mail.")

    # ── Manual email send ────────────────────────────────────────────
    if not auto_mail:
        col_a, col_b = st.columns([3, 1])
        with col_a:
            manual_email = st.text_input(
                "Send report to email",
                value=recipient_email,
                key="manual_email_input",
            )
        with col_b:
            st.write("")  # spacer
            st.write("")
            if st.button("📤 Send Email"):
                if manual_email:
                    with st.spinner("Sending…"):
                        mail_status = send_email(manual_email, st.session_state.report)
                    st.info(mail_status)
                else:
                    st.warning("Enter an email address.")
