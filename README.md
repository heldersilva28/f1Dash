<div align="center">

# 🏎️ F1 Dash

### O teu engenheiro de corrida no segundo monitor

Painel de telemetria em tempo real para o **EA SPORTS F1 25** e o **2026 Season Pack**.<br>
Um ecrã próprio para **corrida**, **qualificação** e **treinos livres**, que muda sozinho conforme a sessão.

<br>

![EA SPORTS F1 25](https://img.shields.io/badge/EA_SPORTS-F1_25-E10600?style=for-the-badge&logo=ea&logoColor=white)
![Season Pack 2026](https://img.shields.io/badge/2026-Season_Pack-FF8000?style=for-the-badge)
![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Zero dependências](https://img.shields.io/badge/dependências-zero-2EA043?style=for-the-badge)
![Grátis](https://img.shields.io/badge/preço-grátis-8B5CF6?style=for-the-badge)
[![Testes](https://img.shields.io/github/actions/workflow/status/heldersilva28/f1Dash/testes.yml?branch=main&style=for-the-badge&label=testes)](https://github.com/heldersilva28/f1Dash/actions/workflows/testes.yml)

<br>

[**Começar**](#-começar-em-3-passos) · [**Os ecrãs**](#-os-três-ecrãs) · [**Tablet e telemóvel**](#-no-tablet-ou-telemóvel) · [**Configurar o jogo**](#-configurar-o-jogo) · [**Problemas**](#-problemas-frequentes)

<br>

<img src="imagens/corrida.png" alt="Ecrã de corrida do F1 Dash: classificação, carro da frente e de trás, tempos, estado do carro, estratégia e unidade motriz" width="100%">

<sub>Ecrã de corrida no modo de demonstração, com dados simulados.</sub>

</div>

---

## ✨ Porquê o F1 Dash

<table>
<tr>
<td width="33%" valign="top">

### 🔌 Liga e corre
Sem SimHub, sem programas pagos, sem `pip install`. Só **Python 3.10+** e um duplo clique.

</td>
<td width="33%" valign="top">

### 🧠 Sabe onde estás
Deteta se estás em corrida, qualificação ou treinos e mostra o ecrã certo, sem tocares em nada.

</td>
<td width="33%" valign="top">

### 📡 Dados do próprio jogo
Lê a telemetria UDP oficial da EA, validada contra a especificação dos formatos **2025** e **2026**.

</td>
</tr>
<tr>
<td width="33%" valign="top">

### 🎯 Pensado para decidir
Janela de box, posição à saída do pit, margem para o corte, combustível para a corrida. Números que mudam o que fazes a seguir.

</td>
<td width="33%" valign="top">

### 📱 Monitor, tablet ou telemóvel
Funciona com PC, PS5 ou Xbox. Sem segundo monitor? Abre o painel no tablet ou no telemóvel, com uma vista própria.

</td>
<td width="33%" valign="top">

### 🚨 Alertas de relance
Chuva a caminho, pneus no limite, bandeiras, asa partida, combustível curto: aparecem em grande, por cima de tudo.

</td>
</tr>
</table>

---

## 🚀 Começar em 3 passos

**1. Instala o Python** (só da primeira vez)

Descarrega a versão mais recente em <https://www.python.org/downloads/>. Na primeira janela do instalador, marca **"Add Python to PATH"**.

**2. Liga a telemetria no jogo**

Em **Definições → Definições de telemetria**, liga a *Telemetria UDP* na porta `20777`. Tens a tabela completa em [Configurar o jogo](#-configurar-o-jogo).

**3. Abre o painel**

Faz **duplo clique em `Iniciar.bat`**. O painel abre em <http://localhost:8080>. Arrasta a janela para o segundo monitor e carrega **F11**.

> [!TIP]
> **Ainda sem o jogo aberto?** Usa `Iniciar-demo.bat` e escolhe corrida, qualificação ou treinos para ver o painel a funcionar com dados simulados.

<details>
<summary><b>Outras formas de abrir</b></summary>

<br>

Janela sem barras do browser, se tens o Chrome:

```bat
start chrome --app=http://localhost:8080 --start-fullscreen
```

macOS ou Linux, pela linha de comandos:

```bash
python3 f1dash.py
```

Modo demo pela linha de comandos (`corrida`, `qualificacao` ou `treinos`):

```bash
python3 f1dash.py --demo corrida
```

Da primeira vez, o Windows pode perguntar se deixas o Python usar a rede. Escolhe **Permitir**.

</details>

---

## 📸 Os três ecrãs

### 🏁 Corrida

<img src="imagens/corrida.png" alt="Ecrã de corrida" width="100%">

| | |
|---|---|
| **Classificação** | Três vistas: **Para ti** (quem está à frente com "−", atrás com "+"), **Líder** e **Intervalo**. Com **Auto** ligado, alternam a cada 8 s. A tua linha leva a cor da equipa e a etiqueta **TU**. |
| **Carro da frente e de trás** | Diferença, pneus e ritmo comparado com as últimas 5 voltas. Avisa quando o **Overtake** (2026) ou o **DRS** (2025) fica ao alcance. |
| **Tempos** | Volta atual, última, melhor e mais rápida da sessão, com setores a roxo, verde e amarelo. |
| **Carro** | Dano de cada peça. Os anéis mostram vida dos pneus, temperatura de superfície e interior, e travões. |
| **Estratégia** | Ritmo das últimas voltas, janela de box e a posição em que voltas à pista se parares agora (dada pelo jogo). |
| **Energia** | Unidade motriz, bateria ERS, aero ativa, combustível e mensagens da direção de corrida. |
| **Já sabe o desgaste** | O desgaste e o consumo que mediste nos treinos passam para a corrida, por isso a vida dos pneus aparece logo na primeira volta. |

### ⏱️ Qualificação

<img src="imagens/qualificacao.png" alt="Ecrã de qualificação" width="100%">

| | |
|---|---|
| **Tabela com linha de corte** | Ajustada à sessão (Q1, Q2 ou Q3) e ao número de carros. |
| **Delta ao vivo** | Contra a tua melhor volta do fim de semana: a da Q1 continua a ser a referência na Q2 e na Q3. Com previsão do tempo e da posição. |
| **Mini-setores** | 8 por setor, comparados com a tua melhor volta e com a melhor da sessão. |
| **Números-chave** | Volta ideal, margem para o corte e diferença para a pole. |
| **Gestão da sessão** | Se ainda dá para mais uma tentativa, tráfego à tua volta, temperatura dos pneus e conjuntos disponíveis. |

### 🔧 Treinos livres

<img src="imagens/treinos.png" alt="Ecrã de treinos livres" width="100%">

**Programa automático da sessão.** Cada tarefa marca-se sozinha com o que fazes em pista e mostra o progresso (por exemplo "5 de 8 voltas seguidas").

| Sessão | Programa |
|---|---|
| **TL1** | Reconhecimento da pista, testar os 3 compostos, medir o desgaste dos pneus |
| **TL2** | Simulação de qualificação, simulação de corrida (8 voltas seguidas), medir o consumo |
| **TL3** | Simulação de qualificação, confirmar o ritmo de corrida (5 voltas), desgaste |
| **Treino único** | Reconhecimento, qualificação, corrida e consumo (fins de semana curtos) |

Também mostra:

- **Stints e ritmo do stint atual:** média, degradação por volta, consistência e projeção das próximas voltas.
- **Setores contra os melhores da sessão** e o speed trap.
- **Desgaste de cada pneu por volta** e vida estimada.
- **Combustível para a corrida:** consumo por volta e quanto levar.

<details>
<summary><b>Como é que o painel sabe quantas voltas tem a corrida?</b></summary>

<br>

Procura, por esta ordem:

1. o número que o jogo envia;
2. as voltas da última corrida que fizeste nesse circuito;
3. o número oficial de voltas do circuito, ajustado à duração das tuas corridas (o painel aprende-a sozinho na primeira corrida, por exemplo 50%);
4. a distância completa.

O ecrã mostra de onde veio o número. A memória fica em `memoria.json`.

</details>

### 🚨 Alertas

Por baixo do cabeçalho aparece uma barra com o que precisas de saber já. Fica visível pelo menos 5 segundos, para não piscar.

| Nível | Exemplos |
|---|---|
| 🔴 **Perigo** | Bandeira vermelha · está a chover e tens pneus de seco · pneus no limite, box nas próximas voltas |
| 🟡 **Aviso** | Safety Car / VSC · bandeira amarela · chuva prevista nos próximos 30 min · asa da frente danificada · pneus a sobreaquecer · combustível curto |
| 🔵 **Informação** | Janela de box aberta · modo espectador |

> [!NOTE]
> O botão **⚙** no canto inferior direito abre as definições: escolher o ecrã à mão, escolher a vista (completa ou compacta) e, só se o automático falhar, pôr as voltas da corrida à mão.

---

## 📱 No tablet ou telemóvel

Ao arrancar, o painel mostra o endereço para usar noutro aparelho:

```text
[OK] No tablet ou telemóvel (mesma rede Wi-Fi): http://192.168.1.20:8080
```

Abre esse endereço no browser do tablet ou do telemóvel, ligado ao mesmo Wi-Fi do PC. Em ecrãs pequenos, o painel passa sozinho para a **vista compacta**: cartões grandes com o essencial (posição, diferenças, tempos, pneus, estratégia) que se leem de relance e se ajustam ao ecrã. Podes ter o PC e o tablet abertos ao mesmo tempo.

> [!TIP]
> Se o tablet não conseguir abrir o endereço, a firewall do Windows está a bloquear. Na primeira vez que abres o painel, escolhe **Permitir** também para redes privadas.

---

## 🎮 Configurar o jogo

No F1 25: **Definições → Definições de telemetria**

| Opção | Valor |
|---|---|
| Telemetria UDP | **Ligada** |
| Modo de difusão UDP | Desligado |
| Endereço IP UDP | `127.0.0.1` se jogas no mesmo PC |
| Porta UDP | `20777` |
| Frequência de envio UDP | 20 Hz ou mais (**60 Hz** é o ideal) |
| Formato UDP | **2026** com o 2026 Season Pack, **2025** com os carros de 2025 |
| A tua telemetria | Pública ou restrita: os dados do teu carro chegam sempre |

> [!IMPORTANT]
> Se já jogavas F1 25 antes do Season Pack, o formato pode ter ficado em **2025**. Muda-o à mão para **2026**.

**🎮 PS5 / Xbox:** em *Endereço IP UDP* põe o IP do PC onde corre o painel. Para o saberes, abre a Linha de Comandos no PC, escreve `ipconfig` e usa o "Endereço IPv4".

---

## 💡 Bom saber

- Alguns valores precisam de **1 ou 2 voltas completas** com o painel aberto: consumo, desgaste por volta, vida dos pneus e delta ao vivo. Até lá aparece "a calcular…".
- O delta ao vivo usa a tua melhor volta **feita com o painel aberto**. Na qualificação, essa volta passa da Q1 para a Q2 e para a Q3.
- O painel aguenta **flashbacks**: quando voltas atrás, o delta e os mini-setores refazem-se a partir desse ponto.
- O consumo e o desgaste por composto ficam guardados por circuito em `memoria.json`. Na corrida, o painel usa-os até ter as suas próprias medições e diz de onde vêm.
- O **modo demo não mexe** na memória: experimentar não estraga o que o painel aprendeu das tuas corridas.
- A ver uma sessão como **espectador**, o painel segue o carro que o jogo está a mostrar.
- O jogo não envia o desgaste dos pneus dos outros carros, por isso só aparece o teu.
- Ao arrancar, o painel confirma o tamanho de todos os pacotes contra a especificação oficial da EA.

---

## 🧰 Problemas frequentes

| Sintoma | O que fazer |
|---|---|
| Fica em **"À espera do jogo…"** | Confirma a porta `20777`, o IP e que a telemetria UDP está ligada. Na consola, confirma o IP do PC. |
| **"Estão a chegar dados mas num formato que não conheço"** | Muda o *Formato UDP* para 2026 ou 2025. |
| **"Não consegui abrir a porta UDP"** | Fecha outros programas de telemetria ou usa outra porta: `python f1dash.py --porta-udp 20778` (e põe a mesma no jogo). |
| Queres usar com outro programa ao mesmo tempo | No jogo, envia para este painel. Se o outro programa tiver reencaminhamento UDP, usa-o. |

<details>
<summary><b>Todas as opções da linha de comandos</b></summary>

<br>

| Opção | Por omissão | Para quê |
|---|---|---|
| `--porta-udp` | `20777` | Porta onde o jogo envia a telemetria |
| `--porta-web` | `8080` | Porta do painel no browser |
| `--demo` | | Simula `corrida`, `qualificacao` ou `treinos` sem o jogo |
| `--sem-browser` | | Não abre o browser ao arrancar |

```bash
python f1dash.py --help
```

</details>

---

## ⚙️ Como funciona

```mermaid
flowchart LR
    A["🎮 F1 25<br>(PC, PS5 ou Xbox)"] -- "UDP :20777<br>até 60 Hz" --> B["🐍 f1dash.py<br>descodifica pacotes"]
    B --> C["🧠 telemetria/estado.py<br>estado da sessão"]
    C -- "Server-Sent Events<br>5× por segundo" --> D["🖥️ Monitor<br>localhost:8080"]
    C -- "mesma rede Wi-Fi" --> E["📱 Tablet / telemóvel"]
```

Tudo corre na tua máquina com a biblioteca padrão do Python. O estado é calculado uma vez e partilhado com todos os ecrãs ligados, por isso o PC e o tablet abertos ao mesmo tempo não pesam mais. O painel é HTML, CSS e JavaScript simples, sem frameworks.

<details>
<summary><b>Estrutura do projeto</b></summary>

<br>

```text
f1Dash/
├── f1dash.py            # arranque: escuta UDP e serve o painel
├── demo.py              # simulador de corrida, qualificação e treinos
├── Iniciar.bat          # atalho para Windows
├── Iniciar-demo.bat     # atalho para o modo demo
├── telemetria/
│   ├── pacotes.py       # leitura dos pacotes UDP (formatos 2025 e 2026)
│   └── estado.py        # estado da sessão, cálculos e estratégia
├── web/
│   ├── index.html
│   ├── app.js           # os três ecrãs
│   ├── carro.js         # desenho do carro e dos pneus
│   └── estilo.css
├── testes/              # python -m unittest discover -s testes
│   ├── teste_pacotes.py # leitura dos pacotes 2025 e 2026
│   ├── teste_estado.py  # flashbacks, espectador, alertas, memória…
│   └── teste_servidor.py
├── .github/workflows/   # testes automáticos em cada push (Windows e Linux)
└── imagens/             # capturas usadas neste README
```

</details>

---

<div align="center">

<sub>Projeto de fãs, sem ligação à EA, à Codemasters ou à Formula 1. F1 e EA SPORTS são marcas dos respetivos donos.</sub>

<br>

**Se o F1 Dash te ajudou a ganhar umas décimas, deixa uma ⭐**

</div>
