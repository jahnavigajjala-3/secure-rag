# Design Document — SecureRAG Frontend

## Overview

SecureRAG Frontend is a React 18 single-page application that replaces the existing frontend with a full enterprise flow: public landing page → authentication → role-resolved dashboard. The application is built with TypeScript, Vite, Tailwind CSS, shadcn/ui components, React Router v6, and TanStack Query v5.

The architecture has three major concerns:

1. **Auth** — JWT-based authentication with role resolution from the token payload, stored in `localStorage`, token expiry detection in `AuthContext`.
2. **API Isolation** — All HTTP calls live in `src/api/client.ts`. A mock implementation at `src/api/mock.ts` provides identical function signatures and return types for offline development. Switching from mock to live is a single import change.
3. **Route-guarded navigation** — Protected routes check `AuthContext` for authentication and role before rendering. Unauthorized access is redirected immediately without flash of content.

### Research Findings

The tech stack choices are standard and well-supported:

- **React 18** with concurrent features (Suspense, `startTransition`) — no experimental APIs are required for this feature set.
- **TanStack Query v5** changed the API (no more `onSuccess`/`onError` callbacks on `useQuery`; prefer `useEffect` on data; mutations still have `onSuccess`/`onError`). The `staleTime` and `gcTime` (formerly `cacheTime`) options are used for cache management.
- **shadcn/ui** generates components into `src/components/ui/`. All design primitives (Button, Input, Table, Dialog, Badge, etc.) are copied into the project and owned by the developer — they are not an npm dependency.
- **React Router v6** uses the `createBrowserRouter` / `RouterProvider` API. `useNavigate`, `useParams`, `Navigate` component, and `Outlet` are the primary primitives.
- **Vite** — environment variables prefixed with `VITE_` are exposed to the browser. `VITE_API_BASE_URL` controls the backend base URL.

---

## Architecture

### High-Level Component Flow

```
Browser
  └── RouterProvider (createBrowserRouter)
        ├── PublicRoute wrapper — unauthenticated only
        │     ├── / → LandingPage
        │     ├── /login → LoginPage
        │     └── /register → RegisterPage
        └── ProtectedRoute wrapper — authenticated only
              ├── AdminRoute → AdminLayout (Outlet)
              │     ├── /admin/dashboard → AdminDashboardPage
              │     ├── /admin/employees → EmployeesPage
              │     ├── /admin/employees/:id → EmployeeDetailPage
              │     ├── /admin/roles → RolesPage
              │     ├── /admin/roles/:id → RoleDetailPage
              │     ├── /admin/documents → DocumentsPage
              │     ├── /admin/audit-logs → AuditLogsPage
              │     └── /admin/settings → SettingsPage
              └── EmployeeRoute → EmployeeLayout (Outlet)
                    ├── /employee/dashboard → EmployeeDashboardPage
                    ├── /employee/ask-ai → AskAIPage
                    └── /employee/my-documents → MyDocumentsPage
```

### State Management Strategy

- **AuthContext** — React context holding the decoded token, user identity, and helpers. Single source of truth for auth state.
- **TanStack Query** — All server data. No Redux, no Zustand. Each page owns its queries; shared data (roles list) uses shared query keys so multiple pages benefit from the same cache entry.
- **Local component state** — Form fields, UI toggles, chat message array, upload state machine.

---

## Project Directory Structure

```
secure-rag-frontend/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── .env.example                      # VITE_API_BASE_URL=http://localhost:8000
│                                     # VITE_USE_MOCK=true
├── src/
│   ├── main.tsx                      # React root, QueryClientProvider, RouterProvider
│   ├── router.tsx                    # createBrowserRouter — full route table
│   ├── api/
│   │   ├── client.ts                 # Live HTTP implementation
│   │   ├── mock.ts                   # Mock implementation (same signatures)
│   │   └── index.ts                  # Re-exports active implementation based on VITE_USE_MOCK
│   ├── context/
│   │   └── AuthContext.tsx           # AuthProvider, useAuth hook
│   ├── hooks/
│   │   ├── useEmployees.ts
│   │   ├── useRoles.ts
│   │   ├── useDocuments.ts
│   │   ├── useAuditLogs.ts
│   │   └── useSettings.ts
│   ├── components/
│   │   ├── ui/                       # shadcn/ui generated primitives
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── label.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── table.tsx
│   │   │   ├── select.tsx
│   │   │   ├── textarea.tsx
│   │   │   ├── separator.tsx
│   │   │   └── card.tsx
│   │   ├── layout/
│   │   │   ├── AdminLayout.tsx       # AdminSidebar + Outlet + mobile nav
│   │   │   └── EmployeeLayout.tsx    # EmployeeSidebar + Outlet + mobile nav
│   │   ├── navigation/
│   │   │   ├── AdminSidebar.tsx
│   │   │   └── EmployeeSidebar.tsx
│   │   ├── shared/
│   │   │   ├── DataTable.tsx         # Generic sortable table
│   │   │   ├── StatusBadge.tsx       # Color-coded document status pill
│   │   │   ├── DropZone.tsx          # Drag-drop upload with state machine
│   │   │   ├── EmptyState.tsx        # Empty state with icon + message + CTA
│   │   │   ├── LoadingSpinner.tsx    # Centered spinner
│   │   │   ├── ErrorState.tsx        # Error message + retry button
│   │   │   └── ProtectedRoute.tsx    # Auth + role route guard
│   │   └── features/
│   │       ├── auth/
│   │       │   ├── LoginForm.tsx
│   │       │   └── RegisterForm.tsx
│   │       ├── employees/
│   │       │   ├── EmployeeTable.tsx
│   │       │   ├── CreateEmployeeDialog.tsx
│   │       │   └── RoleAssignmentPanel.tsx
│   │       ├── roles/
│   │       │   ├── RoleCard.tsx
│   │       │   └── CreateRoleDialog.tsx
│   │       ├── documents/
│   │       │   ├── DocumentTable.tsx
│   │       │   └── DocumentAccessPanel.tsx
│   │       ├── audit/
│   │       │   └── AuditLogTable.tsx
│   │       └── chat/
│   │           ├── ChatMessage.tsx
│   │           └── ChatInput.tsx
│   ├── pages/
│   │   ├── public/
│   │   │   ├── LandingPage.tsx
│   │   │   ├── LoginPage.tsx
│   │   │   └── RegisterPage.tsx
│   │   ├── admin/
│   │   │   ├── AdminDashboardPage.tsx
│   │   │   ├── EmployeesPage.tsx
│   │   │   ├── EmployeeDetailPage.tsx
│   │   │   ├── RolesPage.tsx
│   │   │   ├── RoleDetailPage.tsx
│   │   │   ├── DocumentsPage.tsx
│   │   │   ├── AuditLogsPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   └── employee/
│   │       ├── EmployeeDashboardPage.tsx
│   │       ├── AskAIPage.tsx
│   │       └── MyDocumentsPage.tsx
│   ├── types/
│   │   └── index.ts                  # All TypeScript interfaces
│   └── lib/
│       ├── utils.ts                  # cn() helper, date formatting
│       ├── queryKeys.ts              # Centralized TanStack Query key factory
│       └── constants.ts             # MAX_FILE_SIZE, ALLOWED_EXTENSIONS, POLL_INTERVAL
```

---

## Complete Route Table

| Path | Layout Component | Auth Guard | Role Guard | Notes |
|---|---|---|---|---|
| `/` | none | redirect if authenticated | redirect to role dashboard | LandingPage |
| `/login` | none | redirect if authenticated | — | LoginPage |
| `/register` | none | redirect if authenticated | — | RegisterPage |
| `/admin/dashboard` | AdminLayout | required | admin only | AdminDashboardPage |
| `/admin/employees` | AdminLayout | required | admin only | EmployeesPage |
| `/admin/employees/:id` | AdminLayout | required | admin only | EmployeeDetailPage |
| `/admin/roles` | AdminLayout | required | admin only | RolesPage |
| `/admin/roles/:id` | AdminLayout | required | admin only | RoleDetailPage |
| `/admin/documents` | AdminLayout | required | admin only | DocumentsPage |
| `/admin/audit-logs` | AdminLayout | required | admin only | AuditLogsPage |
| `/admin/settings` | AdminLayout | required | admin only | SettingsPage |
| `/employee/dashboard` | EmployeeLayout | required | employee only | EmployeeDashboardPage |
| `/employee/ask-ai` | EmployeeLayout | required | employee only | AskAIPage |
| `/employee/my-documents` | EmployeeLayout | required | employee only | MyDocumentsPage |

`ProtectedRoute` covers the authenticated check. `AdminRoute` and `EmployeeRoute` are thin wrappers around `ProtectedRoute` that additionally check the role and redirect when mismatched.

---

## Components and Interfaces

### ProtectedRoute

```tsx
// src/components/shared/ProtectedRoute.tsx
interface ProtectedRouteProps {
  requiredRole?: 'admin' | 'employee'; // undefined = any authenticated user
  children: React.ReactNode;
}
```

Logic:
1. Read `{ user, isLoading }` from `useAuth()`.
2. If `isLoading`, return `<LoadingSpinner />` (avoids redirect flash during token parse).
3. If `!user`, return `<Navigate to="/login" replace />`.
4. If `requiredRole === 'admin'` and `user.role !== 'admin'`, return `<Navigate to="/employee/dashboard" replace />`.
5. If `requiredRole === 'employee'` and `user.role === 'admin'`, return `<Navigate to="/admin/dashboard" replace />`.
6. Otherwise, render `children`.

Public pages (Landing, Login, Register) use a `PublicRoute` wrapper:
1. If `user` exists, redirect to role dashboard.
2. Otherwise render children.

### AdminLayout / EmployeeLayout

Both layouts use the same structure: a persistent sidebar that transitions to a bottom navigation bar on screens narrower than 768px.

```tsx
// AdminLayout renders:
<div className="flex h-screen bg-slate-50">
  <AdminSidebar className="hidden md:flex" />    {/* desktop */}
  <main className="flex-1 overflow-y-auto p-6">
    <Outlet />
  </main>
  <AdminBottomNav className="md:hidden fixed bottom-0 inset-x-0" /> {/* mobile */}
</div>
```

`AdminSidebar` props:
```tsx
interface SidebarProps {
  className?: string;
}
```
No additional props — sidebar reads `useAuth()` internally for user display name and sign-out.

### AdminSidebar

Navigation items (in order, matching Requirement 5.1):
1. Dashboard — `/admin/dashboard` — icon: `LayoutDashboard`
2. Employees — `/admin/employees` — icon: `Users`
3. Roles — `/admin/roles` — icon: `Shield`
4. Documents — `/admin/documents` — icon: `FileText`
5. Audit Logs — `/admin/audit-logs` — icon: `ClipboardList`
6. Settings — `/admin/settings` — icon: `Settings`

Active link detection: `useMatch` or compare `location.pathname` with each path. Active item gets `bg-indigo-50 text-indigo-600 font-medium`; inactive items get `text-slate-600 hover:bg-slate-100`.

User display block at sidebar bottom:
- Avatar circle with first letter of name/email in indigo.
- Full name (or email fallback) in `font-medium text-sm`.
- "Admin" label in `text-xs text-slate-500`.
- Sign-out button inline; calls `auth.logout()`.

### EmployeeSidebar

Navigation items (in order, matching Requirement 14.1):
1. Dashboard — `/employee/dashboard` — icon: `Home`
2. Ask AI — `/employee/ask-ai` — icon: `MessageSquare`
3. My Documents — `/employee/my-documents` — icon: `FolderOpen`

User display block: full name or email, all assigned role names as comma-separated text in `text-xs text-slate-500`.

### DataTable

Generic table component. Avoids re-implementing table boilerplate in every page.

```tsx
interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (row: T) => React.ReactNode; // custom cell renderer
  className?: string;                   // per-column width/alignment
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  emptyMessage?: string;
  isLoading?: boolean;
  className?: string;
}
```

Implementation notes:
- Wraps in `<div className="overflow-x-auto">` for horizontal scroll on mobile.
- When `isLoading`, renders 5 skeleton rows (`animate-pulse bg-slate-200 h-4 rounded`).
- When `data.length === 0` and not loading, renders a centered `emptyMessage` spanning all columns.

### StatusBadge

```tsx
type DocumentStatus = 'UPLOADED' | 'PROCESSING' | 'READY' | 'FAILED';

interface StatusBadgeProps {
  status: DocumentStatus;
}
```

Color mapping:
- `UPLOADED` → `bg-slate-100 text-slate-600`
- `PROCESSING` → `bg-amber-100 text-amber-700`
- `READY` → `bg-emerald-100 text-emerald-700`
- `FAILED` → `bg-red-100 text-red-700`

### DropZone

See the dedicated DropZone Design section below.

### EmptyState

```tsx
interface EmptyStateProps {
  icon?: React.ReactNode;            // defaults to InboxIcon
  title: string;                     // e.g. "No documents yet"
  description?: string;              // explanatory sentence
  action?: {
    label: string;
    onClick: () => void;
  };
}
```

### LoadingSpinner

```tsx
interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';   // sm=16px, md=24px, lg=40px
  className?: string;
  label?: string;                // sr-only accessible label, defaults to "Loading…"
}
```

### ErrorState

```tsx
interface ErrorStateProps {
  title?: string;              // defaults to "Something went wrong"
  description?: string;        // human-readable description, no stack traces
  onRetry?: () => void;        // if provided, shows Retry button
  retryLabel?: string;         // defaults to "Try again"
}
```

---

## Data Models

All TypeScript interfaces mirror the FastAPI Pydantic schemas exactly. They live in `src/types/index.ts`.

```typescript
// ── Auth ──────────────────────────────────────────────────────────────────
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
  confirm_password: string;
  account_type: 'employee'; // frontend always sends "employee"
}

export interface UserAuthResponse {
  id: string;
  email: string;
  role: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
  user: UserAuthResponse;
}

export interface RegisterResponse {
  message: string;
  user: UserAuthResponse;
}

// ── JWT Decoded Payload ────────────────────────────────────────────────────
// Decoded client-side using atob(); never re-verified client-side.
export interface JwtPayload {
  user_id: string;
  sub: string;
  email: string;
  role: string;   // "admin" | "employee" | custom role name
  exp: number;    // Unix timestamp seconds
  iat: number;
}

// ── RBAC ──────────────────────────────────────────────────────────────────
export interface RoleResponse {
  id: string;
  name: string;
}

export interface UserResponse {
  id: string;
  username: string;
  roles: RoleResponse[];
}

// ── Employees (extended from UserResponse for admin UI) ───────────────────
// The backend /api/users endpoint returns UserResponse.
// The admin UI adds derived/display fields locally:
export interface Employee {
  id: string;
  name: string;          // sourced from User.name, falls back to username
  username: string;
  email: string;
  roles: RoleResponse[];
  status: 'Active' | 'Inactive';
}

// ── Documents ─────────────────────────────────────────────────────────────
export type DocumentStatus = 'UPLOADED' | 'PROCESSING' | 'READY' | 'FAILED';

export interface DocumentResponse {
  id: string;
  filename: string;
  file_size: number;      // bytes
  chunk_count: number;
  status: DocumentStatus;
  uploaded_at: string;    // "YYYY-MM-DD HH:MM"
  uploaded_by: string | null;
  accessible_roles: string[];
}

export interface DocumentAccessUpdateRequest {
  allowed_roles: string[];
}

// ── Query / Ask AI ────────────────────────────────────────────────────────
export interface QueryRequest {
  query: string;
}

export interface SourceCitation {
  document_id: string;
  filename: string;
  page: number | null;
  chunk_id: string;
  relevance_score: number;
}

export interface QueryResponse {
  query: string;
  answer: string;
  sources: SourceCitation[];
  grounded: boolean;
  retrieved_chunk_count: number;
}

// ── Audit Logs ────────────────────────────────────────────────────────────
// Backend does not yet expose an /audit-logs endpoint in the provided code.
// The frontend mock defines this shape; live wiring requires adding the endpoint.
export type AuditAction = 'created' | 'updated' | 'deleted';

export interface AuditLogEntry {
  id: string;
  action: AuditAction;
  resource_type: string;  // "employee" | "role" | "document"
  resource_name: string;
  performed_by: string;   // admin name or email
  timestamp: string;      // ISO 8601
}

// ── Settings ──────────────────────────────────────────────────────────────
export interface OrgSettings {
  organization_name: string;
}

// ── Chat (client-only) ────────────────────────────────────────────────────
export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;             // crypto.randomUUID()
  role: ChatRole;
  content: string;
  sources?: SourceCitation[];
  grounded?: boolean;
  isLoading?: boolean;    // true while awaiting response
  isError?: boolean;      // true if request failed
  originalQuery?: string; // stored for retry
}
```

---

## API Isolation Layer

### src/api/index.ts

```typescript
// Selects implementation based on VITE_USE_MOCK env var.
// In production builds, tree-shaking removes the mock module.
const useMock = import.meta.env.VITE_USE_MOCK === 'true';

export * from useMock ? './mock' : './client';
```

> **Important:** Both `client.ts` and `mock.ts` export the exact same function names with the exact same TypeScript signatures. Adding a new endpoint requires updating both files.

### src/api/client.ts — Function Signatures

```typescript
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function authHeader(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  isFormData?: boolean,
): Promise<T>

// ── Auth ──────────────────────────────────────────────────────────────────
export async function login(data: LoginRequest): Promise<TokenResponse>
export async function register(data: RegisterRequest): Promise<RegisterResponse>
export async function getMe(): Promise<UserAuthResponse>

// ── Employees (RBAC users) ────────────────────────────────────────────────
export async function listEmployees(): Promise<UserResponse[]>
export async function createEmployee(username: string): Promise<UserResponse>
export async function assignRoleToEmployee(userId: string, roleId: string): Promise<UserResponse>
export async function removeRoleFromEmployee(userId: string, roleId: string): Promise<UserResponse>

// ── Roles ─────────────────────────────────────────────────────────────────
export async function listRoles(): Promise<RoleResponse[]>
export async function createRole(name: string): Promise<RoleResponse>

// ── Documents ─────────────────────────────────────────────────────────────
export async function listDocuments(): Promise<DocumentResponse[]>
export async function uploadDocument(
  file: File,
  allowedRoles: string[],
): Promise<DocumentResponse>
export async function getDocument(id: string): Promise<DocumentResponse>
export async function updateDocumentAccess(
  id: string,
  data: DocumentAccessUpdateRequest,
): Promise<DocumentResponse>
export async function deleteDocument(id: string): Promise<{ message: string; id: string }>

// ── Audit Logs ────────────────────────────────────────────────────────────
export async function listAuditLogs(): Promise<AuditLogEntry[]>

// ── Settings ──────────────────────────────────────────────────────────────
export async function getSettings(): Promise<OrgSettings>
export async function updateSettings(data: OrgSettings): Promise<OrgSettings>

// ── Query ─────────────────────────────────────────────────────────────────
export async function queryRAG(data: QueryRequest): Promise<QueryResponse>
```

### Error Handling in client.ts

The `request<T>` helper:
1. Performs `fetch(BASE_URL + path, { method, headers: { 'Content-Type': 'application/json', ...authHeader() }, body })`.
2. If `response.ok` is false, reads JSON body and throws `ApiError`:
   ```typescript
   class ApiError extends Error {
     constructor(
       public status: number,
       public detail: string,
     ) { super(detail); }
   }
   ```
3. Components catch `ApiError` and display `error.detail` (already human-readable from the backend). They never display `error.message` from raw `Error` (which may contain stack info).

For `uploadDocument`, uses `FormData` with `Content-Type` header removed (browser sets multipart boundary automatically).

### src/api/mock.ts

Provides the same exported functions backed by in-memory data. Simulates network delay with `await delay(300)`. Simulates document ingestion state machine: after upload, the document status transitions `UPLOADED → PROCESSING` after 1s → `READY` after 4s (allowing polling tests). Data is held in `const mockStore` module-level variables so mutations persist within a session.

---

## AuthContext

### Shape

```typescript
// src/context/AuthContext.tsx

interface AuthUser {
  id: string;
  email: string;
  role: string;         // "admin" | "employee" | custom
  name?: string;        // not in JWT; fetched from /auth/me after login
  exp: number;          // from JWT exp claim
}

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;   // true only during initial token parse on mount
  login: (token: TokenResponse) => void;
  logout: () => void;
}
```

### Token Storage

Token is stored as a plain string under key `"access_token"` in `localStorage`. On `login()`:
1. `localStorage.setItem('access_token', tokenResponse.access_token)`.
2. Decode the JWT payload (base64 decode the middle segment; no signature verification client-side) to extract `{ user_id, email, role, exp }`.
3. Set `user` state.

### JWT Decode (client-side, no library required)

```typescript
function decodeJwt(token: string): JwtPayload {
  const [, payloadB64] = token.split('.');
  const json = atob(payloadB64.replace(/-/g, '+').replace(/_/g, '/'));
  return JSON.parse(json) as JwtPayload;
}
```

No JWT library needed — the client only reads the payload, not verifies it. The backend verifies on every authenticated request.

### Expiry Detection

`AuthProvider` sets up a `useEffect` that:
1. On mount: reads `localStorage.getItem('access_token')`.
2. If token exists, decodes it and checks `payload.exp * 1000 > Date.now()`.
3. If expired: calls `logout()` immediately.
4. If valid: sets `user` and schedules a `setTimeout` for `(exp * 1000 - Date.now() - 60_000)` ms that calls `logout()` (1 minute early warning buffer). Cleans up on unmount.
5. Sets `isLoading = false` after the check regardless.

### logout()

```typescript
function logout() {
  localStorage.removeItem('access_token');
  setUser(null);
  // Navigation is handled by ProtectedRoute rendering <Navigate to="/login" />
  // Do not call navigate() here — context should not know about routing.
}
```

---

## TanStack Query Usage

### Query Client Configuration (src/main.tsx)

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,       // 30s — data stays fresh for 30s before background refetch
      gcTime: 5 * 60_000,      // 5min — inactive cache entries kept for 5 min
      retry: 1,                // one automatic retry on failure
      refetchOnWindowFocus: true,
    },
  },
});
```

### Query Key Factory (src/lib/queryKeys.ts)

```typescript
export const queryKeys = {
  employees: {
    all: ['employees'] as const,
    detail: (id: string) => ['employees', id] as const,
  },
  roles: {
    all: ['roles'] as const,
    detail: (id: string) => ['roles', id] as const,
  },
  documents: {
    all: ['documents'] as const,
    detail: (id: string) => ['documents', id] as const,
  },
  auditLogs: {
    all: ['auditLogs'] as const,
  },
  settings: {
    all: ['settings'] as const,
  },
  me: ['me'] as const,
} as const;
```

### Per-Feature Query Configuration

| Hook | Query Key | staleTime override | Notes |
|---|---|---|---|
| `useEmployees` | `queryKeys.employees.all` | default 30s | |
| `useEmployee(id)` | `queryKeys.employees.detail(id)` | default 30s | |
| `useRoles` | `queryKeys.roles.all` | default 30s | Used by multiple pages; shared cache |
| `useDocuments` | `queryKeys.documents.all` | default 30s | |
| `useDocument(id)` | `queryKeys.documents.detail(id)` | `5_000` (5s) | Used for upload polling |
| `useAuditLogs` | `queryKeys.auditLogs.all` | `0` (always fresh) | Audit logs should show latest |
| `useSettings` | `queryKeys.settings.all` | default 30s | |

### Invalidation Strategy After Mutations

All mutations call `queryClient.invalidateQueries` in their `onSuccess` callback:

| Mutation | Invalidates |
|---|---|
| `createEmployee` | `queryKeys.employees.all` |
| `assignRole` / `removeRole` | `queryKeys.employees.all`, `queryKeys.employees.detail(id)`, `queryKeys.roles.all` |
| `createRole` | `queryKeys.roles.all` |
| `uploadDocument` | `queryKeys.documents.all` |
| `updateDocumentAccess` | `queryKeys.documents.all`, `queryKeys.documents.detail(id)` |
| `deleteDocument` | `queryKeys.documents.all` |
| `updateSettings` | `queryKeys.settings.all` |

### Upload Polling

After a successful upload, the `DropZone` component (or `DocumentsPage`) uses a polling query:

```typescript
const { data: doc } = useQuery({
  queryKey: queryKeys.documents.detail(uploadedDocId),
  queryFn: () => api.getDocument(uploadedDocId),
  enabled: !!uploadedDocId && uploadStatus === 'polling',
  refetchInterval: (query) => {
    const status = query.state.data?.status;
    if (status === 'READY' || status === 'FAILED') return false; // stop polling
    if (pollingElapsed > 10 * 60_000) return false;              // 10min cap
    return 5_000;                                                // 5s interval
  },
  staleTime: 0,
});
```

---

## DropZone Design

### State Machine

```
idle ──── drag-enter ──── drag-over
 │                            │
 │         drag-leave ────────┘
 │
 ├── file-selected (via input click) ──┐
 │                                     │
 └── file-dropped (via drag)  ─────────┤
                                        ▼
                                  [validate file]
                                  type + size check
                                     /       \
                              invalid         valid
                                 │               │
                              show error      uploading
                                             (POST to API)
                                               /     \
                                          error      success
                                             │           │
                                          show error   polling
                                                       (GET /documents/:id every 5s)
                                                         /      \
                                                      error    done (READY|FAILED)
                                                         │           │
                                                      show error  show status badge
```

TypeScript state type:
```typescript
type UploadState =
  | { phase: 'idle' }
  | { phase: 'dragOver' }
  | { phase: 'validationError'; message: string }
  | { phase: 'uploading'; filename: string }
  | { phase: 'polling'; docId: string; filename: string; elapsed: number }
  | { phase: 'done'; doc: DocumentResponse }
  | { phase: 'error'; message: string };
```

### Drag Event Handlers

```typescript
// Prevent browser default (opens file) on all drag events
onDragEnter: (e) => { e.preventDefault(); e.stopPropagation(); setState({ phase: 'dragOver' }); }
onDragOver:  (e) => { e.preventDefault(); e.stopPropagation(); }
onDragLeave: (e) => { e.preventDefault(); e.stopPropagation(); setState({ phase: 'idle' }); }
onDrop:      (e) => { e.preventDefault(); e.stopPropagation(); handleFiles(e.dataTransfer.files); }
```

Counter-based drag-over tracking: `dragCounter` ref increments on `dragEnter` and decrements on `dragLeave` to avoid false `dragLeave` triggers when cursor passes over child elements.

### File Validation

```typescript
const ALLOWED_EXTENSIONS = ['.pdf', '.txt', '.docx', '.doc', '.md', '.csv', '.json'];
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB

function validateFile(file: File): string | null {
  const ext = '.' + file.name.split('.').pop()?.toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(ext))
    return `File type "${ext}" is not supported. Accepted types: ${ALLOWED_EXTENSIONS.join(', ')}.`;
  if (file.size > MAX_FILE_SIZE)
    return `File is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum size is 50 MB.`;
  return null;
}
```

### Props

```typescript
interface DropZoneProps {
  onUploadComplete: (doc: DocumentResponse) => void;
  availableRoles: RoleResponse[];        // for role assignment during upload
  className?: string;
}
```

After upload completes (state `done`), calls `onUploadComplete` so the parent page can invalidate the documents query and show the new row.

The component renders a hidden `<input type="file" accept=".pdf,.txt,.docx,.doc,.md,.csv,.json" />` triggered by clicking the zone. The visible zone is a `<div>` with `role="button"` and `tabIndex={0}` for keyboard accessibility (Enter/Space triggers the hidden input). Minimum touch target: full drop zone area, at least 44px tall on mobile.

---

## AskAI Chat Design

### Message State

```typescript
// AskAIPage.tsx — local state only, not persisted across page navigation
const [messages, setMessages] = useState<ChatMessage[]>([]);
const [input, setInput] = useState('');
const [isSubmitting, setIsSubmitting] = useState(false);
```

Message array is session-scoped (lives in component state). It resets when the component unmounts. No persistence to localStorage is implemented — this is by design per Requirement 16.2 ("current browser session").

### Submit Handler

```typescript
async function handleSubmit() {
  const query = input.trim();
  if (!query || isSubmitting) return;

  const userMessage: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: query };
  const loadingMessage: ChatMessage = {
    id: crypto.randomUUID(),
    role: 'assistant',
    content: '',
    isLoading: true,
    originalQuery: query,
  };

  setMessages(prev => [...prev, userMessage, loadingMessage]);
  setInput('');
  setIsSubmitting(true);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30_000); // 30s timeout

  try {
    const result = await api.queryRAG({ query }, controller.signal);
    clearTimeout(timeoutId);
    setMessages(prev =>
      prev.map(m =>
        m.id === loadingMessage.id
          ? {
              ...m,
              isLoading: false,
              content: result.answer,
              sources: result.sources,
              grounded: result.grounded,
            }
          : m,
      ),
    );
  } catch (err) {
    clearTimeout(timeoutId);
    const isTimeout = err instanceof DOMException && err.name === 'AbortError';
    setMessages(prev =>
      prev.map(m =>
        m.id === loadingMessage.id
          ? {
              ...m,
              isLoading: false,
              isError: true,
              content: isTimeout
                ? 'The request timed out after 30 seconds.'
                : 'Something went wrong. Please try again.',
              originalQuery: query,
            }
          : m,
      ),
    );
  } finally {
    setIsSubmitting(false);
  }
}
```

### Retry Handler

The `ChatMessage` component renders a "Retry" button when `message.isError === true`. Clicking it calls `handleRetry(message.originalQuery)`:

```typescript
function handleRetry(query: string) {
  // Remove the failed assistant message, then re-submit the same query.
  setMessages(prev => prev.filter(m => m.id !== failedMessageId));
  handleSubmitWith(query);
}
```

### Source Citation Rendering

`ChatMessage` renders the assistant bubble. Below the answer text:

```tsx
{message.sources && message.sources.length > 0 ? (
  <div className="mt-2 text-xs text-slate-500">
    <p className="font-medium mb-1">Sources:</p>
    {message.sources.map(s => (
      <div key={s.chunk_id} className="flex items-center gap-1">
        <FileText className="w-3 h-3" />
        <span>{s.filename}</span>
        {s.page && <span className="text-slate-400">· page {s.page}</span>}
      </div>
    ))}
  </div>
) : (
  <p className="mt-2 text-xs text-slate-400 italic">No sources cited.</p>
)}
{message.grounded === false && (
  <p className="mt-1 text-xs text-amber-600">
    This answer may not be based on your authorized documents.
  </p>
)}
```

Auto-scroll: a `messagesEndRef` div at the bottom of the message list, scrolled into view via `useEffect` when `messages` changes.

Max input length enforced via `maxLength={2000}` on the textarea and character counter display `{input.length}/2000`.

---

## Page Specifications

### LandingPage (`/`)

Structure (top to bottom):
1. **Header bar** — logo (shield icon from lucide-react `ShieldCheck`, colored indigo-600) + "SecureRAG" text + right-aligned "Sign In" button.
2. **Hero section** — centered, `max-w-3xl mx-auto`:
   - H1: "SecureRAG" (large, font-bold)
   - Tagline (≤15 words): "Enterprise document intelligence with access controls your organization can trust."
   - Two CTA buttons: primary "Get Started" → `/register`, secondary outlined "Sign In" → `/login`.
3. **Features section** — three cards in a responsive grid (`grid-cols-1 md:grid-cols-3`):
   - Card 1: icon `Lock`, title "Role-Based Access", description in plain English.
   - Card 2: icon `FileSearch`, title "Secure Document Retrieval", description in plain English.
   - Card 3: icon `MessageSquare`, title "AI-Powered Knowledge Search", description in plain English.
4. **Footer** — "© 2025 SecureRAG".

No animations longer than 400ms. No looping animations. No vector/RBAC/embedding terminology visible anywhere.

### LoginPage (`/login`)

Centered card layout (`max-w-md mx-auto mt-20`):
- Logo + "SecureRAG" heading.
- Email input (type=email, autocomplete=email).
- Password input (type=password, autocomplete=current-password).
- Submit button "Sign In" — disabled while `isLoading`.
- Inline error below the form (not inside a toast) for 401 and network errors.
- Link to `/register` ("Don't have an account? Get started").
- Form validation: non-empty email and password before any network call. Inline error message below the field that fails.

On successful login: store token → decode role → navigate to `/admin/dashboard` or `/employee/dashboard`.

### RegisterPage (`/register`)

Same centered card layout:
- Full Name input.
- Email input.
- Password input with length requirement text ("At least 6 characters").
- Confirm Password input.
- No role selector, no admin key field — employee account only (Requirement 3.3).
- Submit button "Create Account" — disabled while `isLoading`.
- Inline validation errors per field.
- On 409: "An account with this email already exists."
- On other errors: "Registration failed. Please try again."
- On success: display success message "Your account has been created. Please sign in." then navigate to `/login` after 2s (or immediately if user clicks "Sign In" link shown alongside message).

### AdminDashboardPage

Four metric cards row (responsive: 2×2 on mobile, 1×4 on desktop):
- Total Employees — count from employees query.
- Total Roles — count from roles query.
- Total Documents — count from documents query.
- Processing — count of documents where `status === 'PROCESSING'`.

Metric card structure:
```tsx
<Card>
  <CardContent className="pt-6">
    <p className="text-3xl font-bold text-indigo-600">{count}</p>
    <p className="text-sm text-slate-500 mt-1">{label}</p>
  </CardContent>
</Card>
```

Recent activity section below: "Recent Activity" heading + table of the 10 most recent audit log entries (action, resource, performed by, timestamp). Uses `DataTable` component. Loading skeleton while queries are in-flight.

No technical terms (no "vector chunks", "embeddings", "ChromaDB") — Requirement 6.6.

### EmployeesPage

Above table: "Employees" heading + "Add Employee" button (opens `CreateEmployeeDialog`).

`CreateEmployeeDialog` fields: Full Name, Email. On submit calls `createEmployee` mutation; on success closes dialog and invalidates employees query. Backend `/api/users` currently only accepts `username` — the frontend generates `username` from `email.split('@')[0]` and sends `name` in a separate field or as part of the username. **Note for wiring:** the backend `POST /api/users` body only has `username`. The admin UI should be designed so the initial create captures name+email, and the frontend constructs the username from the email prefix. If the backend is extended to accept `name`/`email`, update the `createEmployee` API function accordingly. For the mock layer, the full `Employee` shape (with `name`, `email`, `status`) is returned.

Table columns: Name | Employee ID (truncated UUID) | Email | Assigned Roles (comma-separated badges) | Status (`Active`/`Inactive` badge) | Actions (View button).

Row action "View" → `navigate('/admin/employees/' + id)`.

Empty state: `<EmptyState title="No employees yet" description="Add your first employee to get started." action={{ label: 'Add Employee', onClick: openDialog }} />`.

### EmployeeDetailPage

Breadcrumb: "Employees > {name}".

Profile card: name, ID, email, status badge, roles list. "No roles assigned" message when empty.

Two actions below profile:
1. **Add Role** — a `<Select>` populated with roles not yet assigned to this employee. "Assign" button calls `assignRoleToEmployee`. If no unassigned roles exist, shows "All available roles are already assigned."
2. **Remove Role** — each assigned role has an `×` button. Clicking calls `removeRoleFromEmployee`.

Both mutations optimistically update or invalidate `queryKeys.employees.detail(id)` and `queryKeys.employees.all`.

Deactivate employee: "Deactivate" button (red outlined) → confirmation dialog → calls `deactivateEmployee` mutation → employee status becomes "Inactive". The activate/deactivate action is not currently in the backend RBAC endpoint; the mock implements it, and the live endpoint call should be wired to a dedicated endpoint when available.

### RolesPage

Heading + "Create Role" button (opens `CreateRoleDialog`).

Grid of `RoleCard` components (responsive: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`).

`RoleCard` shows:
- Role name (bold).
- Employee count: "N employee(s)".
- Documents: list of document filenames, or "No documents assigned".
- "View Details" link → `/admin/roles/:id`.

`CreateRoleDialog`: single text input for role name (1–50 chars). On 400 conflict: "A role with that name already exists."

### RoleDetailPage

Breadcrumb: "Roles > {name}".

Two sections side by side on desktop, stacked on mobile:
1. **Assigned Employees** — list of employee names with "Remove" option.
2. **Accessible Documents** — list of document filenames. "No documents assigned" empty state.

### DocumentsPage

Heading + `DropZone` at top.

Below: `DocumentTable` — columns: Filename | Upload Date | Status (`StatusBadge`) | Assigned Roles | Actions.

Actions per row: "Edit Access" (opens `DocumentAccessPanel` dialog) | "Delete" (confirmation dialog → `deleteDocument` mutation).

`DocumentAccessPanel`: multi-select of available roles (checkboxes) for the document. Submit calls `updateDocumentAccess`. Removing the last role shows a confirmation: "This document will have no assigned roles and will not be accessible to any employees. Continue?"

### AuditLogsPage

`DataTable` with columns: Action (badge colored by type) | Resource | Performed By | Time (relative + absolute on hover).

Loads up to 500 entries. No filter UI is required by the requirements. Empty state: "No audit log entries yet."

### SettingsPage

`<Card>` with form:
- Organization Name: text input, maxLength=100, required.
- "Save Changes" button.
- Success message: "Settings saved." shown for 3s then hidden.
- Error: "Failed to save settings. Your previous values have been restored."

Form is pre-populated from `useSettings` query.

### EmployeeDashboardPage

Welcome section: "Welcome back, {name}" heading.

Profile card:
- Name, Employee ID, assigned roles as badges.
- Accessible document count (derived by filtering documents where `accessible_roles` intersects employee's role names).

Recent documents section: 5 most recent accessible documents by `uploaded_at` descending. Each row: filename + date formatted `YYYY-MM-DD`. "Available" badge. No role list, no admin metadata.

Empty state when no accessible documents: "No documents are currently available to you. Contact your administrator to request access."

### AskAIPage

Two-column layout on desktop (chat history | input area); single column on mobile.

Top of page: empty state when `messages.length === 0`: icon `MessageSquare`, "Ask a question to get started. Your answers will be sourced from your authorized documents."

Message list: scrollable `div` with `overflow-y-auto flex-1`. Each message is a `ChatMessage` bubble — user messages right-aligned with `bg-indigo-600 text-white` bubble, assistant messages left-aligned with `bg-white border border-slate-200` bubble.

Loading indicator inside the assistant bubble: three animated dots (`animate-bounce` with staggered delays).

Bottom: sticky input area — `<textarea>` (rows=2, resizable, maxLength=2000) + character counter + "Send" button (disabled when empty or `isSubmitting`). Enter to submit, Shift+Enter for newline.

No technical terms visible — Requirement 16.11 prohibits "top-k", "distance threshold", "temperature", model names, embedding model names, vector database names.

### MyDocumentsPage

Heading: "My Documents".

Loads all documents, then client-side filters: `status === 'READY'` AND `doc.accessible_roles` intersects the employee's role names.

Table columns: Filename | Upload Date (YYYY-MM-DD) | Status ("Available" badge always, since only READY docs shown).

Empty state: "No documents are currently available to you. Your administrator assigns documents to roles, which are then granted to your account."

---

## Design Tokens

### Typography

```css
/* tailwind.config.ts */
fontFamily: {
  sans: ['Inter', 'system-ui', 'sans-serif'],
}
```

Load Inter via Google Fonts in `index.html`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
```

Type scale (Tailwind classes in use):
- Display: `text-3xl font-bold` (hero heading)
- H1: `text-2xl font-semibold`
- H2: `text-xl font-semibold`
- H3: `text-lg font-medium`
- Body: `text-sm` (Tailwind default 14px)
- Caption: `text-xs text-slate-500`

Two typefaces total: Inter (primary) + monospace system font for IDs/codes only.

### Color Palette

Single accent color: **Indigo-600** (`#4F46E5`).

```
Accent:       indigo-600  #4F46E5   (buttons, active nav, key numbers)
Accent light: indigo-50   #EEF2FF   (active nav background)
Accent hover: indigo-700  #4338CA   (button hover)

Neutral base: slate-50    #F8FAFC   (page background)
Surface:      white                 (cards, sidebar)
Border:       slate-200   #E2E8F0
Text primary: slate-900   #0F172A
Text muted:   slate-500   #64748B
Text subtle:  slate-400   #94A3B8

Success:      emerald-600 #059669
Warning:      amber-600   #D97706
Error:        red-600     #DC2626
```

No gradients. No shadow more complex than `shadow-sm`. No looping animations.

### Spacing Scale

Follows Tailwind's default 4px base scale. Key values:
- Page padding: `p-6` (24px) on desktop, `p-4` (16px) on mobile.
- Card padding: `p-6`.
- Form field gap: `gap-4` (16px).
- Section gap: `gap-6` (24px).

### Border Radius

`rounded-lg` (8px) for cards and dialogs. `rounded-md` (6px) for inputs and buttons. `rounded-full` for badges and avatars.

### Sidebar Width

`w-64` (256px) on desktop. Collapses to bottom navigation (full-width, 56px tall) on mobile (`md` breakpoint, 768px).

### Touch Target

All interactive elements: minimum `min-h-[44px] min-w-[44px]`. Applied via:
- Buttons: `h-11` or `h-10 px-4` (≥40px, acceptable per WCAG 2.5.5 at 44×44px on links/buttons with padding).
- Nav items: `py-3 px-4` ensuring at least 44px height.
- Bottom nav icons: `p-3` on 24px icons = 48px total.

---

## Responsive Strategy

### Breakpoints

| Name | Min Width | Notes |
|---|---|---|
| `sm` | 640px | Single-column adjustments |
| `md` | 768px | Sidebar appears; bottom nav hides |
| `lg` | 1024px | Multi-column grids expand |

### Sidebar ↔ Bottom Nav

`AdminLayout`:
```tsx
{/* Desktop sidebar — hidden below md */}
<AdminSidebar className="hidden md:flex w-64 flex-shrink-0" />

{/* Mobile bottom nav — hidden at md and above */}
<AdminBottomNav className="md:hidden" />
```

`AdminBottomNav` shows icons only (no text labels) for the 6 admin sections. Active icon colored indigo-600.

### Tables

All `DataTable` instances are wrapped in `<div className="overflow-x-auto">`. Tables use `whitespace-nowrap` on cells that should not wrap (IDs, dates).

### Dialogs

`<Dialog>` (shadcn/ui) is full-screen on mobile (`max-w-full mx-0 rounded-none`) and normal modal on desktop.

### Forms

Inputs are `w-full`. Two-column form layouts on desktop use `grid grid-cols-1 md:grid-cols-2 gap-4`.

---

## Empty / Loading / Error State Patterns

Each page follows this consistent pattern:

```tsx
function SomePage() {
  const { data, isLoading, isError, refetch } = useQuery({...});

  if (isLoading) return <LoadingSpinner label="Loading employees…" />;
  if (isError) return (
    <ErrorState
      description="Failed to load employees."
      onRetry={refetch}
    />
  );
  if (!data || data.length === 0) return (
    <EmptyState
      title="No employees yet"
      description="Add your first employee to get started."
      action={{ label: 'Add Employee', onClick: openCreateDialog }}
    />
  );

  return <DataTable columns={columns} data={data} />;
}
```

Page-specific empty state copy:

| Page | Empty Title | Empty Description |
|---|---|---|
| Employees | "No employees yet" | "Add your first employee to get started." |
| Roles | "No roles yet" | "Create your first role to control document access." |
| Documents | "No documents yet" | "Upload a document to make it available for search." |
| Audit Logs | "No activity recorded" | "Administrative actions will appear here." |
| My Documents | "No documents available" | "Contact your administrator to request access to documents." |
| Ask AI | "Ask a question" | "Your answers will be sourced from your authorized documents." |
| Employee Detail — No Roles | "No roles assigned" | "Assign a role to grant this employee access to documents." |

Page-specific error state copy (description):

| Page | Error Description |
|---|---|
| Employees | "Failed to load employee list. Check your connection and try again." |
| Roles | "Failed to load roles." |
| Documents | "Failed to load documents." |
| Audit Logs | "Failed to load audit logs." |
| Settings | "Failed to load settings. Your changes have not been saved." |
| My Documents | "Failed to load your documents." |
| Employee Dashboard | "Failed to load your profile." |
| Ask AI (query error) | "Something went wrong. Please try again." |
| Ask AI (timeout) | "The request timed out after 30 seconds." |

---

## Error Handling

### API Error Classification

| HTTP Status | User-visible message |
|---|---|
| 400 | Show `error.detail` from backend (e.g., "Role 'foo' is invalid") |
| 401 | "Your session has expired. Please sign in again." → logout |
| 403 | "You do not have permission to perform this action." |
| 404 | "The requested item was not found." |
| 409 | Show `error.detail` from backend (e.g., "An account with this email already exists") |
| 422 | Show `error.detail` from backend (validation error) |
| 5xx | "A server error occurred. Please try again later." |
| Network error | "Unable to connect. Check your internet connection and try again." |

The `request<T>` function in `client.ts` maps all error responses to `ApiError` with `status` and `detail`. Components catch `ApiError` specifically; a plain `Error` from network failure is caught separately and shows the connectivity message.

### 401 Interceptor

`AuthContext` or a wrapper inside `client.ts` detects 401 responses globally. On 401:
1. Call `auth.logout()`.
2. Navigation to `/login` is handled by `ProtectedRoute` re-rendering after `user` becomes null.

Implemented as a wrapper around `request<T>`:
```typescript
if (response.status === 401) {
  // Dispatch a custom event so AuthContext can react
  window.dispatchEvent(new CustomEvent('auth:expired'));
  throw new ApiError(401, 'Session expired.');
}
```
`AuthContext` listens for `'auth:expired'` and calls `logout()`.

### Form Validation

Client-side validation runs on submit (not on blur, to avoid premature errors). Fields are validated in order; only the first error per field is shown. Inline error messages appear below the field in `text-sm text-red-600`.

Validation rules:
- Email: `/.+@.+\..+/` (Requirement 3.9).
- Password: length 6–128 (Requirement 3.5).
- Confirm Password: must equal Password (Requirement 3.4).
- Role name: 1–50 chars (Requirement 9.2).
- Org name: 1–100 chars (Requirement 13.2).
- Chat input: 1–2000 chars (Requirement 16.1).

---

## Testing Strategy

### Dual Testing Approach

The feature uses two complementary layers:
- **Unit tests**: Verify specific behaviors with concrete examples — form validation, route guard redirects, date formatting, status badge colors.
- **Property-based tests**: Verify universal properties that hold across all valid inputs — see Correctness Properties section.

### Unit Test Coverage

Key unit tests (Vitest + React Testing Library):

1. `ProtectedRoute` — renders children when authenticated with correct role; redirects when unauthenticated; redirects employee accessing admin route.
2. `AuthContext` — `decodeJwt` correctly extracts role and exp; expired token triggers logout; valid token sets user state.
3. `validateFile` — accepts valid extensions; rejects unsupported extensions; rejects file > 50MB; accepts file exactly at 50MB.
4. `LoginForm` — submit disabled with empty fields; shows error on 401; navigates on success.
5. `RegisterForm` — password mismatch shows inline error; 409 shows conflict message; success shows confirmation.
6. `DataTable` — renders skeleton rows during loading; renders empty message when data empty; renders all rows when data provided.
7. `StatusBadge` — correct color class for each status variant.
8. `ChatMessage` — shows sources section when sources present; shows "No sources cited" when empty; shows ungrounded warning when `grounded === false`.
9. Query key factory — each key function returns a stable array identity.

### Integration Tests

- Mock Service Worker (MSW) for API layer: intercept fetch calls in tests, return mock JSON matching `DocumentResponse`, `TokenResponse`, etc.
- Test page-level data fetching: `DocumentsPage` calls `GET /admin/documents` and renders returned data.

### Property-Based Testing

See Correctness Properties section below.

### PBT Library

**fast-check** — TypeScript-native property-based testing library.

```bash
npm install --save-dev fast-check
```

Each property test runs minimum 100 iterations (`numRuns: 100`). Test files are co-located with tested modules under `__tests__/`.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

