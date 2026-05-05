# 🚡 SNOWPEAK — Agent SAV Télésièges

Chatbot Streamlit de **diagnostic de pannes pour télésièges** propulsé par
**Mistral**, à partir d'une base de tickets SAV stockée dans un **Google
Sheet public** (ou un fichier local `.ods` / `.xlsx` / `.csv` en dev).

Le technicien tape un code erreur ou une description de panne. L'app cherche
les tickets pertinents par mots-clés, les transmet à Mistral avec un prompt
système structuré, et affiche le diagnostic en 3 sections : 📋 Diagnostic
probable · 🔧 Vérifications pas-à-pas · ✅ Procédure de réparation.

---

## 🛠️ Installation locale

```bash
pip install -r requirements.txt
cp .env.example .env
# remplir MISTRAL_API_KEY et SHEET_URL dans .env
streamlit run app.py
# (ou : python -m streamlit run app.py si streamlit n'est pas dans le PATH)
```

Python 3.10+ recommandé.

---

## ⚙️ Variables d'environnement

| Variable | Obligatoire | Description |
|---|---|---|
| `MISTRAL_API_KEY` | ✅ | Clé API Mistral ([console](https://console.mistral.ai/api-keys/)) |
| `SHEET_URL` | ✅ | URL Google Sheet publique **ou** chemin local (`.ods`/`.xlsx`/`.csv`) |
| `SHEET_GID` | non | GID de l'onglet Google Sheets (défaut `0`) |
| `MISTRAL_MODEL` | non | Modèle Mistral (défaut `mistral-large-latest`) |

---

## 🔍 Comment ça marche (5 étapes)

1. **Chargement** — lecture du Google Sheet via export CSV (ou du fichier
   local), avec cache 5 minutes.
2. **Tokenisation** — la requête est découpée en tokens via une regex qui
   préserve les codes type `err-f12`. Les stop-words FR sont écartés.
3. **Recherche par mots-clés** — chaque ligne du sheet est scorée par le
   nombre de tokens présents. On garde les **5 meilleurs tickets**.
4. **Appel Mistral** — la question + les tickets retenus sont envoyés à
   Mistral avec un prompt système qui impose la structure de réponse.
5. **Affichage** — le diagnostic s'affiche en markdown, avec la liste des
   tickets utilisés en expander.

---

## 📊 Format attendu du Google Sheet

Les colonnes sont **flexibles** : l'app concatène toutes les colonnes pour la
recherche. Schéma type utilisé en démo :

| Référence | Station    | Installation     | Type installation | Objet | Description | Code erreur | Solution | … |
|-----------|------------|------------------|-------------------|-------|-------------|-------------|----------|---|
| T-000001  | Les Aigles | TC de l'Aiguille | Télécabine        | …     | …           | (vide)      | …        |   |

> ⚠️ Garde une colonne **Référence** au format `T-XXXXXX` : le prompt système
> demande à Mistral de citer ces références dans son diagnostic.

---

## ☁️ Déploiement sur Streamlit Community Cloud

### 1. Pré-requis
- Compte **GitHub** + repo (public ou privé)
- Compte **Streamlit Cloud** (https://share.streamlit.io, login GitHub)
- **Google Sheet partagé** en *Tous les utilisateurs disposant du lien · Lecteur*

### 2. Pousser le code sur GitHub
```bash
git init
git add .
git commit -m "init: snowpeak-sav v1"
git branch -M main
git remote add origin git@github.com:<ton-user>/snowpeak-sav.git
git push -u origin main
```
Le `.gitignore` exclut automatiquement `.env`, `*.ods` et `secrets.toml`.

### 3. Déployer sur Streamlit Cloud
1. Aller sur https://share.streamlit.io → **New app**
2. Sélectionner le repo, branche `main`, fichier `app.py`
3. **Advanced settings → Secrets** → coller :
   ```toml
   MISTRAL_API_KEY = "..."
   SHEET_URL = "https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit"
   SHEET_GID = "0"
   MISTRAL_MODEL = "mistral-large-latest"
   ```
4. **Deploy** → l'app sera disponible sous `https://<nom>.streamlit.app`

Streamlit Cloud injecte les secrets dans les variables d'environnement, donc
le code (`os.getenv`) fonctionne sans modification.

### 4. Mise à jour
Chaque `git push` redéploie automatiquement.

---

## 🤔 Pourquoi pas de RAG vectoriel ?

Pour ~quelques milliers de tickets, la **recherche par mots-clés** est
suffisante (codes erreur, références matériel, noms de stations matchent en
exact), lisible (on voit pourquoi un ticket est retenu) et débogable (pas
d'index à reconstruire). Au-delà de ~10 000 tickets très hétérogènes, on
pourra envisager un index vectoriel.

---

## 📁 Structure

```
snowpeak-sav/
├── app.py                          # Application Streamlit
├── requirements.txt                # Dépendances pip
├── .env.example                    # Modèle config locale
├── .streamlit/secrets.toml.example # Modèle secrets Streamlit Cloud
├── .gitignore
└── README.md
```
