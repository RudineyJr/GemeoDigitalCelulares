# Auditoria da divergência entre terminal e painel — 22/10/2026

## Evidência e causa

O log do broker registrou: `Outgoing messages are being dropped for client ...`. A versão anterior confirmava publicação no broker, mas não confirmava gravação pelo coletor. Uma transação por evento, mensagens grandes e simulação acelerada saturaram o caminho do assinante.

As fórmulas de concluídas no simulador e no painel contam a mesma coisa: saída da estação Embalagem. O painel contava corretamente os eventos disponíveis, mas o histórico disponível era incompleto. Mostrar esses números como resultados finais era inadequado.

| Cenário das imagens | Eventos gerados | Eventos encontrados no banco | Concluídas no terminal | Concluídas no painel |
|---|---:|---:|---:|---:|
| Atual — 3296bf6c | 75923 | 39379 | 986 | 518 |
| Proposta — 70e84c75 | 82945 | 31123 | 1047 | 376 |

## Correções

- Lotes com uma transação SQLite por lote.
- Confirmação após COMMIT: o próximo lote aguarda a confirmação de aplicação.
- Repetição idempotente se a confirmação não chegar.
- Arquivo local dos eventos e manifesto para reenvio.
- Sequência única por execução e conferência final de quantidade, IDs e resumo.
- Configuração completa armazenada no primeiro evento, evitando repeti-la milhares de vezes.
- Broker com volume persistente e limite explícito de fila.
- O painel bloqueia resultados finais de históricos incompletos ou ainda em recebimento.
- Novas execuções têm selo de validação e são priorizadas nos seletores.

## Duas novas execuções com os mesmos parâmetros

Não foram alterados tempos, regras, sementes ou probabilidades do modelo. Os históricos antigos permanecem preservados.

| Campo | Atual — 1ef8c5383156487898882e6fb7eb79f4 | Proposta — ae181809818e4e6290effd0e140c74df |
|---|---:|---:|
| Horas | 8 | 8 |
| Semente | 7 | 7 |
| SPI / AOI | desligados | ativos |
| Gerados = gravados | 75923 | 82945 |
| Iniciadas | 1440 | 1440 |
| Concluídas | 986 | 1047 |
| Retidas / reprovadas | 63 | 90 |
| Em processo | 391 | 303 |

As diferenças 986 versus 1047 são do modelo: retirar defeitos antes da montagem libera capacidade nas estações seguintes. Os cenários atuais ainda não incluem o trabalho padronizado e o WIP limitado da proposta completa do HTML original.

O backup anterior às alterações está na pasta backups. A cópia original em outputs do chat não foi modificada; o projeto de trabalho é o de Documentos.
