# System Architecture - Finance OS

## 1. High-Level Architecture
Finance OS uses a **Modular Monolith** approach for the core business logic to reduce complexity, with a separate **AI Service** to isolate heavy LLM dependencies and Python-based data science tools.

### Component Diagram (Conceptual)
`Frontend (Next.js)` $\rightarrow$ `API Gateway (NestJS)` $\rightarrow$ `Core Modules` $\rightarrow$ `PostgreSQL`
                                   $\searrow$ `AI Service (FastAPI)` $\rightarrow$ `Vector DB / LLM`

## 2. Technology Stack

### Frontend
- **Framework**: Next.js (App Router).
- **Language**: TypeScript.
- **Styling**: Tailwind CSS + shadcn/ui.
- **State**: React Query (Server State), Zustand (Client State).
- **Validation**: Zod + React Hook Form.
- **Charts**: Recharts.

### Backend (Core API)
- **Framework**: NestJS.
- **Language**: TypeScript.
- **ORM**: Prisma.
- **Database**: PostgreSQL.
- **Task Queue**: Redis + BullMQ (for imports and notifications).
- **API Style**: REST / OpenAPI.

### AI Service
- **Framework**: FastAPI.
- **Language**: Python.
- **LLM Orchestration**: LangChain / LlamaIndex.
- **Vector Storage**: pgvector (integrated into PostgreSQL).

## 3. Data Model & Financial Integrity

### The Ledger (The Heart of the System)
To ensure absolute precision, Finance OS implements a **Double-Entry Ledger**.
- **Transactions Table**: Groups one or more entries.
- **Entries Table**: Individual debits and credits.
- **Constraint**: $\sum \text{Entries.amount} = 0$ for every Transaction.
- **Data Type**: `Decimal(19, 4)` for all monetary values.

### Multi-Tenancy
- Every table contains a `userId` column.
- Strict Row-Level Security (RLS) or Global Query Filters to prevent cross-user data leaks.

## 4. Infrastructure
- **Development**: Docker Compose (Postgres, Redis, API, AI).
- **CI/CD**: GitHub Actions.
- **Deployment**: Dockerized containers on a cloud provider.

## 5. Security Design
- **Auth**: JWT-based authentication with HttpOnly cookies.
- **Authz**: Role-Based Access Control (RBAC) for different user levels.
- **Input**: Strict Zod validation on all API boundaries.
- **AI**: Prompt injection filters and tool-use restrictions.
