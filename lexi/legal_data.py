"""LexiAssist legal data — fee scales, stamp duty rates, court filing fees,
limitation periods, court hierarchy, legal maxims, and the legal-data
version stamp.

This module holds pure data and pure-arithmetic helpers; it has no
dependencies on Streamlit or any other module.
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════
# LEGAL FEE & STAMP DUTY CALCULATOR — DATA
# ═══════════════════════════════════════════════════════
# Nigerian Legal Practitioners (Remuneration for Legal Documentation
# and Other Land Matters) Order — sliding scale
LAND_MATTERS_SCALE = [
    {"band_label": "First ₦5,000",           "up_to": 5_000,         "rate": 0.10},
    {"band_label": "Next ₦10,000",           "up_to": 15_000,        "rate": 0.075},
    {"band_label": "Next ₦15,000",           "up_to": 30_000,        "rate": 0.05},
    {"band_label": "Next ₦70,000",           "up_to": 100_000,       "rate": 0.035},
    {"band_label": "Next ₦400,000",          "up_to": 500_000,       "rate": 0.025},
    {"band_label": "Remainder above ₦500k",  "up_to": float("inf"),  "rate": 0.015},
]
LAND_MATTERS_MIN_FEE = 10_000  # ₦10,000 minimum for any land transaction

# Stamp Duty rates — Stamp Duties Act Cap S8 LFN 2004 (as amended)
STAMP_DUTY_INSTRUMENTS = {
    "deed_of_assignment":       {"label": "Deed of Assignment / Conveyance",    "rate": 0.015,  "basis": "property_value", "note": "1.5% of property value"},
    "tenancy_lt7":              {"label": "Tenancy / Lease (< 7 years)",         "rate": 0.0078, "basis": "annual_rent_x_years", "note": "0.78% × annual rent × years"},
    "tenancy_7to21":            {"label": "Tenancy / Lease (7–21 years)",        "rate": 0.03,   "basis": "annual_rent",    "note": "3% of annual rent"},
    "tenancy_over21":           {"label": "Tenancy / Lease (> 21 years)",        "rate": 0.06,   "basis": "annual_rent",    "note": "6% of annual rent"},
    "mortgage":                 {"label": "Legal Mortgage / Debenture",          "rate": 0.00375,"basis": "loan_amount",    "note": "0.375% of secured amount"},
    "power_of_attorney_gen":    {"label": "General Power of Attorney",           "rate": None,   "basis": "flat",           "flat": 1_000, "note": "₦1,000 flat"},
    "power_of_attorney_spec":   {"label": "Special Power of Attorney",           "rate": None,   "basis": "flat",           "flat": 500,   "note": "₦500 flat"},
    "affidavit":                {"label": "Affidavit",                           "rate": None,   "basis": "flat",           "flat": 200,   "note": "₦200 flat"},
    "memorandum_of_understanding": {"label": "Memorandum of Understanding (MOU)","rate": 0.0075,"basis": "contract_value",  "note": "0.75% of stated value"},
    "share_transfer":           {"label": "Share Transfer / Stock Transfer Form","rate": 0.015,  "basis": "consideration",  "note": "1.5% of consideration"},
    "loan_agreement":           {"label": "Loan / Credit Agreement",             "rate": 0.00375,"basis": "loan_amount",    "note": "0.375% of loan amount"},
    "guarantee":                {"label": "Guarantee / Indemnity",               "rate": 0.0075, "basis": "guaranteed_sum", "note": "0.75% of guaranteed sum"},
    "joint_venture":            {"label": "Joint Venture Agreement",             "rate": 0.0075, "basis": "contract_value",  "note": "0.75% of stated value"},
    "settlement_agreement":     {"label": "Deed of Settlement / Release",        "rate": 0.015,  "basis": "property_value",  "note": "1.5% of settlement amount"},
}

# Court Filing Fees (indicative — varies by state and court rules; verify before filing)
COURT_FILING_FEES = {
    "magistrate_lagos": {
        "label": "Magistrate Court (Lagos State)",
        "bands": [
            {"claim_max": 100_000,     "fee": 2_000,  "label": "Claim up to ₦100,000"},
            {"claim_max": 300_000,     "fee": 5_000,  "label": "Claim ₦100k–₦300k"},
            {"claim_max": 500_000,     "fee": 8_000,  "label": "Claim ₦300k–₦500k"},
            {"claim_max": float("inf"),"fee": 10_000, "label": "Maximum jurisdiction"},
        ],
        "appeal_fee": 15_000,
        "note": "Lagos Magistrate Courts Law 2009 (as amended). Max civil jurisdiction ₦500,000.",
        "last_verified": "January 2026",
    },
    "high_court_state": {
        "label": "State High Court (e.g. Lagos)",
        "bands": [
            {"claim_max": 500_000,       "fee": 8_000,  "label": "Claim up to ₦500,000"},
            {"claim_max": 1_000_000,     "fee": 15_000, "label": "Claim ₦500k–₦1m"},
            {"claim_max": 5_000_000,     "fee": 25_000, "label": "Claim ₦1m–₦5m"},
            {"claim_max": 20_000_000,    "fee": 40_000, "label": "Claim ₦5m–₦20m"},
            {"claim_max": 100_000_000,   "fee": 75_000, "label": "Claim ₦20m–₦100m"},
            {"claim_max": float("inf"),  "fee": 120_000,"label": "Claim above ₦100m"},
        ],
        "appeal_fee": 50_000,
        "note": "Fees vary by state. Verify with specific court registry before filing.",
        "last_verified": "January 2026",
    },
    "federal_high_court": {
        "label": "Federal High Court",
        "bands": [
            {"claim_max": 1_000_000,     "fee": 10_000,  "label": "Claim up to ₦1m"},
            {"claim_max": 5_000_000,     "fee": 30_000,  "label": "Claim ₦1m–₦5m"},
            {"claim_max": 20_000_000,    "fee": 60_000,  "label": "Claim ₦5m–₦20m"},
            {"claim_max": 100_000_000,   "fee": 100_000, "label": "Claim ₦20m–₦100m"},
            {"claim_max": float("inf"),  "fee": 150_000, "label": "Claim above ₦100m"},
        ],
        "appeal_fee": 75_000,
        "note": "FHC (Civil Procedure) Rules 2019. Verify current rates with court registry.",
        "last_verified": "January 2026",
    },
    "national_industrial_court": {
        "label": "National Industrial Court",
        "bands": [
            {"claim_max": 1_000_000,    "fee": 10_000,  "label": "Claim up to ₦1m"},
            {"claim_max": 10_000_000,   "fee": 25_000,  "label": "Claim ₦1m–₦10m"},
            {"claim_max": float("inf"), "fee": 50_000,  "label": "Claim above ₦10m"},
        ],
        "appeal_fee": 50_000,
        "note": "NIC (Civil Procedure) Rules 2017.",
        "last_verified": "January 2026",
    },
    "court_of_appeal": {
        "label": "Court of Appeal",
        "bands": [
            {"claim_max": float("inf"), "fee": 100_000, "label": "All civil appeals"},
        ],
        "appeal_fee": 0,
        "note": "Court of Appeal Rules 2021. Filing fee covers Notice of Appeal and related documents.",
        "last_verified": "January 2026",
    },
    "supreme_court": {
        "label": "Supreme Court of Nigeria",
        "bands": [
            {"claim_max": float("inf"), "fee": 200_000, "label": "All matters"},
        ],
        "appeal_fee": 0,
        "note": "Supreme Court Rules (as amended). Verify with Supreme Court Registry, Abuja.",
        "last_verified": "January 2026",
    },
    "high_court_lagos": {
        "label": "High Court of Lagos State",
        "bands": [
            {"claim_max": 500_000,       "fee": 8_000,   "label": "Claim up to ₦500,000"},
            {"claim_max": 1_000_000,     "fee": 15_000,  "label": "Claim ₦500k–₦1m"},
            {"claim_max": 5_000_000,     "fee": 25_000,  "label": "Claim ₦1m–₦5m"},
            {"claim_max": 20_000_000,    "fee": 40_000,  "label": "Claim ₦5m–₦20m"},
            {"claim_max": 100_000_000,   "fee": 75_000,  "label": "Claim ₦20m–₦100m"},
            {"claim_max": float("inf"),  "fee": 120_000, "label": "Claim above ₦100m"},
        ],
        "appeal_fee": 50_000,
        "note": "High Court of Lagos State (Civil Procedure) Rules 2019. Verify current rates with Ikeja, Lagos Island, or Badagry Registry.",
        "last_verified": "January 2026",
    },
    "high_court_fct": {
        "label": "High Court of the FCT (Abuja)",
        "bands": [
            {"claim_max": 500_000,       "fee": 5_000,   "label": "Claim up to ₦500,000"},
            {"claim_max": 1_000_000,     "fee": 12_000,  "label": "Claim ₦500k–₦1m"},
            {"claim_max": 5_000_000,     "fee": 20_000,  "label": "Claim ₦1m–₦5m"},
            {"claim_max": 20_000_000,    "fee": 35_000,  "label": "Claim ₦5m–₦20m"},
            {"claim_max": 100_000_000,   "fee": 65_000,  "label": "Claim ₦20m–₦100m"},
            {"claim_max": float("inf"),  "fee": 100_000, "label": "Claim above ₦100m"},
        ],
        "appeal_fee": 50_000,
        "note": "FCT High Court (Civil Procedure) Rules 2018. Verify with Abuja Judicial Division Registry.",
        "last_verified": "January 2026",
    },
    "high_court_rivers": {
        "label": "High Court of Rivers State",
        "bands": [
            {"claim_max": 500_000,       "fee": 6_000,   "label": "Claim up to ₦500,000"},
            {"claim_max": 1_000_000,     "fee": 12_000,  "label": "Claim ₦500k–₦1m"},
            {"claim_max": 5_000_000,     "fee": 22_000,  "label": "Claim ₦1m–₦5m"},
            {"claim_max": 20_000_000,    "fee": 38_000,  "label": "Claim ₦5m–₦20m"},
            {"claim_max": 100_000_000,   "fee": 65_000,  "label": "Claim ₦20m–₦100m"},
            {"claim_max": float("inf"),  "fee": 100_000, "label": "Claim above ₦100m"},
        ],
        "appeal_fee": 40_000,
        "note": "Rivers State High Court (Civil Procedure) Rules 2010 (as amended). Verify with Port Harcourt Registry.",
        "last_verified": "January 2026",
    },
    "magistrate_fct": {
        "label": "Magistrate Court (FCT Abuja)",
        "bands": [
            {"claim_max": 100_000,      "fee": 1_500,  "label": "Claim up to ₦100,000"},
            {"claim_max": 300_000,      "fee": 3_500,  "label": "Claim ₦100k–₦300k"},
            {"claim_max": 1_000_000,    "fee": 6_000,  "label": "Claim ₦300k–₦1m"},
            {"claim_max": float("inf"), "fee": 8_000,  "label": "Max jurisdiction"},
        ],
        "appeal_fee": 12_000,
        "note": "FCT Magistrate Courts Act (as amended). Verify current jurisdictional limit and fees with Registry.",
        "last_verified": "January 2026",
    },
    "tax_appeal_tribunal": {
        "label": "Tax Appeal Tribunal (TAT)",
        "bands": [
            {"claim_max": 1_000_000,    "fee": 15_000,  "label": "Assessment up to ₦1m"},
            {"claim_max": 10_000_000,   "fee": 30_000,  "label": "Assessment ₦1m–₦10m"},
            {"claim_max": float("inf"), "fee": 50_000,  "label": "Assessment above ₦10m"},
        ],
        "appeal_fee": 30_000,
        "note": "TAT Procedure Rules 2021. Notice of Appeal filed within 30 days of FIRS/SIRS assessment — FIRSEA 2007 s. 69.",
        "last_verified": "January 2026",
    },
}


def compute_land_fee(value: float) -> tuple[float, list]:
    """Compute solicitor's fee on a land transaction using the sliding scale.
    Returns (total_fee, breakdown_rows)."""
    fee = 0.0
    breakdown = []
    remaining = value
    prev_band = 0.0
    for band in LAND_MATTERS_SCALE:
        if remaining <= 0:
            break
        cap = band["up_to"]
        taxable = min(remaining, cap - prev_band)
        if taxable <= 0:
            prev_band = cap
            continue
        band_fee = taxable * band["rate"]
        fee += band_fee
        breakdown.append({
            "band": band["band_label"],
            "taxable": taxable,
            "rate": f"{band['rate']*100:.2f}%",
            "fee": band_fee,
        })
        remaining -= taxable
        prev_band = cap
    fee = max(fee, LAND_MATTERS_MIN_FEE)
    return fee, breakdown


def compute_stamp_duty(instrument_key: str, value: float = 0,
                       years: float = 1, annual_rent: float = 0) -> float:
    """Compute stamp duty for an instrument type."""
    inst = STAMP_DUTY_INSTRUMENTS.get(instrument_key)
    if not inst:
        return 0.0
    basis = inst["basis"]
    if basis == "flat":
        return float(inst.get("flat", 0))
    if basis == "property_value":
        return value * inst["rate"]
    if basis == "annual_rent_x_years":
        return (annual_rent or value) * years * inst["rate"]
    if basis == "annual_rent":
        return (annual_rent or value) * inst["rate"]
    if basis in ("loan_amount", "consideration", "guaranteed_sum",
                 "contract_value", "secured_amount"):
        return value * inst["rate"]
    return 0.0


def get_court_filing_fee(court_key: str, claim_value: float) -> tuple[int, str]:
    """Return (fee, note) for filing in a given court with a given claim value."""
    court = COURT_FILING_FEES.get(court_key)
    if not court:
        return 0, ""
    for band in court["bands"]:
        if claim_value <= band["claim_max"]:
            return band["fee"], court["note"]
    return court["bands"][-1]["fee"], court["note"]


# ═══════════════════════════════════════════════════════
# PHASE 4 — LEGAL DATA VERSION TRACKING
# ═══════════════════════════════════════════════════════
LEGAL_DATA_VERSION = {
    "version":     "v9.0.1",
    "updated":     "15 April 2026",
    "last_act":    "Finance Act 2023 (incorporated)",
    "limitations": "Limitation periods last reviewed: March 2026",
    "court_fees":  "Lagos, FCT, Rivers court fees last verified: January 2026",
    "notes": (
        "Finance Act 2023 amends Stamp Duties Act — stamp duty rates updated. "
        "Electoral Act 2022 (all election petition provisions). "
        "Arbitration and Conciliation Act 2023 now governs all arbitrations. "
        "PIA 2021 fully in force — governs all upstream/midstream petroleum operations."
    ),
}

DEFAULT_LIMITATION_PERIODS = [
    {"cause": "Simple Contract", "period": "6 years", "authority": "Limitation Act Cap L16 LFN 2004, s. 8(1)(a)"},
    {"cause": "Tort / Negligence", "period": "6 years", "authority": "Limitation Act, s. 8(1)(a)"},
    {"cause": "Personal Injury (Negligence)", "period": "3 years", "authority": "Limitation Act, s. 8(1)(b)"},
    {"cause": "Defamation / Libel / Slander", "period": "3 years (federal); 1 year (Lagos)", "authority": "Limitation Act s. 7; Lagos Limitation Law 2004 s. 11"},
    {"cause": "Recovery of Land", "period": "12 years", "authority": "Limitation Act, s. 16"},
    {"cause": "Mortgage Foreclosure", "period": "12 years from default", "authority": "Limitation Act, s. 18"},
    {"cause": "Recovery of Rent / Mesne Profits", "period": "6 years", "authority": "Limitation Act, s. 19"},
    {"cause": "Judgment Enforcement", "period": "12 years from judgment date", "authority": "Limitation Act, s. 8(1)(d)"},
    {"cause": "Public Officers (POPA)", "period": "3 months pre-action notice + 12 months to sue", "authority": "Public Officers Protection Act Cap P41 LFN 2004, s. 2"},
    {"cause": "Fundamental Rights Enforcement", "period": "12 months from infringement (NB: subject to continuing violation doctrine, court discretion, and state-specific interpretation — verify applicable authority)", "authority": "Fundamental Rights (Enforcement Procedure) Rules 2009, Order II r. 1"},
    {"cause": "Election Petition (Governorship / NASS)", "period": "21 days from declaration of result", "authority": "Electoral Act 2022, s. 133(1)"},
    {"cause": "Election Petition (Presidential)", "period": "21 days from declaration of result", "authority": "Electoral Act 2022, s. 133(1)"},
    {"cause": "Labour / Employment (NIC)", "period": "No fixed limit — laches & acquiescence apply", "authority": "NIC Act 2006; NIC (CPR) Rules 2017"},
    {"cause": "Wrongful Termination / Breach of Contract of Employment", "period": "6 years (contract)", "authority": "Limitation Act s. 8(1)(a); NIC jurisdiction"},
    {"cause": "Pension Claim (PenCom / Trustee)", "period": "5 years from accrual", "authority": "Pension Reform Act 2014, s. 72"},
    {"cause": "Tax Assessment Appeal (FIRS)", "period": "30 days from service of notice of assessment", "authority": "FIRSEA 2007, s. 69; TAT Procedure Rules 2021"},
    {"cause": "Tax Assessment Appeal (State IRS)", "period": "30 days (varies by state law)", "authority": "State Revenue Service laws (e.g. LIRS Law 2015)"},
    {"cause": "Consumer Protection (FCCPC)", "period": "3 years from cause arising", "authority": "FCCPA 2018, s. 17"},
    {"cause": "Insurance Claim (non-life)", "period": "12 months from loss (per policy); 6 years max", "authority": "Insurance Act 2003, s. 78; policy conditions"},
    {"cause": "Life Assurance Claim", "period": "No statutory bar in most policies; 6 years general", "authority": "Insurance Act 2003; Limitation Act s. 8"},
    {"cause": "Company Derivative Action (CAMA 2020)", "period": "No fixed limit — promptness required", "authority": "CAMA 2020, ss. 339–344"},
    {"cause": "Winding-Up Petition (CAMA 2020)", "period": "Debt must be subsisting; no limitation on petition", "authority": "CAMA 2020, ss. 571–572 (21-day statutory demand first)"},
    {"cause": "Bankers Recovery (Proof of Debt)", "period": "6 years from default", "authority": "BOFIA 2020; Limitation Act s. 8"},
    {"cause": "Mortgage / Debenture Enforcement", "period": "12 years (action on covenant); 12 years (possession)", "authority": "Limitation Act ss. 16, 18"},
    {"cause": "Admiralty / Maritime Claim (arrest)", "period": "Prompt action required — 2 years for damage claims (LLMC)", "authority": "Admiralty Jurisdiction Act 1991; LLMC Convention"},
    {"cause": "Intellectual Property Infringement", "period": "6 years from infringement", "authority": "Limitation Act s. 8(1)(a); Trade Marks Act; Copyright Act 2022"},
    {"cause": "Fraudulent Misrepresentation", "period": "6 years from discovery of fraud", "authority": "Limitation Act s. 26(1) — time runs from discovery"},
    {"cause": "Land Acquisition / Compulsory Acquisition (State)", "period": "12 months from notice of acquisition", "authority": "Land Use Act 1978, s. 29; applicable State law"},
    {"cause": "EFCC / ICPC Forfeiture Proceedings", "period": "No limitation — proceeds of crime, not time-barred", "authority": "EFCCA 2004 s. 28; ICPCA 2000 s. 47"},
    {"cause": "Tenancy / Recovery of Premises", "period": "6 years for rent arrears; state recovery law for possession", "authority": "Applicable State Tenancy Law (e.g. Lagos Tenancy Law 2011)"},
    {"cause": "Breach of Trust (Trustee Act)", "period": "6 years; no limit for fraudulent breach", "authority": "Limitation Act s. 21; Trustees Act Cap T22 LFN 2004"},
    {"cause": "Chieftaincy / Customary Law Title", "period": "No fixed limit — laches applies; urgent notice required", "authority": "State Chieftaincy Laws; customary law principles"},
]

COURT_HIERARCHY = [
    {"level": 1, "name": "Supreme Court of Nigeria", "desc": "Final appellate court", "icon": "🏛️"},
    {"level": 2, "name": "Court of Appeal", "desc": "Intermediate appellate", "icon": "⚖️"},
    {"level": 3, "name": "Federal High Court", "desc": "Federal causes, tax, admiralty", "icon": "🏢"},
    {"level": 3, "name": "State High Courts", "desc": "General civil & criminal", "icon": "🏢"},
    {"level": 3, "name": "National Industrial Court", "desc": "Labour & employment", "icon": "🏢"},
    {"level": 4, "name": "Magistrate / District Courts", "desc": "Summary jurisdiction", "icon": "📋"},
    {"level": 4, "name": "Customary / Sharia Courts", "desc": "Personal law matters", "icon": "📋"},
]

DEFAULT_LEGAL_MAXIMS = [
    {"maxim": "Audi alteram partem", "meaning": "Hear the other side — a pillar of natural justice; no condemnation unheard"},
    {"maxim": "Nemo judex in causa sua", "meaning": "No one should be a judge in their own cause — the rule against bias"},
    {"maxim": "Stare decisis et non quieta movere", "meaning": "Stand by decided cases and do not disturb settled matters — binding precedent"},
    {"maxim": "Ubi jus ibi remedium", "meaning": "Where there is a right, there is a remedy — no right without a corresponding action"},
    {"maxim": "Volenti non fit injuria", "meaning": "No injury is done to one who consents — defence to negligence"},
    {"maxim": "Pacta sunt servanda", "meaning": "Agreements must be kept — fundamental to contract law"},
    {"maxim": "Nemo dat quod non habet", "meaning": "One cannot give what one does not have — root of title and property law"},
    {"maxim": "Res judicata pro veritate accipitur", "meaning": "A decided matter is accepted as truth — estoppel per rem judicatam"},
    {"maxim": "Actus non facit reum nisi mens sit rea", "meaning": "An act does not make a person guilty unless the mind is also guilty — criminal law"},
    {"maxim": "Ignorantia juris non excusat", "meaning": "Ignorance of the law excuses no one — universal legal responsibility"},
    {"maxim": "Qui facit per alium facit per se", "meaning": "He who acts through another acts himself — agency and vicarious liability"},
    {"maxim": "Generalia specialibus non derogant", "meaning": "General provisions do not derogate from special ones — statutory interpretation"},
    {"maxim": "Ex turpi causa non oritur actio", "meaning": "No action arises from a base cause — illegality as a defence"},
    {"maxim": "Delegatus non potest delegare", "meaning": "A delegate cannot further delegate — limits on sub-delegation of power"},
    {"maxim": "Suppressio veri suggestio falsi", "meaning": "Suppression of truth is equivalent to a suggestion of falsehood — equity and fraud"},
    {"maxim": "Damnum sine injuria", "meaning": "Damage without legal injury — no actionable wrong despite loss"},
    {"maxim": "Injuria sine damno", "meaning": "Legal injury without actual damage — actionable without proof of loss (e.g. trespass)"},
    {"maxim": "In pari delicto potior est conditio defendentis", "meaning": "Where both parties are equally at fault, the defendant's position is the stronger"},
    {"maxim": "Falsus in uno, falsus in omnibus", "meaning": "False in one thing, false in everything — goes to witness credibility"},
    {"maxim": "Fraus omnia corrumpit", "meaning": "Fraud vitiates everything — equitable maxim applied in Nigerian courts"},
    {"maxim": "Expressio unius est exclusio alterius", "meaning": "Express mention of one thing excludes others — statutory interpretation"},
    {"maxim": "Ejusdem generis", "meaning": "Of the same kind — general words following specific words take colour from the specific"},
    {"maxim": "Ut res magis valeat quam pereat", "meaning": "Prefer the construction that gives effect to the provision rather than destroys it"},
    {"maxim": "Lex posterior derogat priori", "meaning": "A later law repeals an earlier inconsistent law"},
    {"maxim": "In dubio pro reo", "meaning": "In doubt, for the accused — the criminal law presumption of innocence"},
    {"maxim": "Qui prior est tempore potior est jure", "meaning": "He who is earlier in time is stronger in law — priority of interests"},
    {"maxim": "Consensus ad idem", "meaning": "Meeting of minds — essential element of a valid contract in Nigerian law"},
    {"maxim": "Non est factum", "meaning": "It is not my deed — defence against a deed fundamentally different from what was intended"},
    {"maxim": "Caveat emptor", "meaning": "Let the buyer beware — buyer takes property as found (qualified by disclosure duties)"},
    {"maxim": "Lex loci contractus", "meaning": "The law of the place where a contract is made — choice of law in contracts"},
    {"maxim": "Interest reipublicae ut sit finis litium", "meaning": "It is in the public interest that litigation should have an end — finality of judgments"},
]
