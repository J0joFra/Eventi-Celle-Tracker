import streamlit as st
import json
import calendar as cal
from pathlib import Path
from datetime import datetime, timedelta

# -----------------------------
# Config
# -----------------------------
ICS_FILE = Path(__file__).parent / "eventi-agosto-2026.ics"
DATA_FILE = Path(__file__).parent / "presenze.json"
USERS_FILE = Path(__file__).parent / "utenti.json"

st.set_page_config(page_title="Eventi Agosto 2026", page_icon="📅", layout="centered")

MESI_IT = [
    "", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"
]
GIORNI_IT = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]

STATI = ["Ci sono 🟢", "Forse 🟡", "Non ci sono 🔴"]
STATO_COLORI = {"Ci sono 🟢": "🟢", "Forse 🟡": "🟡", "Non ci sono 🔴": "🔴"}


# -----------------------------
# Parsing ICS (senza dipendenze esterne)
# -----------------------------
def parse_ics(path: Path):
    text = path.read_text(encoding="utf-8")
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
        last_real_day = end - timedelta(days=1)
        if last_real_day <= start:
            return f"{start.day} {MESI_IT[start.month]} {start.year}"
        if start.month == last_real_day.month:
            return f"{start.day}\u2013{last_real_day.day} {MESI_IT[start.month]} {start.year}"
        return (f"{start.day} {MESI_IT[start.month]} \u2013 "
                f"{last_real_day.day} {MESI_IT[last_real_day.month]} {start.year}")
    else:
        ora = start.strftime("%H:%M")
        return f"{start.day} {MESI_IT[start.month]} {start.year}, ore {ora}"


def event_day_range(ev):
    """Restituisce la lista di date (solo giorno) coperte dall'evento."""
    start = ev["start_dt"].date()
    if ev.get("start_all_day", True):
        last_real_day = (ev["end_dt"] - timedelta(days=1)).date()
        if last_real_day < start:
            last_real_day = start
    else:
        last_real_day = start
    giorni = []
    d = start
    while d <= last_real_day:
        giorni.append(d)
        d += timedelta(days=1)
    return giorni


# -----------------------------
# Persistenza JSON generica
# -----------------------------
def load_json(path: Path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def user_key(nome: str, cognome: str) -> str:
    return f"{nome.strip().lower()} {cognome.strip().lower()}"


# -----------------------------
# Login / Registrazione
# -----------------------------
def blocco_login():
    users = load_json(USERS_FILE)

    # se già loggato in questa sessione (o tramite link con ?u=...), salta il form
    if "user_key" not in st.session_state:
        params = st.query_params
        if "u" in params and params["u"] in users:
            st.session_state["user_key"] = params["u"]
            st.session_state["display_name"] = users[params["u"]]["display"]

    if "user_key" in st.session_state:
        return True

    st.subheader("👋 Accedi")
    st.caption("La prima volta che inserisci nome e cognome verrai registrato automaticamente. Le volte successive inserisci di nuovo nome e cognome per accedere.")

    with st.form("login_form"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        submitted = st.form_submit_button("Accedi / Registrati")

    if submitted:
        if not nome.strip() or not cognome.strip():
            st.error("Inserisci sia il nome che il cognome.")
            return False

        key = user_key(nome, cognome)
        display = f"{nome.strip().title()} {cognome.strip().title()}"

        if key not in users:
            users[key] = {"nome": nome.strip().title(), "cognome": cognome.strip().title(), "display": display}
            save_json(USERS_FILE, users)
            st.session_state["_appena_registrato"] = True

        st.session_state["user_key"] = key
        st.session_state["display_name"] = users[key]["display"]
        st.query_params["u"] = key
        st.rerun()

    return False


def blocco_logout():
    with st.sidebar:
        st.write(f"👤 **{st.session_state.get('display_name', '')}**")
        if st.button("Esci"):
            st.session_state.pop("user_key", None)
            st.session_state.pop("display_name", None)
            st.query_params.clear()
            st.rerun()


# -----------------------------
# Calendario mensile
# -----------------------------
def mostra_calendario(events, anno, mese):
    eventi_per_giorno = {}
    for ev in events:
        for giorno in event_day_range(ev):
            if giorno.year == anno and giorno.month == mese:
                eventi_per_giorno.setdefault(giorno.day, []).append(ev.get("summary", ""))

    settimane = cal.Calendar(firstweekday=0).monthdayscalendar(anno, mese)

    css = """
    <style>
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .cal-table th { padding: 6px 2px; font-size: 0.8rem; color: #888; font-weight: 600; }
    .cal-table td { vertical-align: top; border: 1px solid rgba(150,150,150,0.25); height: 78px; padding: 4px; font-size: 0.75rem; }
    .cal-day-num { font-size: 0.85rem; font-weight: 600; opacity: 0.8; }
    .cal-empty { background: transparent; }
    .cal-event { background: #ff4b4b22; border-radius: 4px; padding: 1px 3px; margin-top: 2px; font-size: 0.68rem; line-height: 1.1; overflow: hidden; }
    </style>
    """

    html = css + "<table class='cal-table'><tr>"
    for g in GIORNI_IT:
        html += f"<th>{g}</th>"
    html += "</tr>"

    for settimana in settimane:
        html += "<tr>"
        for giorno in settimana:
            if giorno == 0:
                html += "<td class='cal-empty'></td>"
            else:
                chips = "".join(f"<div class='cal-event'>{s}</div>" for s in eventi_per_giorno.get(giorno, []))
                html += f"<td><div class='cal-day-num'>{giorno}</div>{chips}</td>"
        html += "</tr>"
    html += "</table>"

    st.markdown(html, unsafe_allow_html=True)


# -----------------------------
# App
# -----------------------------
def main():
    st.title("📅 Eventi Agosto 2026")

    if not blocco_login():
        return

    blocco_logout()

    if st.session_state.pop("_appena_registrato", False):
        st.success(f"Benvenuto/a {st.session_state['display_name']}! Ti sei registrato/a ed è stato effettuato l'accesso.")

    if not ICS_FILE.exists():
        st.error(f"Non trovo il file {ICS_FILE.name} nella cartella dell'app.")
        return

    events = parse_ics(ICS_FILE)
    data = load_json(DATA_FILE)
    utente = st.session_state["user_key"]
    nome_visualizzato = st.session_state["display_name"]

    tab_lista, tab_calendario = st.tabs(["📋 Lista eventi", "🗓️ Calendario"])

    with tab_calendario:
        anno_riferimento = events[0]["start_dt"].year if events else datetime.now().year
        mese_riferimento = events[0]["start_dt"].month if events else datetime.now().month
        st.subheader(f"{MESI_IT[mese_riferimento].capitalize()} {anno_riferimento}")
        mostra_calendario(events, anno_riferimento, mese_riferimento)
        st.caption("I giorni con eventi mostrano il nome dell'evento nella cella.")

    with tab_lista:
        st.caption("Segna la tua presenza per ogni evento. Puoi cambiarla o cancellarla in qualsiasi momento rifacendo il login.")

        with st.sidebar:
            st.divider()
            with st.expander("📋 Riepilogo partecipanti registrati"):
                users = load_json(USERS_FILE)
                if users:
                    for u in sorted(users.values(), key=lambda x: x["display"]):
                        st.write(f"- {u['display']}")
                else:
                    st.write("Nessuno ancora registrato.")

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

                if ev_data:
                    for stato in STATI:
                        persone = [n for n, v in ev_data.items() if v == stato]
                        if persone:
                            st.write(f"{STATO_COLORI[stato]} {', '.join(persone)}")
                else:
                    st.write("_Ancora nessuna risposta._")

                valore_attuale = ev_data.get(nome_visualizzato, STATI[1])
                scelta = st.radio(
                    "La tua risposta",
                    STATI,
                    index=STATI.index(valore_attuale) if valore_attuale in STATI else 1,
                    key=f"radio_{uid}",
                    horizontal=True,
                    label_visibility="collapsed",
                )

                bcol1, bcol2 = st.columns([1, 1])
                with bcol1:
                    if st.button("Salva risposta", key=f"salva_{uid}"):
                        data.setdefault(uid, {})[nome_visualizzato] = scelta
                        save_json(DATA_FILE, data)
                        st.success("Risposta salvata!")
                        st.rerun()
                with bcol2:
                    if nome_visualizzato in ev_data:
                        if st.button("🗑️ Cancella la mia risposta", key=f"cancella_{uid}"):
                            data.get(uid, {}).pop(nome_visualizzato, None)
                            save_json(DATA_FILE, data)
                            st.success("Risposta cancellata.")
                            st.rerun()


if __name__ == "__main__":
    main()
