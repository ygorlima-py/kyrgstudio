Eu planejaria o frontend em 5 etapas:
[FEITO]
Contrato e cliente
Regenerar schema.ts.
Adicionar requestPasswordReset() e resetPassword() em auth-api.ts.
Reutilizar o normalizador de erros.

[FEITO]
Tela “Esqueci minha senha”
Criar /forgot-password.
Campo de email com Zod.
Exibir sempre uma resposta neutra, sem revelar se o email existe.
Mostrar estado de envio e sucesso.

[FEITO]
Tela “Redefinir senha”
Criar /reset-password.
Ler o token do fragmento da URL.
Campos para nova senha e confirmação.
Enviar o token somente ao backend.

[FEITO]
Estados de experiência
Token expirado, usado ou inválido.
Senhas incompatíveis.
Erro temporário.
Sucesso com link para login.
Botão para solicitar novo email.

[FEITO]
Integração e validação
Registrar as rotas.
Adicionar traduções em português e inglês.
Manter o layout atual do Kyrg Studio.
Executar lint, build e testar o fluxo manual completo.