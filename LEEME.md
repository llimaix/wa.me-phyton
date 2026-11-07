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

El parámetro opcional `--con-cupos` incorpora la cantidad de personas al texto:

```bash
./iniciar.sh enviar --limite 10 --con-cupos
```

### Flujo de envío

1. Ejecuta `./iniciar.sh validar`; debe terminar **sin incidencias**.
2. Inicia sesión en `https://web.whatsapp.com/` en tu navegador de Linux.
3. Ejecuta `./iniciar.sh enviar --limite 10` para un lote pequeño.
4. Se muestra la persona y se abre su conversación con el texto prellenado.
5. **Tú pulsas Enviar** en WhatsApp. Después contestas `s` en la terminal para registrar el envío.
6. Si no lo enviaste, contesta `n`: seguirá pendiente. Verifica el chat antes de volverlo a intentar, ya que la herramienta no puede consultar WhatsApp para comprobar el envío.
7. Repite los lotes que quieras. Puedes interrumpir con `q` o Ctrl+C. El progreso confirmado se conserva.

### Archivos generados

- `progreso.sqlite3`: base local con teléfonos que marcaste como enviados.
- `reporte_envios.csv`: se genera al ejecutar `exportar`; incluye nombre, teléfono, país, cupos, estado y fecha de confirmación manual.

No borres `progreso.sqlite3` si quieres conservar el historial de envíos. No subas `invitados.csv`, `progreso.sqlite3` ni `reporte_envios.csv` a GitHub, porque contienen datos personales.

## Mensaje

```text
Hola, <Nombre>.

Estás invitado a mi fiesta:
https://rodolfo60s.isdomana.com/

Nota: Confirma tu asistencia respondiendo al número desde el que recibiste este mensaje.

Tu asistencia es muy importante para nosotros.
```

Si se utiliza `--con-cupos`, se agrega la línea `Tu invitación contempla N persona(s).` antes de la nota.

## Limitaciones deliberadas

- No envía automáticamente los mensajes. `wa.me` solo abre el chat con un texto precargado.
- No evita todos los riesgos asociados con mensajes repetidos; evita herramientas de automatización no oficiales y requiere una acción manual para cada envío.
- No prueba si el número existe o tiene WhatsApp.
- No interpreta respuestas ni confirma lectura o entrega.
- Una marca `ENVIADO` es exclusivamente tu confirmación manual.
