# Skill: prompt-engineering

## Objective
Craft and optimize prompts to elicit accurate, professional, and safe responses from LLMs in a financial context.

## Context
Used for building the AI Assistant (Module F).

## Prerequisites
- Access to an LLM (e.g., GPT-4, Claude, Gemini).
- Clear definition of the AI's persona.

## Execution Procedure
1. **Persona Definition**: Define the role (e.g., "You are a senior certified financial planner...").
2. **Context Provision**: Provide the necessary background (user's financial status, current goals).
3. **Constraint Setting**: Explicitly state what the AI *cannot* do (e.g., "Do not invent balances", "Do not give legal advice").
4. **Few-Shot Prompting**: Provide examples of ideal input-output pairs.
5. **Chain-of-Thought**: Instruct the AI to "think step-by-step" before providing the final answer.
6. **Iterative Testing**: Test the prompt with diverse inputs and refine based on output quality.

## Technical Patterns
- System Prompts.
- Few-Shot Learning.
- Chain-of-Thought (CoT).
- Delimiters for clear sectioning.

## Examples
- Crafting a prompt that transforms a raw list of transactions into a concise monthly summary without omitting any category.

## Validation Criteria
- AI follows all constraints in 95%+ of tests.
- Tone is consistent with the product's brand.
- Responses are logically sound.

## Common Errors
- Being too vague in instructions.
- Forgetting to tell the AI how to handle "I don't know" scenarios.

## Security Rules
- Use delimiters to separate user input from system instructions to prevent prompt injection.

## Deliverables
- System Prompt Templates.
- Prompt Version History.
- Test Set for Prompts.
