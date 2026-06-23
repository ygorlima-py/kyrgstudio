Alta: qualquer structured output inválido encerra o workflow. Todas as actions chamam diretamente llm.structured(), por exemplo [actions.py](/home/dministradorygor/projects/kyrgstudio/src/kyrg/workflows/copyadaptation/actions.py):40. Não existe tratamento para ValidationError, campos ausentes ou enums inválidos. O problema que ocorreu com section_type="authority" pode acontecer em estratégia, escrita, review, validação ou correções.


Média: erros de validação são texto livre. validation_errors é list[str] em [schemas.py](/home/dministradorygor/projects/kyrgstudio/src/kyrg/workflows/copyadaptation/schemas.py):352. A correção depende de interpretar frases variáveis em português. Isso explica diagnósticos inconsistentes, como tratar um mecanismo presente no user_profile como prova inventada.

[CORRIGIDO] Média: sections_to_create não contém tipos de seção. A análise agora retorna section_gaps estruturados e prepare_adaptation_input cria apenas tipos canônicos realmente ausentes, encaminhando seções incompletas ou fracas para gaps_to_fix.


