features/auth/
├── api/
│ └── auth-api.ts
├── components/
│ ├── login-form.tsx
│ ├── register-form.tsx
│ └── session-expired.tsx
├── context/
│ └── auth-provider.tsx
├── hooks/
│ └── use-auth.ts
├── schemas/
│ └── auth-schemas.ts
├── types/
│ └── auth-types.ts
└── index.ts

layouts/auth-layout.tsx
routes/login-route.tsx
routes/register-route.tsx

Ordem de construção:
Criar validações de email, senha e nome com Zod. F

Criar as funções HTTP de cadastro, login, refresh, logout e /auth/me. F

Criar AuthProvider para manter usuário, access token e estado da sessão em memória. F

Restaurar a sessão ao abrir o site: usar o refresh cookie e depois buscar /auth/me. F

Construir formulário e rota de cadastro. F

Construir formulário e rota de login. F

Criar proteção para /app, redirecionando usuários não autenticados. F

Implementar logout, limpando backend, token em memória e usuário.

Mostrar estado de sessão expirada quando o refresh falhar.
