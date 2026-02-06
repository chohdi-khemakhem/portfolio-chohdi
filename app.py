from pathlib import Path
from datetime import date
import base64
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from loan_engine import (
    build_schedule,
    TYPE_IN_FINE,
    TYPE_CONSTANT_AMORTIZATION,
    TYPE_SPECIFIC_REPAYMENT,
    BASE_360,
    BASE_MENSUELLE_12,
)

# ============================
# CONFIG
# ============================
st.set_page_config(
    page_title="Chohdi Khemakhem | Portfolio",
    page_icon=" ",
    layout="wide",
)

ROOT = Path("assets")
CV_PATH = ROOT / "cv" / "CV_Chohdi_Khemakhem.pdf"

CREDITTIC_DIR = ROOT / "creditTic"
CCI_DIR = ROOT / "cci_cheques_impayes"
SM_DIR = ROOT / "salle_marche"

CREDITTIC_LINK = ""  # optionnel: lien externe si tu n'as pas de mp4

# ============================
# STYLE (Corporate, no emojis)
# ============================
st.markdown(
    """
<style>
.block-container { max-width: 1180px; padding-top: 1.6rem; padding-bottom: 2.2rem; }

:root{
  --card-bg: rgba(255,255,255,0.04);
  --card-border: rgba(255,255,255,0.10);
  --muted: rgba(255,255,255,0.72);
}

.hero-title{
  font-size: 46px;
  font-weight: 850;
  line-height: 1.06;
  margin: 0;
}
.hero-subtitle{
  font-size: 16px;
  color: var(--muted);
  margin-top: 10px;
  margin-bottom: 0px;
}

.section-title{
  font-size: 18px;
  font-weight: 750;
  margin: 0 0 8px 0;
}

.card{
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 16px;
  padding: 18px 18px;
  box-shadow: 0 10px 26px rgba(0,0,0,0.08);
}

.kpi{
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 12px 12px;
}

.small{
  font-size: 13px;
  color: var(--muted);
}

.hr{
  height: 1px;
  background: rgba(255,255,255,0.10);
  margin: 18px 0;
  border: none;
}

a { text-decoration: none; }
</style>
""",
    unsafe_allow_html=True,
)

# ============================
# HELPERS
# ============================
def exists(p: Path) -> bool:
    try:
        return p.exists()
    except Exception:
        return False


def first_existing(*paths: Path) -> Path | None:
    for p in paths:
        if exists(p):
            return p
    return None


def collect_images(folder: Path, prefixes, exts=("png", "jpg", "jpeg", "webp")):
    """
    Collect images inside 'folder' whose name starts with one of 'prefixes'
    Example: prefixes=["creditTic_", "cci_", "sm_"]
    """
    if not exists(folder):
        return []
    files = []
    for pref in prefixes:
        for ext in exts:
            files.extend(sorted(folder.glob(f"{pref}*.{ext}")))
    # remove duplicates while keeping order
    seen, uniq = set(), []
    for f in files:
        k = f.as_posix()
        if k not in seen:
            uniq.append(f)
            seen.add(k)
    return uniq


def render_gallery(images, per_row=3, limit=None):
    if not images:
        st.caption("Aucune image détectée.")
        return
    if limit is not None:
        images = images[:limit]
    cols = st.columns(per_row)
    for i, p in enumerate(images):
        cols[i % per_row].image(str(p), width="stretch")


def render_download_cv():
    if exists(CV_PATH):
        with open(CV_PATH, "rb") as f:
            st.download_button(
                "Télécharger le CV",
                data=f,
                file_name="CV_Chohdi_Khemakhem.pdf",
                mime="application/pdf",
            )
    else:
        st.warning("CV manquant : assets/cv/CV_Chohdi_Khemakhem.pdf")

st.markdown(
    """
<style>
.sidebar-profile {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: 18px;
}

.profile-photo {
  width: 110px;
  height: 110px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid rgba(255,255,255,0.18);
  box-shadow: 0 8px 22px rgba(0,0,0,0.25);
  margin-bottom: 10px;
}

.sidebar-name {
  font-size: 18px;
  font-weight: 800;
  margin-top: 6px;
}

.sidebar-role {
  font-size: 12px;
  opacity: 0.75;
  margin-top: 4px;
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================
# SIDEBAR (PRO)
# ============================
st.markdown(
    """
<style>
.nav-card{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.04);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 8px;
}

.nav-card:hover{
  background: rgba(255,255,255,0.08);
}

.nav-active{
  background: rgba(255,255,255,0.12);
  border-color: rgba(255,255,255,0.25);
}
.link-card{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.04);
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  color: inherit;
}
.link-card:hover{
  background: rgba(255,255,255,0.08);
}
</style>
""",
    unsafe_allow_html=True,
)


st.markdown(
    """
<style>
.profile-photo-wrapper{
  display: flex;
  justify-content: center;
  margin-bottom: 14px;
}

.profile-photo{
  width: 96px;
  height: 96px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid rgba(255,255,255,0.18);
  box-shadow: 0 8px 22px rgba(0,0,0,0.25);
}
</style>
""",
    unsafe_allow_html=True,
)
def image_to_base64(path: str) -> tuple[str, str]:
    """
    Returns (base64_string, mime_type).
    Supports jpg/jpeg/png/webp.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Image introuvable: {p.resolve()}")

    ext = p.suffix.lower().replace(".", "")
    mime = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }.get(ext, "image/jpeg")

    data = base64.b64encode(p.read_bytes()).decode("utf-8")
    return data, mime

with st.sidebar:
    st.markdown(
        """
<style>
/* Sidebar layout */
.sidebar-card{
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 16px;
  padding: 16px 14px;
  margin-bottom: 14px;
}

.sidebar-name{
  font-size: 18px;
  font-weight: 800;
  line-height: 1.1;
  margin: 0;
}

.sidebar-role{
  font-size: 12px;
  opacity: 0.75;
  margin-top: 6px;
}

.sidebar-divider{
  height: 1px;
  background: rgba(255,255,255,0.10);
  margin: 14px 0;
  border: none;
}

.sidebar-links{
  display: grid;
  gap: 10px;
}

.sidebar-link{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 10px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.04);
}

.sidebar-link span{
  font-size: 13px;
  font-weight: 600;
}
</style>
""",
        unsafe_allow_html=True,
    )

    img_base64 = image_to_base64("assets/profile.jpg")


    # Texte centré
    
    try:
        img_base64, mime = image_to_base64("assets/profile.jpg")  # <-- adapte si ton fichier est .png
        st.markdown(
            f"""
<div class="sidebar-profile">
  <img src="data:{mime};base64,{img_base64}" class="profile-photo"/>
  <div class="sidebar-name">Chohdi Khemakhem</div>
  <div class="sidebar-role">Ingénieur en Informatique Financière</div>
  <div class="sidebar-role">FinTech • Systèmes Bancaires • Risque & Conformité</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown(
    """
<style>
/* Sidebar radio -> modern nav */
section[data-testid="stSidebar"] div[role="radiogroup"]{
  gap: 10px;
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label{
  width: 100%;
  margin: 0;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.04);
  transition: all 0.15s ease;
}

/* remove default circle spacing */
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div{
  gap: 10px;
}

/* text style */
section[data-testid="stSidebar"] div[role="radiogroup"] > label p{
  font-size: 13px !important;
  font-weight: 650 !important;
  margin: 0 !important;
}

/* hover */
section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover{
  background: rgba(255,255,255,0.08);
  border-color: rgba(255,255,255,0.18);
}

/* selected state */
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked){
  background: rgba(255,255,255,0.12);
  border-color: rgba(255,255,255,0.28);
  box-shadow: 0 10px 20px rgba(0,0,0,0.12);
}

/* hide the native radio dot */
section[data-testid="stSidebar"] div[role="radiogroup"] input{
  display: none;
}
</style>
""",
    unsafe_allow_html=True,
)
    

    except Exception as e:
        st.error(str(e))
        st.caption("Vérifie le nom exact du fichier : assets/profile.jpg (ou profile.png).")

    with st.sidebar:
      st.markdown("### Navigation")

      section = st.radio(
          "",
          ["Accueil", "Projets", "Cas pratique", "Compétences", "Contact"],
          label_visibility="collapsed",
      )
    
              

          
          
          
          

    
    st.markdown(
        """
<div class="sidebar-card">
  <div class="sidebar-role">Liens</div>
  <div class="sidebar-divider"></div>

  <a class="link-card" href="https://www.linkedin.com/in/chohdi-khemakhem-a36449279/" target="_blank">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M4 4h16v16H4z" stroke="currentColor" stroke-width="2"/>
      <path d="M8 11v5" stroke="currentColor" stroke-width="2"/>
      <path d="M8 8v.5" stroke="currentColor" stroke-width="2"/>
      <path d="M12 11v5" stroke="currentColor" stroke-width="2"/>
      <path d="M12 11c0-1.2 1-2.2 2.2-2.2S16.4 9.8 16.4 11v5" stroke="currentColor" stroke-width="2"/>
    </svg>
    LinkedIn
  </a>
</div>
""",
        unsafe_allow_html=True,
    )

    # --- Documents ---
    st.markdown(
        """
<div class="sidebar-card">
  <div class="sidebar-role">Documents</div>
  <div class="sidebar-divider"></div>
</div>
""",
        unsafe_allow_html=True,
    )

    if exists(CV_PATH):
        with open(CV_PATH, "rb") as f:
            st.download_button(
                "CV_Chohdi_Khemakhem.pdf",
                data=f,
                file_name="CV_Chohdi_Khemakhem.pdf",
                mime="application/pdf",
            )
    else:
        st.caption("CV introuvable : assets/cv/CV_Chohdi_Khemakhem.pdf")

# ============================
# ACCUEIL
# ============================
if section == "Accueil":
    st.markdown("""
<style>
.hero {
    background: white;
    padding: 3rem;
    border-radius: 20px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 10px 30px rgba(0,0,0,0.06);
}

.hero-name {
    font-size: 44px;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 0.4rem;
}

.hero-subtitle {
    font-size: 18px;
    color: #334155;
    margin-bottom: 1.2rem;
}

.hero-desc {
    font-size: 16px;
    color: #475569;
    max-width: 720px;
    line-height: 1.6;
}

.badges span {
    display: inline-block;
    background: #f1f5f9;
    color: #0f172a;
    padding: 6px 14px;
    border-radius: 999px;
    font-size: 13px;
    margin-right: 8px;
    margin-bottom: 14px;
    border: 1px solid #e2e8f0;
}
</style>
""", unsafe_allow_html=True)



    st.markdown("""
<div class="hero">

  <div class="badges">
    <span>FinTech</span>
    <span>Applications Bancaires</span>
    <span>Risque & Garanties</span>
  </div>

  <div class="hero-name">Chohdi Khemakhem</div>

  <div class="hero-subtitle">
    Ingénieur en Informatique Financière —
    Java / Spring Boot • Angular • Python • KPIs & Tableaux de bord
  </div>

  <div class="hero-desc">
    Je conçois des applications bancaires sécurisées et orientées métier
    (crédit, gestion des garanties, suivi post-attribution),
    avec une approche centrée produit, risque et performance opérationnelle.
  </div>

</div>
""", unsafe_allow_html=True)





    st.write("")
    st.markdown("<hr style='opacity:0.05'/>", unsafe_allow_html=True)


    # Metrics
    st.markdown(
        """
    <style>
    /* Force smaller metrics (Streamlit) */
    div[data-testid="stMetric"] * { 
    font-size: inherit !important;
    }

    div[data-testid="stMetric"] {
    padding: 10px 10px !important;
    }

    div[data-testid="stMetricLabel"] {
    font-size: 12px !important;
    opacity: 0.75 !important;
    margin-bottom: 4px !important;
    }

    div[data-testid="stMetricValue"] {
    font-size: 18px !important;
    font-weight: 650 !important;
    line-height: 1.15 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    }

    /* Sometimes Streamlit wraps the value in p/span */
    div[data-testid="stMetricValue"] p,
    div[data-testid="stMetricValue"] span {
    font-size: 18px !important;
    font-weight: 650 !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Focus", "Crédit & Garanties")

    with c2:
        st.metric("Stack", "Spring Boot / Angular")

    with c3:
        st.metric("Data", "KPIs & Dashboards")

    with c4:
        st.metric("Sécurité", "SSO / MFA")

    st.write("")
    st.markdown("<hr/>", unsafe_allow_html=True)

    # Main content
    left, right = st.columns([1.2, 0.8], gap="large")

    with left:
        st.subheader("🎯 Résumé")
        st.write(
            "Ingénieur FinTech avec expérience pratique sur des plateformes bancaires : "
            "digitalisation du cycle de crédit, calculs financiers (LTV, DTI, annuités), "
            "gestion des garanties/collatéraux, dashboards, génération de documents et sécurité."
        )

        st.subheader("✅ Contenu du portfolio")
        st.write(
            "- Projets bancaires : CréditTic, Centrale des Chèques Impayés, Salle de Marché (captures et démonstrations).\n"
            "- Démo technique : moteur d’échéancier de crédit (plusieurs modes de remboursement) avec export des résultats.\n"
            "- Synthèse compétences : développement, sécurité, KPIs et logique métier bancaire."
        )


    with right:
        st.subheader("📍 Infos")
        st.markdown(
            """
            <div class="card">
                <b>Localisation :</b> Tunis, Tunisie<br/>
                <b>Email :</b> chohdi.kema@gmail.com<br/>
                <b>Tél :</b> +216 50 513 004<br/>
            </div>
            """,
            unsafe_allow_html=True
        )



# ============================
# PROJETS
# ============================
if section == "Projets":
    st.markdown("## Projets")

    tabs = st.tabs(["CréditTic", "Salle de Marché", "Centrale des Chèques Impayés", "DevOps CI/CD & Monitoring"])

    # ---- CréditTic ----
    with tabs[0]:
        st.markdown("""
<div class="card">

<h3>CréditTic — Digitalisation du cycle complet de crédit</h3>

<ul>
  <li>Architecture n-tiers : <b>Spring Boot</b> • <b>Angular</b> • <b>PostgreSQL</b></li>
  <li>Authentification : <b>Keycloak</b> (SSO / MFA)</li>
  <li>Modules : simulation de prêt (<b>LTV</b>, <b>DTI</b>, annuités), gestion des garanties, génération de documents, dashboards</li>

  <li><b>IA intégrée (LLM)</b> : utilisation de <b>Llama 3 8B</b> via <b>LM Studio</b> pour assister les processus de crédit :</li>
  <ul>
    <li>Génération d’une <b>offre de crédit</b> (résumé + proposition) à partir des données client</li>
    <li><b>Optimisation / recommandation</b> de garanties selon le profil et les règles métier</li>
    <li><b>Remplissage automatique</b> de champs (pré-saisie) à partir d’un paragraphe descriptif fourni par l’agent</li>
    <li>Support à la <b>simulation</b> et explication des résultats (LTV/DTI/échéancier) en langage naturel</li>
  </ul>

  <li>Objectif : réduire les délais de traitement, améliorer la traçabilité et l’expérience client</li>
</ul>

</div>
""", unsafe_allow_html=True)




        demo_video = first_existing(CREDITTIC_DIR / "creditTic_demo.mp4")
        if demo_video:
            st.markdown("### Démonstration")
            st.video(str(demo_video))
        elif CREDITTIC_LINK.strip():
            st.markdown("### Démonstration")
            st.video(CREDITTIC_LINK.strip())
        else:
            st.caption("Ajoute assets/creditTic/creditTic_demo.mp4 (optionnel) ou renseigne un lien externe dans CREDITTIC_LINK.")

        arch = first_existing(CREDITTIC_DIR / "creditTic_architecture.png")
        if arch:
            st.write("")
            st.markdown("### Architecture")
            st.markdown("""CréditTic est une plateforme de digitalisation du crédit conçue pour automatiser et sécuriser l’ensemble du cycle de traitement des demandes. Elle combine une architecture web n-tiers moderne, des services bancaires robustes et des capacités d’intelligence artificielle afin d’améliorer la simulation des prêts, l’optimisation des garanties et la génération des offres de crédit, tout en respectant les exigences de sécurité et de conformité du secteur bancaire.""")
            st.image(str(arch), width="stretch")

        st.write("")
        st.markdown("### Captures d'écran")
        credit_imgs = collect_images(CREDITTIC_DIR, prefixes=["creditTic_"])
        render_gallery(credit_imgs, per_row=3, limit=18)

    # ---- CCI ----
    with tabs[2]:
        st.markdown("""
<div class="card">

<h3>Centrale des Chèques Impayés — BNA</h3>

<ul>
<li>Modélisation des processus de gestion internes</li>
<li>Suivi et gestion opérationnelle des chèques impayés</li>
<li>KPIs et dashboards de production</li>
<li>Génération d’états PDF</li>
</ul>

</div>
""", unsafe_allow_html=True)

        cci_demo = first_existing(CCI_DIR/ "cci_demo.mp4", CCI_DIR / "cci_demo.mov")
        if cci_demo:
            st.markdown("### Démonstration")
            st.video(str(cci_demo))
        else:
            st.caption("Ajoute assets/salle_marche/sm_demo.mp4 (optionnel).")
        st.write("")
        st.markdown("### Captures d'écran")
        cci_imgs = collect_images(CCI_DIR, prefixes=["cci_", "CentraledesChequesImpayes", "CentraledesChèquesImpayés"])
        render_gallery(cci_imgs, per_row=3, limit=18)

    # ---- Salle de Marché ----
    with tabs[1]:
        st.markdown("""
<div class="card">

<h3>Simulateur de Salle de Marché</h3>

<ul>
<li>Plateforme interactive de simulation</li>
<li>Analyse technique et fondamentale</li>
<li>Visualisation et indicateurs de marché</li>
</ul>

</div>
""", unsafe_allow_html=True)


        sm_demo = first_existing(SM_DIR / "sm_demo.mp4", SM_DIR / "sm_demo.mov")
        if sm_demo:
            st.markdown("### Démonstration")
            st.video(str(sm_demo))
        else:
            st.caption("Ajoute assets/salle_marche/sm_demo.mp4 (optionnel).")

        st.write("")
        st.markdown("### Captures d'écran")
        sm_imgs = collect_images(SM_DIR, prefixes=["sm_"])
        render_gallery(sm_imgs, per_row=3, limit=24)
    # ---- DevOps ----
    with tabs[3]:
        st.markdown(
            """
    <div class="card">
    <h3>Mise en place d’une Chaîne DevOps CI/CD et de Supervision pour une Architecture Microservices</h3>
    <ul>
      <li><b>CI/CD :</b> Jenkins (tests, build, déploiement automatisé)</li>
      <li><b>Qualité :</b> SonarQube (analyse statique, quality gates)</li>
      <li><b>Monitoring :</b> Prometheus + Grafana (métriques, dashboards, santé des services)</li>
      <li><b>Conteneurisation :</b> Docker (backend, frontend, base de données)</li>
      <li><b>Base de données :</b> MySQL conteneurisé</li>
    </ul>
    </div>
    """,
            unsafe_allow_html=True,
        )

        st.markdown("### Dashboards & supervision")
        st.write(
            "Mise en place de tableaux de bord Grafana pour suivre en temps réel la disponibilité, "
            "la consommation CPU/RAM, les erreurs et la performance des services, avec collecte des métriques via Prometheus."
        )

        st.write("")
        st.markdown("### Captures d'écran")

        # IMPORTANT: DEVOPS_DIR doit exister et pointer vers assets/devops
        DEVOPS_DIR = Path("assets/devops")

        devops_imgs = sorted(
            list(DEVOPS_DIR.glob("devops_*.png"))
            + list(DEVOPS_DIR.glob("devops_*.jpg"))
            + list(DEVOPS_DIR.glob("devops_*.jpeg"))
            + list(DEVOPS_DIR.glob("devops_*.jfif"))
        )

        if devops_imgs:
            render_gallery(devops_imgs, per_row=3, limit=24)
        else:
            st.caption("Aucune image trouvée. Vérifie assets/devops et les noms devops_*.jfif/.jpg/.png")



# ============================
# DEMONSTRATION (loan_engine.py)
# ============================
if section == "Cas pratique":
    st.markdown("## Cas pratique — Moteur d'échéancier de crédit")
    st.markdown("""
<style>
.card {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 20px;
    margin-top: 20px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.05);
}

.small {
    font-size: 15px;
    color: #374151;
    line-height: 1.6;
}
</style>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="card">
  <div class="small">
    Démonstration interactive d’un moteur de calcul d’échéancier
    supportant plusieurs modes de remboursement, la sélection
    de la base de calcul et l’export des résultats.
  </div>
</div>
""", unsafe_allow_html=True)



    st.write("")
    colA, colB, colC = st.columns(3, gap="large")
    with colA:
        amount = st.number_input("Montant du prêt", min_value=0.0, value=119_804.0, step=1_000.0)
        annual_rate = st.number_input("Taux annuel (en %)", min_value=0.0, value=6.5, step=0.1) / 100.0
        period_count = st.number_input("Durée (en périodes)", min_value=1, value=130, step=1)

    with colB:
        repayment_type = st.selectbox(
            "Type de remboursement",
            [TYPE_IN_FINE, TYPE_CONSTANT_AMORTIZATION, TYPE_SPECIFIC_REPAYMENT],
            format_func=lambda x: {
                TYPE_IN_FINE: "In fine",
                TYPE_CONSTANT_AMORTIZATION: "Amortissement constant",
                TYPE_SPECIFIC_REPAYMENT: "Remboursement spécifique (TEG)",
            }[x],
        )
        payment_freq = st.selectbox("Fréquence de paiement (en mois)", [1, 2, 3, 6, 12], index=0)
        base = st.selectbox(
            "Base de calcul",
            [BASE_MENSUELLE_12, BASE_360],
            format_func=lambda x: "Base 12 (mensuel)" if x == BASE_MENSUELLE_12 else "Base 360 (jours)",
        )

    with colC:
        disb = st.date_input("Date de déblocage", value=date(2025, 4, 29))
        first = st.date_input("Première échéance", value=date(2025, 5, 29))

    st.write("")
    if repayment_type == TYPE_SPECIFIC_REPAYMENT:
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            interest_freq = st.selectbox("Fréquence des intérêts (en mois)", [1, 2, 3, 6, 12], index=0)
        with s2:
            deferred = st.number_input("Nombre de périodes différées", min_value=0, value=0, step=1)
        with s3:
            flat = st.toggle("Mode flat", value=False)
        with s4:
            fee = st.number_input("Frais", min_value=0.0, value=200.0, step=10.0)
    else:
        interest_freq, deferred, flat, fee = 1, 0, False, 0.0

    rows, summary = build_schedule(
        repayment_type=repayment_type,
        amount=float(amount),
        annual_rate=float(annual_rate),
        period_count=int(period_count),
        payment_frequency_months=int(payment_freq),
        base=base,
        disbursement_date=disb,
        first_installment_date=first,
        interest_frequency_months=int(interest_freq),
        deferred_periods=int(deferred),
        flat=bool(flat),
        fee_amount=float(fee),
    )

    if not rows:
        st.error("Impossible de générer l'échéancier. Vérifie les paramètres.")
    else:
        df = pd.DataFrame(
            [{
                "Période": r.period,
                "Date": r.date.strftime("%d/%m/%Y"),
                "Versement": round(r.payment, 2),
                "Intérêt": round(r.interest, 2),
                "Principal": round(r.principal, 2),
                "Solde restant": round(r.balance, 2),
            } for r in rows]
        )

        st.write("")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total versements", f"{summary.get('total_payment', 0):,.2f}")
        k2.metric("Total intérêts", f"{summary.get('total_interest', 0):,.2f}")
        k3.metric("Total principal", f"{summary.get('total_principal', 0):,.2f}")
        if repayment_type == TYPE_SPECIFIC_REPAYMENT:
            teg = summary.get("teg", float("nan"))
            k4.metric("TEG (approx.)", "Non calculé" if teg != teg else f"{(teg * 100):.2f}%")
        else:
            k4.metric("Indicateur", "—")

        st.write("")
        st.markdown("### Échéancier (24 premières périodes)")
        st.dataframe(df.head(24), use_container_width=True, hide_index=True)

        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Exporter en CSV",
            data=csv_bytes,
            file_name="echeancier.csv",
            mime="text/csv",
        )

        st.write("")
        st.markdown("### Solde restant (24 premières périodes)")
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=list(range(1, min(24, len(df)) + 1)),
                y=df["Solde restant"].head(24),
                mode="lines",
                name="Solde restant",
            )
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=320,
            xaxis_title="Période",
            yaxis_title="Montant",
        )
        st.plotly_chart(fig, use_container_width=True)


# ============================
# COMPETENCES
# ============================
if section == "Compétences":
    st.markdown("## Compétences")

    st.markdown(
        """
<style>
.skill-card{
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 16px;
  padding: 20px 20px;
  height: 100%;
}

.skill-header{
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.skill-title{
  font-size: 16px;
  font-weight: 700;
}

.skill-desc{
  font-size: 16px;
  opacity: 2;
  margin-bottom: 16px;
}

.skill-tags{
  display: flex;
  font-size: 15px;
  opacity: 4;
  flex-wrap: wrap;
  gap: 8px;
}

.skill-tag{
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.15);
  background: rgba(255,255,255,0.05);
}
</style>
""",
        unsafe_allow_html=True,
    )
    st.markdown(
    """
<style>
.skill-tags{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

.skill-tag{
  background: linear-gradient(
    135deg,
    rgba(255,255,255,0.08),
    rgba(255,255,255,0.03)
  );
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
  white-space: nowrap;

  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.06),
    0 6px 16px rgba(0,0,0,0.08);

  transition: all 0.2s ease;
}

.skill-tag:hover{
  transform: translateY(-2px);
  background: linear-gradient(
    135deg,
    rgba(255,255,255,0.12),
    rgba(255,255,255,0.05)
  );
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 10px 24px rgba(0,0,0,0.12);
}
</style>
""",
    unsafe_allow_html=True,
)


    col1, col2 = st.columns(2, gap="large")

    # --- TECH ---
    with col1:
        st.markdown(
            """
<div class="skill-card">
  <div class="skill-header">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" stroke-width="2"/>
    </svg>
    <div class="skill-title">Compétences techniques</div>
  </div>

  <div class="skill-desc">
    Conception et développement d’applications backend & frontend sécurisées,
    orientées performance et logique métier bancaire.
  </div>

  <div class="skill-tags">
    <div class="skill-tag">Angular</div>
    <div class="skill-tag">FastAPI</div>
    <div class="skill-tag">Python</div>
    <div class="skill-tag">Spring Boot</div>
    <div class="skill-tag">PostgreSQL</div>
    <div class="skill-tag">MySQL</div>
    <div class="skill-tag">Keycloak</div>
    <div class="skill-tag">OIDC / RBAC</div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    # --- FINANCE ---
    with col2:
        st.markdown(
            """
<div class="skill-card">
  <div class="skill-header">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M3 12l3 3 6-6 4 4 5-5" stroke="currentColor" stroke-width="2"/>
    </svg>
    <div class="skill-title">Finance & Banque</div>
  </div>

  <div class="skill-desc">
    Expertise fonctionnelle sur les processus bancaires, le crédit,
    l’analyse du risque et le pilotage par indicateurs.
  </div>

  <div class="skill-tags">
    <div class="skill-tag">Crédit (LTV, DTI)</div>
    <div class="skill-tag">Échéanciers</div>
    <div class="skill-tag">Garanties & Collatéraux</div>
    <div class="skill-tag">KPIs & Dashboards</div>
    <div class="skill-tag">Reporting</div>
    <div class="skill-tag">Process bancaires</div>
    <div class="skill-tag">Suivi post-attribution</div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )



# ============================
# CONTACT
# ============================
if section == "Contact":
    st.markdown("## Contact")

    st.markdown(
        """
<style>
.contact-card{
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 16px;
  padding: 22px 22px;
}

.contact-row{
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 0;
}

.contact-icon{
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(
    135deg,
    rgba(255,255,255,0.12),
    rgba(255,255,255,0.04)
  );
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255,255,255,0.15);
}

.contact-label{
  font-size: 12px;
  opacity: 0.7;
  margin-bottom: 2px;
}

.contact-value{
  font-size: 15px;
  font-weight: 600;
}
</style>

<div class="contact-card">

  <div class="contact-row">
    <div class="contact-icon">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" stroke="currentColor" stroke-width="2"/>
        <circle cx="12" cy="9" r="2.5" stroke="currentColor" stroke-width="2"/>
      </svg>
    </div>
    <div>
      <div class="contact-label">Localisation</div>
      <div class="contact-value">Tunis, Tunisie</div>
    </div>
  </div>

  <div class="contact-row">
    <div class="contact-icon">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <path d="M4 4h16v16H4z" stroke="currentColor" stroke-width="2"/>
        <path d="M4 4l8 8 8-8" stroke="currentColor" stroke-width="2"/>
      </svg>
    </div>
    <div>
      <div class="contact-label">Email</div>
      <div class="contact-value">chohdi.kema@gmail.com</div>
    </div>
  </div>

  <div class="contact-row">
    <div class="contact-icon">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <path d="M22 16.92v3a2 2 0 0 1-2.18 2A19.8 19.8 0 0 1 3 5.18 2 2 0 0 1 5 3h3a2 2 0 0 1 2 1.72c.12.9.32 1.76.6 2.58a2 2 0 0 1-.45 2.11L9 10a16 16 0 0 0 5 5l.59-.15a2 2 0 0 1 2.11.45c.82.28 1.68.48 2.58.6A2 2 0 0 1 22 16.92z"
              stroke="currentColor" stroke-width="2"/>
      </svg>
    </div>
    <div>
      <div class="contact-label">Téléphone</div>
      <div class="contact-value">+216 50 513 004</div>
    </div>
  </div>

</div>
""",
        unsafe_allow_html=True,
    )


