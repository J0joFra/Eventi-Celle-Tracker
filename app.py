import streamlit as st
import json
import re
from pathlib import Path
from datetime import datetime

# -----------------------------
# Config
# -----------------------------
ICS_FILE = Path(__file__).parent / "eventi-agosto-2026.ics"
DATA_FILE = Path(__file__).parent / "presenze.json"

st.set_page_config(page_title="Eventi Agosto 2026", page_icon="📅", layout="centered")

MESI_IT = [
    "", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"
]


# -----------------------------
# Parsing ICS (senza dipendenze esterne)
# -----------------------------
def parse_ics(path: Path):
    text = path.read_text(encoding="utf-8")
    # unfold delle righe (le righe continuate iniziano con uno spazio)
    text = text.replace("\r\n", "\n")
    lines = []
    for line in text.split("\n"):
        if line.startswith(" ") and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)

    events = []
    current = {}
    in_event = False
    for line in lines:
        if line == "BEGIN:VEVENT":
            in_event = True
            current = {}
            continue
        if line == "END:VEVENT":
            in_event = False
            if current:
                events.append(current)
            continue
        if not in_event or ":" not in line:
            continue

        key_part, value = line.split(":", 1)
        key = key_part.split(";")[0]

        if key == "UID":
            current["uid"] = value
        elif key == "SUMMARY":
            current["summary"] = value.replace("\\,", ",").replace("\\;", ";")
        elif key == "DTSTART":
            all_day = "VALUE=DATE" in key_part and "VALUE=DATE-TIME" not in key_part
            current["start_raw"] = value
            current["start_all_day"] = all_day
        elif key == "DTEND":
            all_day = "VALUE=DATE" in key_part and "VALUE=DATE-TIME" not in key_part
            current["end_raw"] = value
            current["end_all_day"] = all_day

    for ev in events:
        ev["start_dt"] = parse_dt(ev.get("start_raw"), ev.get("start_all_day", True))
        ev["end_dt"] = parse_dt(ev.get("end_raw"), ev.get("end_all_day", True))

    events.sort(key=lambda e: e["start_dt"])
    return events


def parse_dt(raw, all_day):
    if raw is None:
        return datetime.min
    raw = raw.rstrip("Z")
    if all_day:
        return datetime.strptime(raw, "%Y%m%d")
    return datetime.strptime(raw, "%Y%m%dT%H%M%S")


def format_date_range(ev):
    start = ev["start_dt"]
    end = ev["end_dt"]

    if ev.get("start_all_day", True):
        # DTEND per gli eventi all-day è esclusivo -> l'ultimo giorno reale è end - 1
        last_day = end
        giorni_evento = (last_day - start).days
        if giorni_evento <= 1:
            return f"{start.day} {MESI_IT[start.month]} {start.year}"
        else:
            last_real_day = last_day
            # end è già il giorno successivo all'ultimo, quindi sottraiamo virtualmente
            from datetime import timedelta
            last_real_day = end - timedelta(days=1)
            if start.month == last_real_day.month:
                return f"{start.day}–{last_real_day.day} {MESI_IT[start.month]} {start.year}"
            else:
                return (f"{start.day} {MESI_IT[start.month]} – "
                        f"{last_real_day.day} {MESI_IT[last_real_day.month]} {start.year}")
    else:
        ora = start.strftime("%H:%M")
        return f"{start.day} {MESI_IT[start.month]} {start.year}, ore {ora}"


# -----------------------------
# Persistenza presenze
# -----------------------------
def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


STATI = ["Ci sono 🟢", "Forse 🟡", "Non ci sono 🔴"]
STATO_COLORI = {"Ci sono 🟢": "🟢", "Forse 🟡": "🟡", "Non ci sono 🔴": "🔴"}


# -----------------------------
# App
# -----------------------------
def main():
    st.title("📅 Eventi Agosto 2026")
    st.caption("Segna la tua presenza per ogni evento. Le modifiche sono visibili a tutti quelli che aprono la pagina.")

    if not ICS_FILE.exists():
        st.error(f"Non trovo il file {ICS_FILE.name} nella cartella dell'app.")
        return

    events = parse_ics(ICS_FILE)
    data = load_data()

    # Nome utente (memorizzato per la sessione del browser)
    with st.sidebar:
        st.header("👤 Chi sei?")
        nome = st.text_input("Il tuo nome", value=st.session_state.get("nome", ""))
        if nome:
            st.session_state["nome"] = nome.strip()
        st.divider()
        st.caption("Suggerimento: usa sempre lo stesso nome così le tue risposte si aggiornano invece di duplicarsi.")

        st.divider()
        with st.expander("📋 Riepilogo partecipanti"):
            tutti_nomi = sorted({n for ev_data in data.values() for n in ev_data.keys()})
            if tutti_nomi:
                for n in tutti_nomi:
                    st.write(f"- {n}")
            else:
                st.write("Nessuno ha ancora risposto.")

    if not st.session_state.get("nome"):
        st.info("👈 Scrivi il tuo nome nella barra laterale per poter segnare la tua presenza.")

    for ev in events:
        uid = ev["uid"]
        summary = ev.get("summary", "Evento senza nome")
        date_str = format_date_range(ev)
        ev_data = data.get(uid, {})

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(summary)
                st.write(f"🗓️ {date_str}")
            with col2:
                presenti = sum(1 for v in ev_data.values() if v == STATI[0])
                st.metric("Confermati", presenti)

            # Riepilogo presenze per stato
            if ev_data:
                for stato in STATI:
                    persone = [n for n, v in ev_data.items() if v == stato]
                    if persone:
                        st.write(f"{STATO_COLORI[stato]} {', '.join(persone)}")
            else:
                st.write("_Ancora nessuna risposta._")

            # Form per rispondere
            nome_corrente = st.session_state.get("nome", "")
            if nome_corrente:
                valore_attuale = ev_data.get(nome_corrente, STATI[1])
                scelta = st.radio(
                    "La tua risposta",
                    STATI,
                    index=STATI.index(valore_attuale) if valore_attuale in STATI else 1,
                    key=f"radio_{uid}",
                    horizontal=True,
                    label_visibility="collapsed",
                )
                if st.button("Salva risposta", key=f"salva_{uid}"):
                    data.setdefault(uid, {})[nome_corrente] = scelta
                    save_data(data)
                    st.success(f"Risposta salvata per {nome_corrente}!")
                    st.rerun()


if __name__ == "__main__":
    main()
