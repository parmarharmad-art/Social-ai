"""ChatGPT-ready Instagram Agent Skills for SocialPilot AI.

Adapted as workflow prompts for the SocialPilot MCP server. These tools generate
drafts and recommendations only; they do not publish, comment, or send DMs.
"""
from typing import Awaitable, Callable

SkillGenerator = Callable[..., Awaitable[str]]

SKILLS: dict[str, dict[str, str]] = {
    "ig-reel": {
        "title": "Reel Script",
        "description": "Create a short Reel with scored hook options, script, on-screen text, beat sheet, and CTA.",
        "instructions": """Create one practical Instagram Reel package. Give 3 distinct hook options and score each 1-10 for specificity, clear audience, stakes, and curiosity; explain scores as editorial judgment, not measured performance. Choose the strongest hook. Include a 20-35 second spoken script, time-coded beats, on-screen text, shot/edit suggestions, caption, one CTA, and up to 5 relevant hashtags. Make it sound natural when spoken. Avoid generic greetings, fake statistics, invented personal stories, and guaranteed virality.""",
    },
    "ig-viral": {
        "title": "Reel Research & Swipe Analysis",
        "description": "Analyze user-provided Reel examples and identify reusable creative patterns without claiming live research.",
        "instructions": """Analyze only the examples, URLs, transcripts, or metrics supplied in the brief. Do not claim you browsed Instagram or verified live view counts. If no examples are supplied, provide a research worksheet and explain what to collect from 5-10 public examples manually. When data is present, compare each post to its own account baseline only if that baseline is supplied; otherwise state the limitation. Extract hook, format, pacing, audience promise, and ethical adaptation ideas. Never copy another creator's wording verbatim or promise virality.""",
    },
    "ig-caption": {
        "title": "Caption Writer",
        "description": "Write a searchable caption with a strong opening, readable body, one CTA, and a feed preview.",
        "instructions": """Write an Instagram caption. Show the opening 125 characters separately as a practical feed-preview estimate, then the full caption, one clear CTA, and up to 5 relevant hashtags. Include supplied search keywords naturally. Keep claims grounded in the brief; use placeholders for unknown figures. Avoid hashtag walls, engagement bait, repetitive phrases, and generic AI wording.""",
    },
    "ig-carousel": {
        "title": "Carousel Builder",
        "description": "Turn a topic into a practical swipeable carousel with slide copy and design guidance.",
        "instructions": """Create an Instagram carousel with a clear cover, 5-8 concise slides, a logical teaching sequence, a practical example, a summary, and one CTA. For each slide provide headline, body copy, and visual/layout direction. Make it readable on a 1080x1350 portrait canvas, with short text and strong contrast. Include a matching caption and up to 5 hashtags. Do not claim to create actual image files unless a separate image-generation action is requested.""",
    },
    "ig-story": {
        "title": "Story Sequence",
        "description": "Create a short sequence of Stories with interactive sticker suggestions and an optional DM funnel.",
        "instructions": """Create a 3-7 frame Instagram Story sequence. For each frame provide on-screen copy, visual direction, and the purpose of the frame. Suggest an appropriate poll, question, quiz, or link sticker only when useful. If a DM keyword is proposed, clearly label it as a draft flow that needs human setup and approval. Do not send messages or claim stickers were added.""",
    },
    "ig-profile": {
        "title": "Profile Audit",
        "description": "Review supplied Instagram profile details and prioritize bio, positioning, and conversion improvements.",
        "instructions": """Audit only the profile name, bio, category, link, audience, and examples supplied by the user. Score clarity, audience fit, value proposition, credibility, discoverability, and CTA out of 100, explaining that this is an editorial rubric, not Instagram's official score. If information is missing, mark it unknown rather than inventing it. Provide a revised name field, bio within Instagram's current UI limits if known, profile CTA, and prioritized fixes.""",
    },
    "ig-plan": {
        "title": "Weekly Content Plan",
        "description": "Plan a week of varied posts with formats, goals, production notes, and suggested posting windows.",
        "instructions": """Build a 7-day Instagram content plan tailored to the supplied audience and goal. Include topic, format, opening hook, audience value, CTA, production effort, and suggested posting window. Treat timing as a test hypothesis, not a guaranteed best time. Rotate formats and content pillars; avoid repeating the same idea. Add a lightweight review checklist and do not schedule or publish anything.""",
    },
    "ig-human": {
        "title": "Humanize Draft",
        "description": "Rewrite supplied AI-sounding copy to be clearer, more specific, and natural without inventing facts.",
        "instructions": """Rewrite the supplied draft into natural, concise, spoken-friendly English. Remove filler, clichés, repetitive sentence patterns, unnecessary em dashes, overblown claims, and generic calls to action. Preserve the author's meaning and factual details. Do not invent personal experiences, results, metrics, or endorsements. Return the revised draft plus a short list of meaningful edits; do not claim it is undetectable by AI detectors.""",
    },
    "ig-comment": {
        "title": "Thoughtful Comment Drafts",
        "description": "Draft relevant comments for supplied public posts; does not post comments automatically.",
        "instructions": """Using only the post caption or context supplied, draft 3 specific, useful comment options in distinct tones (thoughtful question, practical addition, respectful perspective). Avoid generic praise, spam, repetitive emojis, promotional links, or pretending to have watched content not supplied. Keep each comment relevant and human. These are drafts only and must be manually reviewed and posted by the user.""",
    },
    "ig-reply": {
        "title": "Comment Reply Assistant",
        "description": "Classify supplied comments and draft prioritized replies for a creator's own post.",
        "instructions": """Classify each supplied comment as question, potential lead, substantive discussion, support, criticism, or noise. Draft a concise and respectful reply, prioritizing genuine questions and leads. Do not reveal private information, argue aggressively, promise unsupported outcomes, or reply to every comment with the same template. Flag abuse, sensitive issues, or uncertain facts for human review. Do not send replies.""",
    },
    "ig-dm": {
        "title": "DM Funnel Drafts",
        "description": "Draft opt-in keyword delivery and follow-up messages; does not send DMs.",
        "instructions": """Design a consent-based Instagram DM draft flow for the offer and audience supplied. Include the initial response to an explicit keyword/comment opt-in, resource delivery text, one helpful follow-up, and a polite close. Keep messages transparent, relevant, and non-spammy; make it easy to decline further messages. Clearly separate copy drafts from any platform configuration. Never initiate or send DMs and do not recommend unsolicited bulk messaging.""",
    },
    "ig-repurpose": {
        "title": "Content Repurposing",
        "description": "Turn one supplied long-form asset into distinct short-form posts that stand alone.",
        "instructions": """Repurpose the supplied video transcript, podcast, newsletter, or article into a week of distinct Instagram content. Provide 3 Reel concepts with different angles, 1 carousel outline, and 3 Story ideas. Every item must stand alone with its own hook, takeaway, and CTA; do not simply slice the source into disconnected fragments. Preserve the source's facts and mark anything requiring verification. Credit or attribution should be included where appropriate.""",
    },
    "ig-audit": {
        "title": "Content Performance Audit",
        "description": "Audit supplied post metrics and recommend experiments without fabricating analytics.",
        "instructions": """Analyze only the post metrics and context supplied. Summarize what performed relatively well, compare rates only when denominators are available, and distinguish observations from hypotheses. Do not invent reach, saves, watch time, or account baselines. Identify the strongest evidence-backed patterns, weak spots, and 3 prioritized experiments for the next week. Explain small-sample limitations and do not claim causation from correlation.""",
    },
}

async def run_instagram_skill(
    skill_name: str,
    brief: str,
    openai_chat: SkillGenerator,
) -> dict[str, str]:
    """Run one of the 13 named Instagram content workflows through the configured AI provider."""
    key = (skill_name or "").strip().lower()
    skill = SKILLS.get(key)
    if not skill:
        raise ValueError("Unknown skill_name. Choose one of: " + ", ".join(SKILLS))
    clean_brief = " ".join((brief or "").split()).strip()
    if not clean_brief:
        raise ValueError("brief is required. Include the topic, audience, goal, and any source text or metrics.")
    result = await openai_chat(
        [
            {
                "role": "system",
                "content": (
                    "You are the Instagram content and workflow assistant inside SocialPilot AI for "
                    "Kiran Kumar • AI Automation. Write clear professional English for Indian freelancers, "
                    "digital marketers, creators, and small businesses. Be practical, specific, and concise. "
                    "Never fabricate facts, metrics, testimonials, or personal experiences. If evidence is missing, "
                    "state the limitation or use a clear placeholder. This tool only creates drafts and analysis: "
                    "never claim to publish posts, comment, send DMs, browse live Instagram, or change account settings."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"WORKFLOW: {skill['title']} ({key})\n"
                    f"WORKFLOW INSTRUCTIONS:\n{skill['instructions']}\n\n"
                    f"USER BRIEF / SOURCE MATERIAL:\n{clean_brief}"
                ),
            },
        ],
        max_tokens=1800,
    )
    return {
        "ok": True,
        "skill": key,
        "title": skill["title"],
        "draft_only": "true",
        "result": result,
        "note": "Review all output before use. AI text generation may incur provider charges.",
    }
