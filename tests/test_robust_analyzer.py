from llm.analyze import robust_extract_sections, generate_markdown_from_sections


def test_robust_extractor_on_truncated_json():
    truncated = '''{ "ringkasan": "The analysis shows A6 wins.", "perbandingan": "Borda vs Copeland.", "kelebihan_kelemahan": "| M | Pros | Cons |\\n|---|---|---|\\n| SAW | Fast | Sensitive |", "rekomendasi": {"alternative": "A6", "based_on_model": "SAW", "reasons": ["High performance"]}, "risiko": "The risk that memory prices rise.'''

    sections = robust_extract_sections(truncated)
    assert "ringkasan" in sections
    assert "perbandingan" in sections
    assert "kelebihan_kelemahan" in sections
    assert "rekomendasi" in sections

    md = generate_markdown_from_sections(sections, "Gemini 4 Hydrogen", [])
    assert "{" not in md.split("\n")[0]  # first line is the title, not raw JSON
    assert "## 1. 📋 Executive Summary" in md
    assert "## 4. 🎯 Final Recommendation" in md


def test_robust_extractor_on_raw_user_snippet():
    raw = '''{ "ringkasan": "The decision analysis for the company shows that alternative A6 (NX-Train 200) is the dominant winner, favoured by 6 of 8 group decision models. These models are Weighted Borda, Group Copeland, Group AHP AIP, Group SAW, Group WP and Group TOPSIS.\\n\\nHowever, two other models, Unweighted Borda and Group Profile Matching, recommend alternative A2 (NX-Game 40). This shows a significant difference of views depending on how the preferences of the decision makers (DMs) are aggregated.\\n\\nNote that in Unweighted Borda there is a tie between A6 and A7 at rank 3, both with a score of 17.0.", "perbandingan": "The ranking differences between models can be explained by how each model works and how it treats individual preferences and DM weights:\\n\\n* Weighted Borda vs. Unweighted Borda: the most striking difference is here.", "kelebihan_kelemahan": "| Model | Strengths on this data | Weaknesses on this data |\\n|---|---|---|\\n| Weighted Borda | Shows consensus | Sensitivity |\\n| Group Copeland | Consistent with the majority of the other weighted models (picks A6), showing A6 (NX-Train'''

    sections = robust_extract_sections(raw)
    assert sections.get("ringkasan").startswith("The decision analysis")
    assert "perbandingan" in sections
    assert "kelebihan_kelemahan" in sections

    md = generate_markdown_from_sections(sections, "OpenRouter Nemotron", [])
    assert not md.strip().startswith("{")
    assert "A6" in md
