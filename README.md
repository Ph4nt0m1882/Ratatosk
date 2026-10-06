# ![RATATOSK](.github/assets/RATATOSK.webp)

<p align="center">
  <strong>The universal and highly customizable orchestrator that unifies all AI models and combines their skills.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/uv-Package%20Manager-DE5FE9?style=for-the-badge&logo=astral&logoColor=white" />
  <img src="https://img.shields.io/badge/Flutter-Frontend-02569B?style=for-the-badge&logo=flutter&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
</p>

---

## Why Ratatosk 🐿️

In Norse mythology, **Ratatosk** is the squirrel that runs along the world tree, Yggdrasil, carrying messages between all the realms.

Today, every AI has its own strengths and limitations:
- **Using Claude and need an image?** 👉 Anthropic does not provide a native image generation model, so Ratatosk delegates the request to Gemini or Flux in the background.
- **Want a video from a local server?** 👉 Ratatosk orchestrates the call to OpenAI Sora or Runway.
- **Need specialized models?** 👉 Integrate Gemini's computer vision and robotics, or run private local models via Ollama without modifying your client code.
<br/>
---

## Built for Everyone 🎯

Ratatosk is designed for everyone—from everyday users with zero technical background to families, teams, and experienced developers:

* **Family** : Simple and secure, with safety guardrails for children and code execution disabled.
* **Teams & Companies** : Shared knowledge bases (RAG), cost control, usage monitoring, and private models.
* **Power Users & Developers** : MCP tools, execution sandboxes, and unrestricted local models.
<br/>

---

## Two Ways to Run 🚀

| 🖥️ Local Mode | 🌐 Server Mode |
|:---|:---|
| **Runs locally on your computer** | **Deployed on a remote server or VPS** |
| **Best for:** Developers, creators, and individuals working on their own machine. | **Best for:** Families, teams, communities, and businesses. |
| The API runs on `localhost`. Instant setup, ultra-low latency, and zero network exposure. | Distributes a secure, simplified companion app to members via a built-in download portal with QR-code pairing. |
<br/>

---

## System Architecture 🏗️

```mermaid
flowchart TB
    subgraph CLIENTS["📱 1. Client Layer (Flutter)"]
        direction LR
        AdminApp["👑 Admin App<br/>(Dashboard, Config, Deploy)"]
        ChildApp["👶 Companion App<br/>(Streamlined, Zero-Config)"]
        External["💻 Third-Party Clients<br/>(CLI, VS Code, Curl)"]
    end

    subgraph GATEWAY["🚪 2. API Gateway & Portal (FastAPI)"]
        direction TB
        StandardAPI["Standard API (/v1/chat, /v1/models)"]
        RatatoskAPI["Ratatosk API (/pair, /modules, /status)"]
        WebPortal["Web Portal & App Downloads (Server Mode)"]
    end

    subgraph ENGINE["🐿️ 3. Ratatosk Core Engine"]
        direction TB
        AuthGuards["🔐 Profiles & Guardrails (Permissions, Filters, Quotas)"]
        Router["⚡ Intelligent Router (Cross-Delegation)"]
        
        subgraph SUBSYSTEMS["Subsystems (Pluggable)"]
            MCP["🔌 MCP Host (Tools)"]
            RAG["🧠 RAG Engine (Docs & Memory)"]
            Sandbox["📦 Secure Sandbox (Code Exec)"]
        end
    end

    subgraph PROVIDERS["🌐 4. AI Realms (Yggdrasil)"]
        direction LR
        Anthropic["Claude<br/>(Reasoning & Text)"]
        OpenAI["GPT / Sora<br/>(Text & Video)"]
        Gemini["Gemini / Imagen<br/>(Multimodal & Robotics)"]
        Local["Ollama / vLLM<br/>(Local & Offline)"]
    end

    CLIENTS <-->|"REST / SSE / WebSockets"| GATEWAY
    GATEWAY <--> ENGINE
    AuthGuards --> Router
    Router <--> SUBSYSTEMS
    Router <--> PROVIDERS
```

### Cross-Delegation in Action ⚡

How Ratatosk bridges capabilities between models behind the scenes:

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 User (Flutter)
    participant Core as 🐿️ Ratatosk Router
    participant Claude as 🧠 Claude (Anthropic)
    participant Gemini as 🎨 Gemini Imagen

    User->>Core: "Write a fable and generate an illustration for it"
    Note over Core: Detects Claude cannot generate images.<br/>Ratatosk dynamically injects the 'generate_image' tool.
    Core->>Claude: Sends prompt + 'generate_image' tool definition
    Claude-->>Core: Streams story text + Tool Call: generate_image(...)
    Core-->>User: Streams story text in real-time (SSE)
    Core->>Gemini: Request image: generate_image(...)
    Gemini-->>Core: Returns generated image
    Core-->>User: Delivers completed image
```
