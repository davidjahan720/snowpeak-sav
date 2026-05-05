"""
SNOWPEAK — Agent SAV Télésièges
Chatbot Streamlit qui interroge Mistral à partir d'une base de tickets SAV
(Google Sheet public ou fichier local .ods / .xlsx / .csv).
"""

import os
import re
import time
from io import StringIO

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from mistralai.client import Mistral

# ────────────────────────────────────────────────────────────────
# Configuration & variables d'environnement
# ────────────────────────────────────────────────────────────────
load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
SHEET_URL_DEFAULT = os.getenv("SHEET_URL", "")
SHEET_GID_DEFAULT = os.getenv("SHEET_GID", "0")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")

TOP_K_TICKETS = 5

# Stop-words français pour la recherche par mots-clés
STOP_WORDS_FR = {
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "ou",
    "à", "en", "dans", "sur", "pour", "par", "avec", "est", "sont",
    "ce", "cette", "ces", "il", "elle", "ils", "elles", "on", "se",
    "que", "qui", "quoi", "dont", "où", "mais", "donc", "car", "ni",
    "au", "aux", "son", "sa", "ses", "mon", "ma", "mes", "ton", "ta",
    "pas", "plus", "moins", "très", "trop", "aussi", "comme",
}

# ────────────────────────────────────────────────────────────────
# Prompt système (français, structure imposée)
# ────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es l'agent SAV expert de SNOWPEAK, exploitant de remontées mécaniques.
Tu aides les techniciens à diagnostiquer et réparer des pannes sur télésièges.

Catégories d'équipement courantes : Variateur, Moteur, Écran/IHM, Automate, Capteur,
Hydraulique, Câblage.
Stations exploitées : Les Aigles, Col du Sapin, La Crête Blanche, Pic de l'Ours,
Les Marmottes, Mont Serein.

Tu réponds TOUJOURS en français et TOUJOURS dans cette structure exacte :

📋 DIAGNOSTIC PROBABLE
- Cause la plus probable, avec citation explicite des tickets sources sous la forme T-XXXXXX.
- Niveau de confiance : Élevé / Moyen / Faible (justifié).

🔧 VÉRIFICATIONS PAS-À-PAS
- Liste ordonnée des contrôles à effectuer.
- Donne TOUJOURS des valeurs numériques précises et leurs unités :
  intensité (A), pression (bar), température (°C), jeu (mm), isolement (MOhm),
  vibration (mm/s), tension (V), couple (Nm), etc.

✅ PROCÉDURE DE RÉPARATION
- Actions ordonnées, pièces de rechange (référence si connue), paramètres à régler,
  tests de validation après réparation, et consignes de sécurité (consignation,
  EPI, périmètre, redémarrage).

Règles strictes :
- Cite TOUJOURS les T-XXXXXX qui appuient ton raisonnement.
- Si aucun précédent clair n'existe dans les tickets fournis, dis-le honnêtement
  et propose une démarche de diagnostic générique.
- N'invente jamais de référence de ticket : utilise seulement celles présentes dans
  les tickets fournis."""


# ────────────────────────────────────────────────────────────────
# Chargement de la source de tickets
#   - URL Google Sheets publique → export CSV
#   - chemin local (.ods, .xlsx, .csv) → lecture directe via pandas
# ────────────────────────────────────────────────────────────────
def sheet_url_to_csv(sheet_url: str, gid: str = "0") -> str | None:
    """Convertit une URL de Google Sheet partagé en URL d'export CSV.

    Extrait l'ID du sheet et auto-détecte le `gid` depuis l'URL si présent
    dans le fragment `#gid=...` ou la query `?gid=...`. L'argument `gid`
    sert de fallback uniquement.
    """
    if not sheet_url:
        return None
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not match:
        return None
    sheet_id = match.group(1)

    # Auto-détection du gid dans l'URL (fragment `#gid=...` ou query `?gid=...`)
    gid_match = re.search(r"[#&?]gid=(\d+)", sheet_url)
    effective_gid = gid_match.group(1) if gid_match else (gid or "0")

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={effective_gid}"


def _looks_like_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


@st.cache_data(ttl=300)
def load_tickets(source: str, gid: str) -> pd.DataFrame:
    """Charge la source en DataFrame (cache 5 min).

    - URL Google Sheets → export CSV via requests.
    - Chemin local .ods / .xlsx → pd.read_excel.
    - Chemin local .csv → pd.read_csv.
    """
    if not source:
        return pd.DataFrame()

    if _looks_like_url(source):
        csv_url = sheet_url_to_csv(source, gid)
        if not csv_url:
            raise ValueError("URL non reconnue comme Google Sheet (manque /spreadsheets/d/...).")
        response = requests.get(csv_url, timeout=15)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        return df.fillna("")

    # Chemin local
    path = source.strip().strip('"').strip("'")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext == ".ods":
        df = pd.read_excel(path, engine="odf")
    elif ext in (".xlsx", ".xlsm", ".xls"):
        df = pd.read_excel(path)
    elif ext == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(f"Format non supporté : {ext} (utilise .ods, .xlsx ou .csv)")
    return df.fillna("")


# ────────────────────────────────────────────────────────────────
# Recherche par mots-clés (token matching)
# ────────────────────────────────────────────────────────────────
def tokenize(text: str) -> list[str]:
    """Découpe en tokens, en préservant les codes type 'err-f12' ou 'f-001'."""
    text = text.lower()
    tokens = re.findall(r"[a-zà-ÿ0-9]+(?:-[a-zà-ÿ0-9]+)*", text)
    return [t for t in tokens if len(t) >= 3 and t not in STOP_WORDS_FR]


def search_tickets(df: pd.DataFrame, query: str, top_k: int = TOP_K_TICKETS) -> pd.DataFrame:
    """Score chaque ligne par nombre de tokens présents et renvoie le top_k."""
    if df.empty:
        return df
    tokens = tokenize(query)
    if not tokens:
        return df.head(0)

    haystack = df.astype(str).agg(" ".join, axis=1).str.lower()

    def score_row(row_text: str) -> int:
        return sum(1 for tok in tokens if tok in row_text)

    scores = haystack.apply(score_row)
    df_scored = df.assign(_score=scores)
    df_scored = df_scored[df_scored["_score"] > 0]
    df_scored = df_scored.sort_values("_score", ascending=False).head(top_k)
    return df_scored.drop(columns=["_score"])


def format_tickets_for_llm(df: pd.DataFrame) -> str:
    """Mise en forme lisible des tickets pour le LLM."""
    if df.empty:
        return "(Aucun ticket pertinent trouvé dans la base.)"
    blocks = []
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        lines = [f"--- Ticket #{i} ---"]
        for col, val in row.items():
            if str(val).strip():
                lines.append(f"{col}: {val}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


# ────────────────────────────────────────────────────────────────
# Appel Mistral
# ────────────────────────────────────────────────────────────────
def build_user_message(query: str, tickets_text: str) -> str:
    return (
        f"Question du technicien : {query}\n\n"
        f"---\nTickets SAV pertinents :\n\n{tickets_text}\n---\n\n"
        f"Donne ton diagnostic en respectant strictement la structure imposée "
        f"(📋 DIAGNOSTIC PROBABLE / 🔧 VÉRIFICATIONS PAS-À-PAS / ✅ PROCÉDURE DE RÉPARATION)."
    )


def call_mistral(query: str, tickets_text: str) -> tuple[str, float]:
    """Appelle Mistral et retourne (réponse, durée en secondes)."""
    if not MISTRAL_API_KEY:
        return "❌ MISTRAL_API_KEY manquante dans .env.", 0.0
    t0 = time.perf_counter()
    try:
        client = Mistral(api_key=MISTRAL_API_KEY)
        resp = client.chat.complete(
            model=MISTRAL_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_message(query, tickets_text)},
            ],
        )
        return resp.choices[0].message.content or "", time.perf_counter() - t0
    except Exception as e:  # noqa: BLE001
        return f"❌ Erreur Mistral : {e}", time.perf_counter() - t0


# ────────────────────────────────────────────────────────────────
# Interface Streamlit
# ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="SNOWPEAK SAV", layout="wide", page_icon="🚡")
st.title("🚡 SNOWPEAK — Agent SAV Télésièges")
st.caption("Diagnostic de pannes assisté par IA à partir des tickets SAV.")

# Sidebar : configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    sheet_url = st.text_input(
        "URL Google Sheet ou chemin local (.ods / .xlsx / .csv)",
        value=SHEET_URL_DEFAULT,
        help="URL d'un Google Sheet public OU chemin absolu vers un fichier local.",
    )
    sheet_gid = st.text_input("GID de l'onglet (Google Sheets seulement)", value=SHEET_GID_DEFAULT)

    st.markdown("**Clé API**")
    st.markdown(f"- Mistral : {'✅' if MISTRAL_API_KEY else '❌'}")

    if st.button("🔄 Rafraîchir les tickets"):
        load_tickets.clear()
        st.success("Cache vidé.")

    df_tickets = pd.DataFrame()
    if sheet_url:
        try:
            df_tickets = load_tickets(sheet_url, sheet_gid)
            st.metric("Tickets chargés", len(df_tickets))
            with st.expander("Colonnes détectées"):
                st.write(list(df_tickets.columns))
        except Exception as e:  # noqa: BLE001
            st.error(f"Impossible de charger les tickets : {e}")

# Historique des échanges
if "history" not in st.session_state:
    st.session_state.history = []

# Affichage de l'historique
for entry in st.session_state.history:
    st.markdown(f"### 🧑‍🔧 {entry['query']}")
    with st.expander(f"📚 Tickets utilisés ({len(entry['tickets'])})"):
        if entry["tickets"].empty:
            st.info("Aucun ticket pertinent trouvé.")
        else:
            st.dataframe(entry["tickets"], use_container_width=True)
    st.markdown(f"#### 🔵 Mistral · `{MISTRAL_MODEL}` · ⏱ {entry['t_mistral']:.1f}s")
    st.markdown(entry["mistral"])
    st.divider()

# Input chat
query = st.chat_input(
    "Décris la panne, le code erreur, la station... "
    "(ex: 'Err-F12 variateur ACS880 Les Aigles')"
)

if query:
    if df_tickets.empty:
        st.error("Aucun ticket chargé. Vérifie la source dans la sidebar (URL ou chemin local).")
    else:
        with st.spinner("Recherche dans les tickets et appel Mistral…"):
            tickets = search_tickets(df_tickets, query)
            tickets_text = format_tickets_for_llm(tickets)
            response, duration = call_mistral(query, tickets_text)

        st.session_state.history.append({
            "query": query,
            "tickets": tickets,
            "mistral": response,
            "t_mistral": duration,
        })
        st.rerun()
