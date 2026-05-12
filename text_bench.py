#!/usr/bin/env python3
"""text_bench.py — 5 task elaborazione testi italiano per modelli LLM locali.

Tasks: summarization, NER, sentiment classification, translation IT→EN, info extraction.
Each scored as X/N tokens-present or structural-valid. Tied to /v1/chat/completions :1234.
"""
from __future__ import annotations
import argparse, json, re, sys, textwrap, time, urllib.request

URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL = "x"
MAX_TOKENS = 800
TEMP = 0.0


def call(prompt: str, max_tokens: int = MAX_TOKENS) -> tuple[str, float]:
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": TEMP, "seed": 42,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.loads(r.read())
        return d["choices"][0]["message"].get("content") or "", time.time() - t0
    except Exception as e:
        return f"<<ERR: {e}>>", time.time() - t0


# ----- Task 1: Summarization (Italian news) -----
NEWS = textwrap.dedent("""
La Banca Centrale Europea ha annunciato ieri a Francoforte un nuovo taglio dei tassi
di interesse di 25 punti base, portando il tasso di riferimento al 2,75%. La presidente
Christine Lagarde ha motivato la decisione con il rallentamento dell'inflazione,
ora al 2,1% nell'area euro, e con i segnali di debolezza dell'economia tedesca.
Il PIL della Germania si è contratto dello 0,3% nell'ultimo trimestre del 2025.
Gli analisti di Goldman Sachs e Deutsche Bank prevedono ulteriori tagli nei prossimi
sei mesi, con il tasso che potrebbe scendere fino all'1,75% entro luglio 2026.
I mercati hanno reagito positivamente: il DAX di Francoforte ha guadagnato il 1,4%
e l'euro è sceso a 1,03 sul dollaro. Il prossimo meeting del consiglio direttivo BCE
è previsto per il 6 marzo 2026.
""").strip()

SUMM_PROMPT = (f"Riassumi in massimo 3 frasi questo testo, mantenendo i fatti chiave "
               f"(istituzioni, numeri, date):\n\n{NEWS}")
SUMM_REQUIRED = ["BCE", "Lagarde", "25", "2,75", "2,1", "Germania"]  # 6 facts


def score_summarization(text: str) -> tuple[int, int, list]:
    norm = text.replace("’", "'").replace("–", "-").replace(" ", " ")
    missing = [t for t in SUMM_REQUIRED if t not in norm]
    # Try alternative forms for numbers
    if "25" in missing and ("0,25" in norm or "venticinque" in norm.lower()):
        missing.remove("25")
    if "2,75" in missing and "2.75" in norm:
        missing.remove("2,75")
    if "2,1" in missing and ("2.1" in norm or "2,1%" in norm):
        missing.remove("2,1")
    return len(SUMM_REQUIRED) - len(missing), len(SUMM_REQUIRED), missing


# ----- Task 2: NER (named entity recognition, structured JSON) -----
NER_TEXT = textwrap.dedent("""
Il 14 marzo 2026, Marco Rossi, CEO di Edilcasa Srl, ha incontrato a Milano
Giulia Bianchi, direttrice di Banca Intesa Sanpaolo. Hanno discusso l'apertura
di un finanziamento da 2 milioni di euro per il nuovo stabilimento di Bergamo.
""").strip()

NER_PROMPT = (f"Estrai le entità nominate dal seguente testo in formato JSON puro "
              f"(no spiegazioni, no markdown), con chiavi 'persone', 'organizzazioni', "
              f"'luoghi', 'date'. Ogni chiave deve contenere una lista di stringhe.\n\n{NER_TEXT}")
NER_PERSONS = {"Marco Rossi", "Giulia Bianchi"}
NER_ORGS = {"Edilcasa", "Banca Intesa Sanpaolo"}
NER_PLACES = {"Milano", "Bergamo"}
NER_DATES = {"14 marzo 2026", "marzo 2026", "14/03/2026", "14-03-2026"}


def score_ner(text: str) -> tuple[int, int, list]:
    # Try parse JSON
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return 0, 4, ["no_json"]
    try:
        data = json.loads(m.group())
    except Exception:
        return 0, 4, ["invalid_json"]
    score = 0
    missing = []
    persons = " ".join(str(x) for x in data.get("persone", []))
    if any(p in persons for p in NER_PERSONS): score += 1
    else: missing.append("persone")
    orgs = " ".join(str(x) for x in data.get("organizzazioni", []))
    if any(o in orgs for o in NER_ORGS): score += 1
    else: missing.append("organizzazioni")
    places = " ".join(str(x) for x in data.get("luoghi", []))
    if all(p in places for p in NER_PLACES): score += 1
    else: missing.append("luoghi")
    dates = " ".join(str(x) for x in data.get("date", []))
    if any(d in dates for d in NER_DATES): score += 1
    else: missing.append("date")
    return score, 4, missing


# ----- Task 3: Sentiment classification (5 items) -----
REVIEWS = [
    ("Servizio eccellente, consegna rapida e prodotto perfetto.", "positivo"),
    ("Pessima esperienza, non risponderò mai più ai loro contatti.", "negativo"),
    ("Il prodotto era ok, niente di che, abbastanza nella media.", "neutro"),
    ("Veramente terribile, sconsigliato, ho perso soldi e tempo.", "negativo"),
    ("Sono stupita dalla qualità, supera ogni aspettativa.", "positivo"),
]
EXPECTED_LABELS = [r[1] for r in REVIEWS]
SENT_PROMPT = ("Per ogni recensione, scrivi una sola riga 'N: LABEL' dove LABEL è "
               "esattamente uno di {positivo, negativo, neutro}. Niente spiegazioni.\n\n" +
               "\n".join(f"{i+1}. {r[0]}" for i, r in enumerate(REVIEWS)))


def score_sentiment(text: str) -> tuple[int, int, list]:
    lines = text.lower().splitlines()
    score = 0
    missing = []
    for i, expected in enumerate(EXPECTED_LABELS):
        found = False
        for line in lines:
            if re.match(rf"^\s*{i+1}\s*[.:)]", line.strip()) and expected in line:
                found = True
                break
        if found: score += 1
        else: missing.append(f"item{i+1}")
    return score, 5, missing


# ----- Task 4: Translation IT→EN -----
IT_TEXT = textwrap.dedent("""
Il piccolo gatto nero saltò agilmente sul davanzale della finestra,
guardando attentamente gli uccelli che volavano nel giardino sotto la pioggia.
""").strip()
TR_PROMPT = f"Traduci in inglese mantenendo significato e struttura:\n\n{IT_TEXT}"
TR_REQUIRED = ["small", "black cat", "windowsill", "watch", "bird", "garden", "rain"]


def score_translation(text: str) -> tuple[int, int, list]:
    low = text.lower()
    # Allow synonyms
    syn = {"small": ["little", "tiny", "small"],
           "black cat": ["black cat"],
           "windowsill": ["windowsill", "window sill", "ledge", "sill"],
           "watch": ["watch", "look", "observ", "gaz", "stare"],
           "bird": ["bird"],
           "garden": ["garden", "yard"],
           "rain": ["rain"]}
    score = 0
    missing = []
    for key, alts in syn.items():
        if any(a in low for a in alts): score += 1
        else: missing.append(key)
    return score, len(syn), missing


# ----- Task 5: Info extraction (invoice fields, structured JSON) -----
INVOICE = textwrap.dedent("""
FATTURA N. 2026/0142
Data emissione: 28 febbraio 2026
Fornitore: Acme Sistemi Srl, P.IVA 04567890123
Cliente: Studio Legale Bianchi, P.IVA 12345678901
Imponibile: 1.500,00 EUR
IVA 22%: 330,00 EUR
TOTALE: 1.830,00 EUR
Modalità pagamento: bonifico bancario a 30 giorni
""").strip()
INV_PROMPT = (f"Estrai i campi dalla seguente fattura in JSON puro (no markdown, no testo extra), "
              f"chiavi: 'numero', 'data', 'fornitore', 'piva_fornitore', 'cliente', 'piva_cliente', "
              f"'imponibile_eur', 'iva_eur', 'totale_eur'.\n\n{INVOICE}")


def score_invoice(text: str) -> tuple[int, int, list]:
    m = re.search(r"\{[\s\S]*\}", text)
    if not m: return 0, 9, ["no_json"]
    try:
        d = json.loads(m.group())
    except Exception:
        return 0, 9, ["invalid_json"]
    score = 0
    missing = []
    checks = [
        ("numero", "2026/0142"),
        ("data", "28"),  # any form of 28 feb
        ("fornitore", "Acme"),
        ("piva_fornitore", "04567890123"),
        ("cliente", "Bianchi"),
        ("piva_cliente", "12345678901"),
        ("imponibile_eur", "1500"),  # match 1500 or 1.500 or 1500,00
        ("iva_eur", "330"),
        ("totale_eur", "1830"),
    ]
    for key, marker in checks:
        v = str(d.get(key, ""))
        v_norm = v.replace(".", "").replace(",", "").replace(" ", "")
        if marker.replace(".", "").replace(",", "") in v_norm or marker in v:
            score += 1
        else:
            missing.append(f"{key}={v[:40]}")
    return score, 9, missing


# ----- Runner -----
TASKS = [
    ("summarization", SUMM_PROMPT, score_summarization),
    ("ner_json", NER_PROMPT, score_ner),
    ("sentiment_5", SENT_PROMPT, score_sentiment),
    ("translation_it_en", TR_PROMPT, score_translation),
    ("invoice_extraction", INV_PROMPT, score_invoice),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--save", default=None)
    args = ap.parse_args()

    total_score = 0
    total_max = 0
    total_time = 0.0
    per_task = []
    print(f"== text_bench label={args.label} ==")
    for name, prompt, scorer in TASKS:
        resp, t = call(prompt)
        score, mx, miss = scorer(resp)
        total_score += score
        total_max += mx
        total_time += t
        per_task.append({"task": name, "score": score, "total": mx, "time_s": round(t, 2), "missing": miss})
        print(f"  {name:22s} -> {score}/{mx} ({t:.2f}s)  missing={miss}")
    print(f"\nTOTAL: {total_score}/{total_max}  time={total_time:.2f}s")
    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump({"label": args.label, "total_score": total_score, "total_max": total_max,
                       "total_time_s": total_time, "per_task": per_task}, f, indent=2)
    return 0 if total_score == total_max else 2


if __name__ == "__main__":
    sys.exit(main())
