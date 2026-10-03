# KrishiSmriti: Alexa+ Farm Advisor That Remembers Every Plot

Farmers talk to Alexa+ and get advice that remembers what worked, and what failed, on their own plot.

Built for the Build, Ship, Shape: Amazon Developer Hackathon (Alexa+ track).

Demo video: https://www.youtube.com/watch?v=Jn_88sBgozI

## What it does
- Voice first: farmers speak, no typing or reading needed
- Plot memory: treatments, outcomes and issues are stored per plot (Hindsight)
- Grounded advice: past results on that plot shape every answer (Groq LLM)
- Alexa+ integration: a self-hosted MCP server exposes KrishiSmriti's tools to Alexa+

## Architecture
Farmer (voice) -> Alexa+ -> MCP server (FastAPI) -> Hindsight (plot memory) + Groq LLM (reasoning)

## Run it locally
See the `krishismriti` folder. Basic steps:
1. cd krishismriti
2. pip install -r requirements.txt
3. Add your GROQ and HINDSIGHT API keys to a .env file
4. Start the FastAPI server with uvicorn

## Friction log
See [FRICTION_LOG.md](FRICTION_LOG.md).

## License
MIT. See [LICENSE](LICENSE).
