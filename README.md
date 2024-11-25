# Allegro IO - Code Assistant

Un assistente di codice intelligente basato su Streamlit che utilizza modelli LLM (O1 e Claude) per analisi del codice, debug e suggerimenti architetturali.

## 🚀 Caratteristiche

- 💻 Supporto multi-file e ZIP
- 🤖 Auto-selezione del modello LLM più appropriato
- 📝 Templates predefiniti per review, debug e analisi
- ⚡ Caching intelligente per performance ottimali
- 🎨 Syntax highlighting per il codice

## 🛠️ Setup

1. Clona il repository:
```bash
git clone [repository-url]
cd allegro-io
```

2. Crea e attiva un ambiente virtuale:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
venv\Scripts\activate  # Windows
```

3. Installa le dipendenze:
```bash
pip install -r requirements.txt
```

4. Copia il file .env.example in .env e configura le tue API keys:
```bash
cp .env.example .env
```

5. Avvia l'applicazione:
```bash
streamlit run src/main.py
```

## 🎯 Utilizzo

1. Upload del codice (file singoli o ZIP)
2. Seleziona un template o scrivi una domanda
3. Ottieni analisi e suggerimenti in tempo reale

## 📊 Modelli Supportati

- **O1-preview**: Per task complessi e analisi architetturale
- **O1-mini**: Per quick fixes e debugging veloce
- **Claude 3.5 Sonnet**: Per analisi approfondite e spiegazioni dettagliate

## 🤝 Contribuire

Sei interessato a contribuire? Ottimo! 
1. Fai un fork del repository
2. Crea un branch per la tua feature
3. Committa i tuoi cambiamenti
4. Apri una Pull Request

## 📝 License

MIT License. Vedi il file `LICENSE` per i dettagli.