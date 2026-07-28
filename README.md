# Eventi Agosto 2026 — App Streamlit

App per tenere traccia degli eventi con gli amici e vedere chi ci sarà.

## Contenuto
- `app.py` — l'applicazione Streamlit
- `eventi-agosto-2026.ics` — il file con gli eventi (puoi modificarlo per aggiungere/cambiare eventi)
- `presenze.json` — si crea automaticamente e contiene le risposte di tutti (chi partecipa a cosa)
- `requirements.txt` — dipendenze

## Come avviarla in locale
```bash
pip install -r requirements.txt
streamlit run app.py
```
Si apre su `http://localhost:8501`.

## Come condividerla con gli amici (link unico)
Per avere un vero link condiviso a cui accedete tutti, serve pubblicarla online. Il modo più semplice e gratuito:

1. Crea un repository GitHub (anche privato) e carica dentro questi 3 file: `app.py`, `eventi-agosto-2026.ics`, `requirements.txt`.
2. Vai su **share.streamlit.io** (Streamlit Community Cloud), accedi con GitHub e collega il repository.
3. Deploy: in pochi minuti ottieni un link tipo `https://tuonome-eventi.streamlit.app` da condividere nel gruppo.

**Nota importante sulla persistenza:** i dati vengono salvati in un file (`presenze.json`) sullo stesso server dell'app. Su Streamlit Community Cloud questo funziona bene finché l'app resta attiva, ma un riavvio/redeploy dell'app può azzerare le risposte salvate. Per un gruppo di amici va benissimo così; se in futuro vuoi qualcosa di più permanente si può collegare un Google Sheet o un piccolo database — basta chiedere.

## Come modificare gli eventi
Basta modificare il file `eventi-agosto-2026.ics` (aggiungere blocchi `BEGIN:VEVENT ... END:VEVENT`) oppure sostituirlo con una nuova esportazione da Google Calendar/Apple Calendar. L'app rilegge il file ad ogni apertura, quindi non serve toccare il codice.
