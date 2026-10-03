# KrishiSmriti: Friction Log

Build, Ship, Shape: Amazon Developer Hackathon, Alexa+ track.

## 1. Connecting our self-hosted MCP server to Alexa+
- Task: Connect our self-hosted MCP server to Alexa+
- Steps taken: Built the MCP server in FastAPI, deployed it to a public HTTPS URL, registered the endpoint, tested with voice queries
- Expected: Alexa+ calls our tools consistently
- Actual: Tool calls were sometimes skipped or the wrong tool was picked, and it was hard to see why
- Severity: High
- Workaround: Rewrote tool names and descriptions to be more explicit; added server-side logging to see incoming calls
- Suggestion: A developer console showing tool selection, arguments and responses for each Alexa+ turn, plus guidance on writing MCP tool descriptions

## 2. Regional Indian language support
- Task: Support farmers in Telugu, Tamil and Marathi
- Steps taken: Checked Alexa+ language support and tested regional-language queries
- Expected: Regional Indian languages available
- Actual: Limited language support, so we launched with English and Hindi
- Severity: High
- Workaround: Scoped the demo to English and Hindi; other languages kept on the roadmap
- Suggestion: Publish an Alexa+ language roadmap for India and a clear support matrix in the docs
