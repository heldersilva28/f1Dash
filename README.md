# F1 Dash — painel para o segundo monitor

Painel gratuito para o **EA SPORTS F1 25** (incluindo o **2026 Season Pack**). Lê a telemetria que o próprio jogo envia e mostra num segundo monitor um ecrã diferente para **corrida**, **qualificação** e **treinos livres**. O ecrã muda sozinho conforme a sessão em que estás.

Não precisa de SimHub nem de nenhum programa pago. Só precisa de **Python 3.10 ou mais recente** e não instala mais nada.

![Ecrã da corrida do F1 Dash](imagens/corrida.png)

*Capturas tiradas no modo de demonstração (`Iniciar-demo.bat`), com dados simulados.*

---

## 1. Instalar o Python (só da primeira vez)

1. Vai a <https://www.python.org/downloads/> e instala a versão mais recente.
2. Na primeira janela do instalador marca **"Add Python to PATH"**.

## 2. Configurar o jogo

No F1 25: **Definições → Definições de telemetria**

| Opção | Valor |
|---|---|
| Telemetria UDP | Ligada |
| Modo de difusão UDP | Desligado |
| Endereço IP UDP | `127.0.0.1` se jogas no mesmo PC |
| Porta UDP | `20777` |
| Frequência de envio UDP | 20 Hz ou mais (60 Hz é o ideal) |
| Formato UDP | **2026** se usas o 2026 Season Pack, **2025** com os carros de 2025 |
| A tua telemetria | Pública ou restrita, tanto faz: os dados do teu carro chegam sempre |

> Se já jogavas F1 25 antes do Season Pack, o formato pode ter ficado em **2025**. Muda-o à mão para **2026**.

**Consola (PS5 / Xbox):** no *Endereço IP UDP* põe o IP do PC onde corre o painel. Para o saberes, abre a Linha de Comandos no PC, escreve `ipconfig` e usa o "Endereço IPv4".

## 3. Abrir o painel

- Faz **duplo clique em `Iniciar.bat`**. O painel abre no browser em <http://localhost:8080>.
- Arrasta a janela para o segundo monitor e carrega **F11** para ecrã inteiro.
- Da primeira vez, o Windows pode perguntar se deixas o Python usar a rede. Escolhe **Permitir**.

Se preferires uma janela sem barras, com o Chrome instalado:
`start chrome --app=http://localhost:8080 --start-fullscreen`

**Experimentar sem o jogo:** usa `Iniciar-demo.bat`, que simula uma corrida, uma qualificação ou uns treinos com pacotes iguais aos do jogo.

## 4. O que aparece em cada ecrã

### Corrida

![Ecrã da corrida](imagens/corrida.png)

- Classificação com três vistas: **Para ti** (quem está à frente aparece com "−", quem está atrás com "+"), **Líder** e **Intervalo** para o carro da frente. Com **Auto** ligado, as vistas alternam a cada 8 s.
- A tua linha tem a cor da tua equipa e a etiqueta **TU**. Se jogas com um piloto que já existe, aparece o código dele (por exemplo NOR).
- Carro da frente e de trás: diferença, pneus e ritmo comparado com as últimas 5 voltas. Mostra também quando o Overtake (2026) ou o DRS (2025) fica ao alcance.
- Tempos e setores, com as cores roxo, verde e amarelo.
- Desenho do carro com o dano de cada peça. Os anéis à volta mostram a vida dos pneus, as temperaturas da superfície e do interior, e a do travão.
- Ritmo das últimas voltas, janela de box, e a posição em que voltas à pista se parares agora (dada pelo próprio jogo).
- Unidade motriz, bateria ERS, aero ativa, combustível e mensagens da direção de corrida.

### Qualificação

![Ecrã da qualificação](imagens/qualificacao.png)

- Tabela com a linha de corte, ajustada à sessão (Q1, Q2 ou Q3) e ao número de carros.
- Delta ao vivo em relação à tua melhor volta, previsão do tempo da volta e da posição.
- Mini-setores: 8 por setor, comparados com a tua melhor volta e com a melhor da sessão.
- Volta ideal, margem para o corte, diferença para a pole.
- Se ainda tens tempo para mais uma tentativa, tráfego à tua volta, temperatura dos pneus e conjuntos de pneus disponíveis.

### Treinos livres

![Ecrã dos treinos livres](imagens/treinos.png)

- Programa da sessão automático, escolhido pelo tipo de treino. Cada tarefa marca-se sozinha com o que fazes em pista e mostra o progresso (por exemplo "5 de 8 voltas seguidas"):
  - **TL1:** reconhecimento da pista, testar os 3 compostos e medir o desgaste dos pneus.
  - **TL2:** simulação de qualificação, simulação de corrida (8 voltas seguidas) e medir o consumo.
  - **TL3:** simulação de qualificação, confirmar o ritmo de corrida (5 voltas) e o desgaste.
  - **Treino único** (fins de semana curtos): reconhecimento, qualificação, corrida e consumo.
- Stints e ritmo do stint atual: média, degradação por volta, consistência e projeção das próximas voltas.
- Os teus setores comparados com os melhores da sessão, e o speed trap.
- Desgaste de cada pneu por volta e vida estimada.
- Consumo de combustível por volta e quanto combustível levar para a corrida. As voltas da corrida são lidas automaticamente, por esta ordem:
  1. o número que o jogo envia;
  2. as voltas da última corrida que fizeste nesse circuito;
  3. o número oficial de voltas do circuito, ajustado à duração das tuas corridas. O painel aprende essa duração sozinho na primeira corrida (por exemplo 50%);
  4. a distância completa.

  O ecrã mostra de onde veio o número. A memória fica no ficheiro `memoria.json`.

O botão ⚙ no canto inferior direito tem as definições: escolher o ecrã à mão e, só se o automático falhar, pôr as voltas da corrida à mão.

## 5. Bom saber

- Alguns valores precisam de **1 ou 2 voltas completas** com o painel aberto antes de aparecerem: consumo, desgaste por volta, vida dos pneus e delta ao vivo. Até lá aparece "a calcular…".
- O delta ao vivo usa a tua melhor volta **feita com o painel aberto**.
- O jogo não envia o desgaste dos pneus dos outros carros, por isso só aparece o do teu.
- Os dados estão confirmados contra a especificação oficial da EA para os formatos 2025 e 2026. Ao arrancar, o painel verifica o tamanho de todos os pacotes.

## 6. Problemas

| Sintoma | O que fazer |
|---|---|
| Fica em "À espera do jogo…" | Confirma a porta 20777, o IP e que a telemetria UDP está ligada. Na consola, confirma o IP do PC. |
| "Estão a chegar dados mas num formato que não conheço" | Muda o Formato UDP para 2026 ou 2025. |
| "Não consegui abrir a porta UDP" | Fecha outros programas de telemetria ou usa outra porta: `python f1dash.py --porta-udp 20778` (e põe a mesma porta no jogo). |
| Queres usar com outro programa ao mesmo tempo | No jogo, envia para este painel. Se o outro programa tiver reencaminhamento UDP, usa-o. |

Opções da linha de comandos: `python f1dash.py --help`
