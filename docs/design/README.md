# Referência visual CouchPad

`reference.png` é a referência aprovada pelo usuário. A janela de referência
mede 1672 × 941 px; a implementação Qt pode ser comparada nessa mesma dimensão.
Os tokens estão em `shiftpad_linux/qml/components/Theme.qml`, e os componentes
reutilizáveis no mesmo diretório. Fontes e ilustrações estão em `assets/`.

Para gerar comparações reproduzíveis das quatro abas:

```bash
.build/qt-venv/bin/python tools/qa_qt_visual.py
```

As doze capturas ficam em `.build/qt-visual`. Usam dados simulados, explicitamente
separados das preferências e dispositivos pessoais. O roteiro rejeita falhas de
carregamento QML e de recursos durante a renderização.
