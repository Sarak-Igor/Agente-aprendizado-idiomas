# Explicação dos Erros da API Gemini

## Erro 429 - RESOURCE_EXHAUSTED

### O que significa?

O erro **429 RESOURCE_EXHAUSTED** pode ter dois significados diferentes:

#### 1. Cota Realmente Excedida
- Você realmente usou toda a cota do Free Tier
- Limite de requisições por dia/minuto foi atingido
- Limite de tokens foi atingido

#### 2. Modelo Não Disponível para a Conta (Mais Comum)
- O modelo **não está disponível** para sua conta/API version
- A mensagem de erro contém `limit: 0` (limite zero)
- **NÃO é questão de cota excedida**, mas sim de disponibilidade do modelo
- Exemplo: `gemini-2.0-flash` pode não estar disponível na API v1beta para sua conta

### Detalhes do Erro

```
Erro: 429 RESOURCE_EXHAUSTED
Modelo: gemini-2.0-flash
Métricas afetadas:
- generativelanguage.googleapis.com/generate_content_free_tier_requests
- generativelanguage.googleapis.com/generate_content_free_tier_input_token_count
```

### Limites do Free Tier Gemini

O Free Tier do Gemini tem limites diários e por minuto:

- **Requisições por dia**: Limitado (varia por modelo)
- **Requisições por minuto**: Limitado
- **Tokens por dia**: Limitado
- **Tokens por minuto**: Limitado

### Como o Sistema Lida com Isso

O sistema foi configurado para:

1. **Detectar automaticamente** quando um modelo está indisponível (404 ou 429)
2. **Distinguir entre** "cota excedida" e "modelo não disponível" (verifica `limit: 0`)
3. **Bloquear o modelo** problemático automaticamente
4. **Tentar TODOS os modelos disponíveis** (até 10 tentativas) antes de falhar
5. **Ignorar o modelo fixado na sessão** se ele estiver com problema
6. **Continuar tentando** até encontrar um modelo que funcione

### Modelos em Ordem de Prioridade

O sistema tenta os modelos nesta ordem:

1. `gemini-1.5-flash` (melhor suporte free tier)
2. `gemini-1.5-pro`
3. `gemini-2.0-flash` (pode estar sem cota)
4. `gemini-2.5-flash`
5. `gemini-2.5-pro`

### O que Fazer?

#### Se o Erro Mostrar `limit: 0` (Modelo Não Disponível)

**Isso NÃO é cota excedida!** O modelo simplesmente não está disponível para sua conta.

1. **O sistema resolve automaticamente** - tenta outros modelos
2. **Não é necessário fazer nada** - o roteamento funciona automaticamente
3. **O modelo será bloqueado** e não será tentado novamente

#### Se Realmente For Cota Excedida

1. **Aguarde alguns minutos** - As cotas são resetadas periodicamente
2. **O sistema tentará automaticamente** outros modelos
3. **Se todos os modelos estiverem sem cota**, você precisará aguardar o reset da cota

#### Soluções de Longo Prazo

1. **Upgrade para plano pago** - Remove limites de cota
2. **Use múltiplas API keys** - Distribua o uso entre diferentes contas
3. **Configure outros serviços LLM** (OpenRouter, Groq, Together) como fallback
4. **Monitore o uso** - Acompanhe em: https://ai.dev/rate-limit

### Erro 404 - NOT_FOUND (Modelo Não Encontrado)

### O que significa?

O erro **404 NOT_FOUND** indica que o modelo solicitado não está disponível na versão da API que você está usando.

**Exemplo**: `gemini-1.5-flash` pode não estar disponível na API v1beta.

### Como o Sistema Lida com Isso

1. **Detecta o erro 404**
2. **Bloqueia o modelo** automaticamente
3. **Tenta o próximo modelo** da lista
4. **Continua até encontrar um modelo disponível**

### Solução

O sistema resolve automaticamente tentando outros modelos. Não é necessário fazer nada.

## Monitoramento

### Verificar Cotas

- **Dashboard Gemini**: https://ai.dev/rate-limit
- **Documentação**: https://ai.google.dev/gemini-api/docs/rate-limits

### Logs do Sistema

O sistema registra nos logs:
- Quais modelos foram bloqueados
- Por que foram bloqueados (cota, não encontrado, etc.)
- Quais modelos estão sendo tentados
- Sucesso/falha de cada tentativa

## Melhorias Implementadas

O sistema agora:

✅ **Detecta automaticamente** erros 404 e 429
✅ **Bloqueia modelos** problemáticos automaticamente
✅ **Tenta modelos alternativos** sem intervenção manual
✅ **Registra tudo nos logs** para debug
✅ **Fornece mensagens claras** sobre o que está acontecendo

## Próximos Passos Recomendados

1. **Configure outros serviços LLM** como fallback (OpenRouter, Groq, Together)
2. **Monitore o uso** regularmente
3. **Considere upgrade** se o uso for intenso
4. **Use múltiplas API keys** se necessário
