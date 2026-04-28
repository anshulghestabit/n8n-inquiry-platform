#!/bin/bash
set -e

COOKIES=/tmp/smoke_cookies.txt
COUNTER=0
PASS=0
FAIL=0

pass() { COUNTER=$((COUNTER+1)); PASS=$((PASS+1)); echo "✅"; }
fail() { COUNTER=$((COUNTER+1)); FAIL=$((FAIL+1)); echo "❌"; }

cleanup() {
    rm -f "$COOKIES"
}
trap cleanup EXIT

echo "=== Smoke Tests ==="

echo -n "L0 FastAPI health: "
STATUS=$(curl -sf http://localhost:8000/health 2>/dev/null | grep -o '"status":"ok"' || true)
if [ -n "$STATUS" ]; then pass; else fail; fi

echo -n "L0 n8n API: "
N8N_DATA=$(curl -sf -H "X-N8N-API-KEY: ${N8N_API_KEY:-test}" http://localhost:5678/api/v1/workflows 2>/dev/null | grep -o '"data"' || true)
if [ -n "$N8N_DATA" ]; then pass; else fail; fi

echo -n "L5 Auth register: "
REG=$(curl -sf -X POST http://localhost:8000/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email":"smoke@test.com","password":"Test1234!","full_name":"Smoke Test"}' 2>/dev/null | grep -o '"message":"User created"' || true)
if [ -n "$REG" ]; then pass; else fail; fi

echo -n "L5 Auth login: "
LOGIN=$(curl -sf -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"smoke@test.com","password":"Test1234!"}' \
    -c "$COOKIES" 2>/dev/null | grep -o '"message":"Login successful"' || true)
if [ -n "$LOGIN" ]; then pass; else fail; fi

echo -n "L5 Auth me: "
ME=$(curl -sf http://localhost:8000/auth/me -b "$COOKIES" 2>/dev/null | grep -o '"email"' || true)
if [ -n "$ME" ]; then pass; else fail; fi

echo -n "L7 Create workflow: "
WF=$(curl -sf -X POST http://localhost:8000/workflows \
    -H "Content-Type: application/json" \
    -b "$COOKIES" \
    -d '{"name":"Smoke Test Workflow","trigger_channel":"gmail"}' 2>/dev/null | grep -o '"id"' || true)
if [ -n "$WF" ]; then pass; else fail; fi

echo -n "L7 List workflows: "
LIST=$(curl -sf http://localhost:8000/workflows -b "$COOKIES" 2>/dev/null | grep -o '"name"' || true)
if [ -n "$LIST" ]; then pass; else fail; fi

echo -n "L8 Trigger execution: "
EXEC=$(curl -sf -X POST http://localhost:8000/executions/trigger/{workflow_id} \
    -H "Content-Type: application/json" \
    -b "$COOKIES" \
    -d '{"inquiry_text":"Test inquiry for smoke","source_channel":"test"}' 2>/dev/null | grep -o '"execution_id"' || true)
if [ -n "$EXEC" ]; then pass; else fail; fi

echo "=== Results: $PASS/$COUNTER passed ==="

if [ "$FAIL" -eq 0 ]; then
    echo "🎉 All smoke tests passed!"
    exit 0
else
    echo "💥 Some tests failed"
    exit 1
fi