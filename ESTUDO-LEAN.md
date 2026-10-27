# Estudo de balanceamento da bateria

Quatro cenários: Atual (sem SPI/AOI), SPI/AOI com tempos originais, SPI/AOI + Lean local e SPI/AOI + Lean ampliado.

O perfil `--lean` altera somente bateria (27→19 s), alto-falante (15→19 s) e microfone (21→19 s). O conjunto passa de 63 para 57 segundos de trabalho: hipótese de eliminar 6 segundos de desperdício e redistribuir tarefas. Não é resultado de cronoanálise. A viabilidade técnica, a ergonomia e a qualidade precisam ser verificadas antes de aplicação real.

Nenhum operador ou recurso adicional é criado. Teste funcional permanece em 26 s: a melhoria local pode deslocar a espera para ele. Não se afirma que toda a linha passa a produzir uma placa a cada 20 s. Não foram implementados Kanban, limite FIFO, falhas ou retrabalho. Fórmulas e ciclo de referência do OEE permanecem iguais.

Na pasta do projeto, para criar os quatro históricos com mesmos parâmetros de entrada:

```powershell
.\.venv\Scripts\python comparar_lean.py
```

Esse comando grava diretamente no SQLite. Para usar o caminho completo MQTT, abra o Docker, execute `docker compose up -d`, inicie `collect.py`, aguarde a inscrição e execute:

```powershell
.\.venv\Scripts\python comparar_lean.py --mqtt
```

O padrão é oito horas e semente 7. Cada chamada adiciona históricos; não apaga execuções antigas. Para gerar somente o cenário Lean:

```powershell
.\.venv\Scripts\python simulate.py --turno-horas 8 --semente 7 --lean --mqtt
```

No painel, o bloco “Estudo Lean — três cenários” apresenta os históricos validados mais recentes com a mesma semente, duração e condições de entrada do cenário Atual. Os seletores abaixo continuam permitindo comparar dois históricos nos gráficos. Os nomes agora identificam SPI/AOI e SPI/AOI + Lean separadamente.

Compare concluídas, NG no teste, retenções totais, WIP final, fila final/máxima/média da bateria, espera média na bateria e lead time médio. A fila média é ponderada pelo tempo; a espera média considera somente placas que iniciaram atendimento, e o lead time somente peças concluídas. Como o turno não esvazia a linha, essas médias não incluem o percurso futuro do WIP restante.

Para modificar a hipótese, edite `LEAN_TIMES` em `lean_analysis.py` e gere novas execuções. Os tempos usados ficam registrados em cada histórico. A referência industrial precisa vir de demanda, tempo disponível e decomposição das tarefas em um Yamazumi.

## Resultado executado — oito horas, semente 7

Históricos adicionados diretamente ao SQLite e validados por manifesto, sem apagar os anteriores:

| Cenário | Execução | Concluídas | NG teste | WIP final | Fila bateria final | Lead time médio |
|---|---|---:|---:|---:|---:|---:|
| Atual | 8be7759a192343da9ab6588e45b5adea | 986 | 63 | 391 | 369 | 69,43 min |
| SPI/AOI | 607f984148d44388bd1a51b679b68ef9 | 1047 | 2 | 303 | 281 | 57,91 min |
| SPI/AOI + Lean | 19931356321c40f9b275d432598adee5 | 1087 | 2 | 263 | 0 | 50,73 min |

No cenário Lean, a espera na bateria foi zero. Ainda havia 150 placas na fila da câmera traseira e 91 na fila do teste funcional ao final: a melhoria local não resolveu o balanceamento de toda a linha. Retenções/reprovações totais: Atual 63; demais cenários 90. A melhora na produção não decorre de mudar taxas de defeito ou fórmula do OEE.

## Segunda etapa: Lean ampliado

O comando abaixo adiciona somente o novo perfil, preservando históricos e o perfil `--lean` original:

```powershell
.\.venv\Scripts\python simulate.py --turno-horas 8 --semente 7 --lean-completo
```

Acrescente `--mqtt` para transmissão pelo broker com coletor ativo. A execução realizada nesta etapa foi gravada diretamente no SQLite.

| Posto | Lean local | Lean ampliado |
|---|---:|---:|
| Câmera traseira | 24 s | 19 s |
| Câmera frontal | 13 s | 18 s |
| Botões e vibra | 22 s | 19 s |
| Tampa traseira | 17 s | 20 s |
| Teste funcional | 26 s | 19 s |
| Embalagem | 19 s | 20 s |

Os pares de câmeras e botões/tampa conservam o trabalho total: redistribuição hipotética de atividades preparatórias compatíveis com a sequência. Teste/embalagem passa de 45 para 39 s: hipótese adicional de eliminar 6 s por ciclo, não de retirar verificações de qualidade. O modelo ainda não decompõe os movimentos nem demonstra tecnicamente essa redução. É preciso cronoanálise, Yamazumi e validação do método. Recursos, chegadas, taxas de defeito e cobertura das inspeções ficam iguais. Postos de 20 s ficam sem margem nominal para variabilidade, que ainda não é simulada.

Resultado de oito horas, semente 7, execução `656ad257da0e411985e793c9be49a658`: 90.256 eventos confirmados; 1.440 iniciadas; **1.327 concluídas**, 90 retidas/reprovadas, 23 em processo; NG teste 2; lead time médio 8,10 min. Nenhuma placa aguardava em fila ao final. As 23 restantes estavam em operação: fila zero não significa WIP zero, e uma semente não comprova robustez industrial.

O perfil novo registra ciclo de referência de 19 s para o OEE do teste, correspondente à hipótese de novo método; perfis anteriores usam 26 s. A fórmula não mudou, mas os valores de OEE não têm a mesma referência de ciclo: o painel avisa ao comparar. Para comparação estrita de OEE seria necessário validar um ciclo ideal comum, em vez de escolhê-lo para produzir um percentual desejado.

Edite `LEAN_FULL_TIMES` em `lean_analysis.py` para alterar somente a nova hipótese. A tabela do estudo no painel apresenta os quatro cenários, incluindo filas finais de câmera e teste.
