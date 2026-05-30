"""LexiAssist RAG / statute grounding engine.

This module references ``get_db`` (defined in ``lexi.database``); the
import is performed lazily inside helpers to avoid a circular import.
"""
from __future__ import annotations

from .runtime import st, re


def get_db():
    # Lazy indirection to break import cycle. Functions in this module
    # call get_db() at runtime, never at import time.
    from .database import get_db as _real_get_db
    return _real_get_db()

# ═══════════════════════════════════════════════════════
# PHASE 2 — RAG / STATUTE GROUNDING ENGINE
# ═══════════════════════════════════════════════════════

# ── Seed statute database (key provisions — expand by adding to DB via admin) ──
_STATUTE_SEEDS = [
    # CFRN 1999
    {
        "id": "cfrn_36", "source": "CFRN 1999", "section": "Section 36",
        "content": (
            "Section 36(1) CFRN 1999: In the determination of his civil rights and obligations, "
            "including any question or determination by or against any government or authority, "
            "a person shall be entitled to a fair hearing within a reasonable time by a court or "
            "other tribunal established by law and constituted in such manner as to secure its "
            "independence and impartiality. "
            "Section 36(5): Every person who is charged with a criminal offence shall be "
            "presumed to be innocent until he is proved guilty. "
            "Section 36(6): Every person who is charged with a criminal offence shall be "
            "entitled to be informed promptly in the language he understands and in detail of "
            "the nature of the offence; to be given adequate time and facilities for the "
            "preparation of his defence; to defend himself in person or by legal practitioners "
            "of his own choice."
        ),
        "keywords": "fair hearing,criminal,civil rights,court,tribunal,innocent,presumed,charged,offence,constitution,constitutional,fundamental rights",
    },
    {
        "id": "cfrn_308", "source": "CFRN 1999", "section": "Section 308",
        "content": (
            "Section 308 CFRN 1999 (Executive Immunity): Notwithstanding anything to the contrary "
            "in this Constitution, no civil or criminal proceedings shall be instituted or continued "
            "against a person to whom this section applies during his period of office; "
            "a person to whom this section applies shall not be arrested or imprisoned during that "
            "period either in pursuance of the process of any court or otherwise. "
            "This section applies to a person holding the office of President or Vice-President, "
            "Governor or Deputy Governor."
        ),
        "keywords": "immunity,president,governor,vice president,deputy governor,civil proceedings,criminal proceedings,arrest,section 308,executive immunity",
    },
    {
        "id": "cfrn_44", "source": "CFRN 1999", "section": "Section 44",
        "content": (
            "Section 44(1) CFRN 1999: No moveable property or any interest in an immovable "
            "property shall be taken possession of compulsorily and no right over or interest in "
            "any such property shall be acquired compulsorily in any part of Nigeria except in "
            "the manner and for the purposes prescribed by a law that, among other things, "
            "requires the prompt payment of compensation therefor."
        ),
        "keywords": "compulsory acquisition,property,compensation,moveable,immovable,government acquisition,section 44,takeover",
    },
    # Land Use Act 1978
    {
        "id": "lua_1", "source": "Land Use Act 1978", "section": "Section 1",
        "content": (
            "Section 1 Land Use Act 1978: Subject to the provisions of this Act, all land "
            "comprised in the territory of each State in the Federation are hereby vested in "
            "the Governor of that State and such land shall be held in trust and administered "
            "for the use and common benefit of all Nigerians in accordance with the provisions "
            "of this Act."
        ),
        "keywords": "land use act,governor,vested,territory,state land,occupancy,right of occupancy,LUA",
    },
    {
        "id": "lua_22", "source": "Land Use Act 1978", "section": "Section 22",
        "content": (
            "Section 22 Land Use Act 1978: It shall not be lawful for the holder of a statutory "
            "right of occupancy granted by the Governor to alienate his right of occupancy or "
            "any part thereof by assignment, mortgage, transfer of possession, sublease or "
            "otherwise howsoever without the consent of the Governor first had and obtained. "
            "Any such alienation made without such consent shall be null and void."
        ),
        "keywords": "governor consent,alienation,mortgage,assignment,statutory right of occupancy,null void,land,transfer,sublease",
    },
    {
        "id": "lua_28", "source": "Land Use Act 1978", "section": "Section 28",
        "content": (
            "Section 28 Land Use Act 1978: It shall be lawful for the Governor to revoke a right "
            "of occupancy for overriding public interest. Overriding public interest includes: "
            "the alienation by the occupier by assignment, mortgage, transfer of possession, "
            "sublease or otherwise of his right of occupancy contrary to this Act; "
            "the requirement of the land by the Government of the State for public purposes; "
            "the requirement of the land for mining purposes or oil pipelines or for any purpose "
            "connected with or ancillary to oil mining."
        ),
        "keywords": "revocation,right of occupancy,governor,public interest,public purpose,section 28,land use act,mining",
    },
    # Evidence Act 2011
    {
        "id": "ea_131", "source": "Evidence Act 2011", "section": "Section 131",
        "content": (
            "Section 131 Evidence Act 2011: Whoever desires any court to give judgment as to any "
            "legal right or liability dependent on the existence of facts which he asserts shall "
            "prove that those facts exist. "
            "Section 132: The burden of proof in a suit or proceeding lies on that person who "
            "would fail if no evidence at all were given on either side. "
            "Section 133: In civil cases, the burden of first proving the existence or non-existence "
            "of a fact lies on the party against whom the judgment of the court would be given "
            "if no evidence were produced on either side."
        ),
        "keywords": "burden of proof,evidence act,prove,fact,judgment,civil,he who asserts,onus,standard of proof",
    },
    {
        "id": "ea_29", "source": "Evidence Act 2011", "section": "Section 29",
        "content": (
            "Section 29 Evidence Act 2011: In any proceeding, a confession made by a defendant "
            "may be given in evidence against him insofar as it is relevant to any matter in "
            "issue in the proceedings and is not excluded by the court in pursuance of this section. "
            "If, in any proceeding where the prosecution proposes to give in evidence a confession "
            "made by a defendant, it is represented to the court that the confession was or may "
            "have been obtained by oppression of the person who made it or in consequence of "
            "anything said or done which was likely, in the circumstances existing at the time, "
            "to render unreliable any confession which might be made by him in consequence thereof, "
            "the court shall not allow the confession to be given in evidence against him except "
            "insofar as the prosecution proves to the court beyond reasonable doubt that the "
            "confession was not obtained as aforesaid."
        ),
        "keywords": "confession,confessional statement,admissibility,oppression,voluntariness,criminal,trial within trial,caution,statement",
    },
    # CAMA 2020
    {
        "id": "cama_22", "source": "CAMA 2020", "section": "Section 22",
        "content": (
            "Section 22 CAMA 2020: A private company shall not offer its shares or debentures "
            "to members of the public and shall restrict the right to transfer its shares. "
            "The maximum number of members of a private company shall be fifty, not including "
            "persons who are in the employment of the company and persons who having been formerly "
            "in the employment of the company were while in that employment, and have continued "
            "after the determination of that employment to be, members of the company."
        ),
        "keywords": "private company,shares,members,public offer,transfer restriction,CAMA,company law,50 members",
    },
    {
        "id": "cama_839", "source": "CAMA 2020", "section": "Section 839",
        "content": (
            "Section 839 CAMA 2020: Where it appears that any business of a company is being "
            "carried on with intent to defraud creditors of the company or creditors of any other "
            "person or for any fraudulent purpose, the court, on the application of the "
            "Commission or a liquidator or any creditor or contributory of the company, may "
            "declare that any persons who were knowingly parties to the carrying on of the "
            "business in that manner are to be liable to make such contributions (if any) to "
            "the company's assets as the court thinks proper. This is the fraudulent trading provision."
        ),
        "keywords": "fraudulent trading,creditors,defraud,lifting veil,contribution,liability,directors,section 839,winding up",
    },
    # Labour Act
    {
        "id": "labour_7", "source": "Labour Act Cap L1 LFN 2004", "section": "Section 7",
        "content": (
            "Section 7 Labour Act: Not later than three months after the beginning of a worker's "
            "period of employment, the employer shall give to the worker a written statement "
            "specifying the parties to the contract; the date on which the contract began; "
            "the nature of the employment; if the contract is for a fixed term, the date when "
            "the contract expires; the appropriate pay and the intervals at which it will be paid; "
            "the terms and conditions relating to hours of work, holidays, incapacity for work, "
            "pensions and pension schemes, and notice of termination of employment."
        ),
        "keywords": "employment contract,written statement,labour act,employer,worker,terms,conditions,notice,termination,section 7",
    },
    {
        "id": "labour_11", "source": "Labour Act Cap L1 LFN 2004", "section": "Section 11",
        "content": (
            "Section 11(6) Labour Act: Where a contract of employment is for an unspecified period, "
            "the contract may be terminated by either party by one day's notice given orally or "
            "in writing if the worker is paid by the day; by one week's notice if the worker "
            "is paid by the week; by one month's notice or payment in lieu thereof if the worker "
            "is paid by the month; by one month's notice given in writing if the worker has been "
            "in employment for more than 3 months."
        ),
        "keywords": "notice,termination,employment,labour act,payment in lieu,section 11,contract,period,dismiss",
    },
    # ACJA 2015
    {
        "id": "acja_8", "source": "ACJA 2015", "section": "Section 8",
        "content": (
            "Section 8 ACJA 2015: A suspect shall not be arrested merely on a civil wrong or "
            "breach of contract. Any officer who arrests a suspect in contravention of this "
            "provision commits an offence and is liable on conviction to imprisonment for a term "
            "of 7 years or a fine of N200,000.00 or both."
        ),
        "keywords": "arrest,civil wrong,breach of contract,ACJA,suspect,police,unlawful arrest,section 8,fine,imprisonment",
    },
    {
        "id": "acja_35", "source": "ACJA 2015", "section": "Section 35",
        "content": (
            "Section 35 ACJA 2015: A suspect who is arrested, detained or restricted shall be "
            "informed immediately in a language he understands of the reasons for his arrest "
            "and of his rights. The suspect shall be informed of his right to remain silent or "
            "avoid answering any question until after consultation with a legal practitioner or "
            "any other person of his own choice. Every suspect has a right to be brought before "
            "a court within 24 hours of arrest."
        ),
        "keywords": "right to silence,caution,ACJA,arrest,24 hours,court,remand,legal practitioner,section 35,informed",
    },
    # Electoral Act 2022
    {
        "id": "ea2022_134", "source": "Electoral Act 2022", "section": "Section 134",
        "content": (
            "Section 134 Electoral Act 2022: An election may be questioned on the following grounds: "
            "(a) that a person whose election is questioned was, at the time of the election, "
            "not qualified to contest the election; (b) that the election was invalid by reason "
            "of corrupt practices or non-compliance with the provisions of this Act; "
            "(c) that the respondent was not duly elected by majority of lawful votes cast at "
            "the election. The burden of proof of corrupt practice or non-compliance lies on "
            "the petitioner. The petitioner must plead figures and particulars."
        ),
        "keywords": "election petition,grounds,corrupt practices,non-compliance,lawful votes,burden of proof,plead,particulars,electoral act 2022,section 134",
    },
    # PIA 2021
    {
        "id": "pia_9", "source": "Petroleum Industry Act 2021", "section": "Section 9",
        "content": (
            "Section 9 PIA 2021: The Commission shall have power to: grant, renew, extend, "
            "modify, suspend or revoke licences, leases, and permits in the upstream petroleum "
            "sector; ensure compliance with the obligations of licence holders, lessees and "
            "permit holders under the Act; issue regulations, guidelines, codes and standards "
            "for the upstream petroleum operations; impose penalties for breach of the Act."
        ),
        "keywords": "PIA,petroleum industry act,upstream,licence,lease,permit,commission,revoke,grant,oil,gas,2021",
    },
    # Arbitration and Conciliation Act 2023
    {
        "id": "aca_29", "source": "Arbitration and Conciliation Act 2023", "section": "Section 29",
        "content": (
            "Section 29 Arbitration and Conciliation Act 2023: The arbitral tribunal may award "
            "any remedy or relief that could have been ordered by a court including: "
            "a declaration as to any matter to be determined in the proceedings; "
            "an injunction; an order for specific performance; an order for the rectification, "
            "setting aside or cancellation of a deed or other document. "
            "An award is final and binding on the parties and any person claiming through them."
        ),
        "keywords": "arbitration,award,remedy,relief,injunction,specific performance,final,binding,ACA 2023,tribunal",
    },
    # Limitation Law
    {
        "id": "lim_tort", "source": "Limitation Act / Limitation Laws (various States)", "section": "General Limitation Periods",
        "content": (
            "General Limitation Periods under Nigerian Law: "
            "Simple contract: 6 years from date of breach (Limitation Act). "
            "Tort (general): 6 years. "
            "Personal injury claims: 3 years. "
            "Land: 12 years (Limitation Act s.16). "
            "Judgment debt: 12 years. "
            "Actions against government/public officers: pre-action notice required — "
            "typically 3 months under the Public Officers Protection Act. "
            "Fundamental rights enforcement: no strict limitation but unreasonable delay is fatal. "
            "Election petition: 21 days from declaration of results (Electoral Act 2022 s.132)."
        ),
        "keywords": "limitation,period,statute of limitations,6 years,12 years,3 years,time bar,lapse,contract,tort,land,personal injury,POPA,21 days,election petition",
    },
]


def _extract_query_keywords(query: str) -> list[str]:
    """Extract meaningful keywords from a query for RAG retrieval."""
    # Remove very common words
    stopwords = {
        "the","a","an","and","or","but","in","on","at","to","for","of","is","are",
        "was","were","be","been","being","have","has","had","do","does","did","will",
        "would","could","should","may","might","shall","this","that","these","those",
        "my","his","her","their","our","your","i","he","she","they","we","you","it",
        "with","from","by","about","as","into","through","during","before","after",
        "above","below","between","out","off","over","under","again","further","then",
        "once","what","when","where","which","who","how","if","not","no","can","client",
        "matter","case","issue","situation","problem","question","advice","legal","law",
    }
    words = re.findall(r'\b[a-zA-Z]{4,}\b', query.lower())
    return [w for w in words if w not in stopwords]


@st.cache_data(ttl=300, show_spinner=False)
def _load_rag_cache() -> list[dict]:
    """Load all statute chunks into memory (cached 5 min)."""
    try:
        db = get_db()
        # If DB has chunks, use those
        if db.count_statute_chunks() > 0:
            return db.search_statute_chunks([], limit=9999)
        # Otherwise use seeds
        return _STATUTE_SEEDS
    except Exception:
        return _STATUTE_SEEDS


def build_rag_context(query: str, top_k: int = 6) -> str:
    """
    Retrieve the most relevant statute chunks for a query and format as grounding context.
    Returns empty string if nothing relevant found (graceful degradation).
    """
    keywords = _extract_query_keywords(query)
    if not keywords:
        return ""

    chunks = _STATUTE_SEEDS  # always search seeds
    kw_set = {k.lower() for k in keywords}

    scored = []
    for c in chunks:
        kw_field = set(c.get("keywords", "").lower().split(","))
        kw_field = {k.strip() for k in kw_field if k.strip()}
        content_words = set(c.get("content", "").lower().split())
        kw_hits = len(kw_set & kw_field)
        content_hits = len(kw_set & content_words)
        score = kw_hits * 3 + content_hits
        # Precision gate (mirrors the case matcher): a statute provision only
        # qualifies if it hits a tagged KEYWORD, or shares >=2 distinct content
        # terms with the query. A single incidental content-word overlap (e.g.
        # "person", "act") is not enough — that produced unrelated statute
        # blocks being injected as "directly relevant".
        if kw_hits >= 1 or content_hits >= 2:
            scored.append((score, c))

    # Also try DB chunks
    try:
        db_chunks = get_db().search_statute_chunks(keywords, limit=top_k)
        for dc in db_chunks:
            scored.append((dc["score"], dc))
    except Exception:
        pass

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [c for _, c in scored[:top_k]]

    if not top:
        return ""

    lines = [
        "═══ CANDIDATE STATUTORY PROVISIONS (retrieved from primary Nigerian law) ═══",
        "These provisions were retrieved as POSSIBLY relevant to the query. They are",
        "real and quoted accurately. Cite a provision ONLY if it genuinely applies to",
        "the issue; silently ignore any that is not on-point. When you cite one, quote",
        "the section exactly — do not paraphrase around it.",
        "",
    ]
    for i, c in enumerate(top, 1):
        source = c.get("source", "")
        section = c.get("section", "")
        content = c.get("content", "")
        lines.append(f"[{i}] {source} — {section}")
        lines.append(content.strip())
        lines.append("")
    lines.append("═══ END STATUTORY GROUNDING ═══")
    return "\n".join(lines)

