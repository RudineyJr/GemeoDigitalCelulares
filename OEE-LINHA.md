# OEE simplificado da linha — critério atual

Substitui no painel a referência exclusiva do teste funcional. Não exige gerar novos históricos.

Fórmula: `100 × aprovadas que saíram da embalagem × ciclo ideal comum / tempo planejado transcorrido`.

O painel oferece um campo de ciclo ideal da linha, aplicado igualmente a todas as execuções. O padrão de 20 s é uma hipótese de capacidade coerente com a alimentação nominal do modelo e o perfil balanceado; não é uma medição industrial nem deve ser confundido automaticamente com takt. Não usar o gargalo nominal diferente de cada cenário como referência de comparação, nem a soma dos tempos das estações. A fórmula compacta segue a referência: https://www.oee.com/calculating-oee/.

NG é apenas a reprovação no teste funcional. Retenções de SPI/AOI ficam separadas, continuam fora do fluxo e entram no balanço de WIP, mas não contam como NG nem são novamente subtraídas das embaladas boas.

Sem eventos de paradas, disponibilidade é assumida em 100%. Para a decomposição simplificada: saídas consideradas = embaladas boas + NG final; qualidade = embaladas boas / saídas consideradas; desempenho = saídas consideradas × ciclo ideal / tempo planejado. Esses fatores usam fronteiras de saída em pontos diferentes para NG e boas e são uma aproximação acumulada enquanto houver WIP. Não representam medição independente de todas as perdas industriais. O indicador agregado é saída boa / capacidade teórica da linha no período; não multiplicamos por RTY nem FPY outra vez.

O tempo planejado da reprodução é o tempo transcorrido selecionado; no final do histórico de oito horas é 28.800 s. O turno parte com linha vazia e não esvazia depois: o indicador inclui o efeito de partida e peças ainda em processo. Após o relógio começar, sem nenhuma boa embalada o OEE é zero; no instante zero fica indisponível. Valores acima de 100% não são corrigidos artificialmente na tabela: indicariam referência de ciclo incompatível. O radar mantém seu limite visual de 100%.

## Resultado com 20 s comuns, oito horas e semente 7

| Cenário | Embaladas boas | NG final | OEE linha |
|---|---:|---:|---:|
| Atual | 986 | 63 | 68,47% |
| SPI/AOI | 1047 | 2 | 72,71% |
| SPI/AOI + Lean local | 1087 | 2 | 75,49% |
| SPI/AOI + Lean ampliado | 1327 | 2 | 92,15% |

Atual → Lean ampliado: +23,68 pontos percentuais, aproximadamente +34,58% relativo. O modelo atual não fundamenta um OEE inicial de 30–40%: seria necessário modelar e validar as perdas reais adicionais.

Código: `calculateLineOEE` em `metrics.js`, chamada por `buildMetrics(..., lineIdealCycle)`. `app.py` envia `line_ideal_cycle` aos dois templates. A função anterior `calculateFunctionalOEE` permanece como auxiliar matemático testado; o painel chama o critério da linha.

Este documento substitui as explicações anteriores sobre OEE exclusivo do TFF no README, tutorial e estudo Lean. Históricos e resultados de produção não foram modificados.
