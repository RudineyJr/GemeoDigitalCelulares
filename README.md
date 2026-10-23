# Gêmeo digital da linha de celulares — M2

SMT detalhada: Impressora de pasta → SPI → Pick & Place 1–5 → Forno de refusão → AOI → Saída SMT → 12 estações de montagem → embalagem.

## Executar

Nesta pasta, no PowerShell:

```powershell
./iniciar.ps1
```

Ou, com o ambiente já instalado:

```powershell
.\.venv\Scripts\python simulate.py --pecas 100
.\.venv\Scripts\python -m streamlit run app.py --server.address 127.0.0.1
```

Para MQTT, mantenha o Docker Desktop aberto, execute `docker compose up -d`, inicie `./.venv/Scripts/python collect.py` e aguarde a confirmação de inscrição. Em outro terminal:

```powershell
.\.venv\Scripts\python simulate.py --mqtt --pecas 100
```

Adicione `--tempo-real` para acompanhar o relógio em segundos reais. A reprodução no painel percorre os eventos sem executar novamente o modelo.

## Hipóteses do modelo SMT v2

Parâmetros didáticos, não calibrados com equipamentos reais:

- Impressora: 15 s; SPI: 5 s; cada Pick & Place: 12 s; forno: 180 s; AOI: 5 s; saída: 1 s.
- Uma placa por recurso, exceto forno: nove posições simultâneas, entrada espaçada em pelo menos 20 s. Aproximação de forno contínuo, sem perfil térmico nem transporte físico detalhado.
- Chegadas a cada 20 s. Filas ilimitadas; sem falhas mecânicas nesta versão.
- Defeito de pasta criado na impressora; colocação atribuída ao fim do quinto Pick & Place; refusão ao sair do forno. Cada origem tem probabilidade independente, padrão de 2% por placa que alcança a etapa.
- SPI detecta apenas defeito de pasta; AOI detecta qualquer um dos três tipos visuais modelados. Padrão: 95% de detecção condicional por placa defeituosa, sem falsos positivos.
- Retidas no SPI/AOI saem para análise externa, sem retorno. Não são automaticamente sucata e não há retrabalho modelado.
- Teste funcional detecta 100% dos defeitos modelados que escaparam; hipótese simplificadora, não capacidade universal de teste real.
- Uma placa com defeito latente pode receber aprovação na inspeção quando o defeito não é detectado. O painel não conhece esse estado oculto.
- Os tempos das 12 estações manuais seguem os valores nominais do cenário Atual do HTML.
- Cinco sorteios por placa e semente fixa permitem repetir as mesmas condições aleatórias com inspeções ligadas/desligadas.

## Ajustar as inspeções

```powershell
.\.venv\Scripts\python simulate.py --mqtt --pecas 100 --defeitos 0.10 --defeitos-colocacao 0.05 --defeitos-refusao 0.03 --deteccao-spi 0.95 --deteccao-aoi 0.95
.\.venv\Scripts\python simulate.py --mqtt --pecas 100 --sem-spi --sem-aoi
```

`--defeitos` define a taxa de pasta e o valor padrão das outras origens quando não informadas. Probabilidades usam a escala 0 a 1.

## Organização para estudar o SimPy

- `core.py`: nomes, tempos e capacidades dos recursos; SQLite e validação.
- `simulate.py`: `Environment` é o relógio; `Resource` representa as máquinas; `piece_flow` é o percurso de cada placa; `yield request` aguarda uma máquina; `yield env.timeout(...)` representa processamento; `source` cria placas; `env.run()` executa a agenda.
- `collect.py`: recebe o tópico MQTT `celulares/eventos` e grava no banco.
- `app.py`: lê os eventos e envia o histórico à interface.
- `painel.html`: desenhos, reprodução e indicadores calculados dos eventos.

Contrato JSON: `id_evento`, `execucao`, `id_peca`, `estacao`, `tempo_simulado` em segundos, `evento` (fila/entrada/saida), `resultado` (pendente/aprovada/reprovada) e `detalhes` (configuração e motivo da retenção). MQTT usa QoS 1; a chave única evita duplicatas. A migração do banco preserva os eventos antigos.

No painel, WIP inclui filas e operações; ocupação do forno é normalizada por suas nove posições; FPY usa somente o teste funcional. Contagens do SPI/AOI são retenções, não custos nem sucata. Execuções antigas mantêm sua visualização agregada da SMT.

## Verificar

```powershell
.\.venv\Scripts\python -m unittest -v
```

Próximas extensões: retorno de retrabalho, falsos positivos, cobertura de defeitos por inspeção, variabilidade dos tempos, WIP limitado, falhas/reparos e comparação simultânea de cenários.

## Turno de trabalho

`./.venv/Scripts/python simulate.py --turno-horas 8` simula o intervalo [0, 28800) segundos e substitui a quantidade `--pecas`. Entram até 1440 placas (uma a cada 20 s); peças ainda na linha permanecem como WIP, sem esvaziamento após o fim. No modo por quantidade, a simulação continua até todas terminarem. Adicione `--mqtt` para transmitir; sem `--tempo-real`, o cálculo é acelerado. As 8 horas são produtivas contínuas: pausas, refeições e paradas ainda não são modeladas. O painel usa a duração do turno na reprodução do histórico.

## Gráficos e hipóteses de métricas

O painel inclui RTY, FPY, WIP nas filas, falhas por posto, custo da não qualidade estimado, radar e produção acumulada. `metrics.js` calcula as séries a partir dos eventos, em ordem temporal; `node test_metrics.cjs` verifica as fórmulas.

RTY: produto das frações aprovadas na primeira passagem em SPI, AOI e teste funcional ativos. Enquanto houver WIP, as amostras dos postos podem diferir; o resultado é uma estimativa acumulada, sem incluir peças não avaliadas em cada denominador. FPY: aprovadas no teste / total testadas. Sem avaliações suficientes, mostra —.

WIP nas filas conta somente eventos fila ainda sem entrada; WIP total também inclui operações. A média nas filas é ponderada pelo tempo. Retenções são contabilizadas em SPI/AOI e reprovações no teste.

Custos ajustáveis no painel: SPI R$ 15 por retenção, AOI R$ 60 por retenção e teste R$ 240 por reprovação, com referência de R$ 240 por placa iniciada. São hipóteses de tratamento da ocorrência, sem afirmar que toda retenção é sucata. Valores ajustados apenas recalculam a análise; não alteram os dados históricos nem o SimPy.

Radar: FPY, RTY, OEE simplificado do teste funcional (placas aprovadas no teste / [tempo / tempo de ciclo do posto]) e 1 − COPQ (1 − custo estimado / valor de referência das placas iniciadas). OEE industrial completo não está modelado. O radar limita os eixos a 0–100%; a tabela apresenta os valores calculados. Comparação de duas execuções ainda é uma etapa separada.

## Comparar dois cenários no mesmo painel

Ative “Comparar dois cenários” e escolha as execuções nos seletores “Cenário A — Atual” e “Cenário B — Proposta”. Os rótulos exibem identificador curto, inspeções, duração e semente. A comparação não muda os parâmetros nem executa novas simulações.

Os gráficos sobrepõem Atual em rosa contínuo e Proposta em verde tracejado. Barras e radar também apresentam ambos; a tabela calcula a diferença absoluta B − A (em pontos percentuais nas linhas percentuais). O relógio é comum e termina na menor duração disponível. Custos são hipóteses iguais para ambos.

O painel avisa sobre execuções iguais, durações distintas, condições de entrada diferentes e históricos com lacunas. Curvas de WIP e lead time ficam indisponíveis para históricos incompletos. Desative a comparação para voltar ao desenho das estações e à análise individual. Use `node test_comparison.cjs` para verificar a renderização e as diferenças calculadas.

## Correção da coleta MQTT — auditoria de 22/10/2026

A versão anterior esperava somente a confirmação do broker e enviava eventos mais rápido do que o coletor conseguia gravar. O Mosquitto registrou descarte de mensagens por saturação da fila do assinante. Por isso os totais no terminal eram maiores que os do painel. Os históricos antigos foram preservados; os incompletos não podem ser usados na comparação.

Agora o envio ocorre em lotes, com uma confirmação de aplicação após o COMMIT no SQLite, antes do próximo lote. Um manifesto final verifica quantidade, sequência, identificadores dos eventos e resumo de produção. O terminal só informa sucesso depois dessa validação. Uma execução validada aparece com ✓ validada no painel. Reenvios usam os mesmos IDs e não duplicam eventos.

A configuração do broker inclui persistência em volume Docker e fila limitada; o controle de ritmo e a confirmação do coletor são a proteção principal contra saturação. O coletor precisa estar aberto. Inicie o coletor e aguarde a mensagem de inscrição confirmada antes de simular.

Cada nova execução gera `transmissoes/ID.jsonl` e `transmissoes/ID.manifest.json`. O JSONL é uma cópia dos eventos, e o manifesto comprova que a geração terminou. Em caso de falha de envio, com broker e coletor ativos:

```powershell
.\.venv\Scripts\python simulate.py --reenviar transmissoes/ID.jsonl
```

O reenvio não roda novamente o SimPy. Interrupções durante a própria geração em tempo real podem deixar um arquivo sem manifesto; esses arquivos não são aceitos como simulação encerrada. Nas simulações aceleradas a cópia completa é criada antes de começar a transmissão.

Os comandos do VS Code continuam iguais. Para aplicar mudanças futuras no coletor, encerre a instância antiga com Ctrl+C antes de abrir a atualizada. Apenas um coletor é necessário por banco de dados.

## OEE do Teste Funcional Final

A referência do OEE é a saída do Teste funcional, e não a Embalagem nem o intervalo de chegada das placas. `OEE = aprovadas no teste × ciclo ideal de referência / tempo programado transcorrido`. O ciclo atual é de 26 s (nominal usado como hipótese ideal); o painel mostra esse valor explicitamente. O tempo programado vai do início do turno ao instante selecionado, incluindo o período inicial de abastecimento da linha.

Sem eventos de falhas ou paradas, a disponibilidade é assumida em 100%; não é uma medição de disponibilidade real. Desempenho = total testadas × ciclo ideal / tempo programado; qualidade = aprovadas / total testadas; o produto dos três fatores equivale à fórmula direta. OEE permanece — até haver um teste concluído. As peças aprovadas no teste mas ainda não embaladas entram no OEE, porém não no cartão Concluídas. Não foram alterados os eventos ou os resultados das duas simulações.

## Versionamento Git

O repositório contém o código, as configurações, a documentação, os testes e o HTML de referência. O banco SQLite, os backups, os arquivos de transmissão, os logs, as capturas de desenvolvimento e o ambiente .venv ficam somente no computador e não entram nos commits.

Ao copiar ou clonar o projeto em outra pasta, execute `iniciar.ps1` para preparar o ambiente. Para criar os primeiros dados, execute uma simulação; o banco vazio é criado automaticamente. Os arquivos ignorados não constituem backup: preserve o banco e os arquivos de transmissão separadamente quando necessário.

Comandos usuais no terminal do VS Code, nesta pasta:

```powershell
git status
git add .
git commit -m "Descreva a alteração"
git log --oneline
```

O Git local registra as versões. A publicação no GitHub ou outro servidor é uma etapa separada.
