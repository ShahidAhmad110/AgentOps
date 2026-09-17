# 15 — Error Handling & Reliability Specification

## Errors to Handle
- Invalid requests
- Authentication failures
- Database failures
- LLM failures
- Tool failures
- Document processing failures
- Embedding failures
- Timeouts
- Rate limits
- Unexpected agent states

## Rules
- No silent exception swallowing.
- Log failures with useful context.
- Return controlled API errors.
- Preserve user-safe messages.
- Record relevant agent execution status.
- Use retries only where safe and appropriate.
- Avoid duplicate side effects during retries.

## Example
```text
Tool Failure
 ↓
Detect
 ↓
Record error
 ↓
Mark execution failed
 ↓
Return controlled response
```
