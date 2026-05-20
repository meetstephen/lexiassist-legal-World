"""LexiAssist citation engine — verified Nigerian Supreme Court / Court of
Appeal cases, repealed-law and foreign-authority scanners, citation
extraction and audit helpers.
"""
from __future__ import annotations

from .runtime import re, Optional, esc

# ═══════════════════════════════════════════════════════
# CITATION VERIFICATION ENGINE
# ═══════════════════════════════════════════════════════
# Curated database of verified Nigerian Supreme Court & Court of Appeal
# landmark decisions. This is the seed — extend monthly from NWLR/LPELR.
# Format: case name → (citation, court, year, principle)
# ═══════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════
# DETERMINISTIC LEGAL CURRENCY MAP
# ═══════════════════════════════════════════════════════
REPEALED_LAWS = {
    "CAMA 1990": "Companies and Allied Matters Act 2020",
    "Companies and Allied Matters Act 1990": "Companies and Allied Matters Act 2020",
    "Electoral Act 2010": "Electoral Act 2022",
    "Arbitration Act 1988": "Arbitration and Conciliation Act 2023",
    "Arbitration and Conciliation Act 1988": "Arbitration and Conciliation Act 2023",
    "BOFIA 1991": "Banks and Other Financial Institutions Act 2020",
    "Banks and Other Financial Institutions Act 1991": "Banks and Other Financial Institutions Act 2020",
    "Copyright Act 1988": "Copyright Act 2022",
    "Evidence Act 1945": "Evidence Act 2011",
    "Police Act 1943": "Police Act 2020",
}

FOREIGN_PERSUASIVE_MARKERS = [
    "Donoghue v Stevenson",
    "Carlill v Carbolic Smoke Ball",
    "Hadley v Baxendale",
    "Salomon v Salomon",
    "Hedley Byrne",
]


def scan_repealed_laws(text: str) -> list:
    """Deterministically scan text for repealed/superseded laws."""
    findings = []
    if not text:
        return findings
    for old, new in REPEALED_LAWS.items():
        if re.search(rf"\b{re.escape(old)}\b", text, re.IGNORECASE):
            findings.append({
                "authority": old,
                "type": "Statute",
                "status": "Repealed",
                "problem": f"{old} has been repealed/superseded.",
                "fix": f"Use {new} and verify the specific current provision.",
                "confidence": 98,
            })
    return findings


def scan_foreign_authorities(text: str) -> list:
    """Flag common foreign authorities as persuasive only."""
    findings = []
    if not text:
        return findings
    for marker in FOREIGN_PERSUASIVE_MARKERS:
        if re.search(rf"\b{re.escape(marker)}\b", text, re.IGNORECASE):
            findings.append({
                "authority": marker,
                "type": "Case",
                "status": "Foreign",
                "problem": "Foreign authority — persuasive only, not binding in Nigerian courts.",
                "fix": "Use only as persuasive authority and look for Nigerian binding authority.",
                "confidence": 95,
            })
    return findings


VERIFIED_NIGERIAN_CASES = {
    # ─── Constitutional Law ───
    "AG Lagos v AG Federation": {
        "citation": "(2003) 12 NWLR (Pt. 833) 1",
        "court": "Supreme Court", "year": 2003,
        "principle": "Federalism; division of powers between Federation and States",
    },
    "Inakoju v Adeleke": {
        "citation": "(2007) 4 NWLR (Pt. 1025) 423",
        "court": "Supreme Court", "year": 2007,
        "principle": "Impeachment procedure; legislative powers of State Houses of Assembly",
    },
    "Abacha v Fawehinmi": {
        "citation": "(2000) 6 NWLR (Pt. 660) 228",
        "court": "Supreme Court", "year": 2000,
        "principle": "Fundamental rights; African Charter incorporation; locus standi",
    },
    "AG Federation v AG Abia State": {
        "citation": "(2001) 11 NWLR (Pt. 725) 689",
        "court": "Supreme Court", "year": 2001,
        "principle": "Resource control; onshore-offshore dichotomy",
    },

    # ─── Contract Law ───
    "Best (Nig) Ltd v Blackwood Hodge (Nig) Ltd": {
        "citation": "(2011) 5 NWLR (Pt. 1239) 95",
        "court": "Supreme Court", "year": 2011,
        "principle": "Privity of contract; consideration; offer and acceptance",
    },
    "Orient Bank v Bilante International Ltd": {
        "citation": "(1997) 8 NWLR (Pt. 515) 37",
        "court": "Supreme Court", "year": 1997,
        "principle": "Banking contracts; banker-customer relationship",
    },
    "BFI Group Corporation v Bureau of Public Enterprises": {
        "citation": "(2012) 18 NWLR (Pt. 1332) 209",
        "court": "Supreme Court", "year": 2012,
        "principle": "Privatisation contracts; consideration; binding agreements",
    },
    "Tsokwa Motors v UBN Plc": {
        "citation": "(1996) 9 NWLR (Pt. 471) 129",
        "court": "Supreme Court", "year": 1996,
        "principle": "Banker's duty of care; negligence in banking",
    },

    # ─── Land Law ───
    "Savannah Bank v Ajilo": {
        "citation": "(1989) 1 NWLR (Pt. 97) 305",
        "court": "Supreme Court", "year": 1989,
        "principle": "Land Use Act; Governor's consent; mortgage transactions",
    },
    "Adole v Gwar": {
        "citation": "(2008) 11 NWLR (Pt. 1099) 562",
        "court": "Supreme Court", "year": 2008,
        "principle": "Customary land tenure; family land",
    },
    "Ogunleye v Oni": {
        "citation": "(1990) 2 NWLR (Pt. 135) 745",
        "court": "Supreme Court", "year": 1990,
        "principle": "Five ways of proving title to land",
    },
    "Idundun v Okumagba": {
        "citation": "(1976) 9-10 SC 227",
        "court": "Supreme Court", "year": 1976,
        "principle": "Five methods of proving ownership of land",
    },

    # ─── Criminal Law & Procedure ───
    "Sani v State": {
        "citation": "(2018) 10 NWLR (Pt. 1626) 1",
        "court": "Supreme Court", "year": 2018,
        "principle": "Burden of proof; standard of proof beyond reasonable doubt",
    },
    "Esangbedo v State": {
        "citation": "(1989) 4 NWLR (Pt. 113) 57",
        "court": "Supreme Court", "year": 1989,
        "principle": "Confessional statements; voluntariness; trial within trial",
    },
    "Adeyemi v State": {
        "citation": "(1991) 6 NWLR (Pt. 195) 1",
        "court": "Supreme Court", "year": 1991,
        "principle": "Identification evidence; dock identification",
    },

    # ─── Company Law ───
    "Oilfield Supply Centre Ltd v Johnson": {
        "citation": "(1987) 2 NWLR (Pt. 58) 625",
        "court": "Supreme Court", "year": 1987,
        "principle": "Lifting the corporate veil; Salomon principle",
    },
    "Marina Nominees Ltd v FBIR": {
        "citation": "(1986) 2 NWLR (Pt. 20) 48",
        "court": "Supreme Court", "year": 1986,
        "principle": "Corporate personality; nominee shareholding",
    },
    "Edokpolor & Co Ltd v Sem-Edo Wire Industries Ltd": {
        "citation": "(1984) 7 SC 119",
        "court": "Supreme Court", "year": 1984,
        "principle": "Ultra vires doctrine; corporate capacity",
    },

    # ─── Evidence ───
    "Aigbadion v State": {
        "citation": "(2000) 7 NWLR (Pt. 666) 686",
        "court": "Supreme Court", "year": 2000,
        "principle": "Admissibility of confessional statements",
    },
    "Subramanian v Public Prosecutor": {
        "citation": "(1956) 1 WLR 965",
        "court": "Privy Council", "year": 1956,
        "principle": "Hearsay rule; original evidence vs hearsay (persuasive in Nigeria)",
    },

    # ─── Tort ───
    "UBN v Ajabule": {
        "citation": "(2011) 18 NWLR (Pt. 1278) 152",
        "court": "Supreme Court", "year": 2011,
        "principle": "Negligent misstatement; duty of care",
    },
    "Iyere v Bendel Feed and Flour Mill Ltd": {
        "citation": "(2008) 18 NWLR (Pt. 1119) 300",
        "court": "Supreme Court", "year": 2008,
        "principle": "Vicarious liability; course of employment",
    },

    # ─── Labour & Employment ───
    "Olaniyan v University of Lagos": {
        "citation": "(1985) 2 NWLR (Pt. 9) 599",
        "court": "Supreme Court", "year": 1985,
        "principle": "Public employment with statutory flavour; right to fair hearing",
    },
    "Imoloame v WAEC": {
        "citation": "(1992) 9 NWLR (Pt. 265) 303",
        "court": "Supreme Court", "year": 1992,
        "principle": "Master-servant relationship; wrongful dismissal vs unlawful termination",
    },

    # ─── Procedure & Jurisdiction ───
    "Madukolu v Nkemdilim": {
        "citation": "(1962) 2 SCNLR 341",
        "court": "Supreme Court", "year": 1962,
        "principle": "Jurisdictional pre-conditions; competent court requirements",
    },
    "Ariori v Elemo": {
        "citation": "(1983) 1 SCNLR 1",
        "court": "Supreme Court", "year": 1983,
        "principle": "Right to fair hearing; waiver of constitutional rights",
    },
    "Kotoye v CBN": {
        "citation": "(1989) 1 NWLR (Pt. 98) 419",
        "court": "Supreme Court", "year": 1989,
        "principle": "Interlocutory injunctions; undertaking as to damages",
    },
    "Ojukwu v Governor of Lagos State": {
        "citation": "(1986) 3 NWLR (Pt. 26) 39",
        "court": "Supreme Court", "year": 1986,
        "principle": "Rule of law; respect for court orders pendente lite",
    },

    # ─── Banking & Finance ───
    "Yesufu v ACB": {
        "citation": "(1976) 4 SC 1",
        "court": "Supreme Court", "year": 1976,
        "principle": "Banker's duty; combination of accounts",
    },
    "UBA v Tejumola & Sons Ltd": {
        "citation": "(1988) 2 NWLR (Pt. 79) 662",
        "court": "Supreme Court", "year": 1988,
        "principle": "Banker-customer relationship; debtor-creditor",
    },
    "Allied Bank of Nigeria Ltd v Akubueze": {
        "citation": "(1997) 6 NWLR (Pt. 509) 374",
        "court": "Supreme Court", "year": 1997,
        "principle": "Bankers' books; admissibility of bank statements",
    },

    # ─── Family Law ───
    "Amadi v Nwosu": {
        "citation": "(1992) 5 NWLR (Pt. 241) 273",
        "court": "Supreme Court", "year": 1992,
        "principle": "Customary marriage; proof and validity",
    },
    "Mojekwu v Mojekwu": {
        "citation": "(1997) 7 NWLR (Pt. 512) 283",
        "court": "Court of Appeal", "year": 1997,
        "principle": "Oli-ekpe custom; gender discrimination in inheritance",
    },

    # ─── Election Law ───
    "Buhari v Obasanjo": {
        "citation": "(2005) 13 NWLR (Pt. 941) 1",
        "court": "Supreme Court", "year": 2005,
        "principle": "Election petition; substantial compliance test",
    },
    "Atiku Abubakar v INEC": {
        "citation": "(2020) 12 NWLR (Pt. 1737) 37",
        "court": "Supreme Court", "year": 2020,
        "principle": "Election petition procedure; burden of proof",
    },

    # ─── Tax ───
    "7-Up Bottling Co v LSIRB": {
        "citation": "(2000) 3 NWLR (Pt. 650) 565",
        "court": "Court of Appeal", "year": 2000,
        "principle": "Multiple taxation; State vs Federal taxing powers",
    },
    "Aderawos Timber Trading Co Ltd v FBIR": {
        "citation": "(1969) NCLR 287",
        "court": "Supreme Court", "year": 1969,
        "principle": "Income tax; allowable deductions",
    },

    # ─── Equity & Trusts ───
    "Adetona v Zenith International Bank Plc": {
        "citation": "(2011) 18 NWLR (Pt. 1278) 627",
        "court": "Supreme Court", "year": 2011,
        "principle": "Equitable remedies; specific performance",
    },

    # ─── Human Rights ───
    "Director SSS v Agbakoba": {
        "citation": "(1999) 3 NWLR (Pt. 595) 314",
        "court": "Supreme Court", "year": 1999,
        "principle": "Fundamental rights; freedom of movement; passport seizure",
    },
    "Fawehinmi v IGP": {
        "citation": "(2002) 7 NWLR (Pt. 767) 606",
        "court": "Supreme Court", "year": 2002,
        "principle": "Fundamental rights enforcement; police powers of arrest",
    },

    # ─── Arbitration ───
    "Kano State Urban Development Board v Fanz Construction Ltd": {
        "citation": "(1990) 4 NWLR (Pt. 142) 1",
        "court": "Supreme Court", "year": 1990,
        "principle": "Arbitration agreements; setting aside awards",
    },
    "Statoil (Nig) Ltd v NNPC": {
        "citation": "(2013) 14 NWLR (Pt. 1373) 1",
        "court": "Supreme Court", "year": 2013,
        "principle": "Arbitration; public policy; setting aside awards",
    },

    # ─── IP ───
    "Ferodo Ltd v Ibeto Industries Ltd": {
        "citation": "(2004) 5 NWLR (Pt. 866) 317",
        "court": "Supreme Court", "year": 2004,
        "principle": "Trade mark infringement; passing off",
    },

    # ─── Maritime ───
    "MV Caroline Maersk v Nokoy Investment Ltd": {
        "citation": "(2002) 12 NWLR (Pt. 782) 472",
        "court": "Supreme Court", "year": 2002,
        "principle": "Admiralty jurisdiction; bills of lading",
    },

    # ─── Practice & Procedure ───
    "Tukur v Government of Gongola State": {
        "citation": "(1989) 4 NWLR (Pt. 117) 517",
        "court": "Supreme Court", "year": 1989,
        "principle": "Locus standi; sufficient interest test",
    },
    "Adesanya v President of Nigeria": {
        "citation": "(1981) 5 SC 112",
        "court": "Supreme Court", "year": 1981,
        "principle": "Locus standi; constitutional challenges",
    },
    "Owners of MV Arabella v NAIC": {
        "citation": "(2008) 11 NWLR (Pt. 1097) 182",
        "court": "Supreme Court", "year": 2008,
        "principle": "Service of process; foreign defendants",
    },

    # ═══════════════════════════════════════════════════════
    # EXPANDED CASE DATABASE — added to reduce AI citation
    # hallucinations. Curated from landmark Nigerian decisions
    # (foundational + recent). The `verify_case_name()` matcher
    # uses NAMES only; citations and principles are informational
    # and should be re-verified against NWLR / LPELR before any
    # filing. When in doubt, treat as UNVERIFIED.
    # ═══════════════════════════════════════════════════════

    # ─── Constitutional Law (expansion) ───
    "Awolowo v Shagari": {
        "citation": "(1979) 6-9 SC 51",
        "court": "Supreme Court", "year": 1979,
        "principle": "Two-thirds majority doctrine; presidential election interpretation",
    },
    "Amaechi v INEC": {
        "citation": "(2008) 5 NWLR (Pt. 1080) 227",
        "court": "Supreme Court", "year": 2008,
        "principle": "Gubernatorial election; political party as candidate at elections",
    },
    "Ngige v Obi": {
        "citation": "(2006) 14 NWLR (Pt. 999) 1",
        "court": "Court of Appeal", "year": 2006,
        "principle": "Election petition; Anambra gubernatorial dispute",
    },
    "Marwa v Nyako": {
        "citation": "(2012) 6 NWLR (Pt. 1296) 199",
        "court": "Supreme Court", "year": 2012,
        "principle": "Tenure of governors; cumulative tenure on re-run elections",
    },
    "AG Bendel State v AG Federation": {
        "citation": "(1981) 10 SC 1",
        "court": "Supreme Court", "year": 1981,
        "principle": "Allocation of Revenue Act; legislative procedure; bicameral assent",
    },
    "Ransome-Kuti v AG Federation": {
        "citation": "(1985) 2 NWLR (Pt. 6) 211",
        "court": "Supreme Court", "year": 1985,
        "principle": "Fundamental rights; vicarious liability of State for security forces",
    },
    "INEC v Musa": {
        "citation": "(2003) 3 NWLR (Pt. 806) 72",
        "court": "Supreme Court", "year": 2003,
        "principle": "Registration of political parties; freedom of association",
    },
    "AG Lagos State v AG Federation (No 2)": {
        "citation": "(2004) 18 NWLR (Pt. 904) 1",
        "court": "Supreme Court", "year": 2004,
        "principle": "Withholding of LG funds; federal-state revenue allocation",
    },
    "Garba v University of Maiduguri": {
        "citation": "(1986) 1 NWLR (Pt. 18) 550",
        "court": "Supreme Court", "year": 1986,
        "principle": "Right to fair hearing; expulsion from public institution; natural justice",
    },
    "Action Congress v INEC": {
        "citation": "(2007) 12 NWLR (Pt. 1048) 222",
        "court": "Supreme Court", "year": 2007,
        "principle": "Political party rights; INEC powers; substitution of candidates",
    },
    "Falae v Obasanjo": {
        "citation": "(1999) 4 NWLR (Pt. 599) 476",
        "court": "Court of Appeal", "year": 1999,
        "principle": "Election petition; substantial compliance test (1999 election)",
    },
    "Buhari v INEC": {
        "citation": "(2008) 19 NWLR (Pt. 1120) 246",
        "court": "Supreme Court", "year": 2008,
        "principle": "Election petition; burden of proof; presidential election",
    },
    "Ugwu v Ararume": {
        "citation": "(2007) 12 NWLR (Pt. 1048) 367",
        "court": "Supreme Court", "year": 2007,
        "principle": "Substitution of candidates; party primaries; locus standi of aspirants",
    },
    "AG Federation v AG Abia State (No 2)": {
        "citation": "(2002) 6 NWLR (Pt. 764) 542",
        "court": "Supreme Court", "year": 2002,
        "principle": "Resource control; offshore-onshore dichotomy; revenue allocation",
    },
    "Saraki v FRN": {
        "citation": "(2016) 3 NWLR (Pt. 1500) 531",
        "court": "Supreme Court", "year": 2016,
        "principle": "Code of Conduct Tribunal jurisdiction; declaration of assets",
    },
    "APC v Marafa": {
        "citation": "(2019) 5 NWLR (Pt. 1648) 109",
        "court": "Supreme Court", "year": 2019,
        "principle": "Party primaries; Zamfara nominations dispute; INEC binding party records",
    },
    "Atiku Abubakar v Buhari": {
        "citation": "(2020) 12 NWLR (Pt. 1737) 1",
        "court": "Supreme Court", "year": 2020,
        "principle": "Presidential election petition; standard of proof; substantial compliance",
    },
    "Doherty v Balewa": {
        "citation": "(1961) 1 All NLR 604",
        "court": "Federal Supreme Court", "year": 1961,
        "principle": "Constitutional law; powers of Commission of Inquiry; rule of law",
    },
    "Lakanmi v AG Western State": {
        "citation": "(1971) 1 UILR 201",
        "court": "Supreme Court", "year": 1971,
        "principle": "Validity of military decrees; supremacy of Constitution; separation of powers",
    },

    # ─── Contract Law (expansion) ───
    "Adamu v Pyramid Plant Hire Nigeria Ltd": {
        "citation": "(2007) 1 NWLR (Pt. 1015) 305",
        "court": "Supreme Court", "year": 2007,
        "principle": "Breach of contract; quantum of damages",
    },
    "Sparkling Breweries Ltd v UBN": {
        "citation": "(2001) 15 NWLR (Pt. 737) 539",
        "court": "Supreme Court", "year": 2001,
        "principle": "Banker's contract; duty of confidentiality; mistake in account",
    },
    "Yaro v Arewa Construction Ltd": {
        "citation": "(2007) 17 NWLR (Pt. 1063) 333",
        "court": "Supreme Court", "year": 2007,
        "principle": "Contract construction; performance and discharge",
    },
    "Mosheshe General Merchant Ltd v Nigeria Steel Products Ltd": {
        "citation": "(1987) 2 NWLR (Pt. 55) 110",
        "court": "Supreme Court", "year": 1987,
        "principle": "Letters of credit; contractual obligations in commercial contracts",
    },
    "Stabilini Visinoni Ltd v Mallinson Ltd": {
        "citation": "(2014) 12 NWLR (Pt. 1420) 134",
        "court": "Supreme Court", "year": 2014,
        "principle": "Breach of contract; rescission and damages",
    },
    "Beta Glass Plc v Epaco Holdings Ltd": {
        "citation": "(2011) 1 NWLR (Pt. 1228) 219",
        "court": "Supreme Court", "year": 2011,
        "principle": "Contractual interpretation; intention of parties",
    },
    "ACB Plc v Apugo": {
        "citation": "(2001) 4 NWLR (Pt. 702) 32",
        "court": "Supreme Court", "year": 2001,
        "principle": "Banking contracts; recovery of debt; banker-customer obligations",
    },
    "Sona Breweries Plc v Peters": {
        "citation": "(2005) 1 NWLR (Pt. 908) 478",
        "court": "Supreme Court", "year": 2005,
        "principle": "Sale of goods; breach of warranty; defective products",
    },

    # ─── Land Law (expansion) ───
    "Onwugbufor v Okoye": {
        "citation": "(1996) 1 NWLR (Pt. 424) 252",
        "court": "Supreme Court", "year": 1996,
        "principle": "Proof of title to land; traditional history; acts of ownership",
    },
    "Adelaja v Fanoiki": {
        "citation": "(1990) 2 NWLR (Pt. 131) 137",
        "court": "Supreme Court", "year": 1990,
        "principle": "Five ways of proving title to land (restated)",
    },
    "Mogaji v Cadbury Nigeria Ltd": {
        "citation": "(1985) 2 NWLR (Pt. 7) 393",
        "court": "Supreme Court", "year": 1985,
        "principle": "Land Use Act; statutory right of occupancy; consent of Governor",
    },
    "Olohunde v Adeyoju": {
        "citation": "(2000) 10 NWLR (Pt. 676) 562",
        "court": "Supreme Court", "year": 2000,
        "principle": "Land transactions; effect of unregistered registrable instruments",
    },
    "Anyaegbunam v Osaka": {
        "citation": "(2000) 5 NWLR (Pt. 657) 386",
        "court": "Supreme Court", "year": 2000,
        "principle": "Land transactions; trespass; better title",
    },
    "Folarin v Durojaiye": {
        "citation": "(1988) 1 NWLR (Pt. 70) 351",
        "court": "Supreme Court", "year": 1988,
        "principle": "Customary land tenure; family land; partition",
    },
    "Ezeudu v Obiagwu": {
        "citation": "(1986) 2 NWLR (Pt. 21) 208",
        "court": "Supreme Court", "year": 1986,
        "principle": "Customary land law; communal ownership; alienation",
    },
    "Kyari v Alkali": {
        "citation": "(2001) 11 NWLR (Pt. 724) 412",
        "court": "Supreme Court", "year": 2001,
        "principle": "Land Use Act; certificate of occupancy; precedence over earlier deeds",
    },
    "Ibrahim v Mohammed": {
        "citation": "(2003) 6 NWLR (Pt. 817) 615",
        "court": "Supreme Court", "year": 2003,
        "principle": "Customary right of occupancy; title disputes; northern Nigeria",
    },
    "Olubodun v Lawal": {
        "citation": "(2008) 17 NWLR (Pt. 1115) 1",
        "court": "Supreme Court", "year": 2008,
        "principle": "Family land; alienation without consent; void transactions",
    },
    "Romaine v Romaine": {
        "citation": "(1992) 4 NWLR (Pt. 238) 650",
        "court": "Supreme Court", "year": 1992,
        "principle": "Land law; equitable interests; doctrine of notice",
    },

    # ─── Criminal Law & Procedure (expansion) ───
    "Bozin v The State": {
        "citation": "(1985) 2 NWLR (Pt. 8) 465",
        "court": "Supreme Court", "year": 1985,
        "principle": "Standard of proof in criminal cases; corroboration",
    },
    "Onafowokan v The State": {
        "citation": "(1987) 3 NWLR (Pt. 61) 538",
        "court": "Supreme Court", "year": 1987,
        "principle": "Defence of self-defence; proportionality of force",
    },
    "Yongo v Commissioner of Police": {
        "citation": "(1992) 8 NWLR (Pt. 257) 36",
        "court": "Supreme Court", "year": 1992,
        "principle": "Powers of arrest; reasonable suspicion",
    },
    "Akpan v The State": {
        "citation": "(1992) 6 NWLR (Pt. 248) 439",
        "court": "Supreme Court", "year": 1992,
        "principle": "Murder; intent to kill; provocation as defence",
    },
    "Lori v The State": {
        "citation": "(1980) 8-11 SC 81",
        "court": "Supreme Court", "year": 1980,
        "principle": "Circumstantial evidence; proof beyond reasonable doubt",
    },
    "Idiok v The State": {
        "citation": "(2008) 13 NWLR (Pt. 1104) 225",
        "court": "Supreme Court", "year": 2008,
        "principle": "Identification evidence; visual identification; Turnbull guidelines",
    },
    "Adamu v The State": {
        "citation": "(1991) 4 NWLR (Pt. 187) 530",
        "court": "Supreme Court", "year": 1991,
        "principle": "Common intention; unlawful purpose; group criminal liability",
    },
    "Iyaro v The State": {
        "citation": "(1988) 1 NWLR (Pt. 69) 256",
        "court": "Supreme Court", "year": 1988,
        "principle": "Confessional statement; voluntariness; trial within trial",
    },
    "Nkebisi v The State": {
        "citation": "(2010) 5 NWLR (Pt. 1188) 471",
        "court": "Supreme Court", "year": 2010,
        "principle": "Burden of proof; defence of alibi; proper time to raise alibi",
    },
    "Sunday v The State": {
        "citation": "(2017) 18 NWLR (Pt. 1597) 251",
        "court": "Supreme Court", "year": 2017,
        "principle": "Murder; cause of death; medical evidence requirements",
    },

    # ─── Evidence (expansion) ───
    "Adelumola v The State": {
        "citation": "(1988) 1 NWLR (Pt. 73) 683",
        "court": "Supreme Court", "year": 1988,
        "principle": "Admissibility of confessional statement; effect of retraction",
    },
    "Asariyu v The State": {
        "citation": "(1987) 4 NWLR (Pt. 67) 709",
        "court": "Supreme Court", "year": 1987,
        "principle": "Hearsay rule; res gestae; statements in course of crime",
    },
    "Sambo v The State": {
        "citation": "(1993) 6 NWLR (Pt. 300) 399",
        "court": "Supreme Court", "year": 1993,
        "principle": "Documentary evidence; tendering of documents; proof of contents",
    },
    "Igbinovia v The State": {
        "citation": "(1981) 2 SC 5",
        "court": "Supreme Court", "year": 1981,
        "principle": "Identification evidence; weight of identification testimony",
    },

    # ─── Tort (expansion) ───
    "Anuforo v Obilor": {
        "citation": "(2014) 7 NWLR (Pt. 1407) 466",
        "court": "Supreme Court", "year": 2014,
        "principle": "Negligence; duty of care; foreseeability",
    },
    "Calabar Cement Co Ltd v Daniel": {
        "citation": "(1991) 4 NWLR (Pt. 188) 750",
        "court": "Supreme Court", "year": 1991,
        "principle": "Vicarious liability; course of employment; independent contractor",
    },
    "Strabag Construction Nigeria Ltd v Ogarekpe": {
        "citation": "(1991) 1 NWLR (Pt. 170) 733",
        "court": "Supreme Court", "year": 1991,
        "principle": "Occupier's liability; duty to lawful visitors",
    },
    "Ngilari v Mothercat Ltd": {
        "citation": "(1999) 13 NWLR (Pt. 636) 626",
        "court": "Supreme Court", "year": 1999,
        "principle": "Negligence; res ipsa loquitur; circumstantial proof of negligence",
    },
    "Nigerian Bottling Co Ltd v Ngonadi": {
        "citation": "(1985) 1 NWLR (Pt. 4) 739",
        "court": "Supreme Court", "year": 1985,
        "principle": "Product liability; negligence; defective consumer goods",
    },
    "UBN Ltd v Ozigi": {
        "citation": "(1994) 3 NWLR (Pt. 333) 385",
        "court": "Supreme Court", "year": 1994,
        "principle": "Banker's negligence; conversion; duty to verify signatures",
    },

    # ─── Company Law (expansion) ───
    "Trenco Nigeria Ltd v African Real Estate Ltd": {
        "citation": "(1978) 1 LRN 146",
        "court": "Supreme Court", "year": 1978,
        "principle": "Corporate personality; separate legal entity from members",
    },
    "Yalaju-Amaye v Associated Registered Engineering Contractors Ltd": {
        "citation": "(1990) 4 NWLR (Pt. 145) 422",
        "court": "Supreme Court", "year": 1990,
        "principle": "Minority shareholder protection; oppression and unfair prejudice",
    },
    "Okoya v Santilli": {
        "citation": "(1990) 2 NWLR (Pt. 131) 172",
        "court": "Supreme Court", "year": 1990,
        "principle": "Lifting the veil of incorporation; fraud and impropriety",
    },
    "FBN Plc v Owie": {
        "citation": "(2009) 10 NWLR (Pt. 1149) 359",
        "court": "Supreme Court", "year": 2009,
        "principle": "Corporate authority; ostensible authority of officers",
    },

    # ─── Banking & Finance (expansion) ───
    "Diamond Bank Ltd v Partnership Investment Co Ltd": {
        "citation": "(2009) 18 NWLR (Pt. 1172) 67",
        "court": "Supreme Court", "year": 2009,
        "principle": "Banker-customer relationship; duty of care; payment by mistake",
    },
    "UBN v Sax Nigeria Ltd": {
        "citation": "(1994) 8 NWLR (Pt. 361) 150",
        "court": "Supreme Court", "year": 1994,
        "principle": "Bills of exchange; conversion; conditional indorsement",
    },
    "Skye Bank Plc v Iwu": {
        "citation": "(2017) 16 NWLR (Pt. 1590) 24",
        "court": "Supreme Court", "year": 2017,
        "principle": "Banking employment dispute; National Industrial Court jurisdiction",
    },
    "FBN Plc v Maiwada": {
        "citation": "(2013) 5 NWLR (Pt. 1348) 444",
        "court": "Supreme Court", "year": 2013,
        "principle": "Bank guarantees; demand guarantees vs sureties",
    },
    "Wema Bank Plc v Osilaru": {
        "citation": "(2008) 10 NWLR (Pt. 1094) 150",
        "court": "Supreme Court", "year": 2008,
        "principle": "Banker's lien; combination of accounts; set-off",
    },

    # ─── Family Law (expansion) ───
    "Anekwe v Nweke": {
        "citation": "(2014) 9 NWLR (Pt. 1412) 393",
        "court": "Supreme Court", "year": 2014,
        "principle": "Customary inheritance; female right to inherit; repugnancy doctrine",
    },
    "Ukeje v Ukeje": {
        "citation": "(2014) 11 NWLR (Pt. 1418) 384",
        "court": "Supreme Court", "year": 2014,
        "principle": "Igbo customary law; gender discrimination in inheritance unconstitutional",
    },
    "Mojekwu v Iwuchukwu": {
        "citation": "(2004) 11 NWLR (Pt. 883) 196",
        "court": "Supreme Court", "year": 2004,
        "principle": "Customary law; oli-ekpe custom (qualifying earlier CA decision)",
    },
    "Salubi v Nwariaku": {
        "citation": "(2003) 7 NWLR (Pt. 819) 426",
        "court": "Supreme Court", "year": 2003,
        "principle": "Customary marriage; legitimacy of children",
    },
    "Ezennah v Atta": {
        "citation": "(2004) 7 NWLR (Pt. 873) 468",
        "court": "Supreme Court", "year": 2004,
        "principle": "Statutory marriage; matrimonial causes; custody of children",
    },

    # ─── Election Law (expansion) ───
    "Buhari v Yusuf": {
        "citation": "(2003) 14 NWLR (Pt. 841) 446",
        "court": "Court of Appeal", "year": 2003,
        "principle": "Election petition; pleadings; particulars of malpractice",
    },
    "Ojukwu v Yar Adua": {
        "citation": "(2009) 12 NWLR (Pt. 1154) 50",
        "court": "Supreme Court", "year": 2009,
        "principle": "Presidential election petition; non-compliance must be substantial",
    },
    "Ogboru v Uduaghan": {
        "citation": "(2013) 13 NWLR (Pt. 1370) 33",
        "court": "Supreme Court", "year": 2013,
        "principle": "Election petition; over-voting; effect on declaration",
    },

    # ─── Procedure & Jurisdiction (expansion) ───
    "Skenconsult Nigeria Ltd v Ukey": {
        "citation": "(1981) 1 SC 6",
        "court": "Supreme Court", "year": 1981,
        "principle": "Service of process; non-compliance; void vs voidable proceedings",
    },
    "Bronik Motors Ltd v Wema Bank Ltd": {
        "citation": "(1983) 1 SCNLR 296",
        "court": "Supreme Court", "year": 1983,
        "principle": "Federal High Court jurisdiction; banking business; preliminary objection",
    },
    "Saraki v Kotoye": {
        "citation": "(1992) 9 NWLR (Pt. 264) 156",
        "court": "Supreme Court", "year": 1992,
        "principle": "Interlocutory injunctions; balance of convenience; status quo",
    },
    "Adigun v AG Oyo State": {
        "citation": "(1987) 1 NWLR (Pt. 53) 678",
        "court": "Supreme Court", "year": 1987,
        "principle": "Right to fair hearing; audi alteram partem; chieftaincy disputes",
    },
    "Onyema v Oputa": {
        "citation": "(1987) 3 NWLR (Pt. 60) 259",
        "court": "Supreme Court", "year": 1987,
        "principle": "Tribunal of inquiry; jurisdiction; rules of natural justice",
    },
    "NDIC v CBN": {
        "citation": "(2002) 7 NWLR (Pt. 766) 272",
        "court": "Supreme Court", "year": 2002,
        "principle": "Federal High Court jurisdiction; banking and insurance disputes",
    },
    "Dapianlong v Dariye": {
        "citation": "(2007) 8 NWLR (Pt. 1036) 332",
        "court": "Supreme Court", "year": 2007,
        "principle": "Impeachment; legislative procedure; judicial review",
    },
    "AG Anambra State v AG Federation": {
        "citation": "(2005) 9 NWLR (Pt. 931) 572",
        "court": "Supreme Court", "year": 2005,
        "principle": "Original jurisdiction of Supreme Court; federal-state disputes",
    },

    # ─── Arbitration (expansion) ───
    "NNPC v Klifco Nigeria Ltd": {
        "citation": "(2011) 10 NWLR (Pt. 1255) 209",
        "court": "Supreme Court", "year": 2011,
        "principle": "Arbitration agreement; stay of proceedings; mandatory provisions",
    },
    "MV Lupex v NOC Shipping Services Ltd": {
        "citation": "(2003) 15 NWLR (Pt. 844) 469",
        "court": "Supreme Court", "year": 2003,
        "principle": "Arbitration; foreign arbitration clauses; admiralty jurisdiction",
    },
    "Sundersons Ltd v Cruiser Shipping Agencies Ltd": {
        "citation": "(2010) 5 NWLR (Pt. 1186) 60",
        "court": "Supreme Court", "year": 2010,
        "principle": "Arbitration; setting aside awards; misconduct of arbitrator",
    },

    # ─── Tax (expansion) ───
    "AG Lagos State v Eko Hotels Ltd": {
        "citation": "(2018) 7 NWLR (Pt. 1619) 518",
        "court": "Supreme Court", "year": 2018,
        "principle": "Sales tax vs VAT; State legislative competence on consumption taxes",
    },
    "Shell Petroleum Development Co Nigeria Ltd v FBIR": {
        "citation": "(1996) 8 NWLR (Pt. 466) 256",
        "court": "Supreme Court", "year": 1996,
        "principle": "Petroleum profit tax; allowable deductions; revenue assessment",
    },

    # ─── Human Rights (expansion) ───
    "Uzoukwu v Ezeonu II": {
        "citation": "(1991) 6 NWLR (Pt. 200) 708",
        "court": "Court of Appeal", "year": 1991,
        "principle": "Fundamental rights enforcement procedure; jurisdiction of High Court",
    },
    "Jim-Jaja v Commissioner of Police Rivers State": {
        "citation": "(2013) 6 NWLR (Pt. 1350) 225",
        "court": "Supreme Court", "year": 2013,
        "principle": "Unlawful detention; damages for breach of fundamental rights",
    },
    "Chairman EFCC v Littlechild": {
        "citation": "(2015) 17 NWLR (Pt. 1488) 339",
        "court": "Supreme Court", "year": 2015,
        "principle": "Fundamental rights; powers of EFCC; due process in investigations",
    },

    # ─── Labour & Employment (expansion) ───
    "Texaco Nigeria Plc v Kehinde": {
        "citation": "(2001) 6 NWLR (Pt. 708) 224",
        "court": "Supreme Court", "year": 2001,
        "principle": "Wrongful dismissal; damages; reasonable notice",
    },
    "PHCN v Offoelo": {
        "citation": "(2012) 17 NWLR (Pt. 1330) 463",
        "court": "Supreme Court", "year": 2012,
        "principle": "Public employment with statutory flavour; reinstatement remedy",
    },
    "Bamgboye v University of Ilorin": {
        "citation": "(1999) 10 NWLR (Pt. 622) 290",
        "court": "Supreme Court", "year": 1999,
        "principle": "Employment dismissal; fair hearing required for statutory employees",
    },

    # ─── Maritime (expansion) ───
    "American International Insurance Co v Ceekay Traders Ltd": {
        "citation": "(1981) 5 SC 81",
        "court": "Supreme Court", "year": 1981,
        "principle": "Marine insurance; subrogation; duty to disclose material facts",
    },
    "MV Panormos Bay v Olam Nigeria Plc": {
        "citation": "(2004) 5 NWLR (Pt. 865) 1",
        "court": "Supreme Court", "year": 2004,
        "principle": "Admiralty jurisdiction; bills of lading; carriage of goods by sea",
    },

    # ─── Oil & Gas ───
    "Shell Petroleum Development Co v Isaiah": {
        "citation": "(2001) 11 NWLR (Pt. 723) 168",
        "court": "Supreme Court", "year": 2001,
        "principle": "Compensation for oil pollution; Petroleum Act; duty to clean up",
    },
    "Nigerian Agip Oil Co Ltd v Kemmer": {
        "citation": "(2001) 8 NWLR (Pt. 716) 506",
        "court": "Supreme Court", "year": 2001,
        "principle": "Oil and gas; trespass to land; quantum of damages",
    },
    "SPDC v Tiebo VII": {
        "citation": "(2005) 9 NWLR (Pt. 931) 439",
        "court": "Supreme Court", "year": 2005,
        "principle": "Oil pollution; community rights; environmental damage",
    },

    # ─── Insurance ───
    "Royal Exchange Assurance v Anumnu": {
        "citation": "(2003) 6 NWLR (Pt. 815) 52",
        "court": "Supreme Court", "year": 2003,
        "principle": "Insurance contracts; duty of utmost good faith; non-disclosure",
    },
    "NICON Hotels Ltd v NDC Ltd": {
        "citation": "(2007) 13 NWLR (Pt. 1051) 237",
        "court": "Supreme Court", "year": 2007,
        "principle": "Insurance; subrogation; rights of insurer",
    },

    # ─── IP ───
    "Microsoft Corporation v Frank Investment Nigeria Ltd": {
        "citation": "(2009) 5 CLRN 96",
        "court": "Federal High Court", "year": 2009,
        "principle": "Software piracy; copyright infringement; Anton Piller orders",
    },
    "Procter & Gamble Co v Global Soap and Detergent Industries Ltd": {
        "citation": "(2013) 4 NWLR (Pt. 1344) 333",
        "court": "Court of Appeal", "year": 2013,
        "principle": "Trade mark infringement; passing off; goodwill",
    },

    # ─── Equity & Trusts (expansion) ───
    "Mobil Oil Nigeria Ltd v Coker": {
        "citation": "(1975) 3 SC 175",
        "court": "Supreme Court", "year": 1975,
        "principle": "Specific performance; equitable remedy; readiness and willingness",
    },

    # ─── Customary Law (expansion) ───
    "Lewis v Bankole": {
        "citation": "(1908) 1 NLR 81",
        "court": "Supreme Court", "year": 1908,
        "principle": "Foundational case on customary law; family land; Yoruba inheritance",
    },
    "Cole v Folami": {
        "citation": "(1956) 1 FSC 66",
        "court": "Federal Supreme Court", "year": 1956,
        "principle": "Customary law; alienation of family property; consent of family head",
    },
}

# ── Citation regex patterns ──
_CITATION_PATTERNS = [
    # NWLR format: (YYYY) Vol NWLR (Pt. XXX) Page
    re.compile(
        r"\(?(?P<year>(?:18|19|20)\d{2})\)?\s+"
        r"(?P<vol>\d{1,3})\s+"
        r"(?P<reporter>NWLR|SCNLR|SC|LPELR|FWLR|CCHCJ|NCLR|NSCC|WACA|NRNLR|WLR)"
        r"(?:\s*\(?\s*Pt\.?\s*(?P<part>\d+)\)?)?"
        r"\s+(?P<page>\d{1,4})",
        re.IGNORECASE,
    ),
    # LPELR format: [YYYY] LPELR-NNNNN(COURT)
    re.compile(
        r"\[?(?P<year>(?:19|20)\d{2})\]?\s+"
        r"LPELR[-\s]?(?P<num>\d{2,6})"
        r"(?:\((?P<court>SC|CA|HC|NIC)\))?",
        re.IGNORECASE,
    ),
]


def extract_citations(text: str) -> list[dict]:
    """Pull every citation-shaped string out of text."""
    found = []
    seen_spans = set()
    for pattern in _CITATION_PATTERNS:
        for m in pattern.finditer(text):
            span = m.span()
            if any(s[0] <= span[0] < s[1] for s in seen_spans):
                continue
            seen_spans.add(span)
            found.append({
                "raw": m.group(0).strip(),
                "year": m.groupdict().get("year", ""),
                "reporter": m.groupdict().get("reporter", "LPELR"),
                "start": span[0],
                "end": span[1],
            })
    return found


def extract_case_names(text: str) -> list[str]:
    """Extract case names in the format 'X v Y'."""
    pattern = re.compile(
        r"\b([A-Z][A-Za-z&\.\s\-']{2,60}?)\s+v\.?\s+([A-Z][A-Za-z&\.\s\-']{2,60}?)"
        r"(?=\s*[\(\[\.,;]|\s+(?:and|or|in|on|at|of)\b|$)",
        re.MULTILINE,
    )
    names = []
    for m in pattern.finditer(text):
        full = f"{m.group(1).strip()} v {m.group(2).strip()}"
        full = re.sub(r"\s+", " ", full)
        if 8 <= len(full) <= 120:
            names.append(full)
    return list(dict.fromkeys(names))  # dedupe while preserving order


def verify_case_name(name: str) -> Optional[dict]:
    """Look up a case name with exact, partial, and fuzzy matching."""
    name_clean = re.sub(r"\s+", " ", name.strip()).lower()

    # Empty / whitespace-only input must NOT match anything. The
    # substring loop below uses ``name_clean in key.lower()``, and an
    # empty string is a substring of every key in Python — without this
    # guard, ``verify_case_name("")`` would silently report the first
    # database entry as a "partial match", labelling AI hallucinations
    # of empty responses as verified.
    if not name_clean:
        return None

    # Exact match
    for key, val in VERIFIED_NIGERIAN_CASES.items():
        if key.lower() == name_clean:
            return {"name": key, **val, "match_type": "exact"}

    # Partial/substring match
    for key, val in VERIFIED_NIGERIAN_CASES.items():
        if key.lower() in name_clean or name_clean in key.lower():
            return {"name": key, **val, "match_type": "partial"}

    # Fuzzy token overlap (last resort)
    name_tokens = set(name_clean.replace(" v ", " ").split())
    best_score = 0
    best_match = None

    for key, val in VERIFIED_NIGERIAN_CASES.items():
        key_tokens = set(key.lower().replace(" v ", " ").split())
        if not key_tokens or not name_tokens:
            continue
        overlap = len(name_tokens & key_tokens)
        score = overlap / max(len(name_tokens), len(key_tokens))
        if score > best_score and score >= 0.7:
            best_score = score
            best_match = {"name": key, **val, "match_type": "fuzzy", "score": round(score, 2)}

    return best_match


def find_relevant_verified_cases(query: str, top_k: int = 8) -> list[dict]:
    """Retrieval helper for grounded precedent finding.

    Searches ``VERIFIED_NIGERIAN_CASES`` for cases whose ``principle`` field
    most strongly overlaps the query keywords. Returns up to ``top_k`` matches
    sorted by overlap score, each as a dict ready to inject into a prompt.

    The scoring is intentionally simple (token-overlap, no embeddings) because:
      * the verified DB is small and curated (every entry is a landmark);
      * we only need a candidate set, not a final ranking — the AI re-ranks; and
      * it has zero external deps and works offline.

    Returns empty list if query is empty or no candidates score > 0.
    """
    if not query or not query.strip():
        return []
    stopwords = {
        "the","a","an","and","or","but","in","on","at","to","for","of","is","are",
        "was","were","be","been","being","have","has","had","do","does","did","will",
        "would","could","should","may","might","shall","this","that","these","those",
        "what","when","where","which","who","how","if","not","no","can","client",
        "matter","case","issue","situation","problem","question","advice","legal","law",
        "nigerian","nigeria","under","about",
    }
    words = re.findall(r"\b[a-zA-Z]{3,}\b", query.lower())
    keywords = {w for w in words if w not in stopwords}
    if not keywords:
        return []

    scored: list[tuple[int, str, dict]] = []
    for name, val in VERIFIED_NIGERIAN_CASES.items():
        principle = (val.get("principle") or "").lower()
        name_low = name.lower()
        principle_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", principle))
        name_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", name_low))
        score = (
            3 * len(keywords & principle_tokens)
            + 1 * len(keywords & name_tokens)
        )
        if score > 0:
            scored.append((score, name, val))

    scored.sort(key=lambda t: (-t[0], t[1]))
    return [
        {"name": n, **v, "_score": s}
        for s, n, v in scored[:top_k]
    ]


def verify_response_citations(response_text: str) -> dict:
    """Full citation audit on AI-generated legal response."""
    citations = extract_citations(response_text)
    case_names = extract_case_names(response_text)

    verified_cases = []
    unverified_cases = []

    for name in case_names:
        match = verify_case_name(name)
        if match:
            verified_cases.append({"raw": name, **match})
        else:
            unverified_cases.append(name)

    return {
        "citations_found": len(citations),
        "case_names_found": len(case_names),
        "verified_cases": verified_cases,
        "unverified_cases": unverified_cases,
        "citations": citations,
    }


def render_citation_audit(audit: dict) -> str:
    """Returns HTML for citation audit display in Streamlit."""
    if audit["case_names_found"] == 0 and audit["citations_found"] == 0:
        return ""

    verified_count = len(audit["verified_cases"])
    unverified_count = len(audit["unverified_cases"])

    if unverified_count == 0 and verified_count > 0:
        banner_color = "#059669"
        banner_bg = "#f0fdf4"
        icon = "✅"
        msg = f"All {verified_count} case(s) cited match the verified Nigerian case database."
    elif verified_count > 0 and unverified_count > 0:
        banner_color = "#d97706"
        banner_bg = "#fffbeb"
        icon = "⚠️"
        msg = (f"{verified_count} verified · {unverified_count} unverified — "
               "check unverified citations against NWLR/LPELR before relying on them.")
    else:
        banner_color = "#dc2626"
        banner_bg = "#fef2f2"
        icon = "🚫"
        msg = (f"{unverified_count} case citation(s) could NOT be verified against "
               "the database. Treat as UNVERIFIED — do not file without independent check.")

    html = f"""
    <div style="background:{banner_bg}; border:1.5px solid {banner_color};
                border-radius:0.6rem; padding:0.9rem 1.1rem; margin:1rem 0; font-size:0.88rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="color:{banner_color};">{icon} Citation Audit</strong>
            <span style="font-size:0.78rem; color:{banner_color};">
                {audit['citations_found']} citation(s) · {audit['case_names_found']} case name(s)
            </span>
        </div>
        <p style="margin:0.5rem 0 0 0; color:{banner_color};">{msg}</p>
    </div>"""

    if audit["verified_cases"]:
        html += f'<details style="margin-top:0.5rem;"><summary style="cursor:pointer; font-size:0.85rem; color:#059669; font-weight:600;">✅ Verified Cases ({len(audit["verified_cases"])})</summary><div style="margin-top:0.5rem; font-size:0.83rem;">'
        for vc in audit["verified_cases"]:
            html += (f'<div style="padding:0.4rem 0; border-bottom:1px solid #e2e8f0;">'
                     f'<strong>{esc(vc["name"])}</strong> '
                     f'<code style="background:#f0fdf4; padding:0.1rem 0.4rem; border-radius:3px;">{esc(vc["citation"])}</code><br>'
                     f'<small style="color:var(--la-text2);">{esc(vc["court"])} · {vc["year"]} · {esc(vc["principle"])}</small>'
                     f'</div>')
        html += '</div></details>'

    if audit["unverified_cases"]:
        html += f'<details style="margin-top:0.5rem;" open><summary style="cursor:pointer; font-size:0.85rem; color:#dc2626; font-weight:600;">⚠️ Unverified — Check Before Filing ({len(audit["unverified_cases"])})</summary><div style="margin-top:0.5rem; font-size:0.83rem;">'
        for uc in audit["unverified_cases"]:
            html += (f'<div style="padding:0.4rem 0; border-bottom:1px solid #fee2e2;">'
                     f'<strong style="color:#991b1b;">{esc(uc)}</strong> '
                     f'<span style="background:#fee2e2; color:#991b1b; padding:2px 6px; border-radius:3px; font-size:0.75rem;">UNVERIFIED</span><br>'
                     f'<small style="color:#7f1d1d;">Not found in verified database. Verify on NWLR / LPELR / LawPavilion before citing.</small>'
                     f'</div>')
        html += '</div></details>'

    return html

