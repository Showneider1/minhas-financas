# Skill: llm-evaluation

## Objective
Quantitatively and qualitatively measure the performance of LLM responses to ensure safety, accuracy, and helpfulness.

## Context
Used during the development and iteration of the AI Assistant.

## Prerequisites
- A set of "Golden Queries" (benchmark questions and ideal answers).
- A way to run bulk tests.

## Execution Procedure
1. **Dataset Creation**: Build a test set of queries across different categories (Calculation, Advice, Summary, Safety).
2. **Metric Selection**:
    - **Accuracy**: Does the number match the DB?
    - **Faithfulness**: Is the answer based on the provided context?
    - **Toxicity/Safety**: Does it violate any safety rules?
    - **Conciseness**: Is the response overly wordy?
3. **Evaluation Method**:
    - **LLM-as-a-Judge**: Use a more powerful model (e.g., GPT-4o) to grade the output of the assistant.
    - **Human Review**: Manual grading of a subset.
4. **Iterative Refinement**: Use failures to refine prompts or tools.

## Technical Patterns
- RAGAS framework.
- A/B Testing for prompts.
- Precision/Recall for retrieval.

## Examples
- Testing the AI with 50 different "Spending" queries and measuring how many times it correctly called the `get_spending` tool.

## Validation Criteria
- Score improvement over iterations.
- Zero "Critical" safety failures.
- High correlation between LLM-judge and human-judge.

## Common Errors
- Relying on a single metric (e.g., only accuracy) while ignoring tone.
- Not updating the test set as the product evolves.

## Security Rules
- N/A.

## Deliverables
- Evaluation Dataset.
- Performance Reports.
- Comparison Matrix for different prompt versions.
