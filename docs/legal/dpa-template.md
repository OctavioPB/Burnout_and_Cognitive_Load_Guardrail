# Data Processing Agreement (DPA) Template

> **IMPORTANT:** This is a template for informational purposes.
> Before using in production, have this document reviewed and approved by
> qualified legal counsel and your organisation's DPO.
> This template does not constitute legal advice.

---

**DATA PROCESSING AGREEMENT**

This Data Processing Agreement ("Agreement") is entered into between:

**Controller:** [CUSTOMER ORGANISATION NAME], a company registered at [ADDRESS] ("Controller" or "Customer")

**Processor:** [VENDOR ORGANISATION NAME], operating the Burnout & Cognitive Load Guardrail service ("Processor" or "Vendor")

Effective date: [DATE]

---

## 1. Definitions

**"Personal Data"** means any information relating to an identified or identifiable natural person as defined by applicable data protection law (including GDPR Article 4).

**"Processing"** means any operation performed on Personal Data, including collection, storage, analysis, disclosure, or erasure.

**"Service"** means the Burnout & Cognitive Load Guardrail platform, which processes collaboration metadata to produce team-level resilience scores.

**"Collaboration Metadata"** means the specific subset of Personal Data processed by this Service: event timestamps, event durations, event participant counts, message timestamps, and activity counts. Explicitly excluded: message content, document content, video recordings, and audio.

---

## 2. Subject matter and nature of processing

2.1 The Processor processes Collaboration Metadata on behalf of the Controller for the purpose of computing team-level Attention Fragmentation Scores and generating HR intervention recommendations.

2.2 The legal basis for processing is the Controller's legitimate interest in employee wellbeing and workforce management, subject to the consent and transparency obligations set out in Section 5.

2.3 Categories of data subjects: employees and contractors of the Controller who are members of in-scope team units.

---

## 3. Processor obligations

3.1 The Processor shall:
- Process Personal Data only on documented instructions from the Controller.
- Ensure persons authorised to process Personal Data are bound by confidentiality obligations.
- Implement the technical and organisational security measures set out in Annex 1.
- Not engage sub-processors without the Controller's prior written authorisation (see Annex 2 for current sub-processors).
- Assist the Controller in fulfilling data subject rights requests (access, rectification, erasure, portability) within 5 business days of notification.
- Notify the Controller of a Personal Data breach without undue delay and within 72 hours of becoming aware.
- Delete or return all Personal Data on termination of the Agreement.
- Make available all information necessary to demonstrate compliance with this Agreement.

3.2 The Processor shall not sell, rent, or otherwise disclose Personal Data to third parties except as strictly necessary to provide the Service (e.g., integration API calls) or as required by law.

---

## 4. Data retention

| Data type | Retention period | Action on expiry |
|---|---|---|
| Raw collaboration events (Kafka) | 7 days | Automatic deletion via Kafka retention policy |
| Aggregated daily features (Postgres) | 90 days | Automatic deletion via scheduled job |
| Team AFS scores and history | 180 days | Automatic deletion via scheduled job |
| Intervention records | Duration of Agreement + 30 days | Exported to Controller on termination, then deleted |
| Audit log entries | 365 days | Archived to Controller's data lake or deleted on instruction |

---

## 5. Data subject rights and consent

5.1 The Controller is responsible for providing employees with a privacy notice that clearly describes the collection and use of collaboration metadata before any data collection begins.

5.2 The Processor provides a consent activation mechanism. Data collection for any workspace is disabled by default and must be explicitly enabled by the Controller's administrator.

5.3 The Processor will assist the Controller in responding to data subject requests. The Controller remains the primary point of contact for data subjects.

---

## 6. International transfers

6.1 Personal Data shall be processed within the EEA/UK unless the Controller explicitly authorises processing in a third country.

6.2 Any transfer to a third country shall be subject to appropriate safeguards (adequacy decision, Standard Contractual Clauses, or Binding Corporate Rules).

---

## 7. Audit rights

7.1 The Processor shall provide the Controller with all information necessary to demonstrate compliance with this Agreement.

7.2 The Processor shall permit and contribute to audits conducted by the Controller or a mandated auditor, provided:
- 30 days' written notice is given.
- Audits occur no more than once per calendar year.
- The auditor is subject to confidentiality obligations.

---

## 8. Liability

8.1 Each party's liability under this Agreement shall be subject to the liability caps and exclusions set out in the main Services Agreement between the parties.

8.2 The Processor shall indemnify the Controller for any fines, penalties, or damages arising directly from the Processor's breach of this Agreement, up to the liability cap.

---

## 9. Termination

9.1 This Agreement terminates automatically upon termination of the main Services Agreement.

9.2 Within 30 days of termination, the Processor shall: (a) provide the Controller with an export of all intervention records and audit logs; (b) permanently delete all Personal Data from its systems; (c) provide written certification of deletion.

---

## Annex 1 — Technical and organisational measures

| Control | Measure |
|---|---|
| Access control | Role-based access (HR Admin, Team Manager, Viewer); JWT authentication in production |
| Encryption in transit | TLS 1.2+ on all connections |
| Encryption at rest | AES-256 on all database volumes (AWS RDS) |
| Data minimisation | Only metadata processed; content explicitly excluded at ingestion |
| Audit logging | All data access logged with actor identity and timestamp |
| Intrusion detection | Prometheus alerting on anomalous access patterns |
| Penetration testing | Annual third-party penetration test; findings remediated before production |
| Vulnerability management | Automated dependency scanning (Dependabot + pip-audit) |
| Incident response | Breach notification within 72 hours per GDPR Article 33 |
| Data retention enforcement | Automated TTL jobs for all data categories |

---

## Annex 2 — Sub-processors

| Sub-processor | Location | Purpose |
|---|---|---|
| Amazon Web Services (AWS) | EU-WEST-1 (Ireland) | Cloud infrastructure, RDS, S3, EKS |
| Confluent Cloud | EU | Kafka managed service (or self-hosted on AWS — delete as appropriate) |
| Anthropic | US | ML model API calls for rule interpretation (if enabled) |

Changes to sub-processors will be notified to the Controller with 30 days' notice.

---

*[Controller signature block]*

Name: ___________  Title: ___________  Date: ___________

*[Processor signature block]*

Name: ___________  Title: ___________  Date: ___________
