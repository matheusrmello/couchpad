import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "components" as UI

ApplicationWindow {
 id: window
 width: 1320; height: 760; minimumWidth: 800; minimumHeight: 600
 visible: true; title: "CouchPad"; color: UI.Theme.app
 flags: Qt.Window | Qt.FramelessWindowHint
 property var s: backend.data
 property int page: 0
 readonly property bool compact: width < 1200
 readonly property bool stacked: width < 1000
 font.family: fontLoader.name; font.pixelSize: 16
 FontLoader { id: fontLoader; source: "../assets/fonts/InterVariable.ttf" }
 FileDialog { id: launcherChooser; title: "Escolher inicializador"; onAccepted: launcherPath.text = backend.localPath(selectedFile) }
 component LabelText: Text { color: UI.Theme.white; font.family: fontLoader.name; font.pixelSize: 16; elide: Text.ElideRight }
 component Muted: Text { color: UI.Theme.secondary; font.family: fontLoader.name; font.pixelSize: 18; wrapMode: Text.WordWrap }
 component Art: UI.Icon { }
 header: Rectangle {
  height: 52; color: UI.Theme.sidebar
  Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: UI.Theme.border }
  MouseArea { anchors.fill: parent; onPressed: window.startSystemMove(); onDoubleClicked: window.visibility === Window.Maximized ? window.showNormal() : window.showMaximized() }
  RowLayout { anchors.fill: parent; anchors.leftMargin: 30; spacing: 18
   Art { objectName: "brandIcon"; source: "../assets/ui/brand.svg"; Layout.preferredWidth: 28; Layout.preferredHeight: 28 }
   LabelText { text: "CouchPad"; font.pixelSize: 22; font.bold: true }
   Rectangle { width: 1; height: 28; color: UI.Theme.border; Layout.leftMargin: 14; Layout.rightMargin: 14 }
   UI.Status { text: !s.online ? "Monitor indisponível" : s.active ? "Sessão na TV ativa" : "Pronto para jogar"; tint: s.online ? UI.Theme.green : UI.Theme.warning; Layout.fillWidth: true }
   Repeater { model: [{label:"Minimizar",text:"−"},{label:"Maximizar",text:"□"},{label:"Fechar",text:"×"}]
    delegate: Button { required property int index; required property var modelData; implicitWidth: 52; implicitHeight: 51; hoverEnabled: true; Accessible.name: modelData.label
     contentItem: LabelText { text: modelData.text; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: 28 }
     background: Rectangle { color: parent.hovered ? (parent.index === 2 ? "#FF5470" : UI.Theme.hover) : "transparent" }
     onClicked: index === 0 ? window.showMinimized() : index === 1 ? (window.visibility === Window.Maximized ? window.showNormal() : window.showMaximized()) : window.close()
    }
   }
  }
 }
 RowLayout { anchors.fill: parent; spacing: 0
  Rectangle { Layout.fillHeight: true; Layout.preferredWidth: compact ? 68 : 210; color: UI.Theme.sidebar
   Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: UI.Theme.border }
   ColumnLayout { anchors.fill: parent; anchors.margins: 12; spacing: 6
    Item { Layout.preferredHeight: 30 }
    Repeater { model: [{label:"Visão geral",icon:"home"},{label:"Dispositivos",icon:"devices"},{label:"Inicializadores",icon:"layers"},{label:"Configurações",icon:"settings"}]
     delegate: Button { id: nav; required property int index; required property var modelData; Layout.fillWidth: true; implicitHeight: 52; hoverEnabled: true; Accessible.name: modelData.label
      background: Rectangle { radius: 12; color: nav.index === page ? "#12382F" : nav.hovered ? UI.Theme.hover : "transparent"; border.color: nav.activeFocus ? UI.Theme.green : nav.index === page ? "#1D5A45" : "transparent"; Behavior on color { ColorAnimation { duration: 150 } }
       Rectangle { visible: nav.index === page; width: 3; height: parent.height - 20; anchors.verticalCenter: parent.verticalCenter; color: UI.Theme.green; radius: 2 }
      }
      contentItem: RowLayout { spacing: 18
       Art { source: "../assets/ui/" + nav.modelData.icon + ".svg"; Layout.preferredWidth: 24; Layout.preferredHeight: 24; Layout.leftMargin: 12 }
       LabelText { visible: !compact; text: nav.modelData.label; font.pixelSize: 17; font.weight: nav.index === page ? Font.DemiBold : Font.Normal; Layout.fillWidth: true }
      }
      onClicked: page = index
     }
    }
    Item { Layout.fillHeight: true }
   }
  }
  ScrollView { id: scroll; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
   ColumnLayout { id: content; width: scroll.availableWidth; spacing: 22
    transform: Translate { id: slide; y: 0 }
    Connections { target: window; function onPageChanged() { fade.restart(); scroll.contentItem.contentY = 0 } }
    ParallelAnimation { id: fade; NumberAnimation { target: content; property: "opacity"; from: 0; to: 1; duration: 200 } NumberAnimation { target: slide; property: "y"; from: 8; to: 0; duration: 200; easing.type: Easing.OutCubic } }
    Item { Layout.preferredHeight: 4 }
    UI.Card { visible: page === 0; Layout.leftMargin: 30; Layout.rightMargin: 24; Layout.fillWidth: true; Layout.preferredHeight: 98; radius: 16; clip: true
     gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: "#111827" } GradientStop { position: 0.6; color: "#2A1F5C" } GradientStop { position: 1; color: "#111827" } }
     Rectangle { width: parent.width * 0.5; height: 150; x: parent.width * 0.68; y: 25; rotation: -23; radius: 90; color: "#4B2F9E"; opacity: 0.3 }
     RowLayout { anchors.fill: parent; anchors.margins: 22; spacing: 18
      Art { source: "../assets/ui/brand.svg"; Layout.preferredWidth: 48; Layout.preferredHeight: 48 }
      ColumnLayout { Layout.fillWidth: true; spacing: 6
       LabelText { text: s.enabled ? "Automação ativada" : "Automação desativada"; font.pixelSize: compact ? 21 : 26; font.bold: true; Layout.fillWidth: true }
       Muted { text: "Ao conectar um controle, o CouchPad alterna o jogo da tela do PC para a TV."; font.pixelSize: compact ? 14 : 17; Layout.fillWidth: true }
      }
      UI.Toggle { checked: s.enabled; enabled: s.online && !s.busy; Accessible.name: "Ativar automação"; onClicked: backend.command(checked ? 'enable' : 'disable') }
     }
    }
    RowLayout { visible: page !== 0; Layout.leftMargin: 30; Layout.rightMargin: 30; Layout.fillWidth: true
     ColumnLayout { Layout.fillWidth: true
      LabelText { text: ["Visão geral","Dispositivos","Inicializadores","Configurações"][page]; font.pixelSize: 32; font.bold: true }
      Muted { text: ["","Controles, telas e áudio da sua sessão de jogo.","Escolha o que abrir ao preparar a TV.","Personalize o comportamento do CouchPad."][page]; Layout.fillWidth: true }
     }
     UI.Action { text: page === 1 ? "Detectar dispositivos" : page === 2 ? "Escolher inicializador" : "Configuração completa"; variant: "primary"; textSize: 17; onClicked: page === 1 ? backend.refresh() : page === 2 ? launcherChooser.open() : backend.openSettings() }
    }
    GridLayout { id: displayGrid; objectName: "displayGrid"; visible: page === 0; Layout.fillWidth: true; Layout.leftMargin: compact ? 30 : 84; Layout.rightMargin: compact ? 24 : 84; columns: stacked ? 1 : 3; columnSpacing: 22; rowSpacing: 14
     UI.Card { Layout.fillWidth: true; Layout.preferredHeight: 155; radius: 16; border.color: UI.Theme.strong
      RowLayout { anchors.fill: parent; anchors.margins: 30; spacing: 24
       Art { source: "../assets/ui/monitor-art.svg"; Layout.preferredWidth: compact ? 78 : 128; Layout.preferredHeight: 110 }
       ColumnLayout { Layout.fillWidth: true; spacing: 14
        LabelText { text: "Monitor"; font.pixelSize: compact ? 21 : 27; font.bold: true }
        UI.Status { text: "Ativo (desktop)"; textSize: compact ? 15 : 18; Layout.fillWidth: true }
        Muted { text: (s.desktopResolution || s.desktop) + " (Principal)"; font.pixelSize: compact ? 14 : 17; Layout.fillWidth: true }
       }
      }
     }
     Art { visible: !stacked; source: "../assets/ui/arrow.svg"; Layout.preferredWidth: 28; Layout.preferredHeight: 28 }
     UI.Card { id: tvCard; variant: "success"; selected: s.tvConnected; Layout.fillWidth: true; Layout.preferredHeight: 155; radius: 16
      SequentialAnimation on opacity { running: s.pending; loops: 2; NumberAnimation { from: 1; to: 0.65; duration: 600 } NumberAnimation { from: 0.65; to: 1; duration: 600 } }
      RowLayout { anchors.fill: parent; anchors.margins: 22; spacing: 18
       Art { source: "../assets/ui/tv-art.svg"; Layout.preferredWidth: compact ? 80 : 140; Layout.preferredHeight: 112
        Text { anchors.centerIn: parent; anchors.verticalCenterOffset: -10; text: (s.tvTitle || "").toLowerCase().indexOf("samsung") >= 0 ? "SAMSUNG" : ""; color: UI.Theme.white; font.family: fontLoader.name; font.pixelSize: compact ? 9 : 13; font.bold: true }
       }
       ColumnLayout { Layout.fillWidth: true; spacing: 14
        LabelText { text: s.tvTitle || "TV"; font.pixelSize: compact ? 21 : 26; font.bold: true; Layout.fillWidth: true }
        UI.Status { text: s.tvConnected ? "Conectada" : "Desconectada"; tint: s.tvConnected ? UI.Theme.green : UI.Theme.error; textSize: compact ? 15 : 18; Layout.fillWidth: true }
        Muted { text: (s.tvResolution || s.tv) + " (TV)"; font.pixelSize: compact ? 14 : 17; Layout.fillWidth: true }
       }
      }
     }
    }
    GridLayout { visible: page === 0; columns: stacked ? 1 : 2; Layout.fillWidth: true; Layout.leftMargin: compact ? 30 : 184; Layout.rightMargin: compact ? 24 : 172; columnSpacing: 32; rowSpacing: 12
     ColumnLayout { Layout.fillWidth: true; spacing: 8
      UI.Action { objectName: "activateTv"; Layout.fillWidth: true; Layout.preferredHeight: 54; variant: "primary"; text: s.pending ? "Contagem em andamento…" : "Ativar TV"; textSize: compact ? 18 : 23; iconSource: Qt.resolvedUrl("../assets/ui/play.svg"); enabled: s.online && s.enabled && !s.active && !s.busy; onClicked: backend.command('activate') }
      Muted { text: "Alterna o jogo para a TV e configura áudio e exibição."; font.pixelSize: compact ? 15 : 18; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
     }
     ColumnLayout { Layout.fillWidth: true; spacing: 8
      UI.Action { objectName: "restoreDesktop"; Layout.fillWidth: true; Layout.preferredHeight: 54; text: "Restaurar desktop"; textSize: compact ? 17 : 21; iconSource: Qt.resolvedUrl("../assets/ui/monitor.svg"); enabled: s.online && s.active && !s.busy; onClicked: backend.command('restore') }
      Muted { text: "Volta para o monitor e restaura o ambiente de trabalho."; font.pixelSize: compact ? 15 : 18; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
     }
    }
    UI.Card { visible: page === 0; Layout.fillWidth: true; Layout.leftMargin: 30; Layout.rightMargin: 24; Layout.preferredHeight: 70
     RowLayout { anchors.fill: parent; anchors.margins: 18; spacing: 24
      Art { source: "../assets/ui/clock.svg"; Layout.preferredWidth: 28; Layout.preferredHeight: 28; Layout.leftMargin: 12 }
      ColumnLayout { Layout.fillWidth: true; spacing: 4
       LabelText { text: "Tempo de contagem regressiva"; font.pixelSize: compact ? 16 : 18; font.bold: true; Layout.fillWidth: true }
       Muted { text: "Aguarde antes de ativar a TV após o controle ser conectado."; font.pixelSize: compact ? 15 : 18; Layout.fillWidth: true }
      }
      UI.Select { Layout.preferredWidth: compact ? 150 : 250; model: ["3 segundos","5 segundos","10 segundos","15 segundos", s.connect + " segundos (atual)"]; currentIndex: [3,5,10,15].indexOf(s.connect) < 0 ? 4 : [3,5,10,15].indexOf(s.connect); enabled: s.online && !s.busy; onActivated: { if (currentIndex < 4) backend.saveSettings(s.mode, [3,5,10,15][currentIndex], s.disconnect, s.steam) } }
     }
    }
    GridLayout { objectName: "summaryGrid"; visible: page === 0; columns: stacked ? 1 : 3; Layout.fillWidth: true; Layout.leftMargin: 30; Layout.rightMargin: 24; columnSpacing: 24; rowSpacing: 16
     Repeater { model: [{title:"Controle",value:s.controller,sub:s.controller,icon:"devices",art:"controller-art",variant:"success"},{title:"Áudio",value:"Saída da TV",sub:s.audio,icon:"audio",art:"audio-art",variant:"accent"},{title:"Inicializadores",value:s.steam ? "Steam Big Picture" : s.launcherEnabled ? "Outro programa" : "Nenhum configurado",sub:s.steam || s.launcherEnabled ? "Será aberto ao ativar a TV" : "Configure na aba Inicializadores",icon:"layers",art:"steam-art",variant:"default"}]
      delegate: UI.Card { required property var modelData; Layout.fillWidth: true; Layout.preferredHeight: 125; variant: modelData.variant
       ColumnLayout { anchors.fill: parent; anchors.margins: 18; spacing: 8
        RowLayout { spacing: 16; Art { source: "../assets/ui/" + modelData.icon + ".svg"; Layout.preferredWidth: 25; Layout.preferredHeight: 25 } LabelText { text: modelData.title; font.pixelSize: compact ? 18 : 20; font.weight: Font.DemiBold; Layout.fillWidth: true } }
        RowLayout { Layout.fillWidth: true
         ColumnLayout { Layout.fillWidth: true; spacing: 8
          LabelText { text: modelData.value; font.pixelSize: compact ? 16 : 18; font.bold: true; Layout.fillWidth: true }
          Muted { text: modelData.sub; font.pixelSize: compact ? 14 : 18; Layout.fillWidth: true; maximumLineCount: 1; elide: Text.ElideRight }
         }
         Art { source: "../assets/ui/" + modelData.art + ".svg"; Layout.preferredWidth: 50; Layout.preferredHeight: 48 }
        }
       }
      }
     }
    }
    UI.Card { visible: page === 1; Layout.fillWidth: true; Layout.leftMargin: 30; Layout.rightMargin: 30; Layout.preferredHeight: deviceList.implicitHeight + 48
     ColumnLayout { id: deviceList; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 24; spacing: 24
      LabelText { text: "Controles e telas/áudio"; font.pixelSize: 24; font.bold: true }
      Repeater { model: s.deviceRows || []
       delegate: UI.ListRow { required property var modelData; Layout.fillWidth: true; title: modelData.title; description: modelData.description; status: modelData.status; iconSource: Qt.resolvedUrl("../assets/ui/" + modelData.kind + ".svg") }
      }
      UI.EmptyState { visible: !s.deviceRows || s.deviceRows.length === 0; title: "Nenhum dispositivo detectado"; description: "Conecte seu controle e sua TV e selecione Detectar dispositivos."; Layout.fillWidth: true }
     }
    }
    UI.Card { visible: page === 2; variant: "accent"; Layout.fillWidth: true; Layout.leftMargin: 30; Layout.rightMargin: 30; Layout.preferredHeight: 120
     RowLayout { anchors.fill: parent; anchors.margins: 24; spacing: 22
      UI.ListRow { Layout.fillWidth: true; title: "Steam Big Picture"; description: "Será aberto ao ativar a TV"; iconSource: Qt.resolvedUrl("../assets/ui/steam-art.svg"); status: s.steam ? "Ativado" : "Desativado" }
      UI.Toggle { checked: s.steam; enabled: s.steamEditable && s.online && !s.busy; Accessible.name: "Abrir Steam Big Picture"; onClicked: backend.saveSteam(checked) }
     }
    }
                UI.Card { visible: page === 1; Layout.fillWidth: true; Layout.leftMargin: 30; Layout.rightMargin: 30; Layout.preferredHeight: deviceSettings.implicitHeight + 40
                    ColumnLayout { id: deviceSettings; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 20; spacing: 10
                        LabelText { text: "Selecionar dispositivos"; font.bold: true; font.pixelSize: 19 }
                        Muted { text: "Restaure o desktop antes de alterar os dispositivos."; Layout.fillWidth: true }
                        RowLayout { Layout.fillWidth: true; LabelText { text: "TV"; Layout.preferredWidth: 100 }
                            UI.Select { objectName: "tvSelector"; Layout.fillWidth: true; model: s.tvChoices; textRole: "label"; valueRole: "value"; currentIndex: indexOfValue(s.tvValue); enabled: s.online && !s.active && !s.busy; onActivated: backend.selectTv(currentValue) } }
                        RowLayout { Layout.fillWidth: true; LabelText { text: "Controle"; Layout.preferredWidth: 100 }
                            UI.Select { objectName: "gamepadSelector"; Layout.fillWidth: true; model: s.gamepadChoices; textRole: "label"; valueRole: "value"; currentIndex: indexOfValue(s.gamepadValue); enabled: s.online && !s.active && !s.busy; onActivated: { if (currentValue !== '__saved__') backend.selectGamepad(currentValue) } } }
                        RowLayout { Layout.fillWidth: true; LabelText { text: "Áudio"; Layout.preferredWidth: 100 }
                            UI.Select { objectName: "audioSelector"; Layout.fillWidth: true; model: s.audioChoices; textRole: "label"; valueRole: "value"; currentIndex: indexOfValue(s.audioValue); enabled: s.online && !s.active && !s.busy; onActivated: backend.selectAudio(currentValue) } }
                    }
                }
                UI.Card { visible: page === 2 || page === 3; Layout.fillWidth: true; Layout.leftMargin: 30; Layout.rightMargin: 30; Layout.preferredHeight: settingsContent.implicitHeight + 40
                    ColumnLayout { id: settingsContent; anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 20; spacing: 12
                        LabelText { text: page === 2 ? "Outro inicializador" : "Automação · Vídeo e áudio"; font.bold: true; font.pixelSize: 19 }
                        RowLayout { visible: page === 2; Layout.fillWidth: true
                            UI.Field { id: launcherPath; objectName: "launcherPath"; Layout.fillWidth: true; placeholderText: "Executável, AppImage ou .desktop"; text: s.launcherPath; Accessible.name: "Caminho do inicializador" }
                            UI.Action { text: "Escolher"; onClicked: launcherChooser.open() }
                        }
                        UI.Field { id: launcherArgs; objectName: "launcherArgs"; visible: page === 2; Layout.fillWidth: true; placeholderText: "Argumentos (opcional)"; text: s.launcherArgs; Accessible.name: "Argumentos do inicializador" }
                        UI.Check { id: launcherEnabled; visible: page === 2; text: "Abrir outro programa"; checked: s.launcherEnabled; palette.windowText: UI.Theme.white }
                        UI.Check { id: launcherClose; visible: page === 2; text: "Fechar somente o inicializador ao restaurar"; checked: s.launcherClose; palette.windowText: UI.Theme.white }
                        UI.Action { visible: page === 2; text: "Salvar outro programa"; enabled: s.online && !s.busy; onClicked: backend.saveLauncher(launcherPath.text, launcherArgs.text, launcherEnabled.checked, launcherClose.checked) }
                        GridLayout { visible: page === 3; Layout.fillWidth: true; columns: compact ? 2 : 4
                            LabelText { text: "Modo de vídeo" }
                            UI.Select { id: mode; model: ["Somente TV", "Estendido", "Espelhado"]; currentIndex: s.mode === 'extend' ? 1 : s.mode === 'mirror' ? 2 : 0; enabled: s.online && !s.busy; onActivated: backend.saveSettings(['tv-only','extend','mirror'][currentIndex], s.connect, s.disconnect, s.steam) }
                        }
                        GridLayout { visible: page === 3; Layout.fillWidth: true; columns: compact ? 2 : 4
                            LabelText { text: "Atraso ao conectar (s)" }
                            UI.NumberField { id: connectDelay; from: 0; to: 3000; value: Math.round(s.connect * 10); editable: true; enabled: s.online && !s.busy; textFromValue: function(v) { return (v / 10).toFixed(1) }; valueFromText: function(t) { return Math.round(Number(t.replace(',', '.')) * 10) }; onValueModified: backend.saveSettings(s.mode, value / 10, s.disconnect, s.steam) }
                            LabelText { text: "Ao desconectar (s)" }
                            UI.NumberField { id: disconnectDelay; from: 0; to: 3000; value: Math.round(s.disconnect * 10); editable: true; enabled: s.online && !s.busy; textFromValue: function(v) { return (v / 10).toFixed(1) }; valueFromText: function(t) { return Math.round(Number(t.replace(',', '.')) * 10) }; onValueModified: backend.saveSettings(s.mode, s.connect, value / 10, s.steam) }
                        }
                        RowLayout {
                            UI.Action { text: "Configuração completa"; onClicked: backend.openSettings() }
                        }
                    }
                }

    UI.Card { visible: page === 3; Layout.fillWidth: true; Layout.leftMargin: 30; Layout.rightMargin: 30; Layout.preferredHeight: 180
     ColumnLayout { anchors.fill: parent; anchors.margins: 28; spacing: 14
      LabelText { text: "Geral"; font.pixelSize: 24; font.bold: true }
      RowLayout { Layout.fillWidth: true
       ColumnLayout { Layout.fillWidth: true
        LabelText { text: "Iniciar com o sistema" }
        Muted { text: "Integração de login ainda não disponível."; Layout.fillWidth: true }
       }
       UI.Toggle { enabled: false; checked: false; Accessible.name: "Iniciar com o sistema, indisponível" }
      }
      Muted { text: "Quando há bandeja disponível, fechar a janela mantém o monitor em execução."; Layout.fillWidth: true }
     }
    }
    UI.Card { visible: page === 3; Layout.fillWidth: true; Layout.leftMargin: 30; Layout.rightMargin: 30; Layout.preferredHeight: 160
     ColumnLayout { anchors.fill: parent; anchors.margins: 28; spacing: 14
      LabelText { text: "Aparência"; font.pixelSize: 24; font.bold: true }
      RowLayout { Layout.fillWidth: true
       ColumnLayout { Layout.fillWidth: true
        LabelText { text: "Tema e cor de destaque" }
        Muted { text: "Tema escuro e verde definidos pelo design atual."; Layout.fillWidth: true }
       }
       UI.Select { model: ["Escuro · Verde"]; enabled: false; Layout.preferredWidth: compact ? 180 : 260 }
      }
     }
    }
    UI.Card { visible: page === 3; Layout.fillWidth: true; Layout.leftMargin: 30; Layout.rightMargin: 30; Layout.preferredHeight: 150
     ColumnLayout { anchors.fill: parent; anchors.margins: 28; spacing: 14
      LabelText { text: "Sobre"; font.pixelSize: 24; font.bold: true }
      Muted { text: "CouchPad 0.1.0b1 · Qt Quick · Backend KDE/Wayland"; Layout.fillWidth: true }
      Muted { text: "Atualizações automáticas ainda não disponíveis."; Layout.fillWidth: true }
     }
    }
    UI.Action { visible: page === 1; Layout.leftMargin: 30; text: "Detectar dispositivos"; enabled: !s.busy; onClicked: backend.refresh() }
    UI.Action { visible: s.pending; Layout.leftMargin: 30; text: "Cancelar troca para TV"; variant: "destructive"; onClicked: backend.command('cancel') }
    UI.Action { visible: !s.online; Layout.leftMargin: 30; text: "Iniciar serviço"; onClicked: backend.startService() }
    Muted { visible: s.message.length > 0; Layout.fillWidth: true; Layout.leftMargin: 30; Layout.rightMargin: 30; text: s.message }
    Item { Layout.preferredHeight: 0 }
   }
  }
 }
 UI.Toast { anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 24; width: Math.min(420, window.width - 48); text: s.message; visible: s.message.length > 0 && toastTimer.running; z: 90 }
 Timer { id: toastTimer; interval: 5000 }
 Connections { target: backend; function onChanged() { if (s.message.length > 0) toastTimer.restart() } }
 // Native system resizing preserves compositor behavior with the custom title bar.
 Repeater { model: [Qt.LeftEdge,Qt.RightEdge,Qt.TopEdge,Qt.BottomEdge]
  delegate: MouseArea { required property int modelData; z: 100; x: modelData === Qt.RightEdge ? window.width - 5 : 0; y: modelData === Qt.BottomEdge ? window.height - 5 : 0; width: modelData === Qt.TopEdge || modelData === Qt.BottomEdge ? window.width : 5; height: modelData === Qt.LeftEdge || modelData === Qt.RightEdge ? window.height : 5; onPressed: window.startSystemResize(modelData) }
 }
}
