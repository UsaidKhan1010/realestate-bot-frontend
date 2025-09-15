@'
# frontend.py — final, robust dark/chat UI for AI Realtor Assistant
import streamlit as st
import requests
from requests.exceptions import RequestException
import html

# ========== CONFIG ==========
BACKEND_URL = "https://realestate-bot-backend.onrender.com"
CHAT_ENDPOINT = f"{BACKEND_URL}/chat"
LEAD_ENDPOINT = f"{BACKEND_URL}/lead"

# ========== safe rerun helper ==========
def safe_rerun():
    rerun_fn = getattr(st, "experimental_rerun", None) or getattr(st, "rerun", None)
    if callable(rerun_fn):
        try:
            rerun_fn()
        except Exception:
            pass

# ========== page setup ==========
st.set_page_config(page_title="AI Realtor Assistant", page_icon="🏠", layout="wide")

# ========== styles ==========
st.markdown(
    """
    <style>
    .stApp { background-color: #071027; color: #e6eef6; }
    .title { font-size:34px; color:#7dd3fc; text-shadow:0 0 10px #0891b2; }
    .user-bubble { background: linear-gradient(135deg,#0ea5e9,#2563eb); color:white; padding:12px; border-radius:12px; margin:8px 0; max-width:85%; margin-left:auto; box-shadow:0 6px 18px rgba(38,132,255,0.12); }
    .bot-bubble { background: linear-gradient(135deg,#0b1220,#1e293b); color:#e6eef6; padding:12px; border-radius:12px; margin:8px 0; max-width:85%; box-shadow:0 6px 18px rgba(14,165,233,0.08); }
    .quick { display:inline-block; background:#07143a; border:1px solid #2563eb; color:#c7f9ff; padding:8px 12px; border-radius:8px; margin:4px; cursor:pointer; }
    .meta { color:#94a3b8; font-size:12px; margin-top:6px; }
    .typing { color:#94a3b8; font-style:italic; margin:6px 0; }
    @keyframes fadeIn { from {opacity: 0; transform: translateY(6px);} to {opacity: 1; transform: translateY(0);} }
    .user-bubble, .bot-bubble { animation: fadeIn 0.35s ease-in-out; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div style='text-align:center'><div class='title'>🤖 AI Realtor Assistant</div><div style='color:#94a3b8'>Instant answers · Tour booking · Lead capture</div></div>", unsafe_allow_html=True)

# ========== session state ==========
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "awaiting_lead" not in st.session_state:
    st.session_state["awaiting_lead"] = False
if "lead_count" not in st.session_state:
    st.session_state["lead_count"] = 0
if "last_error" not in st.session_state:
    st.session_state["last_error"] = None
if "is_typing" not in st.session_state:
    st.session_state["is_typing"] = False

# ========== layout ==========
chat_col, side_col = st.columns([4,1])

with side_col:
    st.markdown("### ⚙ Bot Dashboard")
    st.markdown(f"**Backend:** {BACKEND_URL.split('//')[-1]}")
    st.markdown(f"**Leads captured:** {st.session_state['lead_count']}")
    st.markdown("---")
    st.markdown("### 💡 Quick asks")
    if st.button("Show me 2BHK under $500k"):
        st.session_state["messages"].append({"role":"user","content":"Show me 2BHK apartments under $500k"})
        safe_rerun()
    if st.button("Book a tour tomorrow 5pm"):
        st.session_state["messages"].append({"role":"user","content":"Book a tour for tomorrow at 5PM"})
        safe_rerun()
    st.markdown("---")
    st.markdown("### ❓ What to ask")
    st.markdown("- Show me 2BHK apartments under $500k")
    st.markdown("- Book me a tour tomorrow at 5PM")
    st.markdown("- What’s the home buying process?")

with chat_col:
    for msg in st.session_state["messages"]:
        content = html.escape(msg["content"]).replace("\n","<br>")
        if msg["role"] == "user":
            st.markdown(f"<div class='user-bubble'>{content}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-bubble'>{content}</div>", unsafe_allow_html=True)

    if st.session_state["is_typing"]:
        st.markdown("<div class='typing'>Aiden is typing...</div>", unsafe_allow_html=True)

    if st.session_state["last_error"]:
        st.markdown(f"<div class='meta'>Last error: {st.session_state['last_error']}</div>", unsafe_allow_html=True)

    prompt = st.chat_input("Type your message...")

    if prompt:
        st.session_state["messages"].append({"role":"user","content":prompt})

        if st.session_state["awaiting_lead"]:
            parts = [p.strip() for p in prompt.split(",")]
            try:
                if len(parts) >= 3:
                    name = parts[0]; email = parts[1]; phone = parts[2]
                    budget = parts[3] if len(parts) >= 4 else "N/A"
                    payload = {"name": name, "email": email, "phone": phone, "budget": budget}
                    try:
                        resp = requests.post(LEAD_ENDPOINT, json=payload, timeout=10)
                        if resp.status_code == 200:
                            bot_reply = "✅ Thanks — I’ve saved your info. An agent will contact you soon."
                            st.session_state["lead_count"] += 1
                            st.session_state["awaiting_lead"] = False
                        else:
                            bot_reply = f"⚠️ Could not save lead (status {resp.status_code}): {resp.text}"
                            st.session_state["last_error"] = bot_reply
                    except RequestException as e:
                        bot_reply = f"Error contacting lead endpoint: {e}"
                        st.session_state["last_error"] = str(e)
                else:
                    bot_reply = "Please provide: Name, Email, Phone, Budget(optional). Example: John Doe, john@mail.com, +123456789, 500000"
            except Exception as e:
                bot_reply = f"Invalid input format: {e}"

            st.session_state["messages"].append({"role":"assistant","content":bot_reply})
            safe_rerun()
        else:
            history_payload = st.session_state["messages"][-12:]
            payload = {"message": prompt, "history": history_payload}

            st.session_state["is_typing"] = True
            safe_rerun()

            bot_reply = "⚠️ No response (network)."
            try:
                resp = requests.post(CHAT_ENDPOINT, json=payload, timeout=12)
                if resp.status_code == 200:
                    data = resp.json()
                    bot_reply = data.get("response", "No response from backend.")

                    if isinstance(data, dict) and "lead_capture" in data:
                        lc = data["lead_capture"]
                        try:
                            lead_resp = requests.post(LEAD_ENDPOINT, json=lc, timeout=8)
                            if lead_resp.status_code == 200:
                                bot_reply += "\n\n✅ I saved your contact — an agent will reach out soon."
                                st.session_state["lead_count"] += 1
                                st.session_state["awaiting_lead"] = False
                            else:
                                bot_reply += f"\n\n⚠️ Could not save contact (status {lead_resp.status_code})."
                        except Exception as e:
                            bot_reply += f"\n\n⚠️ Failed saving contact: {e}"
                    else:
                        if any(phrase in bot_reply.lower() for phrase in ["save your contact", "can i get your", "please provide: name", "please provide"]):
                            bot_reply += "\n\n💡 Please provide: Name, Email, Phone, Budget(optional)"
                            st.session_state["awaiting_lead"] = True

                    st.session_state["last_error"] = None
                else:
                    bot_reply = f"Backend error (status {resp.status_code}): {resp.text}"
                    st.session_state["last_error"] = bot_reply

            except requests.exceptions.ReadTimeout:
                bot_reply = "⚠️ Request timed out. Try again — the backend may be busy."
                st.session_state["last_error"] = "Request timed out"
            except requests.exceptions.ConnectionError as e:
                bot_reply = f"⚠️ Connection error: {e}"
                st.session_state["last_error"] = str(e)
            except Exception as e:
                bot_reply = f"⚠️ Unexpected error: {e}"
                st.session_state["last_error"] = str(e)
            finally:
                st.session_state["is_typing"] = False

            st.session_state["messages"].append({"role":"assistant","content":bot_reply})
            safe_rerun()

st.markdown("---")
st.markdown("<div style='color:#94a3b8;font-size:12px'>Tip: To save contact quickly type: Name, email@example.com, +1234567890, 450000</div>", unsafe_allow_html=True)
'@ | Set-Content .\frontend.py -Encoding utf8


