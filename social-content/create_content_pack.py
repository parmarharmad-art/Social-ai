"""Skill-orchestrated AI social content pack generator.

Requires OPENAI_API_KEY and an API-enabled OpenAI project. API usage may incur charges.
It uses strategy, content-production, short-form-video and analytics standards to create
a reviewable draft pack; it does not publish anything or claim performance outcomes.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILLS_ROOT = ROOT.parent / ".github" / "skills"
SKILLS = {
    "strategy": "social-media-strategy",
    "production": "social-content-production",
    "video": "short-form-video",
    "analytics": "social-analytics-optimization",
    "community": "community-management",
    "publishing": "social-publishing-automation",
    "engineering": "social-automation-engineering",
}
def read_skill(name):
    p = SKILLS_ROOT / SKILLS[name] / "SKILL.md"
    if not p.exists():
        raise RuntimeError("Required skill file missing: " + str(p))
    return p.read_text(encoding="utf-8")
def call_openai(api_key, model, brief, count, platform, language, brand):
    skill_text = "\n\n".join(read_skill(k) for k in SKILLS)
    schema = {
      "type": "object",
      "properties": {
        "audience_and_goal": {"type":"object","properties":{
          "audience":{"type":"string"},"primary_goal":{"type":"string"},
          "content_pillars":{"type":"array","items":{"type":"string"}},
          "assumptions":{"type":"array","items":{"type":"string"}}},"required":["audience","primary_goal","content_pillars","assumptions"],"additionalProperties":False},
        "items": {"type":"array","minItems":count,"maxItems":count,"items":{
          "type":"object","properties":{
            "topic":{"type":"string"},"hook":{"type":"string"},
            "format":{"type":"string"},"script_or_body":{"type":"string"},
            "caption":{"type":"string"},"cta":{"type":"string"},
            "hashtags":{"type":"array","items":{"type":"string"}},
            "visual_brief":{"type":"string"},"alt_text":{"type":"string"},
            "community_prompt":{"type":"string"},
            "success_metric":{"type":"string"},
            "experiment_hypothesis":{"type":"string"},
            "fact_check_notes":{"type":"array","items":{"type":"string"}}
          },"required":["topic","hook","format","script_or_body","caption","cta","hashtags","visual_brief","alt_text","community_prompt","success_metric","experiment_hypothesis","fact_check_notes"],"additionalProperties":False}}
      },"required":["audience_and_goal","items"],"additionalProperties":False
    }
    system = """You are a senior social-media content team executing these 7 installed skill standards.
Use the skill files as operational requirements, not merely labels. Make channel-specific, useful,
original drafts; do not invent statistics, testimonials, credentials, current trends or client results.
Use three hook candidates internally and return the strongest one. Every video script must include
a spoken opening hook, beat-by-beat sequence, on-screen text, and ending CTA. For non-video formats,
give ready-to-produce copy and structure. Include a clear community prompt, one primary CTA, alt text,
one measurable success metric, and a testable experiment hypothesis. Avoid repeating ideas among items.
Mark assumptions and any claims that need verification. Do not promise virality. No live publishing."""
    user = f"""BRAND: {brand}
PLATFORM: {platform}
LANGUAGE: {language}
NUMBER OF CONTENT ITEMS: {count}
BRIEF / NICHE / TOPIC: {brief}
TODAY: {date.today().isoformat()}
SKILL STANDARDS:
{skill_text}
Return a complete content pack matching the JSON schema. Make each item meaningfully different and suitable for the platform."""
    payload = {"model":model,"messages":[{"role":"system","content":system},{"role":"user","content":user}],
               "response_format":{"type":"json_schema","json_schema":{"name":"social_content_pack","strict":True,"schema":schema}},
               "temperature":0.8}
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:1200]
        raise RuntimeError(f"OpenAI API HTTP {e.code}: {detail}") from e
    except Exception as e:
        raise RuntimeError(f"OpenAI API request failed: {e}") from e
    try:
        result = json.loads(data["choices"][0]["message"]["content"])
    except Exception as e:
        raise RuntimeError("Provider returned no valid JSON content pack") from e
    return result
def validate(pack, count):
    errors=[]
    items=pack.get("items", [])
    if len(items) != count: errors.append(f"Expected {count} items, received {len(items)}")
    hooks=[re.sub(r"[^a-z0-9]+"," ",i.get("hook","").lower()).strip() for i in items]
    if len(hooks) != len(set(hooks)): errors.append("Duplicate hooks detected")
    for n,item in enumerate(items,1):
        for key in ("topic","hook","format","script_or_body","caption","cta","visual_brief","alt_text","success_metric","experiment_hypothesis"):
            if not str(item.get(key,"")).strip(): errors.append(f"Item {n}: missing {key}")
        if len(item.get("caption","")) < 40: errors.append(f"Item {n}: caption too short for review")
        if not item.get("hashtags"): errors.append(f"Item {n}: missing hashtag/keyword suggestions")
    if errors: raise RuntimeError("Quality gate failed:\n- "+"\n- ".join(errors))
def write_markdown(pack, meta, path):
    lines=[f"# Social Content Pack: {meta['brand']}", "", f"- Platform: {meta['platform']}",f"- Language: {meta['language']}",f"- Brief: {meta['brief']}","",
           "> Status: AI-generated DRAFT. Human fact-check and approval required. Nothing has been published.","",
           "## Strategy",f"- Audience: {pack['audience_and_goal']['audience']}",f"- Goal: {pack['audience_and_goal']['primary_goal']}",
           "- Pillars: "+", ".join(pack['audience_and_goal']['content_pillars']),"- Assumptions: "+"; ".join(pack['audience_and_goal']['assumptions']),""]
    for n,item in enumerate(pack["items"],1):
        lines += [f"## {n}. {item['topic']}","",f"**Hook:** {item['hook']}","",f"**Format:** {item['format']}","",
                  "**Script / body**",item["script_or_body"],"","**Caption**",item["caption"],"",
                  f"**CTA:** {item['cta']}","", "**Hashtags / keywords:** "+" ".join(item["hashtags"]), "",
                  "**Visual brief:** "+item["visual_brief"],"","**Alt text:** "+item["alt_text"],"",
                  "**Community prompt:** "+item["community_prompt"],"","**Success metric:** "+item["success_metric"],"",
                  "**Experiment hypothesis:** "+item["experiment_hypothesis"],"","**Fact-check before publishing:** "+"; ".join(item["fact_check_notes"] or ["No explicit claims flagged; still review all facts."]),"","---",""]
    path.write_text("\n".join(lines),encoding="utf-8")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--brief",required=True)
    p.add_argument("--platform",choices=["Instagram","LinkedIn","Facebook","YouTube Shorts","TikTok"],default="Instagram")
    p.add_argument("--count",type=int,default=5)
    p.add_argument("--language",default="English")
    p.add_argument("--brand",default="Kiran Kumar • AI Automation")
    p.add_argument("--model",default=os.environ.get("OPENAI_MODEL","gpt-4.1-mini"))
    p.add_argument("--out",default=str(ROOT/"generated"))
    a=p.parse_args()
    if not 1 <= a.count <= 15: p.error("--count must be between 1 and 15")
    key=os.environ.get("OPENAI_API_KEY","").strip()
    if not key:
        print("ERROR: OPENAI_API_KEY is not configured. No content was generated; add an API key to GitHub Actions Secrets.",file=sys.stderr)
        return 2
    pack=call_openai(key,a.model,a.brief,a.count,a.platform,a.language,a.brand)
    validate(pack,a.count)
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    meta={"brand":a.brand,"platform":a.platform,"language":a.language,"brief":a.brief,"model":a.model,"status":"draft_needs_human_review"}
    (out/"content-pack.json").write_text(json.dumps({"metadata":meta,**pack},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    write_markdown(pack,meta,out/"content-pack.md")
    print(f"PASS: generated and validated {len(pack['items'])} draft items; files saved to {out}. Nothing was published.")
if __name__=="__main__":
    try: main_code=main()
    except RuntimeError as exc:
        print(str(exc),file=sys.stderr); sys.exit(1)
    sys.exit(main_code or 0)
