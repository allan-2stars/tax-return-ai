#!/usr/bin/env bash
# Test the classification endpoint.
#
# Usage:
#   bash scripts/test_classify.sh              # test with current AI_PROVIDER (default: mock)
#   AI_PROVIDER=anthropic bash scripts/test_classify.sh   # test with Anthropic
#   AI_PROVIDER=openai    bash scripts/test_classify.sh   # test with OpenAI
#
# Note: Real providers require ANTHROPIC_API_KEY or OPENAI_API_KEY set
# in docker-compose.yml environment or in backend container's env.
set -euo pipefail

API="${API_URL:-http://localhost:8010}"
PROVIDER="${AI_PROVIDER:-}"

# Get session and document IDs from seeded demo data
echo "→ Fetching session & document IDs..."
IDS=$(docker compose exec backend python -c "
import httpx, json

API = 'http://localhost:8010'

# Get sessions
sessions = httpx.get(f'{API}/api/sessions').json()
if not sessions:
    print('NO_SESSION')
else:
    sid = sessions[0]['id']
    # Get documents
    docs = httpx.get(f'{API}/api/documents?session_id={sid}').json()
    if docs:
        did = docs[0]['id']
        print(f'{sid}|{did}')
    else:
        print(f'{sid}|NO_DOC')
")

IFS='|' read -r SESSION_ID DOCUMENT_ID <<< "$IDS"

if [ "$SESSION_ID" = "NO_SESSION" ] || [ -z "$SESSION_ID" ]; then
    echo "  ✗ No sessions found. Run \`make seed-demo\` first."
    exit 1
fi
echo "  Session:   $SESSION_ID"
echo "  Document:  $DOCUMENT_ID"

if [ "$DOCUMENT_ID" = "NO_DOC" ]; then
    echo "  ✗ No documents in session. The classify endpoint requires a valid document_id."
    exit 1
fi

# Build JSON payload with python to avoid shell escaping hell
echo ""
echo "→ Test 1: Salary (income, auto-classified)"
docker compose exec backend python -c "
import httpx, json
payload = {
    'document_id': '$DOCUMENT_ID',
    'session_id': '$SESSION_ID',
    'extracted_text': 'Salary from employer ABC Corp \$85,000 paid fortnightly'
}
r = httpx.post('http://localhost:8010/api/items/classify', json=payload)
data = r.json()
print(json.dumps(data, indent=2))
if data.get('needs_review') == False and data.get('confidence', 0) >= 0.9:
    print()
    print('  ✓ PASS: salary auto-classified with high confidence')
else:
    print()
    print('  ✗ FAIL: expected needs_review=false, confidence>=0.9')
"

echo ""
echo "→ Test 2: Officeworks (deduction, needs review)"
docker compose exec backend python -c "
import httpx, json
payload = {
    'document_id': '$DOCUMENT_ID',
    'session_id': '$SESSION_ID',
    'extracted_text': 'Officeworks USB hub \$89 and keyboard \$60'
}
r = httpx.post('http://localhost:8010/api/items/classify', json=payload)
data = r.json()
print(json.dumps(data, indent=2))
if data.get('needs_review') == True and data.get('confidence', 1) == 0.70:
    print()
    print('  ✓ PASS: tools_equipment needs review (borderline confidence)')
else:
    print()
    print('  ✗ FAIL: expected needs_review=true, confidence=0.70')
"

echo ""
echo "→ Test 3: Mixed use (triggers review)"
docker compose exec backend python -c "
import httpx, json
payload = {
    'document_id': '$DOCUMENT_ID',
    'session_id': '$SESSION_ID',
    'extracted_text': 'Mixed use laptop for personal and work'
}
r = httpx.post('http://localhost:8010/api/items/classify', json=payload)
data = r.json()
print(json.dumps(data, indent=2))
if data.get('needs_review') == True and 'mixed' in data.get('review_reason', '').lower():
    print()
    print('  ✓ PASS: mixed use detected, flagged for review')
else:
    print()
    print('  ✗ FAIL: expected needs_review=true with mixed use reason')
"

echo ""
echo "→ Test 4: BAS statement (out of scope)"
docker compose exec backend python -c "
import httpx, json
payload = {
    'document_id': '$DOCUMENT_ID',
    'session_id': '$SESSION_ID',
    'extracted_text': 'BAS statement for quarter ending March 2025'
}
r = httpx.post('http://localhost:8010/api/items/classify', json=payload)
data = r.json()
print(json.dumps(data, indent=2))
if data.get('item_type') == 'out_of_scope' and data.get('needs_review') == True:
    print()
    print('  ✓ PASS: BAS flagged as out_of_scope with review')
else:
    print()
    print('  ✗ FAIL: expected item_type=out_of_scope, needs_review=true')
"

echo ""
echo "→ Test 5: Empty text (insufficient evidence)"
docker compose exec backend python -c "
import httpx, json
payload = {
    'document_id': '$DOCUMENT_ID',
    'session_id': '$SESSION_ID',
    'extracted_text': ''
}
r = httpx.post('http://localhost:8010/api/items/classify', json=payload)
data = r.json()
print(json.dumps(data, indent=2))
if data.get('needs_review') == True and 'insufficient' in data.get('review_reason', '').lower():
    print()
    print('  ✓ PASS: empty text → insufficient_evidence, flagged for review')
else:
    print()
    print('  ✗ FAIL: expected needs_review=true with insufficient_evidence')
"

# Summary
echo ""
echo "========================================"
echo "CLASSIFICATION TESTS COMPLETE"
echo "========================================"
if [ -n "$PROVIDER" ]; then
    echo "Provider: $PROVIDER"
else
    echo "Provider: current (default: mock)"
fi
echo "To test with Anthropic:"
echo "  1. Set ANTHROPIC_API_KEY in docker-compose.yml"
echo "  2. Set AI_PROVIDER=anthropic in docker-compose.yml"
echo "  3. make up"
echo "  4. AI_PROVIDER=anthropic bash scripts/test_classify.sh"
echo "========================================"
