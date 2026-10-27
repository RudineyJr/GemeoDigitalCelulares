# Editar tempos entre simulações

No painel, abra **Novo balanceamento — editar tempos e simular**.

1. Escolha Original, Lean local ou Lean ampliado como ponto de partida.
2. Edite a coluna Tempo (s), incluindo casas decimais se necessário.
3. Dê um nome diferente a cada hipótese, por exemplo “Bateria 18 e câmera 19”.
4. Informe turno, semente, inspeções ativas e taxa de defeito.
5. Escolha Direto no banco, que dispensa Docker, ou Via MQTT, que exige broker e coletor ativos.
6. Clique em Executar nova simulação e aguarde a confirmação.
7. Escolha o novo nome nos seletores A/B para comparar os gráficos. A tabela de estudo Lean continua restrita aos quatro perfis padronizados; hipóteses personalizadas aparecem nos seletores gerais.

Editar a tabela não altera execuções já salvas. Cada nova execução registra todos os tempos efetivamente usados na configuração do seu primeiro evento. A simulação salva somente após clicar no botão; reproduzir o histórico não aplica novos tempos.

Capacidades, sequência e chegada a cada 20 s continuam iguais. O forno permanece limitado a pelo menos 20 s neste modelo; reduzir sua permanência não muda o intervalo mínimo de entrada nem o número de posições. Não há validação automática de precedência das tarefas, ergonomia ou cobertura de um teste mais curto. Os tempos são hipóteses a justificar por análise do trabalho.

O campo de ciclo ideal comum da linha, usado pelo OEE, é independente dos tempos de processamento editados. Preserve uma referência tecnicamente justificada e igual entre cenários para comparar OEE. Os gráficos usam os tempos registrados em cada histórico.

## Reutilizar pelo terminal

Baixe o JSON pelo botão do editor e salve na pasta do projeto como `tempos-estacoes.json`. O formato associa nomes exatos a segundos; também é permitido fornecer somente os postos a alterar:

```json
{
  "Bateria": 18,
  "Câmera traseira": 19,
  "Teste funcional": 19
}
```

Depois execute na pasta do projeto:

```powershell
.\.venv\Scripts\python simulate.py --turno-horas 8 --semente 7 --tempos tempos-estacoes.json --nome-cenario "Meu balanceamento"
```

Acrescente `--mqtt` para transmitir. Com `--lean` ou `--lean-completo`, o arquivo sobrepõe os tempos dos postos informados e preserva o restante do perfil escolhido. Sem perfil Lean, os demais postos usam os tempos originais.

Os perfis enviados pelo editor são também salvos com nomes únicos em `cenarios/`. Esses JSON contêm apenas tempos e podem ser reutilizados com `--tempos cenarios/ARQUIVO.json`. Para manter um experimento reprodutível, registre também nome, semente, turno, probabilidades e inspeções: eles constam na configuração histórica do banco.
