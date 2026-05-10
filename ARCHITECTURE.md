# Visual Barista AI — End-to-End Architecture

```mermaid
flowchart TB
    subgraph Client["Client"]
        User["User"]
        Vue["Vue 3 + Vite Frontend"]
        User --> Vue
    end

    subgraph API["FastAPI Backend"]
        Routes["Routes"]
        Routes --> Health["/health"]
        Routes --> Menu["/menu"]
        Routes --> Recommend["POST /recommend-drink"]
        Routes --> Feedback["POST /feedback"]
    end

    subgraph Pipeline["Recommendation Pipeline (LangGraph)"]
        direction TB
        MA["Mood Agent"]
        CA["Context Agent"]
        CPA["Coffee Profile Agent"]
        MBA["Menu Blender Agent"]
        PGA["Price Guardrail Agent"]
        MA --> CA --> CPA --> MBA --> PGA
    end

    subgraph Services["Backend Services"]
        MenuSvc["Menu Service\n(starbucks_menu.json)"]
        ImageSvc["Image Service"]
    end

    subgraph External["External APIs"]
        WeatherAPI["WeatherAPI\n(weather + location)"]
        Gemini["Google Gemini\n(mood, profile, image, GEPA)"]
    end

    subgraph FeedbackLoop["Feedback Loop"]
        Store["Feedback Store"]
        GEPA["GEPA Optimizer"]
        Store --> GEPA
    end

    Vue -->|mood, location| Recommend
    Vue -->|thumbs_up/down| Feedback
    Vue --> Menu
    Vue -.->|preview| WeatherAPI

    Recommend --> Pipeline
    Pipeline --> MenuSvc
    Pipeline --> WeatherAPI
    Pipeline --> Gemini
    MBA --> ImageSvc
    ImageSvc --> Gemini

    Feedback --> Store
    Feedback --> GEPA
    GEPA --> Gemini
```

## Data flow (recommendation)

```mermaid
sequenceDiagram
    participant U as User
    participant V as Vue Frontend
    participant API as FastAPI
    participant G as LangGraph Pipeline
    participant W as WeatherAPI
    participant GM as Gemini

    U->>V: mood text + location
    V->>API: POST /recommend-drink
    API->>G: invoke(mood_text, location)

    G->>G: Mood Agent (Gemini: mood + energy)
    G->>G: Context Agent (WeatherAPI: weather, timezone)
    G->>G: Coffee Profile Agent (DSPy/Gemini: temp, flavor, body)
    G->>G: Menu Blender (score + GEPA prefs, pick drink)
    G->>G: Price Guardrail (DSPy: validate price)

    G->>GM: generate drink image
    G-->>API: drink_recommendation
    API-->>V: drink + context + image_url
    V-->>U: show recommendation
```

## Component summary

| Layer | Components |
|-------|------------|
| **Frontend** | Vue 3, Vite; mood/location input; drink cards; feedback (thumbs up/down); optional weather preview via WeatherAPI |
| **API** | FastAPI; CORS; `/health`, `/menu`, `POST /recommend-drink`, `POST /feedback`; debug routes under `/debug` |
| **Pipeline** | LangGraph DAG: Mood → Context → Coffee Profile → Menu Blender → Price Guardrail; shared `RecommendationState` |
| **Agents** | Mood (Gemini), Context (WeatherAPI + TZ), Coffee Profile (DSPy/Gemini), Menu Blender (scoring + GEPA), Price Guardrail (DSPy) |
| **External** | WeatherAPI (current weather by location), Google Gemini (mood, profile, image, GEPA reflection) |
| **Feedback** | In-memory feedback store; GEPA optimizer reads history and produces learned preferences for menu blender |
