# Construindo o gêmeo digital à mão, do começo

Este roteiro é para entender e reconstruir o projeto, mesmo sem ter acompanhado sua criação. Leia na ordem e execute um exercício de cada vez. Os exemplos estão em `tutorial/`; não alteram `processo.sqlite3` nem os históricos do painel principal. Não é necessário copiar todo o projeto novamente.

## 1. Primeiro, entenda o que estamos construindo

Queremos responder: quantas placas uma linha produz em um turno, onde elas esperam e onde os defeitos são encontrados? Para isso, escrevemos regras de funcionamento e deixamos um programa calcular os acontecimentos.

O computador não conhece uma impressora, uma placa ou uma inspeção. Nós precisamos dizer a ele:

1. Uma placa chega a cada 20 segundos.
2. Ela passa por uma sequência de estações.
3. Cada estação tem um tempo e um limite de atendimento simultâneo.
4. Se a estação estiver ocupada, a placa espera.
5. Algumas operações podem introduzir defeitos.
6. Inspeções podem detectar esses defeitos e retirar a placa.
7. Cada acontecimento é registrado para consulta posterior.

Isso é o **modelo da linha**. SimPy executa esse modelo. MQTT transporta os registros. SQLite guarda o histórico. O painel transforma esse histórico em desenhos e gráficos.

Fluxo atual: **simulate.py → MQTT/Mosquitto → collect.py → SQLite → app.py → HTML e JavaScript no navegador**.

Existe também o caminho direto: **simulate.py → SQLite**. É útil para estudar o modelo antes de adicionar a comunicação.

## 2. Prepare o lugar onde escrever e executar

Abra o VS Code. Em **Arquivo → Abrir pasta**, selecione:

```text
C:\Users\autom\OneDrive\Documents\GemeoDigitalCelulares
```

Abra **Terminal → Novo Terminal**. O terminal pode ser PowerShell. Todos os comandos deste guia são executados nele, a partir dessa pasta.

Distinga os três lugares:

| Lugar | O que você faz ali |
|---|---|
| Editor do VS Code | Escreve e salva arquivos Python, HTML e configurações. |
| Terminal | Digita comandos para executar os arquivos. |
| Navegador | Usa o painel que o Streamlit disponibiliza. |

Se estivesse começando em uma pasta vazia, primeiro criaria um ambiente Python e instalaria as bibliotecas:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install simpy streamlit paho-mqtt
```

**No seu projeto isso já foi feito.** Não precisa refazer. `.venv` guarda o interpretador e as bibliotecas do projeto. Usar seu caminho completo dispensa ativar o ambiente.

Você escreveria também `requirements.txt` para registrar as dependências. Outra pessoa instala essas dependências com:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## 3. Faça uma placa consumir tempo, sem fila ainda

Abra `tutorial/01_relogio.py`. Execute:

```powershell
.\.venv\Scripts\python tutorial/01_relogio.py
```

Ele mostra a entrada no segundo 0 e a saída no segundo 15. O núcleo é:

```python
def placa(env):
    print(env.now, "entrou")
    yield env.timeout(15)
    print(env.now, "saiu")

env = simpy.Environment()
env.process(placa(env))
env.run()
```

Leia cada parte assim:

| Código | Significado |
|---|---|
| `import simpy` | Disponibiliza a biblioteca instalada. |
| `def placa(env):` | Define o comportamento que será executado para a placa. |
| `Environment()` | Cria o relógio e a agenda de acontecimentos. |
| `env.now` | Consulta o horário simulado atual. |
| `env.timeout(15)` | Cria um evento que ocorrerá 15 unidades de tempo depois. |
| `yield` | Suspende este processo até o evento acontecer; outros podem continuar. |
| `env.process(...)` | Coloca o comportamento da placa na agenda. |
| `env.run()` | Executa a agenda até não haver eventos pendentes. |

Neste projeto, escolhemos que uma unidade equivale a um segundo. SimPy não exige essa unidade por conta própria.

**Quinze segundos simulados não exigem esperar quinze segundos reais.** O relógio salta entre acontecimentos. A opção de tempo real do projeto acrescenta a espera necessária para acompanhar o relógio real.

Experimento: mude 15 para 30, salve e execute de novo. A saída deve passar para o segundo 30. Você acabou de mudar o tempo de uma operação.

## 4. Crie a máquina e deixe uma fila se formar

Execute:

```powershell
.\.venv\Scripts\python tutorial/02_maquina_e_fila.py
```

Três placas chegam nos segundos 0, 10 e 20. A impressora leva 15 segundos por placa e atende uma de cada vez.

| Placa | Chegada | Início | Fim | Espera |
|---|---:|---:|---:|---:|
| P1 | 0 | 0 | 15 | 0 |
| P2 | 10 | 15 | 30 | 5 |
| P3 | 20 | 30 | 45 | 10 |

A máquina é criada assim:

```python
impressora = simpy.Resource(env, capacity=1)
```

E utilizada assim:

```python
with impressora.request() as pedido:
    yield pedido
    yield env.timeout(15)
```

`request()` pede uma vaga. `yield pedido` espera a vaga. O processamento só começa depois da liberação do pedido. Ao sair do bloco `with`, a vaga é devolvida automaticamente. **A fila surge da disputa pela máquina; não precisamos sortear um tamanho de fila.**

`env.process(...)` permite que várias placas estejam em andamento simultaneamente. Enquanto uma placa ocupa a impressora, outra pode estar em outra estação.

Experimento: altere `capacity=1` para `capacity=2`. Agora duas placas podem usar esse recurso ao mesmo tempo. Isso representa duas posições paralelas, não uma máquina duas vezes mais rápida.

## 5. Transforme uma estação em uma linha

No exercício `03_linha_e_inspecao.py`, as estações estão em uma lista:

```python
etapas = [("Impressora", 15), ("SPI", 5), ("Teste funcional", 26)]
maquinas = {nome: simpy.Resource(env, capacity=1) for nome, _ in etapas}
```

Cada placa percorre a lista, pede a máquina correspondente e aguarda seu tempo. O `for` significa “repita para cada estação”. Um dicionário associa cada nome ao seu recurso.

No projeto completo, essa configuração está em **core.py**, nas listas `SMT_PROCESS` e `MANUAL_PROCESS`. A soma das duas é `PROCESS`. O comportamento está em **simulate.py**, principalmente na função interna `piece_flow`.

As estações atuais são:

| Trecho | Estações e tempos nominais em segundos |
|---|---|
| SMT | Impressora 15; SPI 5; Pick & Place 1 a 5, 12 cada; forno 180; AOI 5; saída SMT 1. |
| Montagem | FW 14; PCBA no chassi 18; display 16; bateria 27; alto-falante 15; microfone 21; câmera traseira 24; câmera frontal 13; botões/vibra 22; tampa 17; teste funcional 26; embalagem 19. |

Quase todas têm capacidade 1. O forno tem 9 posições e controle de entrada com intervalo mínimo de 20 segundos. Por isso, **180 segundos dentro do forno não significam uma única placa saindo a cada 180 segundos**. Há placas em processamento simultâneo.

Para criar uma estação nova de verdade no projeto, você faria estas tarefas:

1. Definiria nome, posição no fluxo, duração e capacidade em `core.py`.
2. Acrescentaria regras específicas em `simulate.py` se ela inspecionar, retirar ou transformar uma placa. Uma operação simples já aproveita o percurso genérico.
3. Conferiria como o novo nome aparece no desenho e nos gráficos HTML/JavaScript. Alguns cálculos reconhecem explicitamente SPI, AOI, teste e embalagem.
4. Rodaria uma simulação pequena e verificaria fila, entrada e saída antes de simular um turno.

Adicionar um desenho sozinho não cria uma estação simulada. Adicionar uma estação ao modelo também não garante que o desenho existente a acomode corretamente.

## 6. Acrescente defeitos e inspeções

Execute a mesma miniatura com e sem SPI:

```powershell
.\.venv\Scripts\python tutorial/03_linha_e_inspecao.py
.\.venv\Scripts\python tutorial/03_linha_e_inspecao.py --sem-spi
```

São dez placas, com taxa didática de defeito de 30% para facilitar a observação. Essa taxa **não altera** o projeto principal. O exemplo usa somente um tipo de defeito.

Com a semente 7 deste exercício, o resultado esperado é: com SPI, 6 concluídas e 4 retidas; sem SPI, 6 concluídas e 4 NG no teste. A inspeção antecipa a retirada dos defeitos; ela não conserta as placas. Como este exemplo espera todas terminarem, a quantidade boa final é igual, mas o tempo e o local da detecção mudam.

```python
defeituosa = sorteador.random() < 0.30
```

`random()` produz um número entre 0 e 1. A regra acima dá 30% de probabilidade de defeito. Isso não obriga que exatamente três das dez placas tenham defeito.

Outra decisão representa detectar o defeito:

```python
if nome == "SPI" and defeituosa and sorteio_deteccao < 0.95:
    return
```

`return` encerra o percurso daquela placa. A inspeção só retém uma placa defeituosa se o sorteio indicar detecção. **Gerar defeito e detectar defeito são decisões diferentes.**

No modelo completo: impressora pode gerar defeito de pasta; o último Pick & Place pode gerar defeito de colocação; forno pode gerar defeito de refusão. SPI procura pasta. AOI procura os três defeitos visuais modelados. O teste funcional detecta todos os defeitos modelados que escaparam, por hipótese didática.

As taxas padrão são 2% por origem e 95% de detecção nas inspeções. Não há câmera nem algoritmo de imagem: são regras probabilísticas. Retidas saem do fluxo para análise; não há retorno de retrabalho implementado.

A semente (`seed`) fixa a sequência dos sorteios. Usar a mesma semente e a mesma organização de sorteios ajuda a comparar condições equivalentes. Uma única semente não substitui várias repetições em uma análise estatística.

## 7. Registre os acontecimentos como dados

Até aqui, usamos `print`. Para calcular gráficos depois, precisamos guardar os acontecimentos.

Execute:

```powershell
.\.venv\Scripts\python tutorial/04_eventos_e_banco.py
```

O exemplo cria **tutorial/aprendizado.sqlite3**. Ele grava três tipos de evento:

| Evento | O que significa |
|---|---|
| fila | A placa chegou à estação e pediu atendimento. |
| entrada | A placa conseguiu o recurso e começou a operação. |
| saida | A placa terminou a operação, com seu resultado. |

Pode haver fila e entrada no mesmo segundo se a máquina estiver livre. A espera é `entrada − fila`; a duração de processamento é `saida − entrada`.

O exercício usa SQL básico: `CREATE TABLE` cria a tabela; `INSERT` adiciona uma linha; `SELECT` consulta; `commit()` confirma a gravação. Reexecutar limpa apenas a tabela desse exercício.

No projeto completo, `record` em `simulate.py` monta um dicionário para cada acontecimento. Exemplo ilustrativo:

```json
{
  "id_evento": "identificador-unico-do-evento",
  "sequencia": 12,
  "execucao": "identificador-da-simulacao",
  "id_peca": "P0001",
  "estacao": "SPI",
  "tempo_simulado": 20,
  "evento": "saida",
  "resultado": "aprovada",
  "detalhes": {"motivo": ""}
}
```

Esse JSON é uma ilustração do formato, não um comando para colar no terminal. `execucao` separa os históricos. `id_peca` identifica a placa dentro da execução. `id_evento` permite reconhecer um reenvio. `sequencia` permite conferir continuidade. O primeiro evento também registra a configuração usada.

**Uma placa gera muitos eventos.** Milhares de eventos não significam milhares de placas concluídas. Concluída, no projeto, é a placa que saiu aprovada da embalagem.

`core.py` cria o banco principal, valida eventos e grava lotes. O arquivo `processo.sqlite3` é o histórico permanente usado pelo painel, não o broker.

## 8. Faça seu primeiro painel, antes de MQTT

Depois do exercício 04, execute:

```powershell
.\.venv\Scripts\python -m streamlit run tutorial/05_painel.py --server.port 8503
```

Abra `http://localhost:8503`. Você verá três concluídas, a tabela e a curva acumulada. O exercício usa uma porta diferente da interface principal. Para encerrá-lo, pressione **Ctrl+C** no terminal que o iniciou.

Leia o arquivo: ele abre SQLite, consulta linhas e usa `st.metric`, `st.dataframe` e `st.line_chart`. Esse é o painel mínimo que você escreveria primeiro.

O painel real é mais elaborado: **app.py** consulta o banco e cria seletores; **painel.html** desenha uma execução; **comparacao.html** compara duas; **metrics.js** calcula os indicadores no navegador. Usamos HTML/JavaScript para aproximar a aparência do HTML de referência que você enviou.

O botão **Reproduzir** percorre o histórico salvo. Ele não cria novas placas nem executa o SimPy novamente. O desenho se sincroniza com os eventos selecionados.

## 9. Adicione MQTT quando o modelo e o banco estiverem claros

MQTT é o protocolo de mensagens. Mosquitto é o programa que funciona como broker. Docker executa o Mosquitto em um contêiner. Paho é a biblioteca Python usada para se conectar ao broker.

O publicador envia para um tópico; o broker entrega aos assinantes desse tópico. Um tópico é um endereço de assunto, como `celulares/eventos`.

Para experimentar sem tocar nos históricos, abra o Docker Desktop e, no terminal da pasta principal, execute:

```powershell
docker compose up -d
.\.venv\Scripts\python tutorial/06_receber_mqtt.py
```

Aguarde **Pronto para receber**. Mantenha esse terminal aberto. Abra **outro terminal** na mesma pasta e execute:

```powershell
.\.venv\Scripts\python tutorial/07_enviar_mqtt.py
```

O segundo terminal informa a confirmação do broker; o primeiro mostra o JSON recebido. Os exercícios usam `celulares/tutorial/eventos`, separado do tópico de produção. O assinante didático apenas imprime: não grava no banco.

Se não conectar, confira Docker aberto e o serviço com `docker compose ps`. Se o publicador confirmar mas o receptor não mostrar nada, confira se o assinante já estava pronto e se o tópico é igual. O exercício não solicita mensagem retida; um assinante iniciado depois não deve esperar receber esse exemplo antigo.

Depois de entender esse teste, o próximo passo de construção seria colocar o `INSERT` do exercício 04 dentro do tratamento da mensagem recebida. No projeto real isso é feito por **collect.py**: recebe, valida e grava.

O broker pode persistir estado de mensagens conforme sua configuração, mas **não é o banco de séries históricas que o painel consulta**. Esse papel aqui é do SQLite.

## 10. Entenda a proteção contra perda e duplicação

Na versão completa, não basta publicar e confiar que todos os dados chegaram ao banco. Uma confirmação MQTT do broker não comprova que o coletor terminou de gravar.

**mqtt_transport.py** envia lotes e espera uma resposta do coletor depois da gravação confirmada no SQLite. Só então segue com o próximo lote. IDs únicos tornam o reenvio seguro contra duplicação de eventos.

No final, um manifesto permite conferir quantidade, sequência, resumo e uma assinatura dos identificadores dos eventos. A execução aparece como validada quando essas verificações passam. Isso verifica a integridade da entrega; não prova que as hipóteses industriais do modelo estão corretas.

`transmissoes/` contém cópias JSONL e manifestos para reenvio. `trace_validation.py` também confere a coerência do percurso das placas. Esses cuidados foram acrescentados porque a transmissão antiga podia perder mensagens e mostrar contagens menores no painel.

Nos exercícios MQTT simples não implementamos esse mecanismo completo. Eles servem para entender publicação e assinatura, não para substituir o transporte confiável.

## 11. Simule um turno e entenda as contagens

No modelo real, oito horas equivalem a 28.800 segundos simulados. Com uma chegada a cada 20 segundos, entram 1.440 placas no intervalo do turno. O programa interrompe no final do turno sem esperar esvaziar a linha.

Portanto:

```text
iniciadas = concluídas na embalagem + retidas/reprovadas + em processo
```

Uma placa ainda esperando ou em operação é WIP. Ela não é uma concluída nem uma reprovada.

Para executar novas simulações completas por MQTT, você manteria broker e coletor abertos. Os comandos abaixo são para quando quiser **gerar novos históricos**, não são necessários para estudar os exemplos:

Terminal do coletor:

```powershell
.\.venv\Scripts\python collect.py
```

Em outro terminal, depois da confirmação de inscrição:

```powershell
.\.venv\Scripts\python simulate.py --turno-horas 8 --semente 7 --sem-spi --sem-aoi --mqtt
.\.venv\Scripts\python simulate.py --turno-horas 8 --semente 7 --mqtt
```

O primeiro desliga ambas as inspeções. O segundo usa ambas ligadas, que é o padrão. Sem `--mqtt`, o simulador salva diretamente no banco; sem `--tempo-real`, calcula de forma acelerada.

Depois, abra o painel principal e selecione as duas execuções:

```powershell
.\.venv\Scripts\python -m streamlit run app.py --server.address 127.0.0.1
```

Comparar seletores só escolhe históricos existentes. Não muda uma execução já salva. Para comparar justamente, mantenha iguais duração, chegadas, taxas de defeito e semente; altere a intervenção que deseja estudar.

## 12. Transforme eventos em indicadores

Você escreveria as fórmulas só depois de confirmar os eventos. Hoje elas estão em **metrics.js**.

| Indicador | Como deve ser lido neste projeto |
|---|---|
| Concluídas | Saídas aprovadas da embalagem. |
| NG no teste | Reprovações no teste funcional, não todas as retenções da linha. |
| FPY | Aprovadas no teste funcional / total testadas. |
| RTY | Produto das taxas de aprovação das inspeções ativas; com WIP, os postos podem ter amostras diferentes. |
| WIP total | Placas iniciadas que ainda não concluíram nem foram retiradas/reprovadas. |
| WIP nas filas | Placas com pedido registrado, ainda sem início de atendimento naquela estação. |
| Custos | Estimativas com valores atribuídos a cada ocorrência, não despesas medidas. |

**O OEE atualmente exibido usa o teste funcional como referência:**

```text
OEE = aprovadas no teste × ciclo ideal de referência / tempo planejado
```

O ciclo de referência adotado é 26 segundos. A disponibilidade é assumida como 100%, pois ainda não modelamos paradas. Isso não é uma medição completa do OEE da linha inteira.

Exemplo dos históricos auditados de oito horas: Atual teve 987 aprovadas no teste, então `987 × 26 / 28800 × 100 = 89,10%`. Proposta teve 1047, resultando em `94,52%`. Atual tem 986 embaladas porque uma placa aprovada ainda não terminou a embalagem.

A queda de NG de 63 para 2 aparece diretamente no indicador de NG e na qualidade do teste. Não garante, sozinha, que o OEE passe de 30% para 95%. Para estudar uma diferença desse tamanho, precisamos representar e medir as perdas de disponibilidade, desempenho e qualidade que existem na situação atual. Não devemos alterar a fórmula para obter uma meta escolhida.

## 13. O que você teria escrito, na ordem

| Ordem de construção | Arquivos atuais correspondentes |
|---|---|
| Definir estações, tempos, capacidades e regras | `core.py` e configuração em `simulate.py`. |
| Fazer uma placa percorrer a linha | `simulate.py`: `simulate`, `piece_flow`, `source`. |
| Registrar os acontecimentos | `simulate.py`: `record`. |
| Criar tabelas e salvar eventos | `core.py`: `connect`, `save_many`. |
| Publicar e receber mensagens | `mqtt_transport.py` e `collect.py`. |
| Configurar o broker | `compose.yaml` e `mosquitto.conf`. |
| Conferir a integridade dos históricos | Manifestos em `core.py`, entrega em `mqtt_transport.py`, percurso em `trace_validation.py`. |
| Consultar dados e oferecer seletores | `app.py`. |
| Calcular indicadores e desenhar a interface | `metrics.js`, `painel.html`, `comparacao.html`. |
| Facilitar instalação e abertura | `requirements.txt`, `iniciar.ps1` e arquivos `.cmd`. |
| Conferir regras e evitar regressões | Arquivos `test_*.py` e `test_*.cjs`. |
| Registrar versões e compartilhar código | Git local e repositório no GitHub. |

`referencia-original.html` é a referência visual recebida; não é o simulador Python em execução. `backups/` contém cópias de segurança. `.venv/` é instalação local. `processo.sqlite3` contém dados gerados. O Git versiona o código; ambiente, históricos, backups e credenciais ficam fora dele conforme `.gitignore`.

No VS Code, procure os nomes com **Ctrl+Shift+F**. Para acompanhar o modelo, comece por `PROCESS` em `core.py`, depois `simulate`, `record`, `piece_flow`, `source` e `main` em `simulate.py`. `main` lê os argumentos do terminal e escolhe como executar e salvar. Não comece pelo HTML: ele mostra as consequências do modelo.

## 14. Confira o que você aprendeu

Antes de avançar, tente responder e confirmar executando:

1. Se dobrar o tempo da impressora, em que horários as três placas saem?
2. Por que a segunda placa precisa esperar no exercício 02?
3. Qual a diferença entre placa defeituosa e placa detectada pelo SPI?
4. Por que desligar o SPI pode aumentar o NG encontrado mais adiante?
5. Por que nove eventos no exercício 04 correspondem a três placas?
6. Por que abrir ou reproduzir o painel não inicia uma simulação?
7. Onde os dados ficam guardados depois que fechamos o simulador?
8. Por que o total aprovado no teste pode diferir do total embalado ao fim do turno?

Para conferir o projeto completo após uma alteração de código, execute:

```powershell
.\.venv\Scripts\python -m unittest -v
node test_metrics.cjs
node test_comparison.cjs
```

Os testes verificam regras específicas; não substituem calibrar os parâmetros com a linha real. Ainda faltam, entre outras extensões, sensores reais, visão computacional, paradas, tempos variáveis, retrabalho e validação industrial.

**Seu primeiro objetivo de estudo:** execute o exercício 01, altere o tempo e explique a saída. Depois faça o mesmo com a fila no exercício 02. Ao chegar ao exercício 07, você terá percorrido em miniatura o caminho que sustenta o projeto completo.
