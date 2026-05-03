# Multi-Domain Support Triage Agent

A terminal-based AI support triage agent that handles support tickets across three ecosystems:
- **HackerRank** (https://support.hackerrank.com/)
- **Claude / Anthropic** (https://support.claude.ai/)
- **Visa** (https://www.visa.co.in/support.html)

---

## Architecture

```
support_tickets.csv
        │
        ▼
┌─────────────────────┐
│   Input Parser      │  Reads and cleans each ticket (issue, subject, company)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Support Corpus    │  Static knowledge base built from the 3 official support portals.
│   (in agent.py)     │  The agent is ONLY allowed to use this corpus — no outside knowledge.
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Claude API        │  claude-opus-4-5 reasons over the ticket + corpus and returns
│   (Reasoning Layer) │  a structured JSON response with all 5 required output fields.
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Validator         │  Enforces allowed values for status and request_type.
│                     │  Auto-corrects any invalid API output before writing.
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Output Writer     │  Writes support_issues/support_issues.csv and log.txt
└─────────────────────┘
```

---

## Design Decisions

### Why a static corpus instead of RAG?
The support portals are small and well-structured. A static corpus embedded directly
in the system prompt is simpler, faster, fully deterministic, and easier to audit than
a vector database. RAG would add complexity without meaningful benefit at this scale.

### Why Claude API for reasoning?
The classification task requires nuanced judgment — detecting prompt injections,
handling multi-language tickets, inferring company from vague issues, and deciding
when to escalate vs reply. A large language model handles these edge cases far better
than classical ML or rule-based routing.

### Why structured JSON output?
Structured output ensures the 5 required columns are always present and correctly
typed. The validator layer enforces allowed values, making the pipeline robust even
if the model occasionally produces unexpected output.

### Escalation logic
The agent escalates when:
- Platform is completely down (bug, engineering needed)
- Security vulnerability or bug bounty report
- Identity theft or financial fraud
- Billing refund required
- No safe answer exists in the corpus
- Issue is too vague to resolve remotely

### Safety checks
The agent detects and refuses:
- Prompt injection attempts (e.g. "ignore your rules and...")
- Requests for harmful code or system access
- Requests to reveal internal instructions
- Malicious instructions hidden in foreign-language text

---

## How to Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your API key
```bash
# Windows CMD
set ANTHROPIC_API_KEY=sk-ant-your-key-here

# Or just run the script — it will prompt you
```

### 3. Run the agent
```bash
python agent.py
```

### 4. Output
Results are saved to:
```
support_issues/
    support_issues.csv   ← predictions (submit this)
    log.txt              ← run log (submit this)
```

---

## Input Schema
| Field | Description |
|---|---|
| `issue` | Main ticket body |
| `subject` | Ticket subject (may be blank or noisy) |
| `company` | HackerRank, Claude, Visa, or None |

## Output Schema
| Field | Allowed Values |
|---|---|
| `status` | `replied`, `escalated` |
| `product_area` | `screen`, `community`, `privacy`, `conversation_management`, `travel_support`, `general_support`, `fraud_support`, `dispute_support`, `billing`, `security` |
| `response` | User-facing reply grounded in corpus |
| `justification` | One-sentence explanation of decision |
| `request_type` | `product_issue`, `feature_request`, `bug`, `invalid` |

---

## Files
| File | Description |
|---|---|
| `agent.py` | Main triage agent |
| `makelog.py` | Utility to regenerate log.txt from existing CSV |
| `support_tickets.csv` | Input tickets (29 real tickets) |
| `sample_support_tickets.csv` | Sample tickets with expected outputs |
| `requirements.txt` | Python dependencies |
| `support_issues/support_issues.csv` | Agent predictions |
| `support_issues/log.txt` | Run log |

---

## Known Limitations & Failure Modes
- **Vague tickets**: Tickets with no useful content (e.g. "it's not working") are hard
  to classify accurately. The agent asks for more info or escalates.
- **Corpus gaps**: If a topic is not covered in the corpus, the agent escalates rather
  than hallucinating an answer.
- **Multi-language**: The agent handles French/Spanish tickets but may miss nuance in
  rare languages.
- **Prompt injection**: The agent detects most injection attempts but sophisticated
  multi-step injections could potentially bypass detection.

---

## Chat Transcript Logging
The agent writes a `log.txt` file after every run containing each ticket's
classification decision and justification, traceable back to the corpus.
