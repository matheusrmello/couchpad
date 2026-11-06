# Instruções para agentes — CouchPad

Leia `docs/arquitetura.md` e `docs/agentes-ia.md` antes de mudanças relevantes;
consulte também o guia específico da área afetada. Respeite alterações existentes
no workspace e as instruções mais recentes do usuário.

## Projeto e invariantes

- Python 3.11+, interface GTK 3 e prévia Qt Quick/PySide6; backend atual Linux/KDE Plasma em Wayland,
  com XWayland, KScreen, pactl e evdev. Outros ambientes ainda não são suportados.
- Preserve ativação desativada no primeiro uso, configurações e nomes históricos
  `shiftpad-linux`, socket, lock e recuperação de sessão. Mudanças de formato
  exigem compatibilidade ou migração e testes de recuperação.
- A ativação captura estado antes de alterar telas/áudio; restauração deve
  continuar recuperável após falha. Não encerre jogos ou processos alheios;
  somente o launcher próprio identificado pode ser encerrado.
- Preserve as regras atuais: TV 4K usa escala 2,75, saída da TV usa 100% e
  valores anteriores são restaurados. Mudanças requerem pedido do usuário.
- O Flatpak atual executa o payload no host: não apresente esse pacote como
  isolado. O AppImage é construído em Debian 12, com limite glibc 2.36.

## Trabalho e verificação

- Escolha os papéis em `docs/agentes-ia.md` conforme a tarefa. São papéis de
  trabalho, não processos autônomos permanentes. Use subagentes somente quando
  habilitados pelas instruções da sessão ou solicitados pelo usuário.
- Mudanças que atravessam interface, IPC, sessão ou empacotamento devem validar
  os contratos entre áreas. Prefira testes isolados e mocks para efeitos reais.
- Suíte principal: `python3 -m unittest discover -s tests -v`. Para interface,
  consulte `tools/qa_tray.py` e suas premissas antes de executar. Para pacotes,
  siga os manuais em `packaging/` e o relatório de reconstrução.
- Consultas `doctor`, `devices` e `preview` não aplicam alterações; `switch`,
  `restore`, `run` e a automação podem afetar a sessão gráfica. Ao realizar
  testes reais autorizados, use configuração e estado isolados, desative
  launchers e garanta restauração mesmo em caso de falha.
- Relate testes executados, falhas, limitações e diferença entre simulação,
  carregamento em contêiner e validação de hardware real. Não afirme suporte
  ou publicação que não tenham sido verificados.
