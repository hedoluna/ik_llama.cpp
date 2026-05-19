"""
Italian Legal Benchmark (IT-LegalBench v0.1)
============================================

Suite custom di 20 quesiti di diritto italiano per valutare LLM su:
- Conoscenza articoli specifici (CC, CP, CPC, CPP, Costituzione, Stat. Lavoratori)
- Comprensione brocardi/latinismi giuridici
- Citation extraction (riconoscere art. da testo)
- Classificazione materia (civile/penale/amministrativo/lavoro/commerciale)
- Applicazione regole (prescrizione, decadenza, calcolo termini)

Scoring deterministico via regex (ogni quesito ha keyword obbligatori).
Pass@1 contro un server llama.cpp/lm-studio compat OpenAI API su porta 18080.

Usage:
  python it_legal_bench.py --base-url http://127.0.0.1:18080 --model italian-legal-qwen
"""
import argparse
import json
import re
import time
from urllib.parse import urljoin
import urllib.request


# 20 quesiti, ognuno con: id, category, prompt, must_match (regex list ANY = at-least-one),
# must_match_all (regex list ALL must appear), forbidden (regex list, none must appear).
BENCH: list[dict] = [
    # ---- A. Articoli specifici (7) ----
    {
        "id": "A1_art2043CC",
        "category": "art_specifico",
        "prompt": "Cosa stabilisce l'articolo 2043 del Codice Civile italiano? Rispondi in massimo 3 frasi.",
        "must_match_all": [r"(?i)\b(danno|responsabilit[aà])\b", r"(?i)\b(colpa|dolo|ingiusto|risarc)"],
        "forbidden": [r"(?i)contratto\s+di\s+lavoro"],
    },
    {
        "id": "A2_art595CP",
        "category": "art_specifico",
        "prompt": "Cosa punisce l'articolo 595 del Codice Penale italiano? Rispondi in massimo 3 frasi.",
        "must_match_all": [r"(?i)\bdiffamaz(ione|atorio)"],
        "forbidden": [r"(?i)\bingiuria\b.{0,20}(esclusivamente|solo|soltanto)"],
    },
    {
        "id": "A3_art416bisCP",
        "category": "art_specifico",
        "prompt": "Cosa disciplina l'articolo 416 bis del Codice Penale italiano? Rispondi in massimo 3 frasi.",
        "must_match_all": [r"(?i)\b(associazion\w+\s+(di\s+tipo\s+)?mafios|mafia|intimidaz)"],
    },
    {
        "id": "A4_art2697CC",
        "category": "art_specifico",
        "prompt": "Cosa stabilisce l'articolo 2697 del Codice Civile in materia di onere della prova? Rispondi in massimo 3 frasi.",
        "must_match_all": [r"(?i)\bonere\s+(della\s+)?prova", r"(?i)\b(fatt[oi]|fonda|costitu)"],
    },
    {
        "id": "A5_art18StatLav",
        "category": "art_specifico",
        "prompt": "Cosa prevede l'articolo 18 dello Statuto dei Lavoratori (legge 300/1970, anche dopo Jobs Act)? Rispondi in massimo 3 frasi.",
        "must_match_all": [r"(?i)\b(licenziamento|reintegra|tutel\w+)"],
    },
    {
        "id": "A6_art32Cost",
        "category": "art_specifico",
        "prompt": "Cosa tutela l'articolo 32 della Costituzione italiana? Rispondi in massimo 3 frasi.",
        "must_match_all": [r"(?i)\b(salute|diritto\s+(fondamentale\s+)?alla\s+salute)"],
    },
    {
        "id": "A7_art1322CC",
        "category": "art_specifico",
        "prompt": "Cosa stabilisce l'articolo 1322 del Codice Civile italiano riguardo all'autonomia contrattuale? Rispondi in massimo 3 frasi.",
        "must_match_all": [r"(?i)\b(autonomia|libert[aà])\b.*\b(contr|negozi)", r"(?i)\b(meritevol|tipic|atipic)"],
    },

    # ---- B. Brocardi/latinismi (4) ----
    {
        "id": "B1_nemo_iudex",
        "category": "brocardo",
        "prompt": "Cosa significa il brocardo latino 'nemo iudex in causa sua' nel diritto processuale? Rispondi in 1-2 frasi.",
        "must_match_all": [r"(?i)\b(nessuno|non).{0,40}\b(giudic|giudice).{0,80}\b(propri[oa]|sua|causa)"],
    },
    {
        "id": "B2_ne_bis_in_idem",
        "category": "brocardo",
        "prompt": "Cosa esprime il principio 'ne bis in idem' nel diritto penale italiano? Rispondi in 1-2 frasi.",
        "must_match_all": [r"(?i)\b(non|nessuno)\b.{0,60}(due\s+volte|nuovamente|secondo|reiterat)", r"(?i)\b(stess[oa]\s+(fatto|reato)|medesim[oa])"],
    },
    {
        "id": "B3_in_dubio_pro_reo",
        "category": "brocardo",
        "prompt": "Cosa significa 'in dubio pro reo' nel processo penale? Rispondi in 1-2 frasi.",
        "must_match_all": [r"(?i)\b(dubbio|incertezza)", r"(?i)\b(imputato|reo|favore|assolu)"],
    },
    {
        "id": "B4_pacta_sunt_servanda",
        "category": "brocardo",
        "prompt": "Cosa esprime il principio 'pacta sunt servanda' nel diritto civile? Rispondi in 1-2 frasi.",
        "must_match_all": [r"(?i)\b(patti|accord|contratt)", r"(?i)\b(osservat|rispettat|adempiut|vincolant|forza\s+di\s+legge)"],
    },

    # ---- C. Citation extraction (3) ----
    {
        "id": "C1_citation_2043",
        "category": "citation",
        "prompt": "Identifica l'articolo principale citato nel seguente testo e rispondi SOLO con il numero dell'articolo e il codice (formato: 'art. NUMERO CODICE'):\n\n\"Il Tribunale ha condannato il convenuto al risarcimento del danno ai sensi dell'art. 2043 del Codice Civile, ritenendo provato il nesso causale tra la condotta colposa e l'evento dannoso.\"",
        "must_match_all": [r"(?i)\bart\.?\s*2043\b.*\b(c\.?\s*c\.?|codice\s+civile)\b"],
        "max_tokens": 60,
    },
    {
        "id": "C2_citation_416bis",
        "category": "citation",
        "prompt": "Identifica l'articolo principale citato nel seguente testo e rispondi SOLO con il numero dell'articolo e il codice (formato: 'art. NUMERO CODICE'):\n\n\"L'imputato è stato rinviato a giudizio per il reato di cui all'art. 416-bis c.p. per aver fatto parte di un'associazione di stampo mafioso operante nel territorio.\"",
        "must_match_all": [r"(?i)\bart\.?\s*416[-\s]?bis\b.*\b(c\.?\s*p\.?|codice\s+penale)\b"],
        "max_tokens": 60,
    },
    {
        "id": "C3_citation_constitution",
        "category": "citation",
        "prompt": "Identifica l'articolo principale della Costituzione citato nel seguente testo e rispondi SOLO con il numero (formato: 'art. NUMERO Cost.'):\n\n\"La Corte ha richiamato l'art. 32 della Costituzione, che tutela la salute come fondamentale diritto dell'individuo e interesse della collettività.\"",
        "must_match_all": [r"(?i)\bart\.?\s*32\b.*(cost|costituzion)"],
        "max_tokens": 60,
    },

    # ---- D. Classificazione materia (3) ----
    {
        "id": "D1_class_civile",
        "category": "classificazione",
        "prompt": "Classifica la seguente questione in UNA delle categorie: civile, penale, amministrativo, lavoro, commerciale. Rispondi SOLO con una parola (la categoria).\n\nQuestione: \"Tizio chiede a Caio il pagamento di 5.000 euro in forza di un contratto di mutuo non onorato.\"",
        "must_match_all": [r"(?i)^\s*civile\s*\.?\s*$|^\s*civile\b"],
        "max_tokens": 20,
    },
    {
        "id": "D2_class_penale",
        "category": "classificazione",
        "prompt": "Classifica la seguente questione in UNA delle categorie: civile, penale, amministrativo, lavoro, commerciale. Rispondi SOLO con una parola (la categoria).\n\nQuestione: \"Caio viene denunciato per aver sottratto un orologio del valore di 2.000 euro dalla vetrina di una gioielleria.\"",
        "must_match_all": [r"(?i)^\s*penale\s*\.?\s*$|^\s*penale\b"],
        "max_tokens": 20,
    },
    {
        "id": "D3_class_lavoro",
        "category": "classificazione",
        "prompt": "Classifica la seguente questione in UNA delle categorie: civile, penale, amministrativo, lavoro, commerciale. Rispondi SOLO con una parola (la categoria).\n\nQuestione: \"Un dipendente impugna il licenziamento intimato dal datore di lavoro per giusta causa, chiedendone la nullità e la reintegra ex art. 18 St. Lav.\"",
        "must_match_all": [r"(?i)^\s*lavoro\s*\.?\s*$|^\s*lavoro\b"],
        "max_tokens": 20,
    },

    # ---- E. Termini / applicazione regole (3) ----
    {
        "id": "E1_prescrizione_ordinaria",
        "category": "applicazione",
        "prompt": "Qual è il termine ordinario di prescrizione dei diritti nel Codice Civile italiano (art. 2946 CC)? Rispondi indicando il numero di anni.",
        "must_match_all": [r"\b10\s*anni\b|\bdieci\s+anni\b"],
        "max_tokens": 100,
    },
    {
        "id": "E2_prescrizione_risarcimento_extracontrattuale",
        "category": "applicazione",
        "prompt": "Qual è il termine di prescrizione del diritto al risarcimento del danno extracontrattuale (art. 2947 CC, fattispecie ordinaria, non da reato)? Rispondi indicando il numero di anni.",
        "must_match_all": [r"\b5\s*anni\b|\bcinque\s+anni\b"],
        "max_tokens": 100,
    },
    {
        "id": "E3_appello_civile_termine",
        "category": "applicazione",
        "prompt": "Qual è il termine breve per proporre appello civile dalla notificazione della sentenza di primo grado (art. 325 CPC)? Rispondi indicando il numero di giorni.",
        "must_match_all": [r"\b30\s*giorni\b|\btrenta\s+giorni\b"],
        "max_tokens": 100,
    },
]


def query(base_url: str, model: str, prompt: str, max_tokens: int = 400, temperature: float = 0.1, timeout: int = 120) -> dict:
    """OpenAI-compatible /v1/chat/completions."""
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "Sei un assistente esperto di diritto italiano. Rispondi in italiano, in modo conciso e tecnicamente accurato. Cita gli articoli quando rilevante."},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "top_p": 0.95,
        "max_tokens": max_tokens,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        urljoin(base_url, "/v1/chat/completions"),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        wall = time.time() - t0
        return {
            "ok": True,
            "wall_s": round(wall, 2),
            "content": data["choices"][0]["message"]["content"],
            "usage": data.get("usage", {}),
        }
    except Exception as e:
        return {"ok": False, "wall_s": round(time.time() - t0, 2), "error": str(e), "content": ""}


def score_response(item: dict, response: str) -> dict:
    """Return {pass: bool, reasons: list[str]}."""
    reasons = []
    if not response:
        return {"pass": False, "reasons": ["empty response"]}
    for pat in item.get("must_match_all", []):
        if not re.search(pat, response):
            reasons.append(f"missing required pattern: {pat}")
    for pat in item.get("must_match", []):
        if not re.search(pat, response):
            reasons.append(f"missing at-least-one pattern: {pat}")
    for pat in item.get("forbidden", []):
        if re.search(pat, response):
            reasons.append(f"contains forbidden pattern: {pat}")
    return {"pass": len(reasons) == 0, "reasons": reasons}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:18080")
    p.add_argument("--model", default="model")
    p.add_argument("--output", default=None, help="JSON output path")
    p.add_argument("--temp", type=float, default=0.1)
    p.add_argument("--limit", type=int, default=None, help="Run only first N items")
    args = p.parse_args()

    results = []
    total_pass = 0
    total = 0
    per_cat: dict[str, dict[str, int]] = {}
    t0 = time.time()

    items = BENCH[: args.limit] if args.limit else BENCH

    for item in items:
        total += 1
        cat = item["category"]
        per_cat.setdefault(cat, {"pass": 0, "total": 0})
        per_cat[cat]["total"] += 1

        max_tok = item.get("max_tokens", 400)
        r = query(args.base_url, args.model, item["prompt"], max_tokens=max_tok, temperature=args.temp)
        score = score_response(item, r.get("content", ""))

        if score["pass"]:
            total_pass += 1
            per_cat[cat]["pass"] += 1

        flag = "PASS" if score["pass"] else "FAIL"
        print(f"[{flag}] {item['id']} ({cat})  wall={r.get('wall_s', 0):.1f}s")
        if not score["pass"]:
            print(f"       reasons: {score['reasons']}")
            print(f"       response: {r.get('content', '')[:200]}")
        results.append({
            "id": item["id"],
            "category": cat,
            "pass": score["pass"],
            "reasons": score["reasons"],
            "wall_s": r.get("wall_s", 0),
            "response": r.get("content", ""),
            "ok": r.get("ok", False),
        })

    wall_total = time.time() - t0
    summary = {
        "model": args.model,
        "base_url": args.base_url,
        "temperature": args.temp,
        "total": total,
        "pass": total_pass,
        "score_pct": round(100 * total_pass / total, 1) if total else 0,
        "wall_total_s": round(wall_total, 1),
        "per_category": {c: {**v, "pct": round(100 * v["pass"] / v["total"], 1)} for c, v in per_cat.items()},
        "results": results,
    }

    print("\n" + "=" * 60)
    print(f"MODEL: {args.model}")
    print(f"SCORE: {total_pass}/{total} ({summary['score_pct']}%)  wall={wall_total:.1f}s")
    print("PER CATEGORY:")
    for c, v in summary["per_category"].items():
        print(f"  {c:18s} {v['pass']}/{v['total']} ({v['pct']}%)")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()
