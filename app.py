import streamlit as st
import json
import hashlib
import calendar as cal
from pathlib import Path
from datetime import datetime, date, time, timedelta

# -----------------------------
# Config
# -----------------------------
ICS_FILE = Path(__file__).parent / "eventi-agosto-2026.ics"
DATA_FILE = Path(__file__).parent / "presenze.json"
USERS_FILE = Path(__file__).parent / "utenti.json"

st.set_page_config(page_title="Eventi", page_icon="📅", layout="centered")

MESI_IT = [
    "", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"
]
GIORNI_IT = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]

STATI = ["Ci sono 🟢", "Forse 🟡", "Non ci sono 🔴"]
STATO_COLORI = {"Ci sono 🟢": "🟢", "Forse 🟡": "🟡", "Non ci sono 🔴": "🔴"}

# Palette di colori distinti (sfondo, colore testo leggibile) per ogni evento
PALETTE = [
    ("#E63946", "#FFFFFF"),
    ("#457B9D", "#FFFFFF"),
    ("#2A9D8F", "#FFFFFF"),
    ("#F4A261", "#1A1A1A"),
    ("#8338EC", "#FFFFFF"),
    ("#FB8500", "#1A1A1A"),
    ("#3A86FF", "#FFFFFF"),
    ("#06D6A0", "#1A1A1A"),
    ("#EF476F", "#FFFFFF"),
    ("#118AB2", "#FFFFFF"),
    ("#FFD166", "#1A1A1A"),
    ("#9B5DE5", "#FFFFFF"),
]


def color_for_uid(uid: str):
    h = int(hashlib.md5(uid.encode("utf-8")).hexdigest(), 16)
    return PALETTE[h % len(PALETTE)]


# -----------------------------
# CSS globale (bottoni presenza colorati)
# -----------------------------
def inject_css():
    st.markdown("""
    <style>
    div[data-testid="stRadio"] > div[role="radiogroup"] {
        gap: 10px;
        flex-wrap: wrap;
    }
    div[data-testid="stRadio"] label {
        border-radius: 8px;
        padding: 10px 16px;
        border: 2px solid transparent;
        font-weight: 700;
        cursor: pointer;
        transition: transform 0.05s ease-in-out;
    }
    div[data-testid="stRadio"] label:nth-of-type(1) {
        background-color: #2a9d3f;
        color: #ffffff;
    }
    div[data-testid="stRadio"] label:nth-of-type(2) {
        background-color: #e9c000;
        color: #1a1a1a;
    }
    div[data-testid="stRadio"] label:nth-of-type(3) {
        background-color: #d62828;
        color: #ffffff;
    }
    div[data-testid="stRadio"] label:has(input:checked) {
        border-color: #1a1a1a;
        box-shadow: 0 0 0 2px rgba(0,0,0,0.35);
        transform: scale(1.03);
    }
    div[data-testid="stRadio"] label p {
        color: inherit !important;
        font-weight: 700 !important;
    }
    </style>
    """, unsafe_allow_html=True)


# -----------------------------
# Parsing / serializzazione ICS
# -----------------------------
def escape_ics_text(text: str) -> str:
    return (text.replace("\\", "\\\\")
                .replace("\n", "\\n")
                .replace(",", "\\,")
                .replace(";", "\\;"))


def unescape_ics_text(text: str) -> str:
    return (text.replace("\\n", "\n")
                .replace("\\,", ",")
                .replace("\\;", ";")
                .replace("\\\\", "\\"))


def parse_ics(path: Path):
    """Ritorna una lista di eventi in forma canonica:
    uid, summary, description, all_day, start_date, end_date (incluso), start_time, end_time
    """
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n")
    lines = []
    for line in text.split("\n"):
        if line.startswith(" ") and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)

    raw_events = []
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
                raw_events.append(current)
            continue
        if not in_event or ":" not in line:
            continue

        key_part, value = line.split(":", 1)
        key = key_part.split(";")[0]

        if key == "UID":
            current["uid"] = value
        elif key == "SUMMARY":
            current["summary"] = unescape_ics_text(value)
        elif key == "DESCRIPTION":
            current["description"] = unescape_ics_text(value)
        elif key == "DTSTART":
            all_day = "VALUE=DATE" in key_part and "VALUE=DATE-TIME" not in key_part
            current["start_raw"] = value
            current["start_all_day"] = all_day
        elif key == "DTEND":
            all_day = "VALUE=DATE" in key_part and "VALUE=DATE-TIME" not in key_part
            current["end_raw"] = value
            current["end_all_day"] = all_day

    events = []
    for ev in raw_events:
        start_dt = parse_dt_raw(ev.get("start_raw"), ev.get("start_all_day", True))
        end_dt = parse_dt_raw(ev.get("end_raw"), ev.get("end_all_day", True))
        all_day = ev.get("start_all_day", True)

        if all_day:
            start_date = start_dt.date()
            end_date_incl = (end_dt - timedelta(days=1)).date() if end_dt else start_date
            if end_date_incl < start_date:
                end_date_incl = start_date
            start_time = None
            end_time = None
        else:
            start_date = start_dt.date()
            end_date_incl = end_dt.date() if end_dt else start_date
            start_time = start_dt.time()
            end_time = end_dt.time() if end_dt else start_time

        events.append({
            "uid": ev.get("uid", ""),
            "summary": ev.get("summary", "Evento senza nome"),
            "description": ev.get("description", ""),
            "all_day": all_day,
            "start_date": start_date,
            "end_date": end_date_incl,
            "start_time": start_time,
            "end_time": end_time,
        })

    events.sort(key=lambda e: (e["start_date"], e["start_time"] or time.min))
    return events


def parse_dt_raw(raw, all_day):
    if raw is None:
        return None
    raw = raw.rstrip("Z")
    if all_day:
        return datetime.strptime(raw, "%Y%m%d")
    return datetime.strptime(raw, "%Y%m%dT%H%M%S")


def save_ics(events):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Eventi//IT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Eventi",
    ]
    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    for ev in events:
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{ev['uid']}")
        lines.append(f"DTSTAMP:{now_stamp}")
        if ev["all_day"]:
            start_str = ev["start_date"].strftime("%Y%m%d")
            end_str = (ev["end_date"] + timedelta(days=1)).strftime("%Y%m%d")
            lines.append(f"DTSTART;VALUE=DATE:{start_str}")
            lines.append(f"DTEND;VALUE=DATE:{end_str}")
        else:
            start_dt = datetime.combine(ev["start_date"], ev["start_time"])
            end_dt = datetime.combine(ev["end_date"], ev["end_time"])
            lines.append(f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}")
            lines.append(f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}")
        lines.append(f"SUMMARY:{escape_ics_text(ev['summary'])}")
        if ev.get("description"):
            lines.append(f"DESCRIPTION:{escape_ics_text(ev['description'])}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    ICS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def new_uid(summary: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in summary.lower()).strip("-")
    return f"{slug or 'evento'}-{int(datetime.now().timestamp())}@local"


def format_date_range(ev):
    start = ev["start_date"]
    end = ev["end_date"]

    if ev["all_day"]:
        if end <= start:
            return f"{start.day} {MESI_IT[start.month]} {start.year}"
        if start.month == end.month:
            return f"{start.day}\u2013{end.day} {MESI_IT[start.month]} {start.year}"
        return f"{start.day} {MESI_IT[start.month]} \u2013 {end.day} {MESI_IT[end.month]} {start.year}"
    else:
        ora_i = ev["start_time"].strftime("%H:%M") if ev["start_time"] else ""
        ora_f = ev["end_time"].strftime("%H:%M") if ev["end_time"] else ""
        base = f"{start.day} {MESI_IT[start.month]} {start.year}, ore {ora_i}"
        if ora_f and ora_f != ora_i:
            base += f"\u2013{ora_f}"
        return base


def event_day_range(ev):
    giorni = []
    d = ev["start_date"]
    while d <= ev["end_date"]:
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

    if "user_key" not in st.session_state:
        params = st.query_params
        if "u" in params and params["u"] in users:
            st.session_state["user_key"] = params["u"]
            st.session_state["display_name"] = users[params["u"]]["display"]

    if "user_key" in st.session_state:
        return True

    st.subheader("👋 Accedi")
    st.caption("La prima volta che inserisci nome e cognome verrai registrato automaticamente. "
               "Le volte successive inserisci di nuovo nome e cognome per accedere.")

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


def blocco_logout_e_admin():
    with st.sidebar:
        st.write(f"👤 **{st.session_state.get('display_name', '')}**")
        if st.button("Esci"):
            st.session_state.pop("user_key", None)
            st.session_state.pop("display_name", None)
            st.query_params.clear()
            st.rerun()
        st.divider()
        st.session_state["admin_mode"] = st.checkbox(
            "🔧 Modalità admin",
            value=st.session_state.get("admin_mode", False),
            help="In modalità admin puoi aggiungere, modificare ed eliminare eventi.",
        )


# -----------------------------
# Calendario mensile
# -----------------------------
def mostra_calendario(events):
    if "cal_anno" not in st.session_state or "cal_mese" not in st.session_state:
        if events:
            st.session_state["cal_anno"] = events[0]["start_date"].year
            st.session_state["cal_mese"] = events[0]["start_date"].month
        else:
            oggi = date.today()
            st.session_state["cal_anno"] = oggi.year
            st.session_state["cal_mese"] = oggi.month

    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        if st.button("◀", key="mese_prec"):
            m = st.session_state["cal_mese"] - 1
            a = st.session_state["cal_anno"]
            if m < 1:
                m, a = 12, a - 1
            st.session_state["cal_mese"], st.session_state["cal_anno"] = m, a
            st.rerun()
    with c2:
        st.markdown(
            f"<h4 style='text-align:center'>{MESI_IT[st.session_state['cal_mese']].capitalize()} "
            f"{st.session_state['cal_anno']}</h4>",
            unsafe_allow_html=True,
        )
    with c3:
        if st.button("▶", key="mese_succ"):
            m = st.session_state["cal_mese"] + 1
            a = st.session_state["cal_anno"]
            if m > 12:
                m, a = 1, a + 1
            st.session_state["cal_mese"], st.session_state["cal_anno"] = m, a
            st.rerun()

    anno = st.session_state["cal_anno"]
    mese = st.session_state["cal_mese"]

    eventi_per_giorno = {}
    for ev in events:
        bg, txt = color_for_uid(ev["uid"])
        for giorno in event_day_range(ev):
            if giorno.year == anno and giorno.month == mese:
                eventi_per_giorno.setdefault(giorno.day, []).append((ev["summary"], bg, txt))

    settimane = cal.Calendar(firstweekday=0).monthdayscalendar(anno, mese)

    css = """
    <style>
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .cal-table th { padding: 6px 2px; font-size: 0.8rem; color: #888; font-weight: 600; }
    .cal-table td { vertical-align: top; border: 1px solid rgba(150,150,150,0.25); height: 82px; padding: 4px; font-size: 0.75rem; }
    .cal-day-num { font-size: 0.85rem; font-weight: 600; opacity: 0.8; }
    .cal-empty { background: transparent; }
    .cal-event { border-radius: 4px; padding: 1px 4px; margin-top: 2px; font-size: 0.66rem; line-height: 1.15; font-weight: 600; overflow: hidden; }
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
                chips = "".join(
                    f"<div class='cal-event' style='background:{bg};color:{txt}'>{s}</div>"
                    for s, bg, txt in eventi_per_giorno.get(giorno, [])
                )
                html += f"<td><div class='cal-day-num'>{giorno}</div>{chips}</td>"
        html += "</tr>"
    html += "</table>"

    st.markdown(html, unsafe_allow_html=True)


# -----------------------------
# Form di modifica/creazione evento (admin)
# -----------------------------
def form_evento(events, ev=None, key_suffix="new"):
    is_edit = ev is not None
    default_summary = ev["summary"] if is_edit else ""
    default_desc = ev["description"] if is_edit else ""
    default_all_day = ev["all_day"] if is_edit else True
    default_start = ev["start_date"] if is_edit else date.today()
    default_end = ev["end_date"] if is_edit else date.today()
    default_start_time = ev["start_time"] if (is_edit and ev["start_time"]) else time(18, 0)
    default_end_time = ev["end_time"] if (is_edit and ev["end_time"]) else time(19, 0)

    with st.form(f"form_evento_{key_suffix}"):
        summary = st.text_input("Titolo evento", value=default_summary)
        all_day = st.checkbox("Evento senza orario preciso (tutto il giorno)", value=default_all_day,
                               key=f"allday_{key_suffix}")
        c1, c2 = st.columns(2)
        start_date_in = c1.date_input("Data inizio", value=default_start, key=f"start_{key_suffix}")
        end_date_in = c2.date_input("Data fine", value=default_end, key=f"end_{key_suffix}")

        if not all_day:
            c3, c4 = st.columns(2)
            start_time_in = c3.time_input("Ora inizio", value=default_start_time, key=f"stime_{key_suffix}")
            end_time_in = c4.time_input("Ora fine", value=default_end_time, key=f"etime_{key_suffix}")
        else:
            start_time_in = None
            end_time_in = None

        description = st.text_area(
            "Descrizione / note / link",
            value=default_desc,
            placeholder="Es. Portare la torta! Link: https://maps.google.com/...",
            key=f"desc_{key_suffix}",
        )

        submitted = st.form_submit_button("💾 Salva modifiche" if is_edit else "➕ Aggiungi evento")

    if submitted:
        if not summary.strip():
            st.error("Il titolo dell'evento non può essere vuoto.")
            return False
        if end_date_in < start_date_in:
            st.error("La data di fine non può essere prima della data di inizio.")
            return False

        new_ev = {
            "uid": ev["uid"] if is_edit else new_uid(summary),
            "summary": summary.strip(),
            "description": description.strip(),
            "all_day": all_day,
            "start_date": start_date_in,
            "end_date": end_date_in,
            "start_time": start_time_in,
            "end_time": end_time_in,
        }

        if is_edit:
            for i, e in enumerate(events):
                if e["uid"] == ev["uid"]:
                    events[i] = new_ev
                    break
        else:
            events.append(new_ev)

        save_ics(events)
        st.success("Evento salvato!")
        st.rerun()

    return False


# -----------------------------
# App
# -----------------------------
def main():
    inject_css()
    st.title("📅 Eventi")

    if not blocco_login():
        return

    blocco_logout_e_admin()

    if st.session_state.pop("_appena_registrato", False):
        st.success(f"Benvenuto/a {st.session_state['display_name']}! Ti sei registrato/a ed è stato effettuato l'accesso.")

    events = parse_ics(ICS_FILE)
    data = load_json(DATA_FILE)
    nome_visualizzato = st.session_state["display_name"]
    admin = st.session_state.get("admin_mode", False)

    tab_lista, tab_calendario = st.tabs(["📋 Lista eventi", "🗓️ Calendario"])

    with tab_calendario:
        mostra_calendario(events)
        st.caption("I giorni con eventi mostrano il nome dell'evento colorato nella cella. Usa ◀ ▶ per cambiare mese.")

    with tab_lista:
        st.caption("Segna la tua presenza per ogni evento. Puoi cambiarla o cancellarla in qualsiasi momento.")

        with st.sidebar:
            st.divider()
            with st.expander("📋 Partecipanti registrati"):
                users = load_json(USERS_FILE)
                if users:
                    for u in sorted(users.values(), key=lambda x: x["display"]):
                        st.write(f"- {u['display']}")
                else:
                    st.write("Nessuno ancora registrato.")

        if admin:
            with st.expander("➕ Aggiungi nuovo evento", expanded=False):
                form_evento(events, ev=None, key_suffix="new")

        if not events:
            st.info("Nessun evento presente. " + ("Aggiungine uno qui sopra!" if admin else ""))

        for ev in events:
            uid = ev["uid"]
            summary = ev["summary"]
            date_str = format_date_range(ev)
            ev_data = data.get(uid, {})
            bg, txt = color_for_uid(uid)

            with st.container(border=True):
                st.markdown(
                    f"<div style='background:{bg};color:{txt};display:inline-block;"
                    f"padding:6px 14px;border-radius:8px;font-weight:800;font-size:1.1rem;"
                    f"margin-bottom:6px;'>{summary}</div>",
                    unsafe_allow_html=True,
                )
                st.write(f"🗓️ {date_str}")
                if ev.get("description"):
                    st.markdown(ev["description"])

                col1, col2 = st.columns([3, 1])
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

                if admin:
                    with st.expander("✏️ Modifica evento (admin)"):
                        form_evento(events, ev=ev, key_suffix=uid)
                        conferma = st.checkbox("Conferma di voler eliminare questo evento", key=f"conf_del_{uid}")
                        if st.button("🗑️ Elimina evento", key=f"elimina_{uid}", disabled=not conferma):
                            events = [e for e in events if e["uid"] != uid]
                            save_ics(events)
                            data.pop(uid, None)
                            save_json(DATA_FILE, data)
                            st.success("Evento eliminato.")
                            st.rerun()


if __name__ == "__main__":
    main()
