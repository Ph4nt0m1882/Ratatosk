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

---

## Database Architecture (MCD) 🗄️

Ratatosk centralizes its state, relational history, and attachments in a unified database (SQLite locally, PostgreSQL + pgvector on servers):

```plantuml
@startuml Ratatosk_MCD
!theme plain
hide empty methods
hide circle
hide <<Association>> stereotype
skinparam linetype ortho

skinparam class {
    BackgroundColor White
    BorderColor #2C3E50
    ArrowColor #2C3E50
    HeaderBackgroundColor #ECF0F1
    RoundCorner 4

    BackgroundColor<<Association>> #EBF5FB
    BorderColor<<Association>> #2980B9
    HeaderBackgroundColor<<Association>> #D4E6F1
    RoundCorner<<Association>> 30
}

' ==================== ENTITIES ====================

entity "USER" as user {
    * **id** : uuid <<PK>>
    --
    * username : varchar(100) <<unique>>
    email : varchar(255)
    hashed_password : varchar(255)
    * is_active : boolean
    * is_admin : boolean
    * created_at : timestamptz
}

entity "USER_SESSION" as session {
    * **id** : uuid <<PK>>
    --
    device_name : varchar(255)
    * token_hash : varchar(255) <<unique>>
    * expires_at : timestamptz
    * created_at : timestamptz
}

entity "RULE" as rule {
    * **id** : uuid <<PK>>
    --
    * name : varchar(255)
    description : text
    * content : text
    application_rules : text
    * is_active : boolean
    * created_at : timestamptz
    * updated_at : timestamptz
}

entity "COMMAND" as cmd {
    * **id** : uuid <<PK>>
    --
    * name : varchar(100)
    description : text
    * content : text
    * is_active : boolean
    * created_at : timestamptz
    * updated_at : timestamptz
}

entity "PERSONA" as persona {
    * **id** : uuid <<PK>>
    --
    * content : text
    * updated_at : timestamptz
}

entity "USER_FACT" as user_fact {
    * **id** : uuid <<PK>>
    --
    * content : text
    * embedding : vector
    * created_at : timestamptz
    * updated_at : timestamptz
}

entity "CONVERSATION" as conv {
    * **id** : uuid <<PK>>
    --
    title : varchar(255)
    ai_notes : text
    analyzed_at : timestamptz
    * created_at : timestamptz
    * updated_at : timestamptz
}

entity "MESSAGE" as msg {
    * **id** : uuid <<PK>>
    --
    * role : varchar(50)
    * model : varchar(100)
    content : text
    parts : jsonb
    token_count : integer
    * created_at : timestamptz
}

entity "ATTACHMENT" as attach {
    * **id** : uuid <<PK>>
    --
    * filename : varchar(255)
    * mime_type : varchar(100)
    * file_path : text
    * file_size : integer
    description : text
    * is_generated : boolean
    expires_at : timestamptz
    * created_at : timestamptz
}

entity "DOCUMENT" as doc {
    * **id** : uuid <<PK>>
    --
    * filename : varchar(255)
    * mime_type : varchar(100)
    * file_path : text
    * file_size : integer
    * created_at : timestamptz
}

entity "DOCUMENT_CHUNK" as doc_chunk {
    * **id** : uuid <<PK>>
    --
    * chunk_index : integer
    * content : text
    * embedding : vector
    metadata : jsonb
}

entity "MCP_SERVER" as mcp {
    * **id** : uuid <<PK>>
    --
    * name : varchar(100)
    * transport : varchar(50)
    * command_or_url : text
    args : jsonb
    env_or_headers : jsonb
    * is_active : boolean
    * created_at : timestamptz
    * updated_at : timestamptz
}

entity "HOOK" as hook {
    * **id** : uuid <<PK>>
    --
    * name : varchar(100)
    * tool_pattern : varchar(255)
    * event : varchar(50)
    * action : varchar(50)
    condition : text
    * is_active : boolean
    * created_at : timestamptz
    * updated_at : timestamptz
}

entity "ACCESS_POLICY" as policy {
    * **id** : uuid <<PK>>
    --
    * name : varchar(100)
    allowed_models : jsonb
    blocked_models : jsonb
    * can_generate_image : boolean
    * can_generate_video : boolean
    * can_use_mcp : boolean
    max_daily_tokens : integer
    max_daily_cost : numeric(10,4)
    * updated_at : timestamptz
}

entity "USAGE_LOG" as usage {
    * **id** : uuid <<PK>>
    --
    * provider : varchar(50)
    * model : varchar(100)
    * operation_type : varchar(50)
    * input_tokens : integer
    * output_tokens : integer
    * estimated_cost : numeric(10,6)
    * created_at : timestamptz
}

entity "SYSTEM_PROMPT" as sys_prompt #F8F9F9 {
    * **id** : varchar(36) <<PK>>
    --
    * name : varchar(255) <<unique>>
    * hierarchy : integer
    description : text
    * content : text
    * is_active : boolean
    * is_default : boolean
    * created_at : timestamptz
    * updated_at : timestamptz
}

' ==================== ASSOCIATIONS (RELATIONS) ====================

class "DEFINES" as rel_defines <<Association>> {
}

class "CREATES" as rel_creates <<Association>> {
}

class "PROFILES" as rel_profiles <<Association>> {
}

class "REMEMBERS" as rel_remembers <<Association>> {
}

class "OWNS" as rel_owns <<Association>> {
}

class "CONTAINS" as rel_contains <<Association>> {
}

class "UPLOADS / GENERATES" as rel_uploads <<Association>> {
}

class "REFERENCES" as rel_references <<Association>> {
}

class "INDEXES" as rel_indexes <<Association>> {
}

class "SPLIT_INTO" as rel_splits <<Association>> {
}

class "CONNECTS" as rel_connects <<Association>> {
}

class "GUARDS" as rel_guards <<Association>> {
}

class "GOVERNED_BY" as rel_governed <<Association>> {
}

class "CONSUMES" as rel_consumes <<Association>> {
}

class "AUTHENTICATES" as rel_auth <<Association>> {
}

' ==================== CARDINALITIES (MERISE) ====================

user "0,n" -up- rel_auth
rel_auth -up- "1,1" session

user "0,n" -right- rel_defines
rel_defines -right- "1,1" rule

user "0,n" -left- rel_creates
rel_creates -left- "1,1" cmd

user "0,1" -up- rel_profiles
rel_profiles -up- "1,1" persona

user "0,n" -up- rel_remembers
rel_remembers -up- "1,1" user_fact

user "0,n" -- rel_owns
rel_owns -- "1,1" conv

conv "0,n" -- rel_contains
rel_contains -- "1,1" msg

user "0,n" -- rel_uploads
rel_uploads -- "1,1" attach

msg "0,n" -- rel_references
rel_references -- "0,n" attach

user "0,n" -- rel_indexes
rel_indexes -- "0,1" doc

doc "1,n" -- rel_splits
rel_splits -- "1,1" doc_chunk

user "0,n" -- rel_connects
rel_connects -- "0,1" mcp

user "0,n" -- rel_guards
rel_guards -- "0,1" hook

user "0,1" -- rel_governed
rel_governed -- "0,n" policy

user "0,n" -- rel_consumes
rel_consumes -- "1,1" usage

@enduml
```

### Key Design Principles:
1. **User Ownership (`USER`)**: Unifies local single-user mode (auto-seeded admin) and multi-user remote server deployments without schema alterations.
2. **Turn-by-Turn Model Selection & Working Memory (`MESSAGE.model` & `CONVERSATION.ai_notes`)**: The AI model is attached to the *message*, not the *conversation*, enabling seamless switching between models within the same thread, while `ai_notes` gives the AI a persistent per-conversation scratchpad to track context, decisions, or rolling summaries across models and turns.
3. **Deployment-Level Modular Prompting (`SYSTEM_PROMPT`)**: Independent configuration modules managed at the instance level. All active modules are compiled globally for the deployment, applying the unified system persona consistently across all users and conversations.
4. **User-Level Custom Instructions & Commands (`RULE` & `COMMAND`)**:
   - `RULE`: Personal guidelines and behaviors owned by each user, injected automatically or conditionally via `application_rules` (e.g., when analyzing images or writing code).
   - `COMMAND`: Explicit user-triggered action templates (e.g., `/summarize`, `/review`) injected on demand to enforce a specific task workflow.
5. **Hybrid Background User Profiling (`PERSONA` & `USER_FACT`)**: Built asynchronously when the server is idle by analyzing conversations (`CONVERSATION.analyzed_at`):
   - `PERSONA`: Compact core identity sheet (name, age, general profile) always injected in context for tone and safety.
   - `USER_FACT`: Atomic user facts stored with vector embeddings (`embedding`) and retrieved selectively via semantic search (RAG) only when relevant to the current prompt.
6. **Unified Attachments & Purge Policy (`ATTACHMENT`)**: Handles chat attachments and AI-generated media (images, videos, audio) with an optional `description` (for lightweight context in subsequent turns) and an `expires_at` retention policy for automated background cleanup.
7. **Shared & Private Knowledge Base (`DOCUMENT` & `DOCUMENT_CHUNK`)**: A single `DOCUMENT` entity linked to `USER` via a `0,n` — `0,1` relation: `0` user means a global deployment document shared with everyone, while `1` user means a private user document. Each document is split into vectorized `DOCUMENT_CHUNK`s for semantic retrieval.
8. **Decoupled MCP Servers & Tool Guardrails (`MCP_SERVER` & `HOOK`)**:
   - `MCP_SERVER`: Dynamic MCP server configurations (`stdio`, `sse`, `http`), linked in `0,1` to `USER` (supporting both instance-wide servers and personal user integrations).
   - `HOOK`: Intentionally decoupled from `MCP_SERVER` so manual guardrails (`tool_pattern`, `event`, `action` such as confirmation prompts or blocks, and `condition`) apply uniformly to both MCP tools and native built-in tools.
9. **Admin Access Control & Quotas (`ACCESS_POLICY`)**: Allows the administrator (e.g., family server host or team admin) to restrict specific users or groups (`0,1` — `0,n`) by whitelisting/blacklisting models (`allowed_models`, `blocked_models`), toggling capabilities (`can_generate_image`, `can_generate_video`, `can_use_mcp`), and enforcing daily token or cost ceilings.
10. **Persistent Telemetry & Cost Tracking (`USAGE_LOG`)**: Tracks every model invocation (`chat`, `image_gen`, `embedding`, `persona_worker`) with `input_tokens`, `output_tokens`, and `estimated_cost`. Linked directly to `USER` rather than `MESSAGE` so usage history and budget enforcement remain intact even when a user deletes their conversations.

