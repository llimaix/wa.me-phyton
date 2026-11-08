# Invitaciones desde Linux usando WhatsApp personal (wa.me)

Herramienta local para **preparar** mensajes individuales en WhatsApp y registrar los que envías **manualmente**. No usa herramientas no oficiales, no automatiza la pulsación de Enviar, no verifica entregas y no garantiza ausencia total de restricciones de WhatsApp.

## Requisitos

- Linux con entorno gráfico, navegador predeterminado y WhatsApp Web vinculado a tu WhatsApp personal.
- Python 3.10+; solo biblioteca estándar de Python.
- `xdg-open` (paquete `xdg-utils` en Debian/Ubuntu).

En Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 xdg-utils
```

No ejecutes el script con `sudo`. Si lo utilizas desde un servidor sin interfaz gráfica, se imprimirá el enlace para abrirlo manualmente desde un navegador.

## CSV

Coloca tu archivo real en la **misma carpeta** que `iniciar.sh`, con el nombre exacto **`invitados.csv`**. El archivo de ejemplo del paquete es deliberadamente inválido: no son números reales y solo indica el formato.

Encabezados requeridos (se permite `,` o `;`):

```csv
Nombre,Telefono,Invitados
Carlos,50255551234,2
Ana,+1 (202) 555-0100,3
```

Guatemala: 8 dígitos locales o 502 + 8 dígitos. Prefijo +1: 10 dígitos nacionales o 1 + 10 dígitos. `+1` comprende Estados Unidos, Canadá y otros territorios: el script **no verifica** que el número sea realmente estadounidense. No se valida la existencia de la cuenta WhatsApp. Si tu CSV exportado desde Excel alteró los teléfonos o incluye números con otros códigos de país, corrígelo primero.

La columna `Invitados` es la cantidad de cupos y debe ser un entero positivo.

## Uso

```bash
chmod +x iniciar.sh
./iniciar.sh validar
./iniciar.sh enviar --limite 10
./iniciar.sh reporte
./iniciar.sh exportar
```

### Modos de envío

El comando `enviar` tiene tres modos. En todos, **WhatsApp requiere que tú pulses Enviar**; `wa.me` solo abre el chat con el texto precargado.

- **Interactivo (por defecto)**: abre de uno en uno y te pregunta por cada contacto si lo enviaste. Máximo control.
  ```bash
  ./iniciar.sh enviar --limite 10
  ```
- **Ráfaga**: abre todos los chats de corrido con una pausa entre cada uno, sin preguntarte contacto por contacto. Tú solo vas pulsando Enviar en cada ventana que aparece. Con `--marcar` registra cada uno como ENVIADO al abrirlo.
  ```bash
  ./iniciar.sh enviar --rafaga --pausa 3
  ./iniciar.sh enviar --rafaga --pausa 3 --marcar
  ```
- **Solo enlaces**: no abre nada; imprime todos los enlaces `wa.me` para que los abras como prefieras (copiar/pegar, otro script, etc.).
  ```bash
  ./iniciar.sh enviar --solo-enlaces
  ```

Opciones:

- `--limite N`: máximo de conversaciones a procesar.
- `--rafaga`: abre todo de corrido sin confirmar uno por uno.
- `--pausa S`: segundos entre cada chat en modo `--rafaga` (por defecto 3).
- `--marcar`: en `--rafaga`, marca cada contacto como ENVIADO automáticamente al abrirlo.
- `--solo-enlaces`: imprime los enlaces sin abrir el navegador (incompatible con `--rafaga`).

### Flujo de envío recomendado

1. Ejecuta `./iniciar.sh validar`; debe terminar **sin incidencias**.
2. Inicia sesión en `https://web.whatsapp.com/` en tu navegador de Linux.
3. Prueba primero contigo: `./iniciar.sh enviar --limite 1`.
4. Para enviar a todos de forma fluida: `./iniciar.sh enviar --rafaga --pausa 3`.
5. **Tú pulsas Enviar** en cada ventana de WhatsApp. En modo interactivo confirmas con `s` en la terminal; en ráfaga usa `--marcar` si quieres registro automático.
6. Puedes interrumpir con `q` (modo interactivo) o Ctrl+C. El progreso confirmado se conserva y al reanudar solo verás los pendientes.

### Archivos generados

- `progreso.sqlite3`: base local con teléfonos que marcaste como enviados.
- `reporte_envios.csv`: se genera al ejecutar `exportar`; incluye nombre, teléfono, país, cupos, estado y fecha de confirmación manual.

No borres `progreso.sqlite3` si quieres conservar el historial de envíos. No subas `invitados.csv`, `progreso.sqlite3` ni `reporte_envios.csv` a GitHub, porque contienen datos personales.

## Mensaje

El texto se arma en la función `crear_mensaje` de `invitaciones.py`. Usa formato de WhatsApp (`*texto*` para negrita) y emojis:

```text
🎉✨ *¡Tenemos una alegría muy especial que queremos compartir contigo!* ✨🎉

Con el corazón lleno de felicidad y gratitud a Dios, queremos celebrar una hermosa bendición: *¡los 60 años de vida de nuestro querido Edvin!* 🎂❤️

*Nos llenaría de alegría contar con tu presencia* para compartir juntos este día tan especial, lleno de sonrisas, cariño y hermosos recuerdos. 🥳

💌 *Hemos preparado esta invitación especialmente para ti:*

🔗 https://rodolfo60s.isdomana.com/

*¡Te esperamos con mucho cariño para celebrar juntos esta gran bendición!* ❤️🎊
```

Para cambiar el texto o la URL, edita `crear_mensaje` y la constante `FIESTA_URL` en `invitaciones.py`.

### Nota sobre emojis en Linux

Si los emojis se ven como un rombo con signo de interrogación, es que a tu sistema Linux le falta una fuente de emojis a color. El mensaje se envía bien igualmente; es solo cómo lo muestra tu pantalla. Instálala con:

```bash
sudo apt install -y fonts-noto-color-emoji
```

Luego reinicia el navegador. El destinatario los verá correctamente aunque tú no.

## Limitaciones deliberadas

- No envía automáticamente los mensajes. `wa.me` solo abre el chat con un texto precargado.
- No evita todos los riesgos asociados con mensajes repetidos; evita herramientas de automatización no oficiales y requiere una acción manual para cada envío.
- No prueba si el número existe o tiene WhatsApp.
- No interpreta respuestas ni confirma lectura o entrega.
- Una marca `ENVIADO` es exclusivamente tu confirmación manual.
