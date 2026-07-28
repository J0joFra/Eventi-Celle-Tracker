# Eventi Agosto 2026 — App Streamlit

App per tenere traccia degli eventi con gli amici e vedere chi ci sarà.

## Contenuto
- `app.py` — l'applicazione Streamlit
- `eventi-agosto-2026.ics` — il file con gli eventi (viene modificato automaticamente dalla modalità admin)
- `presenze.json` — si crea automaticamente e contiene le risposte di tutti (chi partecipa a cosa)
- `utenti.json` — si crea automaticamente e contiene l'elenco di chi si è registrato (nome e cognome)
- `requirements.txt` — dipendenze

## Come funziona il login
- La prima volta che qualcuno inserisce Nome e Cognome viene **registrato automaticamente** in `utenti.json`.
- Le volte successive basta reinserire lo **stesso Nome e Cognome** per accedere: non serve una password, nome+cognome fungono da identificativo.
- Una volta loggato, l'utente resta collegato anche ricaricando la pagina. Il bottone **"Esci"** nella barra laterale disconnette.
- Le presenze di ogni evento restano salvate per sempre in `presenze.json`. Ogni volta che si rientra si possono **cambiare** o **cancellare del tutto**.
- I bottoni di risposta (Ci sono / Forse / Non ci sono) sono rettangoli colorati (verde/giallo/rosso) con testo ben leggibile.

## Modalità admin
- Nella barra laterale c'è un interruttore **"🔧 Modalità admin"**: chiunque può attivarlo (non è protetto da password, come richiesto).
- Con la modalità admin attiva, in cima alla lista compare **"➕ Aggiungi nuovo evento"** (titolo, date, orario opzionale, descrizione/note/link).
- Ogni evento mostra un'espansione **"✏️ Modifica evento (admin)"** per cambiare titolo, date, orario e descrizione, oppure per **eliminarlo** (richiede una spunta di conferma per evitare cancellazioni accidentali).
- Ogni modifica riscrive automaticamente il file `eventi-agosto-2026.ics` e ricarica la pagina, quindi resta sempre sincronizzato per tutti.

## Colori
- Ogni evento ha un colore fisso e distinto (assegnato in automatico in base al nome dell'evento), usato sia nell'etichetta del titolo nella lista sia nei riquadri del calendario, per riconoscerlo a colpo d'occhio.

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
Ora non serve più toccare il file a mano: basta attivare la **modalità admin** nella barra laterale e usare i form dentro l'app per aggiungere, modificare o eliminare eventi. Il file `eventi-agosto-2026.ics` viene riscritto automaticamente. Resta comunque possibile modificarlo manualmente se preferisci (es. incollando un'esportazione da Google Calendar/Apple Calendar), l'app lo rilegge ad ogni apertura.
