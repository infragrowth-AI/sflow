<p align="center">
  <img src="logo.png" width="110" alt="SFlow">
</p>

<h1 align="center">SFlow</h1>

<p align="center"><strong>Dictado por voz para tu Mac. Hablás, soltás, y el texto aparece donde está tu cursor.</strong><br>
Gratis, sin internet y sin que tu voz salga de la compu.</p>

---

## Qué hace

Mantenés apretado un atajo, hablás y soltás. SFlow transcribe lo que dijiste y lo escribe en
la app que estés usando: Gmail, WhatsApp Web, Slack, Notion, un documento, el CRM. Sirve para
responder mails, dejar notas de una reunión o escribirle a un cliente sin tipear.

Transcribe con **Whisper**, un modelo de reconocimiento de voz que corre **en tu propia Mac**.
No pagás nada por usarlo y funciona sin internet.

Lo armamos en Infragrowth AI para que lo instales en un paso, pidiéndoselo a Claude Code.

## Qué necesitás

- Una Mac con **chip Apple** (M1, M2, M3, M4 o posterior). Lo ves en  → Acerca de esta Mac.
- **macOS 15 (Sequoia)** o más nuevo.
- Unos **6 GB libres** en el disco.
- Internet sólo para instalarlo (después funciona sin conexión).
- [Claude Code](https://claude.com/claude-code), si querés que lo instale por vos.

¿Tenés una Mac con Intel? Funciona, pero sin el motor local: transcribe en la nube con Groq y
necesitás una clave (hay plan gratis). Te lo explicamos en [Privacidad](#privacidad).

## Instalación con Claude Code (recomendada)

Abrí Claude Code en tu Mac y pegale esto:

> Instalame SFlow desde https://github.com/infragrowth-AI/sflow siguiendo su CLAUDE.md

Claude descarga el proyecto, lo arma, comprueba que transcribe bien y después te guía para
darle los permisos de macOS, de a uno. Termina cuando dictaste una frase y la viste aparecer.
La primera vez tarda entre 10 y 20 minutos, casi todo es descarga.

## Instalación a mano

Abrí la app **Terminal** y pegá esto:

```bash
git clone https://github.com/infragrowth-AI/sflow.git ~/sflow
cd ~/sflow
./install.sh
```

Si macOS te pide instalar las "herramientas de línea de comandos", aceptá y volvé a correrlo.
Para que SFlow arranque solo cuando prendés la Mac: `./install.sh --login` (o activá
"Iniciar con macOS" en el menú de SFlow).

No borres la carpeta `~/sflow`: la vas a necesitar para actualizar o desinstalar.

## Cómo se usa

| Para… | Hacé esto |
|---|---|
| Dictar | Mantené **Control + Opción (⌃⌥)**, hablá y soltá |
| Dictar largo, sin las manos | Tocá **Control** dos veces rápido. Para terminar, tocalo una vez más |
| Ver tu historial | Hacé clic en el ícono de SFlow en la barra de menú |

Mientras grabás aparece una pastilla abajo de la pantalla con barras que se mueven. Cuando
termina, el texto se escribe solo. Por ahora transcribe en **español**.

## Permisos (y por qué)

Antes de abrir SFlow por primera vez, dale dos permisos en Ajustes del Sistema →
Privacidad y seguridad (el instalador te abre la pantalla). En cada lista, borrá con «–»
cualquier SFlow vieja y agregá la nueva con «+» desde `~/Applications`:

1. **Accesibilidad**: para escribir el texto donde está tu cursor.
2. **Monitoreo de entrada**: para darse cuenta de que apretaste el atajo.
3. **Micrófono**: para escucharte. Sólo graba mientras mantenés el atajo.

El del micrófono te lo pide sola la primera vez que dictás. Si actualizás SFlow, macOS te
vuelve a pedir los dos primeros: es normal.

## Cuánto cuesta

**$0.** El motor local no tiene costo por uso. La primera vez SFlow baja el modelo de voz
(unos **1,6 GB**) y la instalación baja otros ~2 GB de componentes. Después no consume
internet.

Si elegís Groq (nube) o activás las funciones con IA, pagás lo que cobre Groq; tiene un plan
gratis que alcanza para uso personal.

## Privacidad

- **Motor local (el que viene por defecto):** tu audio nunca sale de tu Mac. El historial
  (textos y grabaciones) queda guardado en tu Mac, en `~/Library/Application Support/SFlow`.
  El panel web del historial (`http://localhost:5678`) sólo se abre desde tu propia compu.
- **Groq (opcional):** el audio viaja a los servidores de Groq para transcribirse. Lo mismo
  pasa con el texto si activás "Limpiar con Llama" o los atajos **Opción + 1…8**, que
  reescriben el texto seleccionado.
- **La clave de Groq** se pega en la propia app: ícono de SFlow → Ajustes → Clave de Groq.
  No se la pases a nadie por chat, tampoco a Claude.

## Límites

- Sólo Mac. El motor local necesita chip Apple.
- El texto se escribe simulando el teclado (o el portapapeles, si lo cambiás en Ajustes).
  Algunos campos no lo aceptan, por ejemplo los de contraseña o algunos escritorios remotos.
- La app está firmada "ad-hoc", sin certificado de Apple. Por eso, **cada vez que la
  actualizás o se reconstruye, macOS te pide de nuevo Accesibilidad y Monitoreo de entrada**.
  Qué hacer: ver [Actualizar](#actualizar).
- Si tenés otra versión de SFlow instalada (por ejemplo en `/Applications`), no abras las dos
  a la vez: escuchan el mismo atajo.

## Actualizar

La forma fácil: abrí Claude Code (o Codex) y pegale esto:

> Actualizame SFlow siguiendo el CLAUDE.md de ~/sflow

A mano:

```bash
cd ~/sflow && git pull && ./install.sh
```

Si no hubo cambios, no toca nada. **Si los hubo, macOS se olvida de los permisos** y además
deja la SFlow vieja en las listas, con el mismo nombre y el mismo ícono que la nueva. Por eso,
después de actualizar:

1. Cerrá SFlow (ícono de la barra de menú → Salir).
2. En **Accesibilidad** y en **Monitoreo de entrada** (Ajustes del Sistema → Privacidad y
   seguridad), borrá con «–» **todas** las SFlow que aparezcan.
3. En cada una, tocá «+», apretá **Cmd + Shift + G**, pegá `~/Applications/SFlow.app`,
   tocá Abrir y activala.
4. Abrí SFlow de nuevo y probá el atajo.

Si dejó de andar el atajo o el pegado después de actualizar, casi siempre es esto.

## Desinstalar

```bash
cd ~/sflow && ./uninstall.sh
```

Borra la app y el inicio automático; tu historial queda. Para borrar todo:
`./uninstall.sh --purge --remove-model` (historial, ajustes, clave y el modelo de 1,6 GB).
Después podés borrar la carpeta `~/sflow`.

## Qué trae

- Instalación en un paso (`install.sh`), en tu carpeta de usuario y sin contraseña de
  administrador. No toca otras versiones de SFlow que tengas.
- Identificador propio (`ai.infragrowth.sflow`), así no choca con otras versiones de SFlow.
- Arranca sin pedir clave de Groq: el motor local es el que viene por defecto.
- El motor local no depende de `ffmpeg`, que en muchas Macs no está.
- El panel del historial no carga nada de internet y sólo responde a tu propia Mac.
- Una prueba automática (`scripts/verify.sh`) que comprueba que transcribe, sin micrófono
  ni permisos.

## Licencia

Código abierto, bajo licencia [MIT](LICENSE).
