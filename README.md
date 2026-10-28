# Vibhek Soni

Backend engineer in New York. I build API infrastructure and security tools. Most of them start with me taking a protocol apart.

Open to backend, AI infrastructure and security roles. [vibheksoni.com](https://vibheksoni.com/) · [vibheksoni@engineer.com](mailto:vibheksoni@engineer.com)

## FreeTheAI

A free AI API and model marketplace behind one OpenAI-compatible endpoint. It has served over 219 billion tokens across 7.5 million requests ([public stats](https://freetheai.org/stats)). I built and run the Go gateway.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/freetheai-dark.png">
  <img src="assets/freetheai-light.png" width="100%" alt="FreeTheAI request path: clients such as OpenAI SDKs, Claude Code and curl call the Go gateway at api.freetheai.org/v1, which handles API keys, wallet and credits, rate limits, abuse controls and usage metering. A router resolves the model, picks an upstream by price or speed and streams tokens back from a free model pool or marketplace sellers. PostgreSQL stores accounts, keys and the usage ledger. Redis holds rate limits and shared request state.">
</picture>

## Other work

- [GoonPAI](https://goonpai.chat/) is a roleplay chat site I'm building on the FreeTheAI API.
- [stealth-browser-mcp](https://github.com/vibheksoni/stealth-browser-mcp) lets AI agents drive a real Chrome browser. Over 3,200 stars.
- [secrets.wtf](https://secrets.wtf/) lists 181 AI servers left open on the internet and how to lock each one down.
- [UniClaudeProxy](https://github.com/vibheksoni/UniClaudeProxy) runs Claude Code on OpenAI, Gemini, DeepSeek and Ollama.
- [unbuned](https://github.com/vibheksoni/unbuned) pulls the JavaScript back out of Bun executables.

The rest is in my [repositories](https://github.com/vibheksoni?tab=repositories).

## About

I mostly write Go and Python on top of PostgreSQL and Redis. Some Rust too. B.S. in Computer Science from WGU in 2026.

[LinkedIn](https://www.linkedin.com/in/vibheksoni/) · [X](https://x.com/ImVibhek) · [OpenDoors](https://opendoors.wtf/) · [YouTube](https://www.youtube.com/@vibheksoni) · [Instagram](https://www.instagram.com/nyc.vibhek/) · [Buy Me a Coffee](https://buymeacoffee.com/vibheksoni)
