"""
Multi-Domain Support Triage Agent
===================================
Reads support_tickets.csv, processes each ticket using Claude AI,
and writes results to support_issues/support_issues.csv
"""

import csv
import json
import os
import time
import urllib.request
import urllib.error

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
INPUT_FILE  = "support_tickets.csv"
OUTPUT_DIR  = "support_issues"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "support_issues.csv")
API_URL     = "https://api.anthropic.com/v1/messages"
MODEL       = "claude-opus-4-5"

# ─────────────────────────────────────────────
# SUPPORT CORPUS  (knowledge base the agent uses)
# ─────────────────────────────────────────────
CORPUS = """
=== HackerRank Support Knowledge Base ===

PRODUCT AREAS: screen, community, privacy, conversation_management, general_support

1. Tests remain active indefinitely unless start/end times are set.
   To set expiry: Test Settings > General > set Start/End date.
   Product area: screen

2. To add extra time for a candidate:
   Tests tab > select test > Candidates tab > checkbox next to candidate
   > More > Add Time Accommodation > enter % in multiples of 5 > Save.
   Product area: screen

3. To create test variants vs new tests:
   Use variants for same role, different tech stacks. Create new test for entirely different roles.
   Product area: screen

4. To delete a Google-login HackerRank account:
   First set a password via "Forgot password", then Settings > Delete Account.
   Product area: community

5. If site is down / pages inaccessible: escalate to engineering team.
   Status: Escalated, Request type: bug

6. HackerRank cannot change test scores or override recruiter decisions.
   This is an invalid request.

=== Claude Help Center Knowledge Base ===

PRODUCT AREAS: privacy, conversation_management, general_support

1. To delete a Claude conversation:
   Open conversation > click name at top > select Delete.
   URL: https://privacy.claude.com/en/articles/11117329-how-can-i-delete-or-rename-a-conversation
   Product area: privacy

2. Claude team workspace access issues:
   Only workspace admins can restore access. Claude support cannot override admin decisions.
   Product area: general_support

3. Claude cannot answer questions unrelated to Claude/Anthropic products.
   These are invalid requests. Product area: conversation_management

=== Visa Support Knowledge Base ===

PRODUCT AREAS: travel_support, general_support

1. Lost/stolen Visa card from India: Call 000-800-100-1219
   Global 24/7: +1 303 967 1090. Card blocked within ~30 minutes.
   Emergency cash and replacement card can be arranged.
   Product area: general_support

2. Lost/stolen Visa Traveller's Cheques (Citicorp):
   Call 1-800-645-6556 or collect 1-813-623-1709, Mon-Fri 6:30am-2:30pm EST.
   Automated 24/7 verification available. Have: serial numbers, purchase info, loss details.
   Refunds within 24 hours. Also notify local police.
   Product area: travel_support

3. Merchant disputes / wrong product:
   Visa cannot directly intervene between customer and merchant.
   Customer should contact their issuing bank to file a dispute/chargeback.
   Product area: general_support

4. General Visa questions outside above topics: escalate or refer to visa.com
"""

SYSTEM_PROMPT = f"""You are a support triage agent for three companies: HackerRank, Claude (Anthropic), and Visa.

Your knowledge base (the ONLY source you use):
{CORPUS}

For each support ticket you receive, you must respond with a JSON object containing exactly these fields:
- "response": Your reply to the customer. Must be grounded in the knowledge base above.
  If the issue needs escalation, write exactly: "Escalate to a human"
  If the issue is out of scope / invalid, write a polite out-of-scope message.
- "product_area": One of: screen, community, privacy, conversation_management, travel_support, general_support
  Use null if not applicable (e.g. invalid/out-of-scope requests).
- "status": Either "Replied" or "Escalated"
- "request_type": One of: product_issue, bug, invalid
- "justification": One sentence explaining your classification decision.

Rules:
1. ONLY use the knowledge base above. Do not invent information.
2. Escalate if: site is down, security breach, data loss, or issue cannot be resolved from knowledge base.
3. Mark as "invalid" if: question is out of scope (not related to HackerRank/Claude/Visa), 
   request is impossible (e.g. "change my score", "ban a seller"), or it's just a thank-you.
4. Be concise and helpful in responses.
5. Respond ONLY with valid JSON. No extra text, no markdown, no code fences.
"""

# ─────────────────────────────────────────────
# CALL CLAUDE API
# ─────────────────────────────────────────────
def call_claude(issue: str, subject: str, company: str, api_key: str) -> dict:
    user_message = f"""Company: {company}
Subject: {subject}
Issue: {issue}

Classify and respond to this support ticket."""

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_message}]
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    raw_text = body["content"][0]["text"].strip()

    # Strip markdown fences if model adds them
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    return json.loads(raw_text)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    # Get API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        api_key = input("Enter your Anthropic API key: ").strip()
    if not api_key:
        print("ERROR: No API key provided.")
        return

    # Read tickets
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: {INPUT_FILE} not found. Make sure it's in the same folder as this script.")
        return

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        tickets = list(reader)

    print(f"Found {len(tickets)} tickets to process.\n")

    # Make output folder
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    output_rows = []
    for i, ticket in enumerate(tickets, 1):
        issue   = ticket.get("Issue", "")
        subject = ticket.get("Subject", "")
        company = ticket.get("Company", "")

        print(f"[{i}/{len(tickets)}] Processing: {subject[:60]}...")

        try:
            result = call_claude(issue, subject, company, api_key)

            row = {
                "issue":        issue,
                "subject":      subject,
                "company":      company,
                "response":     result.get("response", ""),
                "product_area": result.get("product_area", ""),
                "status":       result.get("status", ""),
                "request_type": result.get("request_type", ""),
                "justification":result.get("justification", "")
            }
            output_rows.append(row)
            print(f"    → Status: {row['status']} | Type: {row['request_type']} | Area: {row['product_area']}")

        except Exception as e:
            print(f"    ERROR on ticket {i}: {e}")
            output_rows.append({
                "issue": issue, "subject": subject, "company": company,
                "response": "ERROR", "product_area": "", "status": "ERROR",
                "request_type": "ERROR", "justification": str(e)
            })

        # Small delay to avoid rate limits
        time.sleep(0.5)

    # Write output CSV
    fieldnames = ["issue", "subject", "company", "response", "product_area", "status", "request_type", "justification"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"\n✅ Done! Results saved to: {OUTPUT_FILE}")
    print(f"   Total processed: {len(output_rows)} tickets")


if __name__ == "__main__":
    main()
