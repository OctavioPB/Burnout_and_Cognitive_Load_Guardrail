# HR Admin Guide — Team Resilience Dashboard

> **Audience:** HR Administrators with full dashboard access.
> **Last updated:** 2026-05-11

---

## What this dashboard does

The Team Resilience Dashboard gives HR a real-time view of team stress levels across the organisation. It processes collaboration *metadata* only — no message content, no document contents, no video — and aggregates it at the team level so no individual score is ever surfaced.

The core metric is the **Attention Fragmentation Score (AFS)**: a 0–100 index that measures how fragmented a team's focused work time is. Higher is worse.

---

## Resilience zones

| Zone | AFS range | What it means |
|---|---|---|
| 🟢 Green | 0–39 | Healthy — no action needed |
| 🟡 Yellow | 40–69 | Monitor — check trend direction |
| 🔴 Red | 70–100 | Intervene — sustained high fragmentation |

---

## Dashboard Home

### KPI cards (top row)
- **Red Zone Teams** — number of teams currently in Red. Any non-zero value here warrants attention.
- **Avg AFS** — organisation-wide average. A rising trend over multiple days is an early warning.
- **Active Alerts** — alerts that fired in the last 7 days (3+ consecutive Red days for a team).

### Department heatmap
Each tile is a department. The colour matches the zone of the highest-AFS team in that department. Click a tile to filter the team list below.

### Team list
Sorted by AFS descending (highest risk first). Click any row to open the team drill-down.

---

## Team Drill-Down

### AFS trend chart (30 days)
The coloured background bands match the zone thresholds. The line shows daily AFS. A line trending upward through Yellow into Red over 5–10 days is the pattern to watch.

### Feature breakdown
Four contributing factors, each shown as a percentage bar:
- **Calendar Density** — meeting hours as a fraction of working hours
- **After-Hours Index** — activity outside 09:00–18:00
- **Context Switches** — number of cross-tool context changes per day
- **Sprint Health** — story-points delivered vs. committed (inverted: lower delivery = higher stress)

### Interventions panel
Lists all suggested and previously applied interventions for this team.

---

## Responding to a Red Zone alert

1. Open the team drill-down.
2. Read the feature breakdown — identify the dominant stressor (calendar density? after-hours?).
3. Review suggested interventions in the Interventions panel.
4. Choose an action:

| Action | When to use |
|---|---|
| **Accept** | You agree the intervention is appropriate and want to execute it immediately |
| **Write message & Apply** (Async-First Week only) | You want to personalise the Slack message before sending |
| **Dismiss** | The suggestion is not appropriate for this team right now (e.g. already underway) |

5. Accepted interventions execute their integration automatically:
   - *Meeting-Free Friday* → creates a recurring Friday calendar block for the team
   - *Load Redistribution* → opens a Jira epic with a capacity review checklist
   - *Async-First Week* → posts and pins your message to the team's Slack channel

---

## Reading the Efficacy view

After an intervention has been applied, click **View efficacy** on its card.

- The **dashed grey line** shows AFS in the 13 days before the intervention.
- The **solid blue line** shows AFS in the 14 days after.
- The **gold vertical line** marks the intervention date.
- **Avg AFS before / after / change** are shown at the top.

If fewer than 14 post-intervention days have elapsed, the chart shows available data with a notice that the full view is pending.

A **negative change** (green) means the intervention correlated with reduced fragmentation. A positive change (red) means the team's AFS continued rising — consider a follow-up conversation.

---

## Audit log

The Audit Log (top navigation, HR Admin only) records every dashboard read and intervention action: who, what, and when.

Use it to:
- Demonstrate compliance with your organisation's data access policy
- Investigate any concern about unauthorised data access
- Produce evidence for an internal audit

The log is append-only and cannot be edited.

---

## Frequently asked questions

**Q: Can I see individual employee data?**
A: No. All data is aggregated to the team level before entering the dashboard. The system is designed so that individual identification is technically impossible from dashboard data.

**Q: What happens if I dismiss an intervention by mistake?**
A: Dismissed interventions are recorded but do not block you from applying the same intervention later. Return to the team drill-down and the dismissed card will still be visible. Contact your administrator if you need the record corrected.

**Q: How fresh is the data?**
A: AFS scores are updated daily. The trend chart reflects yesterday's score as the most recent data point.

**Q: A team manager says their team is fine but AFS is Red. Who is right?**
A: Both perspectives are valid data. AFS measures metadata signals; the manager has qualitative context. Use this as a conversation starter, not a verdict. The dashboard is a guardrail, not a surveillance tool.

**Q: How do I add a new team?**
A: Team unit configuration is managed by the Platform Engineering team. Raise a request via the standard IT intake process.
