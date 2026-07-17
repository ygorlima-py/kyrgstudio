# Planejamento Do Package De Autenticação

## Objetivo

`src/app/auth` será responsável por transformar credenciais verificadas em uma
identidade interna confiável.

O restante da aplicação nunca deve confiar em `user_id`, email, Google subject
ou permissões enviados diretamente pelo cliente. Rotas protegidas recebem um
`AuthenticatedPrincipal` produzido por este package.

```text
credencial do cliente
        |
        v
app.auth valida a credencial
        |
        v
carrega e valida o usuário no banco
        |
        v
AuthenticatedPrincipal
        |
        v
API usa principal.user_id
```

O package não implementa regras de jobs, billing, storage, workflows ou
respostas HTTP de domínio.

## Decisões Arquiteturais

### Access Token

As rotas normais da API usarão um access token JWT curto:

```http
Authorization: Bearer <access_token>
```

O access token:

- terá duração curta, inicialmente 15 minutos;
- será assinado pelo backend;
- usará `sub` como identificador interno do usuário em formato string;
- validará assinatura, algoritmo, `iss`, `aud`, `exp`, `iat`, `nbf`, `jti` e
  tipo do token;
- nunca conterá senha, hash, Google token, dados de billing ou informações
  sensíveis;
- não será aceito por query string.

O algoritmo permitido vem exclusivamente das settings. O backend nunca escolhe
o algoritmo a partir do header recebido no próprio JWT.

### Refresh Token

Para manter a sessão sem criar access tokens longos, o app usará refresh tokens
opacos, aleatórios e rotativos.

O refresh token:

- será gerado com um gerador criptograficamente seguro;
- será armazenado no navegador em cookie `HttpOnly` e `Secure`;
- será persistido no banco somente como hash;
- será substituído a cada renovação;
- invalidará a família da sessão quando um token antigo for reutilizado;
- será revogado em logout, troca de senha ou desativação da conta;
- terá expiração absoluta e expiração por inatividade.

Jobs continuarão usando Bearer access token. CSRF será necessário apenas nas
operações autenticadas por cookie, principalmente refresh e logout.

### Senhas

Senhas serão processadas com Argon2id através de uma biblioteca especializada.

Regras:

- nunca armazenar senha em texto puro;
- nunca usar SHA-256, MD5 ou criptografia reversível como password hash;
- aplicar salt automaticamente pelo algoritmo;
- executar verificação contra um hash fictício quando o email não existir,
  reduzindo diferenças de tempo que permitam enumeração;
- permitir atualização futura dos parâmetros do hash;
- limitar tamanho mínimo e máximo antes do hashing para evitar abuso de CPU.

### Google

O frontend enviará ao backend um Google ID token, nunca somente `google_sub`,
email ou identificador fornecido pelo navegador.

O backend deverá verificar:

- assinatura com as chaves públicas do Google;
- `aud` contra os client IDs configurados;
- `iss`;
- `exp`;
- `sub`;
- email e `email_verified` quando necessários.

O backend não deve validar Google ID tokens manualmente com chamadas improvisadas
ou confiar em payload decodificado sem assinatura.

Uma conta Google existente será localizada por `google_sub`. Uma conta local
existente com o mesmo email não será vinculada automaticamente apenas pela
coincidência do email. O sistema exigirá um fluxo explícito de vinculação ou
uma verificação adicional, evitando tomada de conta.

## Estrutura Do Package

Os arquivos já criados serão mantidos. Três módulos adicionais são necessários
para impedir que `service.py` misture criptografia de senha e validação Google.

```text
src/app/auth/
  __init__.py
  principal.py
  passwords.py
  tokens.py
  google.py
  transactional_store.py
  service.py
  dependencies.py
  README.md
```

Contratos HTTP de login e cadastro pertencem a:

```text
src/app/schemas/auth.py
```

Rotas HTTP pertencem a:

```text
src/app/api/routers/auth.py
```

Persistência de refresh sessions pertence ao store:

```text
src/app/store/auth_sessions.py
```

Essa separação mantém:

```text
API -> auth -> store
```

`app.auth` não deve importar `app.api`.

## Módulos

### `principal.py`

Define a identidade autenticada utilizada pelo restante da aplicação.

Contrato principal:

```text
AuthenticatedPrincipal
  user_id
  email
  name
  auth_provider
  email_verified
```

Regras:

- usar dataclass imutável;
- exigir `user_id` positivo;
- normalizar email;
- não incluir `password_hash`, `google_sub`, tokens ou objetos SQLAlchemy;
- não retornar o model `User` diretamente para routers;
- representar somente informações já verificadas.

Também pode definir contratos imutáveis usados entre os módulos:

```text
GoogleIdentity
AccessTokenClaims
IssuedAuthTokens
```

Esses contratos não executam lógica de criptografia ou banco.

### `passwords.py`

Implementa hashing e verificação de senha.

Contratos:

```text
PasswordHasher
  hash(password)
  verify(password, password_hash)
  verify_and_update(password, password_hash)

Argon2PasswordHasher
```

Responsabilidades:

- configurar Argon2id;
- validar limites de tamanho;
- produzir hash pronto para `UserStore`;
- verificar senha sem expor a razão da falha;
- gerar e manter um dummy hash;
- retornar novo hash quando os parâmetros precisarem ser atualizados.

Não acessa banco, HTTP, JWT ou Google.

### `tokens.py`

Implementa tokens pertencentes ao próprio Kyrg Studio.

Responsabilidades:

- emitir access JWT;
- validar access JWT;
- rejeitar token expirado, adulterado ou destinado a outro issuer/audience;
- exigir `type="access"`;
- gerar `jti` único;
- gerar refresh token opaco;
- produzir hash determinístico do refresh token para consulta no banco;
- nunca registrar tokens completos em logs.

Contrato sugerido:

```text
AccessTokenService
  issue(principal)
  decode(token)

RefreshTokenGenerator
  generate()
  digest(token)
```

O módulo deve receber configuração pronta. Não chama `load_settings()` dentro
de métodos e não mantém estado de usuário em memória.

### `google.py`

Verifica identidades emitidas pelo Google.

Contratos:

```text
GoogleTokenVerifier
  verify(id_token) -> GoogleIdentity

GoogleIdentity
  subject
  email
  email_verified
  name
  avatar_url
```

Responsabilidades:

- usar a biblioteca oficial ou suportada para verificação;
- validar client ID, issuer, assinatura e expiração;
- converter claims Google em um contrato interno mínimo;
- nunca criar ou atualizar usuário diretamente;
- nunca aceitar `google_sub` ou email sem ID token verificável.

### `transactional_store.py`

Adapta `UserStore` e `AuthSessionStore` para operações curtas e duráveis.

Esse módulo segue o mesmo princípio de `PipelineJobStore` e `WorkerJobStore`:
stores SQLAlchemy executam SQL, enquanto o adapter define onde cada transação
começa e termina.

Contrato sugerido:

```text
AuthStore
  get_user(user_id)
  get_user_by_email(email)
  get_user_by_google_sub(subject)
  create_password_user_with_session(...)
  create_google_user_with_session(...)
  create_session(user_id, ...)
  rotate_session(...)
  revoke_session(...)
  revoke_user_sessions(user_id)
  update_password_hash(user_id, password_hash)
```

Responsabilidades:

- receber `SessionFactory`;
- usar sessão curta para leituras;
- usar `async_transaction_scope` para escritas;
- combinar criação de usuário e refresh session na mesma transação;
- executar rotação de refresh token atomicamente;
- fechar a sessão antes de devolver o resultado;
- retornar contratos internos, não uma sessão aberta.

Não executa hashing, JWT, Google ou lógica HTTP.

### `service.py`

Contém os casos de uso de autenticação sem depender de FastAPI.

`AuthService` recebe dependências prontas:

```text
AuthStore
PasswordHasher
AccessTokenService
RefreshTokenGenerator
GoogleTokenVerifier
```

Casos de uso:

```text
register_with_password(email, password, name)
login_with_password(email, password)
login_with_google(google_id_token)
refresh(refresh_token)
logout(refresh_token)
authenticate_access_token(access_token)
```

#### Cadastro Por Senha

1. normalizar e validar email;
2. validar senha;
3. gerar Argon2id hash;
4. pedir ao `AuthStore` para criar usuário e refresh session atomicamente;
5. emitir access token;
6. retornar principal e tokens.

Nunca passa senha pura ao store.

#### Login Por Senha

1. buscar usuário por email;
2. executar verificação de senha ou dummy hash;
3. retornar o mesmo erro público para email inexistente e senha incorreta;
4. rejeitar usuário desativado;
5. atualizar hash quando necessário;
6. pedir ao `AuthStore` para criar refresh session em transação curta;
7. emitir access token.

#### Login Google

1. verificar Google ID token antes de abrir transação de escrita;
2. localizar usuário por `google_sub`;
3. não vincular automaticamente conta local existente somente por email;
4. rejeitar usuário desativado;
5. criar refresh session em transação curta ou criar usuário e sessão
   atomicamente quando a conta ainda não existir;
6. emitir access token.

#### Refresh

1. gerar digest do token recebido;
2. localizar e bloquear a refresh session na transação;
3. rejeitar token expirado ou revogado;
4. detectar reutilização;
5. revogar token anterior;
6. criar novo token na mesma família;
7. emitir novo access token;
8. confirmar tudo em uma única transação.

#### Autenticação De Requisição

1. validar access JWT;
2. extrair `sub`;
3. buscar o usuário;
4. rejeitar usuário inexistente ou desativado;
5. criar `AuthenticatedPrincipal`;
6. fechar a sessão de banco antes de executar a rota protegida.

O serviço nunca retorna models SQLAlchemy para a API.

### `dependencies.py`

Adapta autenticação ao FastAPI.

Responsabilidades:

- declarar `HTTPBearer(auto_error=False)`;
- extrair exclusivamente o header `Authorization`;
- exigir o esquema `Bearer`;
- obter o `AuthService` já configurado nos recursos da aplicação;
- chamar `AuthService.authenticate_access_token`;
- retornar `AuthenticatedPrincipal`;
- garantir que o adapter transacional feche a sessão antes de entregar o
  principal à rota.

Função pública principal:

```python
async def get_current_user(...) -> AuthenticatedPrincipal:
    ...
```

Essa dependência não deve manter uma transação aberta enquanto uma rota envia
vídeo ao storage, aguarda fila ou executa outra operação lenta.

Também deve fornecer dependências específicas para refresh/logout que validem:

- cookie de refresh;
- header CSRF;
- `Origin` ou `Referer` nas operações mutáveis.

Não implementa login, criação de usuário ou regras de Google dentro da função
`get_current_user`.

### `__init__.py`

Implementar por último.

Exportar apenas a API estável:

```text
AuthenticatedPrincipal
AuthService
AccessTokenService
GoogleTokenVerifier
PasswordHasher
get_current_user
```

Não exportar helpers criptográficos, dummy hash, nomes internos de cookie,
funções privadas de parsing ou implementações de store.

## Persistência Necessária

Refresh token com rotação exige estado persistido. Adicionar ao store:

```text
AuthSession
  id
  user_id
  token_hash
  family_id
  expires_at
  last_used_at
  revoked_at
  replaced_by_session_id
  created_at
```

Regras:

- `token_hash` único e indexado;
- índice em `user_id`;
- índice em `family_id`;
- nunca persistir refresh token puro;
- rotação executada atomicamente;
- reutilização revoga a família ativa;
- sessões expiradas devem ter política de limpeza;
- troca de senha e desativação revogam todas as sessões do usuário.

Criar:

```text
AuthSessionStoreBase
SQLAlchemyAuthSessionStore
```

O store executa SQL. `AuthService` decide quando criar, rotacionar ou revogar
uma sessão.

## Settings

Adicionar configurações validadas:

```text
auth_jwt_secret
auth_jwt_algorithm
auth_issuer
auth_audience
auth_access_token_ttl_seconds
auth_refresh_token_ttl_seconds
auth_refresh_cookie_name
auth_refresh_cookie_secure
auth_refresh_cookie_samesite
auth_csrf_cookie_name
auth_allowed_clock_skew_seconds
google_client_ids
```

Regras:

- segredo JWT obrigatório fora de testes;
- segredo forte carregado de secret manager ou variável de ambiente;
- algoritmo permitido configurado pelo servidor;
- issuer e audience obrigatórios;
- TTLs positivos;
- cookie `Secure` obrigatório em produção;
- wildcard não permitido nos client IDs Google;
- não aplicar fallback inseguro para segredo JWT.

O codec de token deve ficar atrás de contrato próprio. Isso permite trocar
HS256 por assinatura assimétrica posteriormente sem alterar `AuthService`,
dependencies ou routers.

## Erros Públicos

Adicionar erros estáveis em `app.errors`:

```text
AuthenticationRequiredError -> 401
InvalidCredentialsError -> 401
InvalidTokenError -> 401
RefreshTokenInvalidError -> 401
AccountDisabledError -> 403
EmailVerificationRequiredError -> 403
AccountLinkRequiredError -> 409
AuthConfigurationError -> 500
```

Regras:

- respostas `401` incluem `WWW-Authenticate: Bearer`;
- login não revela se o email existe;
- token expirado e assinatura inválida não expõem detalhes criptográficos;
- logs não contêm senha, access token, refresh token ou Google ID token;
- detalhes técnicos ficam somente nos logs controlados.

Atualizar `exception_handlers.py` antes de expor rotas de autenticação.

## Contratos HTTP Futuros

Adicionar em `app.schemas.auth`:

```text
RegisterRequest
PasswordLoginRequest
GoogleLoginRequest
AccessTokenResponse
CurrentUserResponse
```

Rotas futuras:

```text
POST /v1/auth/register
POST /v1/auth/login
POST /v1/auth/google
POST /v1/auth/refresh
POST /v1/auth/logout
GET  /v1/auth/me
```

O refresh token não aparece no JSON. Ele é transportado por cookie protegido.
O access token pode ser retornado no JSON e mantido em memória pelo frontend.

## Transações

Não manter transação de banco aberta durante:

- hashing de senha;
- verificação Google;
- chamadas externas;
- processamento de arquivo;
- execução de jobs.

Ordem recomendada:

```text
validar credencial fora da transação
        |
        v
abrir transação curta
        |
        v
persistir usuário/sessão
        |
        v
commit
        |
        v
emitir resposta
```

Refresh rotation é exceção: leitura bloqueada, revogação e criação do novo
registro precisam ocorrer na mesma transação.

## CSRF E CORS

CORS não substitui proteção CSRF.

Configuração:

- origens explícitas;
- nunca usar `*` com credentials;
- permitir somente métodos e headers necessários;
- expor somente headers públicos, como `X-Request-ID`;
- cookies com `HttpOnly`, `Secure` e `SameSite`;
- emitir um token CSRF aleatório em cookie separado e não `HttpOnly`;
- refresh e logout exigem `X-CSRF-Token`;
- comparar header e cookie CSRF em tempo constante;
- rotacionar o token CSRF junto com o refresh token;
- validar `Origin` ou `Referer` em operações autenticadas por cookie.

As rotas de jobs usam Bearer access token e não dependem do refresh cookie.

## Proteções Operacionais

Antes de publicar autenticação:

- HTTPS obrigatório;
- rate limit por IP e por identidade em login, cadastro e refresh;
- limite de tamanho do body;
- respostas iguais para email inexistente e senha incorreta;
- auditoria de login, logout, refresh reuse e conta desativada;
- nenhuma credencial em logs;
- rotação de segredos planejada;
- política de expiração e limpeza de sessões;
- revogação de sessões após troca de senha;
- proteção contra enumeração de email;
- testes com relógio controlável para expiração de tokens.

## Testes

### Unitários

```text
tests/unit/app/auth/
  test_auth_principal.py
  test_auth_passwords.py
  test_auth_tokens.py
  test_auth_google.py
  test_auth_transactional_store.py
  test_auth_service.py
  test_auth_dependencies.py
  test_auth_public_api.py
```

Cobrir:

- validação do principal;
- hash e verificação Argon2id;
- dummy hash para usuário inexistente;
- emissão e validação JWT;
- algoritmo, issuer, audience e expiração inválidos;
- geração e digest de refresh token;
- login por senha;
- login Google;
- usuário desativado;
- conflito de vinculação;
- refresh rotation e replay;
- extração Bearer;
- ausência de credencial;
- sessão fechada antes da rota protegida;
- exports públicos.

### Integração

```text
tests/integration/app/auth/
  test_auth_service_integration.py
  test_auth_api_integration.py
```

Cobrir com banco migrado:

- cadastro e login reais;
- persistência de Argon2id hash;
- criação e rotação de refresh session;
- revogação por logout;
- revogação por troca de senha;
- detecção de refresh token reutilizado;
- criação de usuário Google com verifier fake;
- rejeição de conta desativada;
- rota protegida usando access token;
- cookie e CSRF em refresh/logout;
- nenhuma credencial persistida ou retornada indevidamente.

Testes reais contra Google não pertencem à suíte unitária.

## Ordem Exata De Construção

Seguir esta ordem:

1. adicionar dependências `pwdlib[argon2]`, `PyJWT` e `google-auth`;
2. adicionar settings de autenticação e validações;
3. adicionar erros `401`, `403`, `409` e atualizar exception handlers;
4. adicionar `AuthSession`, store, índices e migration;
5. implementar `principal.py`;
6. criar e implementar `passwords.py`;
7. implementar `tokens.py`;
8. criar e implementar `google.py`;
9. implementar `transactional_store.py`;
10. implementar `service.py`;
11. implementar `dependencies.py`;
12. implementar `__init__.py`;
13. criar schemas HTTP em `app.schemas.auth`;
14. criar rotas em `app.api.routers.auth`;
15. integrar auth service e token services no lifespan/dependencies da API;
16. proteger rotas de jobs com `get_current_user`;
17. criar testes unitários;
18. criar testes de integração;
19. executar um fluxo real de cadastro, login, refresh, job protegido e logout.

Não construir `dependencies.py` antes de principal, tokens e service. Não criar
rotas antes de erros, settings e persistência de sessão.

## Definição De Pronto

O package estará pronto quando:

- nenhuma rota protegida aceitar `user_id` do cliente;
- access tokens forem curtos e completamente validados;
- refresh tokens forem opacos, rotativos, revogáveis e armazenados por hash;
- senha pura nunca chegar ao store ou aos logs;
- Google ID tokens forem verificados no backend;
- usuário inexistente ou desativado não produzir principal;
- autenticação fechar banco antes da lógica pesada da rota;
- erros `401/403` forem públicos e seguros;
- refresh/logout tiverem CSRF e cookies seguros;
- testes unitários, integração e um fluxo real passarem.

## Referências

- [FastAPI OAuth2 com JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Google: autenticar com backend](https://developers.google.com/identity/sign-in/web/backend-auth)
- [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [OAuth 2.0 Security Best Current Practice](https://datatracker.ietf.org/doc/html/rfc9700)
