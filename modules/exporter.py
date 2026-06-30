"""
modules/exporter.py
-------------------
Handles exporting the final report to Markdown or CSV formats.
"""

import io
import csv


def export_markdown(report: dict, stats: dict) -> str:
    """
    Format the complete AI analysis report and dataset stats into a Markdown string.

    Args:
        report: The analysis dictionary containing themes, questions, root_causes_and_needs.
        stats:  A dictionary containing dataset summary statistics (total, used, mode).

    Returns:
        A Markdown string formatted for readability.
    """
    md = []

    # Title & Metadata
    md.append("# Spotify Review Discovery Engine — Analysis Report")
    md.append(f"**Analysis Mode:** {stats.get('mode', 'Unknown')}")
    md.append(f"**Total Reviews Analyzed:** {stats.get('total', 0)}")
    md.append(f"**Discovery-Relevant Reviews Used:** {stats.get('used', 0)}")
    md.append("---")
    md.append("")

    # Section 1: Themes
    md.append("## 🎯 Discovery Theme Analysis")
    themes = report.get("themes", [])
    if themes:
        for t in themes:
            md.append(f"### {t.get('theme', 'Theme')} `[{t.get('frequency', 'Low')}]`")
            md.append(f"**Description:** {t.get('description', '')}")
            md.append(f"> *Example:* \"{t.get('example', '')}\"")
            md.append("")
    else:
        md.append("No themes identified.")
        md.append("")

    # Section 2: Six Questions
    md.append("## ❓ Research Questions & Answers")
    questions = report.get("questions", {})
    if questions and "error" not in questions:
        q_labels = {
            "q1": "1. Why do users struggle to discover new music?",
            "q2": "2. What are the most common recommendation frustrations?",
            "q3": "3. What listening behaviors are users trying to achieve?",
            "q4": "4. What causes users to repeatedly listen to the same content?",
            "q5": "5. Which user segments experience different challenges?",
            "q6": "6. What unmet needs emerge consistently from reviews?",
        }
        for q_key, q_label in q_labels.items():
            md.append(f"### {q_label}")
            val = questions.get(q_key, "Not answered.")
            if isinstance(val, dict) and "explanation" in val:
                md.append(f"{val.get('explanation', '')}")
                md.append("")
                
                insights = val.get("key_insights", [])
                if insights:
                    md.append("**Key Insights:**")
                    for insight in insights:
                        md.append(f"- {insight}")
                    md.append("")
                
                evidences = val.get("evidence", [])
                if evidences:
                    md.append("**Evidence from Reviews:**")
                    for ev in evidences:
                        md.append(f"> *Evidence:* \"{ev}\"")
                    md.append("")
            elif q_key == "q4" and isinstance(val, dict):
                md.append(f"**Unwanted Repetition (Algorithm Failure):** {val.get('unwanted_repetition', 'Not answered.')}")
                md.append(f"**Intentional Repetition (User Choice):** {val.get('intentional_repetition', 'Not answered.')}")
                md.append("")
            else:
                md.append(str(val))
                md.append("")
    else:
        md.append(f"Research questions not answered: {questions.get('error', 'No data')}")
        md.append("")

    # Section 3: User Segments
    md.append("## 👤 Use-Case Based User Segments")
    segments = questions.get("segments", [])
    if segments:
        for seg in segments:
            md.append(f"### 👤 {seg.get('name', 'Segment')} `[Repetition: {seg.get('repetition_type', 'N/A')}]`")
            md.append(f"**What they do:** {seg.get('what_they_do', '')}")
            md.append(f"**Discovery Blocker:** {seg.get('discovery_blocker', '')}")
            md.append(f"> *Evidence Quote:* \"{seg.get('evidence', '')}\"")
            md.append("")
    else:
        md.append("No segments identified.")
        md.append("")

    # Section 4: Root Causes
    md.append("## 🔍 Root Cause Synthesis")
    root_data = report.get("root_causes_and_needs", {})
    if root_data and "error" not in root_data:
        md.append("### Primary Root Causes of Discovery Failure")
        for cause in root_data.get("root_causes", []):
            md.append(f"- {cause}")
        md.append("")

        md.append("### Causes of Unwanted Repetition")
        for cause in root_data.get("unwanted_repetition_causes", []):
            md.append(f"- {cause}")
        md.append("")

        note = root_data.get("intentional_repetition_note", "")
        if note:
            md.append(f"**On Intentional Repetition:** {note}")
            md.append("")
    else:
        md.append(f"Root cause data not available: {root_data.get('error', 'No data')}")
        md.append("")

    # Section 5: Unmet Needs
    md.append("## 💡 Unmet User Needs")
    needs = root_data.get("unmet_needs", [])
    if needs:
        for n in needs:
            md.append(f"### 💡 {n.get('need', 'Need')}")
            md.append(f"**Segment:** {n.get('segment', 'General')}")
            md.append(f"**Evidence:** {n.get('evidence', '')}")
            md.append("")
    else:
        md.append("No unmet needs identified.")
        md.append("")

    # Section 6: Key Insights & Takeaways
    md.append("## 🔑 Key Insights & Actionable Takeaways")
    insights = root_data.get("key_insights", [])
    if insights:
        for ki in insights:
            md.append(f"### 🔑 {ki.get('insight', 'Insight')}")
            md.append(f"**Impact:** {ki.get('impact', '')}")
            md.append(f"**Actionable Takeaway:** {ki.get('actionable_takeaway', '')}")
            md.append("")
    else:
        md.append("No key insights identified.")
        md.append("")

    return "\n".join(md)


def export_csv(report: dict) -> str:
    """
    Flatten the report dictionary into a CSV string.

    CSV Headers: Section, Item, Detail, Evidence / Extra Info

    Args:
        report: The analysis dictionary.

    Returns:
        CSV formatted string.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Section", "Item", "Detail", "Evidence / Extra Info"])

    # 1. Themes
    for t in report.get("themes", []):
        writer.writerow([
            "Themes",
            t.get("theme", ""),
            t.get("description", ""),
            f"Frequency: {t.get('frequency', '')} | Example: {t.get('example', '')}"
        ])

    # 2. Questions
    questions = report.get("questions", {})
    if "error" not in questions:
        q_labels = {
            "q1": "Why do users struggle to discover new music?",
            "q2": "What are the most common recommendation frustrations?",
            "q3": "What listening behaviors are users trying to achieve?",
            "q4": "What causes users to repeatedly listen to the same content?",
            "q5": "Which user segments experience different challenges?",
            "q6": "What unmet needs emerge consistently from reviews?",
        }
        for q_key, label in q_labels.items():
            val = questions.get(q_key, "")
            if isinstance(val, dict) and "explanation" in val:
                detail = val.get("explanation", "")
                evidence_info = "Insights: " + " | ".join(val.get("key_insights", []))
                if val.get("evidence", []):
                    evidence_info += " || Evidence: " + " | ".join(val.get("evidence", []))
                writer.writerow([
                    "Six Questions",
                    label,
                    detail,
                    evidence_info
                ])
            elif q_key == "q4" and isinstance(val, dict):
                # Fallback for old q4 dict format
                writer.writerow([
                    "Six Questions",
                    "What causes users to repeatedly listen to the same content? (Unwanted)",
                    val.get("unwanted_repetition", ""),
                    "Algorithm failure"
                ])
                writer.writerow([
                    "Six Questions",
                    "What causes users to repeatedly listen to the same content? (Intentional)",
                    val.get("intentional_repetition", ""),
                    "User deliberate choice"
                ])
            else:
                writer.writerow([
                    "Six Questions",
                    label,
                    str(val),
                    ""
                ])

        # Segments inside questions
        for seg in questions.get("segments", []):
            writer.writerow([
                "Segments",
                seg.get("name", ""),
                f"What they do: {seg.get('what_they_do', '')} | Blocker: {seg.get('discovery_blocker', '')}",
                f"Repetition: {seg.get('repetition_type', '')} | Evidence: {seg.get('evidence', '')}"
            ])

    # 3. Root Causes & Needs
    root_data = report.get("root_causes_and_needs", {})
    if "error" not in root_data:
        for idx, cause in enumerate(root_data.get("root_causes", [])):
            writer.writerow([
                "Root Causes",
                f"Discovery Failure Root Cause {idx+1}",
                cause,
                ""
            ])
        for idx, cause in enumerate(root_data.get("unwanted_repetition_causes", [])):
            writer.writerow([
                "Root Causes",
                f"Unwanted Repetition Cause {idx+1}",
                cause,
                ""
            ])

        note = root_data.get("intentional_repetition_note", "")
        if note:
            writer.writerow([
                "Root Causes",
                "Intentional Repetition Note",
                note,
                "Deliberate user choice context"
            ])

        # Unmet Needs
        for n in root_data.get("unmet_needs", []):
            writer.writerow([
                "Unmet Needs",
                n.get("need", ""),
                f"Segment: {n.get('segment', 'General')}",
                n.get("evidence", "")
            ])

        # Key Insights
        for ki in root_data.get("key_insights", []):
            writer.writerow([
                "Key Insights",
                ki.get("insight", ""),
                f"Impact: {ki.get('impact', '')}",
                f"Actionable Takeaway: {ki.get('actionable_takeaway', '')}"
            ])

    return output.getvalue()
