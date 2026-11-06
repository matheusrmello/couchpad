# Interface Qt Quick

A janela `shiftpad_linux/qml/Main.qml` e o controlador Python
`shiftpad_linux/qt_frontend.py` usam PySide6 e o socket local do monitor. O
AppImage e o Flatpak reconstruídos iniciam essa interface; pelo código-fonte,
`python -m shiftpad_linux qt` abre o Qt e `tray` mantém a interface GTK histórica.

A visão geral mostra o estado recebido do monitor, TV, controle e áudio
identificados; oferece ativação, restauração, cancelamento e chave de automação.
A navegação e os cartões usam ícones SVG incluídos no pacote. Em janelas
menores a barra lateral se recolhe e os cartões são organizados em uma coluna;
o conteúdo continua acessível por rolagem. A interface inclui transições de
hover, clique, seleção e alternância da automação.
A página de dispositivos seleciona TV, controle e áudio. Uma TV nova precisa de
EDID consistente com uma nova consulta e as seleções ficam bloqueadas enquanto
a sessão estiver ativa. A página de inicializadores permite habilitar Steam e
configurar executável, argumentos e fechamento do processo próprio. Em
Configurações ficam modo de vídeo e atrasos. O arquivo TOML continua disponível
para opções avançadas. Os atalhos da bandeja acompanham o estado do monitor.

As seleções de dispositivo e opções de sessão usam autosave; o outro
inicializador tem salvamento explícito. Chamadas IPC e descobertas são feitas
em uma thread de trabalho e o resultado chega à interface por sinais Qt.

O pacote congelado usa `QT_QUICK_BACKEND=software` por padrão, pois a criação
do contexto OpenGL falhou no teste local; a variável pode ser ajustada pelo
usuário antes da execução. Isso pode reduzir o desempenho gráfico em algumas
máquinas. Continuam observados avisos não fatais de fontconfig do host.

A interface Qt usa o backend Linux/KDE existente. Não adiciona suporte a GNOME,
Cinnamon ou Windows. O Flatpak inicia o payload no host, com acesso como o
usuário; não oferece isolamento da aplicação. Veja os manuais em `packaging/`.

Verificações: suíte Python com `tests/test_qt_frontend.py`; testes isolados de
seleção e persistência com daemon simulado; carregamento QML; abertura e
encerramento do AppImage com configuração temporária; `--version` e
`--runtime-check` em contêineres limpos. Estes não certificam acionamento por
controle, troca real de TV ou restauração usando a nova janela. O teste físico
anterior está documentado em `reconstrucao-2026-11-06.md` e usou o backend da
beta anterior.

## Design system da referência

`qml/components/Theme.qml` centraliza paleta, raios e tipografia. A biblioteca
inclui Card, Action, Toggle, Select, Field, NumberField, Check, Radio, Range,
Status, Pill, ListRow, EmptyState e Toast. As quatro abas usam a mesma paleta e
componentes. A fonte Inter 4.1 é distribuída com sua licença em `assets/fonts`.
As ilustrações SVG do monitor, TV, controle e áudio são recursos nativos.

`tools/qa_qt_visual.py` renderiza as quatro abas em 1672×941, 1320×760 e 800×700 usando
configuração temporária e hardware explicitamente simulado. Capturas ficam em
`.build/qt-visual/`; não são evidência de dispositivos reais ou de suporte Windows.
A barra própria usa as operações de mover/redimensionar do compositor via Qt.

Recursos do briefing que o backend ainda não implementa (inicialização no login,
múltiplos launchers reordenáveis, tema e atualizações automáticas) não são
apresentados como operacionais. O modelo atual oferece Steam e um programa
adicional; as outras preferências continuam disponíveis no TOML.
