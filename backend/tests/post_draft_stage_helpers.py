"""One answer for the stages that run after the draft, shared by every scripted gateway.

The analysis pass and the two review passes read the committed text and add sections or
reasons. A test that is about something else answers them plainly from here rather than
repeating the contract, so adding a stage does not mean editing every gateway again.
"""

POST_DRAFT_STAGES = {
    "report_analysis": {
        "sections": [
            {
                "heading": "What this means",
                "text": "The reporting establishes movement and suggests intent.",
                "evidence": ["E1"],
            }
        ],
        "diagram": None,
    },
    "entailment": {"assessments": []},
    "contradiction_analysis": {"disagreements": []},
}
