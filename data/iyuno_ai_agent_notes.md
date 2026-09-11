# AI Agent Workflow Notes

This public knowledge note describes the portfolio agent design.

The IYUNO AI Agent uses a multi-step workflow:

1. User Request Analysis: identify the user's goal, constraints, and expected output.
2. Draft Generation: create an initial answer using the analyzed request.
3. Quality Review: review the draft for clarity, completeness, and accuracy.
4. Final Result: return the improved answer to the user.

The project includes a Streamlit web interface with Demo Mode and Live Mode.
Demo Mode uses predefined mock results and does not call the OpenAI API.
Live Mode can call the OpenAI API when a local API key is configured.

For public deployment, Live Mode should be disabled to protect API credits.
The application can enforce this with the `IYUNO_PUBLIC_DEMO_ONLY=true` environment variable.

RAG support uses public `.txt` or `.md` files in the `data/` directory as local knowledge sources.
The documents are split into chunks, embedded, retrieved with vector similarity search, and cited in the final answer.
