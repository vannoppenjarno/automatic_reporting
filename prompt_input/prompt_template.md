Generate a summary report in JSON format based on pre-clustered interaction logs.

Important: 
- Respond ONLY with valid JSON. No explanations, no markdown, no comments.
- If the content is too long, summarize fields but keep valid JSON structure.
- Strictly follow the format instructions provided below.

FORMAT INSTRUCTIONS:
$format_instructions

General instructions:
- Do NOT add any placeholder text like "Continue generating..." or "etc.".
- Fill all fields completely based on the provided logs; do not leave instructions or notes in the JSON.
- All arrays (topics, executive_summary) must contain actual objects only; do not insert strings or commentary.
- Generate the executive_summary array automatically based on the statuses of all topics.
- Do not skip or truncate this section even if there are many topics.

Company Context:
$context

Instructions for topics:
- Generate a broad, descriptive topic label for each cluster, based on all questions in that cluster.
- Suggest recommendations taking into account the company context above.
- Try to have an alternative to the recommended action, considering cost efficiency, potential impact, and alignment with strategic objectives.
- Recommendations should reflect insights from low scoring clusters, knowledge gaps, and frequency trends.
- Be sure to take into account the pre-clustering! Pre-clustered logs: $logs_text

Instructions for executive_summary:
- Summarize key objectives and key decisions needed for management at a glance.

Include an overall_takeaway summarizing the most important insights across all topics.

Now generate the JSON output exactly as specified. Do not add extra text outside the JSON. keep it concise, avoid redundancy, and do not invent categories.