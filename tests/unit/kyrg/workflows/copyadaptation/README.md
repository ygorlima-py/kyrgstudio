# Plano de Testes: CopyAdaptationWorkflow

Este documento define a suíte de testes projetada exclusivamente para o módulo `src/kyrg/workflows/copyadaptation`. A estratégia abrange testes unitários, de integração, regressões e avaliações de qualidade (evals) focadas em LLMs.

## Estrutura de Diretórios

A pasta de testes deve ficar na raiz do projeto, espelhando a estrutura do diretório `src`. Módulos sem comportamento lógico direto (como `state.py` para tipagem, `constants.py` para dados fixos e `prompts.py`) são testados indiretamente e não precisam de arquivos dedicados.

```text
kyrgstudio/
├── src/
│   └── kyrg/
│       └── workflows/
│           └── copyadaptation/
└── tests/
    ├── unit/
    │   └── workflows/
    │       └── copyadaptation/
    │           ├── test_utils.py
    │           ├── test_schemas.py
    │           ├── test_actions.py
    │           ├── test_nodes.py
    │           └── test_routers.py
    ├── integration/
    │   └── workflows/
    │       └── test_copyadaptation_workflow.py
    └── evals/
        └── copyadaptation/
            └── test_copy_quality.py
```

---

## Testes Unitários

### `test_utils.py`
**Status:** Completed on 2026-06-23.

* Calcular a contagem real de palavras por seção, ignorando o `word_count` inventado pela LLM.
* Aplicar a pausa correta para cada `section_type`.
* Aplicar corretamente os coeficientes (short, medium, long e dramatic).
* Garantir o fallback adequado para tipo e intenção desconhecidos.
* Respeitar os limites mínimo de 0.1 e máximo de 1.8 segundos.
* Calcular corretamente a duração da fala em segundos.
* Somar as pausas corretamente, exceto após a última seção.
* Atribuir os status `too_short`, `too_long`, `ok` e `unknown`.
* Aceitar e calcular usando WPM personalizado.
* Gerar erro quando não existirem seções.
* Substituir `sections_revised` mantendo a mesma ordem.
* Incluir e ordenar corretamente uma nova seção revisada.
* Garantir que as seções originais não sejam modificadas.
* Criar uma timeline contínua (próximo start = end anterior + pausa).
* Garantir que a última seção tenha pausa zero.
* Extrair corretamente hooks e CTAs.
* Construir corretamente o script e o `voice_ready_text`.

### `test_schemas.py`
**Status:** Completed on 2026-06-23.

* Validar se instâncias de `UserProfileOutput` são aceitas corretamente.
* Gerar `ValidationError` na ausência de campos obrigatórios.
* Garantir que listas default não sejam compartilhadas entre instâncias.
* Rejeitar valores inválidos para `section_type`.
* Rejeitar valores inválidos para `adaptation_mode`.
* Rejeitar valores inválidos para `pause_intent`.
* Rejeitar valores inválidos para `awareness_level`.
* Rejeitar valores inválidos para `persuasion_pattern`.
* Rejeitar `action` inválida em `SectionRevisionInstruction`.
* Verificar se `TimedScriptSectionOutput` preserva os dados da seção e aceita métricas.
* Garantir que `AdaptedScriptOutput` completo possa ser serializado e restaurado perfeitamente.

### `test_actions.py`
**Status:** Completed on 2026-06-23.

* Garantir que `execute()` chama `structured()` com o schema correto para todas as seis actions.
* Garantir que `aexecute()` chama `astructured()` com o schema correto.
* Verificar se o retorno é exatamente o modelo Pydantic esperado.
* Certificar que o prompt não contém placeholders (`{...}`) vazios.
* Garantir que objetos são serializados como JSON legível.
* Verificar se os dados são inseridos nas tags corretas do prompt.
* Assegurar que rotinas de Retry recebem o contador, a versão anterior e os erros.
* Garantir que a correção receba os erros de validação reais, não dados inventados.
* Verificar se os tokens usados pela action estão acessíveis após a execução.

### `test_nodes.py`
**Status:** Completed on 2026-06-23.

* **prepare_adaptation_input:** Mapear seções da referência; enviar `missing` para `sections_to_create`; enviar `weak` e `incomplete` para `gaps_to_fix`; não duplicar `sections_to_create`; adicionar scores persuasivos baixos e ausência de provas/mecanismos; validar a prioridade correta do idioma; gerar erros claros para entradas obrigatórias ausentes.
* **build_copy_strategy:** Atualizar apenas os campos estratégicos.
* **write_script_sections:** Calcular palavras de forma determinística.
* **review_section_flow:** Converter outputs Pydantic para o estado correto.
* **correct_section:** Usar as seções finais resolvidas e incrementar somente seu próprio contador.
* **validate_script:** Receber corretamente as métricas calculadas.
* **correct_script:** Incrementa somente seu próprio contador e limpar `sections_revised` antigas.
* **build_script_output:** Retornar exclusivamente o `adapted_script`.
* **Geral:** Adicionar corretamente os tokens retornados por cada node e gerar erro imediato na ausência de contexto ou dependência obrigatória.

### `test_routers.py`
**Status:** Completed on 2026-06-23.

* `flow_approved=True` -> Continue.
* `flow_approved=False` (retry abaixo do limite) -> Retry.
* `flow_approved=False` (limite de retry atingido) -> Continue.
* `validation_passed=True` -> Continue.
* `validation_passed=False` (retry abaixo do limite) -> Retry.
* `validation_passed=False` (limite de retry atingido) -> Continue.
* Testar comportamentos com valores `None`, `zero` e limites exatos.

---

## Testes de Integração

### `test_copyadaptation_workflow.py`
**Status:** Completed on 2026-06-23.

**Nota:** Utilizar LLMs fake para previsibilidade e velocidade.
* Percorrer o caminho feliz completo sem acionar correções.
* Acionar retry de fluxo seguido de aprovação.
* Acionar retry de validação seguido de aprovação.
* Acionar retry de fluxo seguido de retry de validação.
* Garantir que o limite de retry impede loops infinitos.
* Verificar se um resultado reprovado após o limite continua com a marcação de reprovado.
* Validar a ordem correta de execução dos nodes.
* Confirmar que o estado final contém o `adapted_script`.
* Confirmar que os tokens de toda a execução se acumulam corretamente.
* Garantir que uma nova `thread_id` inicie com o estado limpo.
* Garantir que a mesma `thread_id` retome do estado interrompido.

---

## Testes de Regressão Obrigatórios
**Status:** Covered by the unit and integration suites on 2026-06-23.

Estes testes evitam que problemas previamente mapeados voltem a ocorrer:
* A duração deve constar sempre em segundos no output.
* As pausas devem obrigatoriamente participar da duração validada.
* A última seção não pode receber pausa em nenhuma hipótese.
* As variáveis `sections_revised` antigas não podem sobrescrever correções novas.
* Contagem correta de `retry_count_correction_section`.
* Contagem correta de `retry_count_correction_script`.
* A variável `sections_to_create` deve conter apenas tipos, nunca descrições longas.
* O `scene_planning_input` não pode reaparecer duplicado no estado.
* O output final não pode duplicar seções que estejam fora de `adapted_script`.

---

## Evals de Qualidade (`test_copy_quality.py`)
**Status:** Implemented on 2026-06-23 as an opt-in `live_eval` test.

**Execution:** Requires `KYRG_RUN_COPYADAPTATION_EVALS=1`, `OPENAI_API_KEY`, and `KYRG_COPYADAPTATION_EVAL_MODEL`. It is excluded from the deterministic suite because it performs paid, non-deterministic API calls.

Devido à imprevisibilidade do LLM, testes unitários comuns não são suficientes. Estes testes utilizam fixtures reais e chamadas reais para avaliar a qualidade gerada:
* O script segue a estrutura da referência original.
* O conteúdo respeita integralmente o `UserProfileOutput`.
* O LLM não inventa provas sociais ou depoimentos inexistentes.
* O LLM não inventa informações de preço, garantia, suporte ou escassez.
* O script obedece todas as restrições fornecidas.
* A saída é produzida exatamente no idioma solicitado.
* O texto gerado se mantém dentro da duração estipulada.
* As transições mantêm coerência lógica entre as seções.
* As rodadas de correção realmente melhoram os erros reportados sem degradar seções que já estavam válidas.
