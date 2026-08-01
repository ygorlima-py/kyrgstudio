frontend/src/
├── features/
│   ├── jobs/
│   │   ├── api/
│   │   │   └── jobs-api.ts
│   │   ├── components/
│   │   │   ├── job-creation-form.tsx
│   │   │   ├── job-type-step.tsx
│   │   │   ├── file-upload-step.tsx
│   │   │   ├── job-settings-step.tsx
│   │   │   ├── job-review-step.tsx
│   │   │   ├── job-form-progress.tsx
│   │   │   └── upload-progress.tsx
│   │   ├── hooks/
│   │   │   └── use-job-submission.ts
│   │   ├── schemas/
│   │   │   └── job-creation-schema.ts
│   │   ├── utils/
│   │   │   └── build-job-request.ts
│   │   └── index.ts
│   └── user-profile/
│       ├── components/
│       │   ├── product-offer-fields.tsx
│       │   ├── audience-problem-fields.tsx
│       │   ├── desire-promise-fields.tsx
│       │   ├── mechanism-fields.tsx
│       │   ├── benefits-fields.tsx
│       │   ├── objections-fields.tsx
│       │   ├── proof-assets-fields.tsx
│       │   ├── offer-terms-fields.tsx
│       │   ├── call-to-action-fields.tsx
│       │   ├── tone-language-fields.tsx
│       │   ├── platform-duration-fields.tsx
│       │   ├── restrictions-fields.tsx
│       │   └── repeatable-text-list.tsx
│       ├── schemas/
│       │   └── user-profile-schema.ts
│       └── index.ts
└── routes/
    └── new-job-route.tsx

Ordem De Construção

[FEITO]
Criar schemas e tipos
Modelar análise, adaptação e user_profile com Zod.
Usar uma união discriminada por pipeline_type.
Não exigir campos de adaptação no fluxo de análise.

[FEITO]
Criar cliente HTTP de jobs
Implementar POST /jobs.
Montar FormData com file e request.
Aceitar AbortSignal, progresso e chave de idempotência.

[FEITO]
Criar transformação do formulário
Converter os valores visuais para o JSON esperado pela API.
Remover user_profile quando for análise.
Nunca enviar nomes internos ou campos vazios desnecessários.

[FEITO]
Criar estrutura do formulário em etapas
Manter um único React Hook Form durante todo o fluxo.
Preservar dados ao avançar ou voltar.
Validar apenas os campos da etapa atual.

[FEITO]
Criar escolha do pipeline
Selecionar análise ou adaptação.
Ler a seleção inicial da query string usada pelo dashboard.

[FEITO]
Criar dropzone
Selecionar vídeo ou áudio.
Validar tipo e tamanho preliminarmente.
Manter apenas a referência File, sem carregar o arquivo inteiro na memória.

[FEITO]
Criar configurações comuns
Idioma.
Correção da transcrição.
Configurações realmente necessárias ao usuário.
Providers e modelos padrão não precisam poluir a interface.

[FEITO]
Criar user_profile modular
Exibir somente para adaptação.
Separar cada grupo de perguntas em componente próprio.
Usar lista repetível para benefícios, objeções, provas e restrições.

[FEITO]
Criar revisão
Mostrar pipeline, arquivo, configurações e resumo do perfil.
Permitir voltar para corrigir qualquer etapa.

[FEITO]
Implementar envio
Gerar uma chave de idempotência.
Enviar multipart com progresso.
Impedir submissões duplicadas.
Redirecionar para /app/jobs/{jobId} após receber 202.

[FEITO]
Tratar falhasErro de validação.
Arquivo incompatível ou grande.
Falha de conexão.
Sessão expirada.
Falha recuperável com nova tentativa usando a mesma chave.

Registrar /app/jobs/newRenderizar NewJobRoute dentro de AppLayout.
Manter todo o fluxo em uma única rota.