# LLM API Comparison Reference

This table summarizes popular free-tier and near free-tier LLM APIs suitable for low-cost integration in our scorecard project. Costs and limits are accurate as of April 2025; check provider docs for updates.

| Model                      | Provider      | Source  | Input Cost per 1M tokens | Output Cost per 1M tokens | Free Tier / Credits                                  |
|----------------------------|---------------|---------|--------------------------:|---------------------------:|-------------------------------------------------------|
| GPT-3.5-turbo              | OpenAI        | Closed  | $1.5                      | $2.0                       | $18 free credit (first 3 months); 3 req/sec; 90k TPM  |
| GPT-4 (8K context)         | OpenAI        | Closed  | $30                       | $60                        | No free tier                                           |
| Claude Instant             | Anthropic     | Closed  | $1.6                      | $8.0                       | 5 RPM; 20 TPM; 300 TPD                                |
| Gemini Nano (beta)         | Google        | Closed  | Free beta                 | Free beta                  | $300 Google Cloud credit (90 days)                    |
| Llama-2-13B-Instruct       | Hugging Face  | Open    | Free inference            | Free inference             | Community-run; rate limits apply                      |
| Cohere Generate (xlarge)   | Cohere        | Closed  | $7.5                      | $7.5                       | 5M tokens/month                                      |
| AI21 Studio Jurassic-1     | AI21 Labs     | Closed  | $35                       | $40                        | 10k tokens/month                                     |
| Qwen-7B-Chat               | Alibaba Cloud | Closed  | ≈$7.5 (0.05 CNY/token)    | ≈$7.5                      | ¥10K free credit                                      |
| DeepInfra Llama-3-Instruct | DeepInfra     | Open    | $1.79                     | $1.79                      | $1.80 signup credit                                  |
| TogetherAI Llama2 / FLAN   | Together AI   | Open    | Free tier                 | Free tier                  | Free Llama2 & FLAN; $5 credit for others             |
| Groq Mixtral 8x7B          | Groq          | Open    | $0.24                     | $0.24                      | 30 RPM; 5k TPM; 500k TPD                             |

Notes:
- Costs are per million tokens; billing increments may vary by provider.
- Free tier limits often include request-per-minute (RPM), tokens-per-minute (TPM), or daily caps.
- Beta or community inference endpoints may impose usage constraints.
- Always verify current pricing and quotas on official provider sites before production use.
