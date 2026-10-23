# Quem é quem no projeto

Os dados desta etapa são simulados. Não há máquinas nem câmeras reais conectadas.

Fluxo: SimPy → mensagens MQTT → Mosquitto → coletor → SQLite → Streamlit → navegador.

| Papel | Nome | Onde está | O que faz |
|---|---|---|---|
| Backend/simulador | SimPy com Python | simulate.py | Cria placas, disputa recursos, forma filas, processa operações e decide inspeções pelas regras configuradas. |
| Configuração e banco | Código comum | core.py | Define estações, tempos e capacidades; abre o SQLite e valida a gravação. |
| Comunicação | MQTT | Usado por simulate.py e collect.py | Define como enviar e receber mensagens. Não é o banco nem o programa broker. |
| Broker | Mosquitto | compose.yaml e mosquitto.conf | Recebe os eventos no tópico celulares/eventos e distribui aos assinantes. |
| Execução do broker | Docker Desktop | Aplicativo do Windows | Executa o Mosquitto em um contêiner. Não executa o SimPy nesta versão. |
| Pipeline/coleta | Coletor Python | collect.py | Assina o tópico e grava os eventos recebidos no SQLite. |
| Banco de dados | SQLite | processo.sqlite3 | Guarda eventos das execuções, peças, estações, horários simulados e resultados. |
| Servidor do frontend | Streamlit | app.py | Lê o banco, oferece seletores e entrega os dados à interface. Não assina MQTT diretamente. |
| Visualização do processo | HTML/JavaScript | painel.html | Desenha as estações e reconstrói o estado com base nos eventos. |
| Comparação | HTML/JavaScript | comparacao.html | Sobrepõe resultados dos dois históricos escolhidos. |
| Cálculo dos indicadores | JavaScript | metrics.js | Calcula séries de FPY, RTY, filas, custos e outros indicadores no navegador. |
| Qualidade do histórico | Validação Python | trace_validation.py | Detecta lacunas que impedem reconstruir o estado das peças. |

## Como abrir

- Abrir painel.cmd: inicia a consulta e visualização dos históricos existentes.
- Iniciar broker.cmd: inicia o Mosquitto; exige Docker Desktop aberto.
- Abrir coletor.cmd: inicia a recepção e gravação dos eventos.
- iniciar.ps1: prepara dependências e abre o painel.
- README.md: comandos para rodar novas simulações.

Abrir o painel não inicia uma nova simulação. Reproduzir percorre eventos salvos. Sem --mqtt, o simulador grava diretamente no banco e não passa pelo broker. Custos do painel são hipóteses de análise, não despesas medidas.

## Relação com os grupos

Backend: simulate.py. Banco: core.py e processo.sqlite3. Pipeline: MQTT, Mosquitto e collect.py. Frontend: app.py e gráficos. Digital Twin: representação das estações em painel.html, sincronizada aos eventos simulados. Dispositivos: ainda não existem sensores ou câmeras publicando; sua integração é uma próxima etapa. A decisão de SPI/AOI hoje é probabilística, sem análise de imagens.
