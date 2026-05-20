"""LexiAssist fuzzy-name matching for the conflict-checker pre-filter.

No external library required — token-set similarity mirrors
rapidfuzz.fuzz.token_set_ratio behaviour.
"""
from __future__ import annotations

from .runtime import st, re

# ═══════════════════════════════════════════════════════
# PHASE 4 — FUZZY NAME MATCHING (Conflict Checker pre-filter)
# ═══════════════════════════════════════════════════════

def _fuzzy_score(a: str, b: str) -> float:
    """Token-set similarity 0.0–1.0. No external library required.
    Mirrors rapidfuzz.fuzz.token_set_ratio logic."""
    def _tok(s: str) -> set:
        return set(re.sub(r"[^a-z0-9\s]", " ", s.lower()).split())
    ta, tb = _tok(a), _tok(b)
    if not ta or not tb:
        return 0.0
    inter = ta & tb
    if not inter:
        return 0.0
    return len(inter) / max(len(ta), len(tb))


def get_fuzzy_conflict_candidates(
    prospect_name: str,
    opponent_name: str,
    related: str,
    extra: str,
    threshold: float = 0.45,
) -> dict[str, list[str]]:
    """
    Pre-screen existing clients and case titles for name similarity BEFORE the AI call.
    Returns dict of {category: [matching names]} to inject into the conflict check prompt.
    Only candidates above threshold are passed to AI — reduces LLM cost and false negatives.
    """
    all_prospects = [
        s.strip() for s in
        f"{prospect_name}\n{opponent_name}\n{related}\n{extra}".splitlines()
        if s.strip()
    ]

    client_hits: list[str] = []
    case_hits:   list[str] = []

    for p in all_prospects:
        if len(p) < 3:
            continue
        for cl in st.session_state.get("clients", []):
            name = cl.get("name", "")
            if _fuzzy_score(p, name) >= threshold:
                client_hits.append(name)
        for c in st.session_state.get("cases", []):
            title = c.get("title", "")
            parties = f"{title} {c.get('notes', '')}"
            if _fuzzy_score(p, parties) >= threshold:
                case_hits.append(title)

    return {
        "fuzzy_client_matches": list(dict.fromkeys(client_hits)),
        "fuzzy_case_matches":   list(dict.fromkeys(case_hits)),
    }

DEFAULT_TEMPLATES = [
    {"id": "builtin_1", "name": "Employment Contract", "cat": "Corporate", "builtin": True,
     "content": "EMPLOYMENT CONTRACT\n\nThis Employment Contract is made on [DATE] between:\n\n1. [EMPLOYER NAME] (\"Employer\"), RC No: [NUMBER], of [ADDRESS]\n\n2. [EMPLOYEE FULL NAME] (\"Employee\"), of [ADDRESS]\n\nTERMS AND CONDITIONS:\n1. POSITION: The Employee is employed as [JOB TITLE] in the [DEPARTMENT] department.\n2. COMMENCEMENT: Employment commences on [START DATE].\n3. PROBATION: Subject to a probationary period of [MONTHS] months, during which either party may terminate on 2 weeks' written notice.\n4. SALARY: ₦[AMOUNT] per month (gross), payable on the [X]th of each month.\n5. WORKING HOURS: [X] hours per week, [DAYS]. Overtime as agreed in writing.\n6. ANNUAL LEAVE: [X] working days per year, taken by mutual arrangement.\n7. PENSION: The Employer shall enrol the Employee under the Contributory Pension Scheme in accordance with the Pension Reform Act 2014. Employer contribution: 10%. Employee contribution: 8%.\n8. TAXES: PAYE tax shall be deducted at source per the Personal Income Tax Act.\n9. TERMINATION: Either party may terminate on [NOTICE PERIOD] written notice after confirmation. Summary dismissal for gross misconduct per the Labour Act.\n10. CONFIDENTIALITY: The Employee shall not disclose trade secrets or confidential information during or after employment.\n11. RESTRICTIVE COVENANT: [INCLUDE / DELETE AS APPROPRIATE — specify scope, duration, geography]\n12. GOVERNING LAW: This Contract is governed by the Labour Act Cap L1 LFN 2004 and the laws of the Federal Republic of Nigeria.\n\nSIGNED:\n_________________________ (for the Employer)\n_________________________ (Employee)\nDate: ___________________\nWitness: ________________"},
    {"id": "builtin_2", "name": "Tenancy Agreement", "cat": "Property", "builtin": True,
     "content": "TENANCY AGREEMENT\n\nThis Tenancy Agreement is made on [DATE] BETWEEN:\n[LANDLORD FULL NAME] of [ADDRESS] (\"Landlord\")\nAND\n[TENANT FULL NAME] of [ADDRESS] (\"Tenant\")\n\n1. PREMISES: The property at [FULL ADDRESS] (\"the Premises\").\n2. TERM: [DURATION] commencing [START DATE] and ending [END DATE].\n3. RENT: ₦[AMOUNT] per [PERIOD], payable [in advance / monthly / quarterly].\n4. DEPOSIT: ₦[AMOUNT] refundable security deposit, held against damage and breach.\n5. USE: [Residential / Commercial] purposes only. No subletting without Landlord's written consent.\n6. REPAIRS: Landlord responsible for structural repairs. Tenant responsible for minor/day-to-day maintenance.\n7. TERMINATION: [X] months' written notice by either party.\n8. STAMP DUTY: This agreement shall be duly stamped per the Stamp Duties Act.\n9. GOVERNING LAW: [Applicable State Tenancy Law, e.g. Lagos Tenancy Law 2011 / Rivers State Tenancy Law]\n\nSIGNED:\n_______________________ (Landlord)\n_______________________ (Tenant)\n\nWitness to Landlord:\nName: _________________ Signature: _____________\n\nWitness to Tenant:\nName: _________________ Signature: _____________\n\n⚠️ STAMP DUTY NOTE: Tenancy < 7 years: 0.78% × annual rent × years. Tenancy 7–21 years: 3% of annual rent."},
    {"id": "builtin_3", "name": "Power of Attorney", "cat": "Litigation", "builtin": True,
     "content": "GENERAL POWER OF ATTORNEY\n\nI, [GRANTOR], of [ADDRESS], appoint [ATTORNEY] of [ADDRESS] as my Attorney.\n\nPOWERS:\n1. Recover debts and execute settlements\n2. Manage real and personal property\n3. Appear before any court or tribunal\n\nIRREVOCABLE for [PERIOD].\n\nDated: [DATE]\nSigned: _______\nWitness: _______"},
    {"id": "builtin_4", "name": "Written Address (Skeleton)", "cat": "Litigation", "builtin": True,
     "content": "IN THE [COURT NAME]\nSUIT NO: [NUMBER]\n\nBETWEEN:\n[CLAIMANT] ............ Claimant\nAND\n[DEFENDANT] ........... Defendant\n\nWRITTEN ADDRESS OF THE [PARTY]\n\n1.0 INTRODUCTION\n2.0 BRIEF FACTS\n3.0 ISSUES FOR DETERMINATION\n4.0 ARGUMENTS\n   4.1 Issue One\n   4.2 Issue Two\n5.0 CONCLUSION\n\nDated: [DATE]\nCounsel: _______"},
    {"id": "builtin_5", "name": "Demand Letter", "cat": "Commercial", "builtin": True,
     "content": "OUR REF: [REF]\nDATE: [DATE]\n\n[RECIPIENT NAME]\n[ADDRESS]\n\nDear Sir/Madam,\n\nRE: DEMAND FOR PAYMENT OF ₦[AMOUNT]\n\nWe are Solicitors and Advocates to [CLIENT NAME] on whose instructions we write this letter.\n\nOur client instructs us that [STATE FACTS OF THE DEBT / OBLIGATION].\n\nDespite repeated demands, you have failed, refused and/or neglected to discharge the above obligation.\n\nWe are therefore instructed and do hereby DEMAND that you pay the sum of ₦[AMOUNT] ([AMOUNT IN WORDS] NAIRA) to our client within [DAYS] days of the date of this letter.\n\nFailing compliance, we have firm instructions to institute legal proceedings against you in the appropriate court to recover the said sum, together with interest, costs and all further reliefs available in law, without any further notice to you.\n\nGOVERNING LAW: This demand is made under the laws of the Federal Republic of Nigeria.\n\nYours faithfully,\n[FIRM NAME]\n[ADDRESS] | [PHONE] | [EMAIL]"},
    {"id": "builtin_5b", "name": "Statutory Demand (CAMA 2020)", "cat": "Corporate", "builtin": True,
     "content": "STATUTORY DEMAND NOTICE\n(Pursuant to Section 572, Companies and Allied Matters Act 2020)\n\nDATE: [DATE]\n\nTO: THE DIRECTORS OF\n[COMPANY NAME] (RC No: [NUMBER])\n[REGISTERED ADDRESS]\n\nDear Sirs,\n\nRE: STATUTORY DEMAND FOR PAYMENT OF ₦[AMOUNT]\n\nWe act as Solicitors for [CREDITOR NAME] ('the Creditor') and write on their instructions.\n\n1. The Creditor is owed the sum of ₦[AMOUNT] ([AMOUNT IN WORDS]) by your company, being [DESCRIPTION OF DEBT — invoice nos./contract reference/loan], which sum is due and payable and has remained unpaid since [DATE].\n\n2. TAKE NOTICE that pursuant to Section 572(1)(a) of the Companies and Allied Matters Act 2020, if the above sum is not paid within TWENTY-ONE (21) DAYS from the date of service of this demand, your company shall be deemed to be unable to pay its debts, and the Creditor shall be at liberty to present a winding-up petition against your company at the Federal High Court without further notice.\n\n3. Payment should be made to:\nAccount Name: [ACCOUNT NAME]\nBank: [BANK NAME]\nAccount Number: [ACCOUNT NO.]\nSort Code: [IF APPLICABLE]\n\n4. Upon receipt of full payment, this demand shall be withdrawn.\n\nYou are strongly advised to take independent legal advice on this letter immediately.\n\nYours faithfully,\n[FIRM NAME]\nSolicitors for the Creditor\n[ADDRESS] | [PHONE] | [EMAIL]"},
    {"id": "builtin_5c", "name": "Retainer Agreement", "cat": "Commercial", "builtin": True,
     "content": "LEGAL RETAINER AGREEMENT\n\nThis Retainer Agreement is made on [DATE] between:\n\n[FIRM NAME] ('the Firm')\nof [FIRM ADDRESS]\nRC/BN: [IF APPLICABLE]\n\nAND\n\n[CLIENT NAME] ('the Client')\nof [CLIENT ADDRESS]\n\n1. SCOPE OF SERVICES\n   The Firm is retained to provide the following legal services:\n   [Describe scope — e.g. general corporate advisory / employment law / all commercial matters / specific matter]\n\n2. RETAINER FEE\n   (a) Monthly retainer: ₦[AMOUNT] payable on or before the [X]th of each month.\n   (b) Included: up to [X] hours of advisory and correspondence per month.\n   (c) Excess hours: billed at ₦[RATE]/hour.\n   (d) Litigation: separate engagement letter required.\n\n3. DISBURSEMENTS\n   All filing fees, stamp duties, process fees, travel and photocopying costs shall be invoiced separately.\n\n4. BILLING\n   Invoices shall be rendered [monthly/quarterly] and are payable within 14 days.\n\n5. CONFIDENTIALITY\n   The Firm shall maintain strict client confidentiality pursuant to Rule 17 of the Rules of Professional Conduct for Legal Practitioners 2007.\n\n6. CONFLICT OF INTEREST\n   The Firm shall promptly disclose any conflict and seek the Client's consent or withdraw as required by the RPC.\n\n7. TERMINATION\n   Either party may terminate on 30 days' written notice. Outstanding fees shall remain due.\n\n8. GOVERNING LAW\n   This Agreement is governed by the laws of the Federal Republic of Nigeria.\n\n   SIGNED:\n   ___________________________ (Authorised Signatory for the Firm)\n   ___________________________ (Client / Authorised Representative)\n   Date: ___________________"},
    {"id": "builtin_6", "name": "Deed of Assignment (Land)", "cat": "Property", "builtin": True,
     "content": "DEED OF ASSIGNMENT\n\nDATE: [DATE]\n\nPARTIES:\n1. [ASSIGNOR NAME] of [ADDRESS] (\"Assignor\")\n2. [ASSIGNEE NAME] of [ADDRESS] (\"Assignee\")\n\nRECITALS:\nA. The Assignor is the beneficial owner of the property described in the Schedule.\nB. The Assignor has agreed to assign all right, title and interest in the said property to the Assignee for the consideration stated herein.\n\nNOW THIS DEED WITNESSES:\n1. CONSIDERATION: The Assignee has paid the Assignor the sum of ₦[AMOUNT] (the receipt of which the Assignor hereby acknowledges).\n2. ASSIGNMENT: The Assignor hereby assigns unto the Assignee ALL THAT piece of land known as [DESCRIPTION], covered by [C of O/Deed/Survey Plan No.], situated at [ADDRESS], TOGETHER with all buildings, fixtures and appurtenances.\n3. COVENANT FOR TITLE: The Assignor covenants with the Assignee that the Assignor has the right to assign the property free from encumbrances.\n4. INDEMNITY: The Assignor shall indemnify the Assignee against any claim arising from prior ownership.\n\nTHE SCHEDULE\nAll that piece of land situate at [FULL ADDRESS], measuring approximately [SIZE] and more particularly delineated on Survey Plan No. [NUMBER] prepared by [SURVEYOR].\n\nIN WITNESS WHEREOF the parties have executed this Deed as of the date first written above.\n\nSigned, sealed and delivered\nby the said ASSIGNOR: _____________\nin the presence of:\nName: _____________ Signature: _____________\nAddress: _____________\nOccupation: _____________\n\nSigned, sealed and delivered\nby the said ASSIGNEE: _____________\nin the presence of:\nName: _____________ Signature: _____________\nAddress: _____________\nOccupation: _____________"},
    {"id": "builtin_7", "name": "Affidavit (General)", "cat": "Litigation", "builtin": True,
     "content": "IN THE [HIGH COURT OF [STATE] STATE / FEDERAL HIGH COURT]\n[JUDICIAL DIVISION]\nSUIT NO: [NUMBER]\n\nIN THE MATTER OF: [SUBJECT]\n\nAFFIDAVIT\n\nI, [FULL NAME], [Occupation], of [Full Address], do hereby make oath and state as follows:\n\n1. That I am the [Applicant/Respondent/Claimant/Defendant] in this matter and I am conversant with the facts deposed to herein.\n\n2. That [STATE FACTS IN NUMBERED PARAGRAPHS — each paragraph to contain one fact]\n\n3. That [CONTINUE FACTS...]\n\n4. That I depose to this Affidavit in good faith believing the contents to be true and correct to the best of my knowledge and belief.\n\nDEPONENT: _____________\n\nSWORN TO at [PLACE] this [DATE]\nBEFORE ME: _____________\n[Commissioner for Oaths / Notary Public]\n\n⚠️ STAMP DUTY: ₦200 flat — Stamp Duties Act"},
    {"id": "builtin_8", "name": "Memorandum of Appearance", "cat": "Litigation", "builtin": True,
     "content": "IN THE [COURT NAME]\n[JUDICIAL DIVISION]\nSUIT NO: [NUMBER]\n\nBETWEEN:\n[CLAIMANT/PLAINTIFF]                           ...  Claimant/Plaintiff\n                                AND\n[DEFENDANT]                                    ...  Defendant\n\nMEMORANDUM OF APPEARANCE\n\nTake notice that [LAW FIRM NAME] of [ADDRESS], solicitors for the Defendant, hereby enter appearance on behalf of the Defendant in this suit.\n\nConditions of Appearance: [UNCONDITIONAL / CONDITIONAL — state conditions if any]\n\nDated this [DATE]\n\n[LAW FIRM NAME]\n[ADDRESS]\n[PHONE]\n[EMAIL]\nSolicitors for the Defendant\n\nTO:\n[CLAIMANT'S SOLICITORS / CLAIMANT]\n[ADDRESS]"},
    {"id": "builtin_9", "name": "Undertaking as to Damages", "cat": "Litigation", "builtin": True,
     "content": "IN THE [COURT NAME]\nSUIT NO: [NUMBER]\n\nBETWEEN:\n[APPLICANT]          ...  Applicant\n         AND\n[RESPONDENT]         ...  Respondent\n\nUNDERTAKING AS TO DAMAGES\n\nI/We, [APPLICANT/SOLICITOR NAME], of [ADDRESS], hereby undertake to the Court that:\n\n1. If the Court grants an interlocutory injunction/Mareva order in this matter and it shall later appear that the Respondent has suffered loss by reason of the order, and the Court is of opinion that the Applicant ought to pay compensation to the Respondent, I/We will comply with any order the Court may make.\n\n2. This undertaking is given in consideration of the Court granting the relief sought in this application.\n\n3. I/We confirm the Applicant has assets within the jurisdiction sufficient to meet any award of compensation that may be ordered.\n\nDated: [DATE]\n\nSigned: _____________\n[Applicant / Applicant's Solicitor]\n\n[FILE BEFORE SERVICE OF ORDER — mandatory for interlocutory injunctions per Kotoye v CBN [1989] NWLR]"},
    {"id": "builtin_10", "name": "Pre-Action Protocol Notice (Lagos)", "cat": "Litigation", "builtin": True,
     "content": "OUR REF: [REF]\nDATE: [DATE]\n\n[DEFENDANT / RESPONDENT NAME]\n[ADDRESS]\n\nDear Sir/Madam,\n\nPRE-ACTION NOTICE — [SUBJECT MATTER]\n[Pursuant to Order 13 Rule 14, High Court of Lagos State (Civil Procedure) Rules 2019]\n\nWe are Solicitors and Advocates to [CLIENT NAME] and write on their instructions.\n\n1. FACTS: [State brief facts of the claim]\n\n2. CLAIM: Our client's claim against you is for: ₦[AMOUNT] / [other relief], arising from [brief basis].\n\n3. DOCUMENTS RELIED UPON: [List key documents]\n\n4. INVITATION TO SETTLE: Pursuant to the Pre-Action Protocol, we invite you to settle this matter within 30 days of the date of this letter, failing which our client shall proceed to institute legal proceedings in the appropriate court without further notice to you.\n\n5. RESPONSE: Kindly respond to this notice within 30 days, indicating whether you accept or dispute the claim, and if disputed, the grounds thereof.\n\nYours faithfully,\n[LAW FIRM NAME]\n[ADDRESS] | [PHONE] | [EMAIL]\nSolicitors to [CLIENT NAME]\n\n⚠️ Note: Failure to respond to a Pre-Action Protocol Notice may result in adverse costs orders — Order 13 Rule 14, Lagos HCCPR 2019."},
    {"id": "builtin_11", "name": "Notice of Appeal (Court of Appeal)", "cat": "Litigation", "builtin": True,
     "content": "IN THE COURT OF APPEAL\n[DIVISION] DIVISION\nAPPEAL NO: CA/[DIV]/[NUMBER]/[YEAR]\n\nBETWEEN:\n[APPELLANT]                ...  Appellant\n         AND\n[RESPONDENT]               ...  Respondent\n\nNOTICE OF APPEAL\n\nTAKE NOTICE that [APPELLANT], being dissatisfied with the decision of [LOWER COURT] delivered on [DATE] in Suit No. [NUMBER], hereby appeals to the Court of Appeal upon the following grounds:\n\nGROUNDS OF APPEAL:\n1. The learned trial Judge erred in law in [STATE GROUND] in that:\n   (a) [PARTICULARS]\n   (b) [PARTICULARS]\n\n2. The decision is against the weight of evidence in that:\n   (a) [PARTICULARS]\n\n3. [ADD FURTHER GROUNDS AS NECESSARY]\n\nRELIEF SOUGHT:\nThe Appellant prays this Honourable Court to:\n(a) Allow this appeal;\n(b) Set aside the decision of the lower court;\n(c) [STATE SPECIFIC RELIEF — substituted judgment / retrial / etc.]\n(d) Award costs in favour of the Appellant.\n\nDated this [DATE]\n\n[LAW FIRM NAME]\n[ADDRESS]\nSolicitors for the Appellant\n\nTO: The Registrar, Court of Appeal, [Division]\nTO: [RESPONDENT'S SOLICITORS]\n\n⚠️ Filing Deadline: 3 months from date of judgment — Section 25(2) Court of Appeal Act.\n⚠️ Filing Fee: ₦100,000 (verify with Registry before filing)."},
]

