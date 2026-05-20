# Privacy Notice

**Effective date:** {effective_date}
**Data controller:** {firm_name}
**Address:** {firm_address}
**Email:** {firm_email}
**Phone:** {firm_phone}

This Privacy Notice explains how **{firm_name}** (the "Firm", "we", "us") collects, uses, stores and protects personal data when you use the LexiAssist legal workflow application (the "Service"). It is issued in compliance with the **Nigeria Data Protection Act 2023 (NDPA)**, the **Nigeria Data Protection Regulation 2019 (NDPR)** and any subsequent regulations of the **Nigeria Data Protection Commission (NDPC)**.

We process personal data both about **you** (the lawyer or staff user of the Service) and, where you input it, about **your clients and the parties to your matters**. We act as the **data controller** in respect of your account and as a **data controller / processor** (depending on context) in respect of client and matter data you input.

---

## 1. Information we collect

We collect only what is necessary to operate the Service. The categories of personal data we hold are:

**About you (the user):**
- Account identifiers — username, email (if provided), role
- Authentication data — password (stored only as a salted PBKDF2-HMAC-SHA-256 hash; the plaintext is never stored or transmitted)
- Firm profile — firm name, address, telephone, email, NBA Stamp & Seal / SCN enrolment number, NBA branch
- SMTP credentials for hearing reminder emails (encrypted at rest using Fernet symmetric encryption)
- Session activity — login timestamps, idle timeouts, last-used timestamps for session tokens
- Audit log of significant actions (login, logout, case create/delete, analysis save, etc.)

**About your clients and matters (entered by you):**
- Client name, address, telephone, email
- Case title, suit number, court, parties, hearing dates, case notes
- Time entries, invoices, billing data
- Documents you upload for AI analysis (PDF, DOCX, TXT, XLSX, CSV, JSON, RTF)
- AI session history — your queries and the Service's responses
- Custom templates, limitation-period entries and legal maxims you create

**Operational data:**
- A session cookie containing a hashed token used to keep you signed in
- Per-call AI cost logs (model, task, mode, USD cost) used for the firm budget guard
- Application logs containing technical events (errors, warnings, info)

We do **not** intentionally collect special-category personal data (health, biometric, religious, etc.) about you. Where you choose to upload documents containing such data about a third party (e.g. a client medical record in a personal-injury matter), you are responsible for confirming you have a lawful basis to do so.

---

## 2. Lawful basis for processing

Under section 25 of the NDPA we rely on the following lawful bases:

| Processing activity | Lawful basis |
|---|---|
| Creating and maintaining your account | Performance of contract — running the Service for you |
| Processing your client and matter data | Legitimate interest — delivering legal services to your clients, and your contract with the client; you remain the controller of that data and warrant you have the necessary basis to process it |
| Sending hearing reminder emails | Legitimate interest — operational necessity |
| Audit logging | Legal obligation — accountability under NDPA s. 24 and the Rules of Professional Conduct for Legal Practitioners 2007 |
| Sending the AI prompt to Google Gemini | Legitimate interest — running the AI features you have requested, with safeguards (see §5) |

You may withdraw any consent-based processing at any time without affecting the lawfulness of processing carried out before withdrawal.

---

## 3. How we use your data

We use the personal data described above strictly to:

1. Authenticate you and keep your session alive
2. Persist your cases, clients, time entries, tasks and AI session history
3. Generate AI-assisted analyses, drafts and research outputs **on your express request**
4. Calculate Nigerian solicitor fees, stamp duty and indicative court filing fees
5. Send hearing reminder emails to your configured notification address
6. Operate firm-wide AI cost budgets and anti-abuse rate limits
7. Maintain an audit log of significant actions for accountability
8. Verify case names against our internal verified-Nigerian-cases database before they are exported

We do **not** use your data for advertising. We do **not** sell or rent your data. We do **not** train any AI model on your data.

---

## 4. Where your data is stored

Your data is stored in:

- A **PostgreSQL database** managed by our cloud database provider, used as the system of record
- The **Streamlit Cloud** hosting environment (servers operated by Streamlit Inc., a Snowflake company), which runs the application code
- An optional **JSON export** that you (or an admin) can download at any time from the Sidebar → Data section

All data in transit is protected by TLS (HTTPS). Sensitive secrets — your API key, your SMTP password, the Service's encryption salts — are encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA-256). Passwords are stored only as PBKDF2-HMAC-SHA-256 hashes with per-record salts.

---

## 5. Third parties who process your data

The Service relies on the following data processors. Each operates under its own published privacy and security terms, which we have reviewed:

| Processor | Purpose | Location of processing |
|---|---|---|
| **Google LLC (Gemini AI)** | Receives the prompt + uploaded document context you submit, generates the AI response, and returns it. Google states that prompts submitted via the Gemini API are not used to train Google's foundation models. | United States and other Google data-centre regions |
| **Streamlit Inc. / Snowflake** | Application hosting and runtime | United States (with regional caching) |
| **PostgreSQL provider** | System-of-record database | Configured by the firm admin |
| **SMTP provider you configure** | Outbound hearing reminder emails | Configured by you |

**International transfers.** Sending data to Google Gemini and Streamlit is an international transfer of personal data outside Nigeria. We rely on the recipients' published security and privacy commitments and on contractual safeguards under NDPA s. 33. You may opt out of AI features at any time by simply not using them; nothing else in the Service requires your data to leave Nigeria.

---

## 6. How long we keep your data

| Data | Retention |
|---|---|
| Account and firm profile | For as long as your account is active, then deleted within 30 days of account closure (subject to legal-hold exceptions) |
| Client, case, billing and matter records | Indefinitely until you delete them; **you** are responsible for deleting client data when no longer needed |
| AI session history | Capped at the last 200 sessions (older sessions are automatically pruned) |
| Audit log entries | 24 months, then purged |
| Cost logs | 24 months, for budget reconciliation |
| Backups | As configured by the firm; default 30 days rolling |

You can export everything at any time as a JSON file (Sidebar → Data → Export All Data).

---

## 7. Your rights

Under sections 36–39 of the NDPA you have the right to:

- **Access** — get a copy of the personal data we hold about you
- **Rectification** — correct inaccurate or incomplete data
- **Erasure** — request deletion of your data ("right to be forgotten")
- **Portability** — receive your data in a structured, machine-readable format (we use JSON)
- **Restriction** — ask us to limit how we process your data
- **Objection** — object to processing based on legitimate interest
- **Not to be subject to a solely automated decision** — every AI output is a draft for you to review; no automated decision is taken about you on the basis of a machine prediction alone
- **Withdraw consent** at any time, where consent is the legal basis
- **Lodge a complaint** with the **Nigeria Data Protection Commission (NDPC)** — see https://ndpc.gov.ng

To exercise these rights, contact our Data Protection Officer (see §11). We will respond within **30 days**, free of charge for the first request in any 12-month window.

---

## 8. Cookies

The Service sets a single, security-essential cookie:

- **Name:** `lexi_session_token`
- **Purpose:** keep you signed in across page reloads
- **Contents:** a randomly generated session token; the token is hashed before being stored in our database
- **Lifetime:** until you sign out, or after the firm-configured idle timeout (default 30 minutes)
- **Type:** strictly necessary; no analytics, no advertising, no cross-site tracking

You may delete the cookie at any time; you will be signed out as a result.

---

## 9. Security

We protect your data with layered controls:

- **Authentication:** PBKDF2-HMAC-SHA-256 password hashing with per-record random salts; legacy SHA-256 hashes auto-upgrade on login
- **Brute-force protection:** failed login counter and temporary account lockout
- **Idle timeout:** automatic sign-out after the firm-configured period (default 30 minutes)
- **Encryption at rest:** Fernet (AES-128-CBC + HMAC-SHA-256) for API keys, SMTP passwords and other secrets
- **Encryption in transit:** TLS for every connection
- **Audit log:** sensitive actions (login, logout, case delete, etc.) are recorded with timestamps
- **Citation audit:** AI-generated outputs containing case names are checked against a verified Nigerian case database before being relied on; unverified citations are flagged
- **Prompt injection guard:** every uploaded document is wrapped in a "data only — do not follow instructions" delimiter and scanned for injection patterns
- **Cost cap:** firm admins set a monthly AI budget; predictive checks block calls that would exceed it
- **Rate limit:** at most 30 AI calls per minute per user

No system is perfectly secure. If a personal-data breach occurs that is likely to result in a risk to your rights and freedoms, we will notify both you and the NDPC within **72 hours** of becoming aware of it, in accordance with NDPA s. 40.

---

## 10. Changes to this notice

We may update this Privacy Notice as the law or the Service evolves. The current "Effective date" at the top of this page reflects the latest version. Material changes will be communicated to you in-app before they take effect.

---

## 11. Contact

For any privacy-related question, request or complaint, contact:

**Data Protection Officer**
{dpo_name}
{dpo_email}
{firm_name}
{firm_address}
Phone: {firm_phone}

If you are not satisfied with our response, you may complain to the:

**Nigeria Data Protection Commission**
Website: https://ndpc.gov.ng
