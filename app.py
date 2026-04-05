"""
🏔️ Agent SAV SNOWPEAK — Interface Streamlit
Diagnostic intelligent de pannes remontées mécaniques
Déployable gratuitement sur Streamlit Cloud
"""

import streamlit as st
import json
import re
import numpy as np
from openai import OpenAI
from datetime import datetime

# ══════════════════════════════════════════════════════════════
# CONFIGURATION DE LA PAGE
# ══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Agent SAV SNOWPEAK",
    page_icon="🏔️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════
# STYLE CSS PERSONNALISÉ
# ══════════════════════════════════════════════════════════════

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

    .main .block-container { padding-top: 2rem; max-width: 800px; }

    .hero-banner {
        background: linear-gradient(135deg, #1a3a5c 0%, #2b5f8a 60%, #1d4b6e 100%);
        border-radius: 16px;
        padding: 28px 32px;
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
    }
    .hero-banner::before {
        content: '';
        position: absolute;
        top: -40px; right: -40px;
        width: 160px; height: 160px;
        border-radius: 50%;
        background: rgba(255,255,255,0.04);
    }
    .hero-title {
        color: white;
        font-family: 'DM Sans', sans-serif;
        font-size: 22px;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .hero-sub {
        color: rgba(255,255,255,0.6);
        font-size: 13px;
        margin: 4px 0 0;
    }

    .ticket-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 500;
        margin: 2px 4px 2px 0;
    }
    .ticket-dot {
        width: 7px; height: 7px;
        border-radius: 50%;
        display: inline-block;
    }

    .cat-variateur { background: #EFF6FF; color: #1E40AF; }
    .cat-moteur { background: #FEF2F2; color: #991B1B; }
    .cat-ecran { background: #F5F3FF; color: #5B21B6; }
    .cat-automate { background: #FFFBEB; color: #92400E; }
    .cat-capteur { background: #ECFDF5; color: #065F46; }
    .cat-hydraulique { background: #ECFEFF; color: #155E75; }
    .cat-cablage { background: #FFF7ED; color: #9A3412; }

    .dot-variateur { background: #3B82F6; }
    .dot-moteur { background: #EF4444; }
    .dot-ecran { background: #8B5CF6; }
    .dot-automate { background: #F59E0B; }
    .dot-capteur { background: #10B981; }
    .dot-hydraulique { background: #06B6D4; }
    .dot-cablage { background: #F97316; }

    .stat-card {
        background: #f8fafc;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        border: 1px solid #e2e8f0;
    }
    .stat-number {
        font-size: 28px;
        font-weight: 700;
        color: #1a3a5c;
        line-height: 1;
    }
    .stat-label {
        font-size: 11px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 4px;
    }

    div[data-testid="stChatMessage"] {
        font-size: 14px;
        line-height: 1.65;
    }

    .stChatInput > div { border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# BASE DE TICKETS SAV (46 tickets)
# ══════════════════════════════════════════════════════════════

@st.cache_data
def load_tickets():
    return [
        {"ref":"T-000001","cat":"Moteur","code":"","equip":"WEG W22 160L","install":"TC de l'Aiguille","station":"Les Aigles","objet":"Perte de puissance progressive","desc":"Perte progressive de puissance au fil de la journée. Le courant consommé augmente mais la vitesse diminue.","solution":"Réducteur grippé : niveau d'huile trop bas. Vidange et remplissage huile adaptée. Puissance normale."},
        {"ref":"T-000002","cat":"Écran","code":"E-TIMEOUT","equip":"SUPREME 12T Retour","install":"TSD de la Cime","station":"Col du Sapin","objet":"Redémarrage intempestif IHM motrice","desc":"L'IHM redémarre de manière aléatoire, 1 à 5 fois par jour.","solution":"Alimentation 24V instable. Micro-coupures oscilloscope. Remplacement alim + condensateur filtrage."},
        {"ref":"T-000003","cat":"Moteur","code":"","equip":"ABB M3BP 250","install":"TK des Écureuils","station":"La Crête Blanche","objet":"Vibrations excessives bâti moteur 8mm/s","desc":"Vibrations importantes sur le bâti. Mesure : 8 mm/s en vitesse efficace.","solution":"Accouplement élastique fissuré. Remplacement + réalignement laser. Vibratoire 2.5 mm/s."},
        {"ref":"T-000004","cat":"Variateur","code":"ERR-0V","equip":"ABB ACS880-01","install":"TSD de l'Arête","station":"Pic de l'Ours","objet":"Défaut puissance surtension bus DC","desc":"Variateur en défaut lors de la décélération. Surtension bus DC.","solution":"Résistance freinage HS remplacée. Décélération 15s→20s. Plus de défaut."},
        {"ref":"T-000005","cat":"Écran","code":"E-DISPLAY","equip":"SUPREME 12T Retour","install":"TSF des Chamois","station":"Pic de l'Ours","objet":"Pixels morts afficheur gare retour","desc":"Zone de pixels morts qui s'agrandit progressivement depuis une semaine.","solution":"Écran LCD fin de vie. Remplacement complet. Reconfiguration IP + comm."},
        {"ref":"T-000006","cat":"Variateur","code":"F-16","equip":"Danfoss VLT FC302","install":"TC des Crêtes","station":"Les Marmottes","objet":"Défaut isolation au démarrage","desc":"Contrôle d'isolation échoue systématiquement au démarrage.","solution":"Humidité boîte à bornes. Séchage + presse-étoupes. Isolement 150 MOhm."},
        {"ref":"T-000007","cat":"Automate","code":"","equip":"Allen-Bradley CompactLogix 5380","install":"TSF des Sapins","station":"Mont Serein","objet":"Décadencement véhicules progressif","desc":"Véhicules se décadencent progressivement, écart > 30%.","solution":"Mesure ligne erronée. Correction 43648→43407 pts. Recadencement complet."},
        {"ref":"T-000008","cat":"Câblage","code":"F-C4","equip":"Danfoss VLT FC302","install":"TK du Lac","station":"Les Aigles","objet":"Perte communication automate intermittente","desc":"Perte communication intermittente, arrêt 2-3 fois/jour.","solution":"Câble Profibus endommagé passage porte armoire. Remplacement + résistances terminaison."},
        {"ref":"T-000009","cat":"Variateur","code":"ERR-HF","equip":"Leroy-Somer Unidrive M200","install":"TK du Lac","station":"Les Aigles","objet":"Défaut haute fréquence temps froid <-10°C","desc":"Défaut à vitesse nominale par temps froid < -10°C.","solution":"Condensateurs bus DC vieillissants. Remplacement carte puissance. Essais froid OK."},
        {"ref":"T-000010","cat":"Capteur","code":"","equip":"Potentiomètre Novotechnik TLH","install":"TSF des Sapins","station":"Mont Serein","objet":"Alarme point fixe intempestive","desc":"Alarme point fixe se déclenche de manière intempestive.","solution":"Potentiomètre encrassé. Nettoyage + recalibration. Seuil alarme réajusté."},
        {"ref":"T-000011","cat":"Variateur","code":"ERR-OC","equip":"Leroy-Somer Unidrive M200","install":"TSF des Chamois","station":"Pic de l'Ours","objet":"Défaut surintensité au démarrage","desc":"Défaut surintensité répétitif au démarrage.","solution":"Courant nominal incorrect après remplacement moteur. Corrigé 12A→18.5A."},
        {"ref":"T-000012","cat":"Variateur","code":"ERR-OC","equip":"Danfoss VLT FC302","install":"TSF des Chamois","station":"Pic de l'Ours","objet":"Oscillation courant sortie ±3A vibrations","desc":"Courant oscille ±3A, vibrations audibles.","solution":"Paramètres PI désajustés après firmware. Gain 150%→80%, Ti 0.5s→1.2s."},
        {"ref":"T-000013","cat":"Automate","code":"","equip":"Pilz PSSu PLC","install":"TSD de la Forêt","station":"La Crête Blanche","objet":"Modification seuils de vent","desc":"Réduire arrêts intempestifs, seuil vent fort 10→15 m/s.","solution":"Seuils ST : vent fort 15 m/s, violent 20 m/s. Seuil FS non modifié (réglementation)."},
        {"ref":"T-000014","cat":"Écran","code":"E-BOOT","equip":"SUPREME 15T Motrice","install":"TSD du Glacier","station":"Mont Serein","objet":"IHM figée au démarrage sur logo","desc":"IHM reste figée sur le logo, impossible d'accéder à l'application.","solution":"Carte CF corrompue. Rechargement depuis clé USB. Remplacement préventif CF."},
        {"ref":"T-000015","cat":"Câblage","code":"","equip":"SECOMEA SiteManager 3529","install":"TSF des Sapins","station":"Mont Serein","objet":"Télémaintenance SECOMEA inaccessible","desc":"Connexion télémaintenance ne fonctionne plus.","solution":"Routeur perdu config après coupure prolongée. Rechargement config + test VPN."},
        {"ref":"T-000016","cat":"Variateur","code":"ERR-OT","equip":"Leroy-Somer Unidrive M100-044","install":"TC du Cirque","station":"Pic de l'Ours","objet":"Défaut thermique après 45min exploitation","desc":"Défaut thermique après 45 minutes, température armoire élevée.","solution":"Ventilateur refroidissement HS. Remplacement + nettoyage filtres. Temp 35°C."},
        {"ref":"T-000017","cat":"Écran","code":"E-SYNC","equip":"Beijer X2 Pro 12","install":"TSF du Torrent","station":"Col du Sapin","objet":"Erreur synchronisation horloge dérive","desc":"Heure dérive de plusieurs minutes par jour.","solution":"Pile CR2032 HS. Remplacement + resynchronisation NTP serveur station."},
        {"ref":"T-000018","cat":"Moteur","code":"","equip":"Leroy-Somer LSMV 225","install":"TSF du Vallon","station":"La Crête Blanche","objet":"Entraînement principal ne démarre pas","desc":"Refuse de démarrer, aucun défaut, contacteur colle mais rien ne bouge.","solution":"Câble puissance sectionné par rongeur. Remplacement + gaine anti-rongeurs."},
        {"ref":"T-000019","cat":"Variateur","code":"F-16","equip":"Schneider ATV930","install":"TSD de la Forêt","station":"La Crête Blanche","objet":"Défaut terre dès mise sous tension","desc":"Défaut terre détecté dès la mise sous tension.","solution":"Phase U1 terre 0.05 MOhm. Moteur en réparation. Moteur secours. Variateur reparamétré."},
        {"ref":"T-000020","cat":"Câblage","code":"","equip":"Multipaire Belden 9842","install":"TC du Cirque","station":"Pic de l'Ours","objet":"Déclenchement Mini-S3 intempestif","desc":"Déclenchement intempestif sécurité Mini-S3.","solution":"Fil terre dans multipaire entre gares. Remplacement paire défectueuse."},
        {"ref":"T-000021","cat":"Capteur","code":"","equip":"Codeur Heidenhain ROD 426","install":"TSD du Glacier","station":"Mont Serein","objet":"Dérive position codeur incrémental","desc":"Codeur génère des impulsions parasites, comptage dérive.","solution":"Blindage câble codeur mal raccordé. Reprise blindage + ferrites. Comptage stable."},
        {"ref":"T-000022","cat":"Écran","code":"E-TOUCH","equip":"SUPREME 12T Retour","install":"TSD de l'Arête","station":"Pic de l'Ours","objet":"Tactile ne répond plus écran fonctionnel","desc":"Écran tactile ne répond plus, affichage fonctionne.","solution":"Calibration perdue après MAJ système. Recalibration menu maintenance."},
        {"ref":"T-000023","cat":"Moteur","code":"","equip":"WEG W22 160L","install":"TC des Crêtes","station":"Les Marmottes","objet":"Bruit métallique gare motrice avec vitesse","desc":"Bruit métallique augmentant avec la vitesse.","solution":"Roulement côté accouplement usé. Remplacement 2 roulements + réalignement."},
        {"ref":"T-000024","cat":"Hydraulique","code":"","equip":"Rexroth 4WREE 10","install":"TC du Cirque","station":"Pic de l'Ours","objet":"Tension câble basse récurrente vérin oscille","desc":"Alarme tension câble basse, vérin oscille.","solution":"Fuite distributeur hydraulique. Remplacement joints + purge circuit."},
        {"ref":"T-000025","cat":"Écran","code":"E-COM","equip":"Schneider Magelis HMIST6","install":"TC du Cirque","station":"Pic de l'Ours","objet":"Perte communication supervision toutes 15min","desc":"Perd communication toutes 10-15 minutes.","solution":"Câble Ethernet défectueux. Sertissage refait 2 extrémités."},
        {"ref":"T-000026","cat":"Hydraulique","code":"","equip":"Rexroth 4WREE 10","install":"TC du Sommet","station":"Mont Serein","objet":"Frein de service temps réponse 3s→7s","desc":"Temps de freinage passé de 3s à 7s.","solution":"Électrovanne freinage obstruée. Démontage + nettoyage. Retour 3.2s."},
        {"ref":"T-000027","cat":"Câblage","code":"","equip":"FO Corning 12 brins SM","install":"TSF de la Combe","station":"Les Aigles","objet":"Coupures fibre 2-10s inter-gares","desc":"Perte communication intermittente via fibre optique.","solution":"Connecteur fibre encrassé. Nettoyage SC + atténuation 1.2 dB."},
        {"ref":"T-000028","cat":"Écran","code":"E-DISPLAY","equip":"SUPREME 12T Retour","install":"TSF du Vallon","station":"La Crête Blanche","objet":"Rétroéclairage éteint par intermittence froid","desc":"Rétroéclairage s'éteint par intermittence par temps froid.","solution":"Connecteur rétroéclairage oxydé. Nettoyage + graisse contact + chauffage armoire."},
        {"ref":"T-000029","cat":"Écran","code":"E-COM","equip":"SUPREME 15T Motrice","install":"TC des Crêtes","station":"Les Marmottes","objet":"Alarmes non remontées supervision","desc":"Alarmes ne s'affichent plus sur supervision.","solution":"Variables alarme non mappées après modif automate. MAJ application supervision."},
        {"ref":"T-000030","cat":"Capteur","code":"","equip":"Codeur Heidenhain ROD 426","install":"TSF de la Bergerie","station":"Les Marmottes","objet":"Mesure vitesse oscille 0 ↔ valeur réelle","desc":"Capteur vitesse donne mesures incohérentes.","solution":"Entrefer capteur inductif trop grand. Réglage 1.5mm + Loctite."},
        {"ref":"T-000031","cat":"Moteur","code":"","equip":"Siemens 1LA7 163","install":"TC du Cirque","station":"Pic de l'Ours","objet":"Claquement sec à chaque démarrage","desc":"Claquement sec à chaque démarrage, zone accouplement.","solution":"Jeu excessif accouplement à denture. Remplacement manchon."},
        {"ref":"T-000032","cat":"Variateur","code":"F-06","equip":"Danfoss VLT FC302","install":"TSD de la Cime","station":"Col du Sapin","objet":"Défaut phase sortie ne démarre plus","desc":"Défaut de phase en sortie, ne démarre plus.","solution":"Phase W2 déconnectée au bornier. Reconnexion + serrage bornes."},
        {"ref":"T-000033","cat":"Moteur","code":"","equip":"Leroy-Somer LSMV 225","install":"TSF de la Combe","station":"Les Aigles","objet":"Sens rotation inversé après intervention","desc":"Sens de rotation inversé après maintenance.","solution":"Deux phases inversées au bornier. Inversion U1/W1 corrigée."},
        {"ref":"T-000034","cat":"Variateur","code":"","equip":"MND MT-200","install":"TSD de la Cime","station":"Col du Sapin","objet":"Oscillation courant excitation ±0.8A","desc":"Courant excitation oscille, vitesse instable.","solution":"Carte régulation excitation défaillante. Remplacement FXMP25. Courant stable 9.2A."},
        {"ref":"T-000035","cat":"Hydraulique","code":"","equip":"Bucher Hydraulics CINDY 12","install":"TK du Lac","station":"Les Aigles","objet":"Pression insuffisante 85 bar consigne 120","desc":"Pression ne monte pas au-dessus de 85 bar.","solution":"Pompe hydraulique usée. Remplacement pompe + filtre HP. Pression OK en 45s."},
        {"ref":"T-000036","cat":"Capteur","code":"","equip":"Baumer GI355","install":"TSF de la Bergerie","station":"Les Marmottes","objet":"Défaut S06 zones cheminement gare retour","desc":"Défauts S06 répétitifs, comptage perturbé.","solution":"Capteurs GI A/B inversés. Rétablissement câblage + déphasage oscilloscope."},
        {"ref":"T-000037","cat":"Automate","code":"","equip":"Pilz PSS 3000","install":"TSD du Glacier","station":"Mont Serein","objet":"Automate motrice STOP aléatoire","desc":"Automate passe en STOP aléatoirement, dépassement cycle.","solution":"Carte comm Ethernet rack extension défaillante. Remplacement carte + fond panier."},
        {"ref":"T-000038","cat":"Variateur","code":"F-02","equip":"ABB ACS880-01","install":"TSD des Bouquetins","station":"Les Aigles","objet":"Surcharge exploitation courant > nominal","desc":"Surcharge après 30 min, courant supérieur au nominal.","solution":"Garniture frein collée. Moteur forçait contre frein. Remplacement garnitures + entrefer."},
        {"ref":"T-000039","cat":"Moteur","code":"","equip":"Leroy-Somer LSMV 180","install":"TSD de l'Arête","station":"Pic de l'Ours","objet":"Surchauffe 145°C seuil 155°C après 2h","desc":"Sonde température déclenche après 2h, 145°C.","solution":"Ventilation obstruée neige compactée. Dégagement + grille protection. Temp 95°C."},
        {"ref":"T-000040","cat":"Moteur","code":"","equip":"Vérin Festo DSBC 40","install":"TK des Écureuils","station":"La Crête Blanche","objet":"Portillon n°3 gare retour bloqué","desc":"Portillon ne s'ouvre plus au passage.","solution":"Vérin pneumatique bloqué. Remplacement vérin + électrovanne. Réglage timing."},
        {"ref":"T-000041","cat":"Moteur","code":"","equip":"Leroy-Somer LSMV 225","install":"TC de l'Aiguille","station":"Les Aigles","objet":"Déclenchement différentiel 300mA","desc":"Différentiel 300mA déclenche aléatoirement.","solution":"Isolement dégradé phase V1 : 2 MOhm. Infiltration eau presse-étoupe. Séchage + remplacement. 250 MOhm."},
        {"ref":"T-000042","cat":"Moteur","code":"","equip":"Siemens 1LA7 163","install":"TSF du Vallon","station":"La Crête Blanche","objet":"Thermique entraînement secours essais <5min","desc":"Protection thermique après 5 min en charge.","solution":"Capot ventilateur déformé. Ventilation insuffisante. Remplacement capot + nettoyage."},
        {"ref":"T-000043","cat":"Variateur","code":"F-09","equip":"ABB ACS580","install":"TSF du Vallon","station":"La Crête Blanche","objet":"Défaut calage démarrage","desc":"Ne parvient pas à atteindre vitesse cadencement.","solution":"Frein parking non desserré. Contacteur commande HS. Remplacement + vérif circuit desserrage."},
        {"ref":"T-000044","cat":"Capteur","code":"","equip":"Cellule Sick WL27-3","install":"TSD des Bouquetins","station":"Les Aigles","objet":"Comptage passagers 40% inférieur","desc":"Compteur 40% inférieur à la réalité.","solution":"Cellule désalignée suite choc. Réalignement + nettoyage. Précision 98%."},
        {"ref":"T-000045","cat":"Capteur","code":"","equip":"Anémomètre Thies 4.3351","install":"TSD de la Cime","station":"Col du Sapin","objet":"Anémomètre valeurs x3 supérieures","desc":"Valeurs vent 3x supérieures à la station météo.","solution":"Roulement anémomètre grippé. Remplacement complet + recalibration seuils vent."},
        {"ref":"T-000046","cat":"Variateur","code":"F-C4","equip":"Leroy-Somer Unidrive M600","install":"TK des Écureuils","station":"La Crête Blanche","objet":"Pas de redémarrage après coupure secteur","desc":"Ne redémarre plus après coupure nocturne.","solution":"Carte contrôle corrompue. Reset usine + rechargement paramètres. Ajout onduleur alim commande."},
    ]


# ══════════════════════════════════════════════════════════════
# FONCTIONS DE RECHERCHE
# ══════════════════════════════════════════════════════════════

CAT_KEYWORDS = {
    "Variateur": ["variateur","vlt","acs","unidrive","atv","fc302","m200","m600","acs880","acs580","err-","f-0","f-1","f-c","surtension","surcharge","bus dc"],
    "Moteur": ["moteur","vibration","surchauffe","roulement","accouplement","bruit","thermique","lsmv","weg","siemens 1la","claquement","rotation","isolement"],
    "Écran": ["écran","ihm","afficheur","tactile","rétroéclairage","pixel","display","supervision","magelis","supreme","beijer","e-boot","e-com","e-touch","e-display"],
    "Automate": ["automate","plc","cpu","programme","cycle","allen-bradley","pilz","compactlogix","pss","décadenc"],
    "Capteur": ["capteur","codeur","anémomètre","potentiomètre","cellule","heidenhain","baumer","sick","novotechnik","thies","comptage"],
    "Hydraulique": ["hydraulique","vérin","pression","pompe","frein","distributeur","rexroth","bucher","électrovanne"],
    "Câblage": ["câble","fibre","multipaire","bornier","blindage","connecteur","ethernet","profibus","secomea","routeur","vpn"],
}

CAT_COLORS = {
    "Variateur": ("cat-variateur", "dot-variateur"),
    "Moteur": ("cat-moteur", "dot-moteur"),
    "Écran": ("cat-ecran", "dot-ecran"),
    "Automate": ("cat-automate", "dot-automate"),
    "Capteur": ("cat-capteur", "dot-capteur"),
    "Hydraulique": ("cat-hydraulique", "dot-hydraulique"),
    "Câblage": ("cat-cablage", "dot-cablage"),
}

CAT_EMOJI = {
    "Variateur": "⚡", "Moteur": "🔧", "Écran": "🖥️",
    "Automate": "🤖", "Capteur": "📡", "Hydraulique": "💧", "Câblage": "🔌"
}


def detect_category(msg):
    msg = msg.lower()
    for cat, kws in CAT_KEYWORDS.items():
        if any(k in msg for k in kws):
            return cat
    return None


def detect_error_code(msg):
    m = re.search(r'\b(err-[a-z0-9]{2,4}|f-[a-z0-9]{2,4}|e-[a-z]{2,8})\b', msg.lower())
    return m.group(1).upper() if m else None


def search_tickets(query, tickets):
    q = query.lower()
    words = [w for w in re.split(r'\W+', q) if len(w) > 2]
    results = []
    for t in tickets:
        score = 0
        hay = f"{t['objet']} {t['solution']} {t['equip']} {t['desc']} {t['cat']} {t['code']}".lower()
        for w in words:
            if w in hay:
                score += 10
        if t['code'] and t['code'].lower() in q:
            score += 50
        cat = detect_category(q)
        if cat and t['cat'] == cat:
            score += 30
        if score > 15:
            results.append({**t, "score": score})
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:5]


def enrich_message(msg):
    cat = detect_category(msg)
    code = detect_error_code(msg)
    parts = []
    if cat:
        parts.append(f"Catégorie: {cat}")
    if code:
        parts.append(f"Code erreur: {code}")
    enriched = msg
    if parts:
        enriched += f"\n\n[Contexte pré-analysé: {' | '.join(parts)}]"
    return enriched


# ══════════════════════════════════════════════════════════════
# PROMPT SYSTÈME
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Tu es l'Agent SAV SNOWPEAK, expert en maintenance de remontées mécaniques.

MÉTHODE OBLIGATOIRE pour chaque panne :

### 📋 DIAGNOSTIC PROBABLE
- Cause probable + tickets sources (T-XXXXXX) + niveau confiance (élevé/moyen/faible)

### 🔧 VÉRIFICATIONS PAS-À-PAS
Étape 1 → [Vérification] — [Outil] — [Valeur attendue]
Étape 2 → ...
(Valeurs numériques : courant A, pression bar, °C, mm, MOhm, mm/s)

### ✅ PROCÉDURE DE RÉPARATION
- Actions ordonnées + pièces + paramètres + tests validation + sécurité

RÈGLES : Citer tickets T-XXXXXX. Valeurs numériques précises. Français. Concis mais complet.
Si message vague → demander précisions (équipement, code erreur, symptômes).
CATÉGORIES : Variateur | Moteur | Écran/IHM | Automate | Capteur | Hydraulique | Câblage
STATIONS : Les Aigles | Col du Sapin | La Crête Blanche | Pic de l'Ours | Les Marmottes | Mont Serein"""


# ══════════════════════════════════════════════════════════════
# INTERFACE PRINCIPALE
# ══════════════════════════════════════════════════════════════

tickets = load_tickets()

# ── Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    api_key = st.text_input("Clé API OpenAI", type="password", help="Votre clé commence par sk-...")

    st.markdown("---")
    st.markdown("### 📊 Base de tickets")

    # Stats
    from collections import Counter
    cats = Counter(t['cat'] for t in tickets)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="stat-card"><div class="stat-number">{len(tickets)}</div><div class="stat-label">Tickets</div></div>', unsafe_allow_html=True)
    with col2:
        n_codes = sum(1 for t in tickets if t['code'])
        st.markdown(f'<div class="stat-card"><div class="stat-number">{n_codes}</div><div class="stat-label">Codes erreur</div></div>', unsafe_allow_html=True)

    st.markdown("")
    for cat, count in cats.most_common():
        emoji = CAT_EMOJI.get(cat, "📋")
        st.markdown(f"{emoji} **{cat}** — {count} tickets")

    st.markdown("---")
    st.markdown("### 🏔️ Stations")
    stations = Counter(t['station'] for t in tickets)
    for sta, count in stations.most_common():
        st.caption(f"📍 {sta} ({count})")

    st.markdown("---")
    if st.button("🗑️ Nouvelle conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ── Header
st.markdown("""
<div class="hero-banner">
    <div class="hero-title">🏔️ Agent SAV SNOWPEAK</div>
    <div class="hero-sub">Diagnostic intelligent • 46 tickets résolus • Procédures pas-à-pas</div>
</div>
""", unsafe_allow_html=True)


# ── Initialisation session
if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Affichage messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🏔️" if msg["role"] == "assistant" else "👷"):
        if msg["role"] == "assistant" and "tickets_found" in msg:
            tickets_found = msg["tickets_found"]
            if tickets_found:
                chips_html = ""
                for t in tickets_found[:4]:
                    cat_cls, dot_cls = CAT_COLORS.get(t['cat'], ('', ''))
                    chips_html += f'<span class="ticket-chip {cat_cls}"><span class="ticket-dot {dot_cls}"></span>{t["ref"]} — {t["cat"]}</span>'
                st.markdown(f'<div style="margin-bottom:8px">{chips_html}</div>', unsafe_allow_html=True)
        st.markdown(msg["content"])


# ── Exemples si conversation vide
if not st.session_state.messages:
    st.markdown("**Décrivez votre panne pour obtenir un diagnostic :**")

    examples = [
        "Variateur ACS880 défaut F-02 après 30 min",
        "Vibrations 8 mm/s sur bâti moteur",
        "Écran SUPREME pixels morts gare retour",
        "Pression hydraulique 85 bar au lieu de 120",
        "Perte communication fibre entre gares",
        "Anémomètre valeurs incohérentes au sommet",
    ]

    cols = st.columns(2)
    for i, ex in enumerate(examples):
        with cols[i % 2]:
            if st.button(f"💬 {ex}", key=f"ex_{i}", use_container_width=True):
                st.session_state.pending_example = ex
                st.rerun()


# ── Gestion des exemples cliqués
if "pending_example" in st.session_state:
    prompt = st.session_state.pending_example
    del st.session_state.pending_example
else:
    prompt = st.chat_input("Décrivez votre panne ou posez votre question...")


# ── Traitement du message
if prompt:
    # Vérifier clé API
    if not api_key:
        st.error("⚠️ Entrez votre clé API OpenAI dans la barre latérale à gauche.")
        st.stop()

    # Afficher message utilisateur
    with st.chat_message("user", avatar="👷"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Recherche tickets similaires
    similar = search_tickets(prompt, tickets)
    enriched = enrich_message(prompt)

    # Construire le contexte
    context = "\n---\n".join([
        f"TICKET {t['ref']} | {t['install']} ({t['station']}) | {t['equip']} | Code: {t['code'] or 'N/A'}\n"
        f"Problème: {t['objet']}\nDescription: {t['desc']}\nSolution: {t['solution']}"
        for t in similar
    ]) if similar else "Aucun ticket similaire trouvé."

    # Préparer les messages API
    api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
    api_messages.append({
        "role": "user",
        "content": f"{enriched}\n\n[TICKETS SIMILAIRES]\n{context}"
    })

    # Appel API
    with st.chat_message("assistant", avatar="🏔️"):
        # Afficher tickets trouvés
        if similar:
            chips_html = ""
            for t in similar[:4]:
                cat_cls, dot_cls = CAT_COLORS.get(t['cat'], ('', ''))
                chips_html += f'<span class="ticket-chip {cat_cls}"><span class="ticket-dot {dot_cls}"></span>{t["ref"]} — {t["cat"]}</span>'
            st.markdown(f'<div style="margin-bottom:8px">{chips_html}</div>', unsafe_allow_html=True)

        with st.spinner("Analyse en cours..."):
            try:
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + api_messages,
                    temperature=0,
                    max_tokens=2000,
                    stream=True
                )

                # Streaming de la réponse
                reply = st.write_stream(response)

            except Exception as e:
                reply = f"❌ Erreur : {str(e)}"
                st.error(reply)

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply,
        "tickets_found": similar
    })
