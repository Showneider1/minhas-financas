# Skill: financial-ai-agent

## Objective
Implement an AI agent that can interact with deterministic tools to provide accurate financial insights.

## Context
The core implementation of the AI Assistant (Module F).

## Prerequisites
- LLM integration.
- Set of deterministic tools (functions) for data retrieval.

## Execution Procedure
1. **Tool Definition**: Define a set of functions the AI can call (e.g., `get_balance(account_id)`, `get_spending_by_category(month)`).
2. **Agent Loop**:
    - User asks a question.
    - AI decides if it needs a tool.
    - AI calls the tool $\rightarrow$ Tool returns data $\rightarrow$ AI incorporates data into response.
3. **Grounding**: Ensure the AI only uses the tool output for numbers, never guessing.
4. **Safety Guardrails**: Implement a filter to block requests for prohibited actions (e.g., "Move money to X").
5. **Memory Management**: Implement a sliding window or summary-based memory for conversations.

## Technical Patterns
- Function Calling (Tool Use).
- ReAct (Reasoning and Acting) pattern.
- Guardrails/Moderation layers.

## Examples
- User: "How much did I spend on food in July?" $\rightarrow$ AI calls `get_spending_by_category('Food', '2026-07')` $\rightarrow$ Returns "R$ 450,00" $\rightarrow$ AI responds: "You spent R$ 450,00 on food in July."

## Validation Criteria
- 100% accuracy for numeric queries (verified against DB).
- Correct tool selection for the given intent.
- Graceful handling of tool errors.

## Common Errors
- Letting the AI "assume" a tool's output.
- Creating too many tools, causing "tool confusion".

## Security Rules
- Tools must use the same authorization checks as the API.
- Sanitize tool inputs to prevent injection.

## Deliverables
- AI Agent Implementation.
- Tool Definitions (JSON Schema).
- Agent-Human Interaction Flows.
