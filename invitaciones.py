#!/usr/bin/env python3
"""Invitaciones por WhatsApp con wa.me y confirmación manual. Python stdlib."""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
import os

BASE = Path(__file__).resolve().parent
CSV_PATH = BASE / 'invitados.csv'
DB_PATH = BASE / 'progreso.sqlite3'
REPORT_PATH = BASE / 'reporte_envios.csv'
FIESTA_URL = 'https://rodolfo60s.isdomana.com/'

@dataclass(frozen=True)
class Invitado:
    nombre: str
    telefono: str
    pais: str
    cupos: int


def normalizar_telefono(valor: str) -> tuple[str, str]:
    """Retorna teléfono internacional sin '+' para wa.me."""
    valor = valor.strip()
    if not valor or not re.fullmatch(r'\+?[\d\s().-]+', valor):
        raise ValueError('teléfono vacío o contiene caracteres no admitidos')
    if '+' in valor[1:]:
        raise ValueError('prefijo + en posición no válida')
    digitos = re.sub(r'\D', '', valor)
    if digitos.startswith('00'):
        digitos = digitos[2:]

    # Se consideran locales de Guatemala los teléfonos de ocho dígitos.
    # Se consideran NANP (+1) los de diez dígitos; incluye EE. UU. y otros territorios.
    if len(digitos) == 8:
        return '502' + digitos, 'Guatemala (+502)'
    if len(digitos) == 11 and digitos.startswith('502'):
        return digitos, 'Guatemala (+502)'
    if len(digitos) == 10:
        return '1' + digitos, 'NANP (+1)'
    if len(digitos) == 11 and digitos.startswith('1'):
        return digitos, 'NANP (+1)'
    raise ValueError(f'prefijo o longitud no reconocidos: {valor!r}')


def leer_csv() -> tuple[list[Invitado], list[str]]:
    if not CSV_PATH.is_file():
        raise FileNotFoundError(
            f'No se encontró {CSV_PATH.name} en {BASE}. '
            'Copia tu CSV real a esa carpeta y conserva el encabezado Nombre,Telefono,Invitados.'
        )
    with CSV_PATH.open('r', encoding='utf-8-sig', newline='') as archivo:
        muestra = archivo.read(8192)
        archivo.seek(0)
        try:
            dialecto = csv.Sniffer().sniff(muestra, delimiters=',;')
        except csv.Error:
            dialecto = csv.excel
        reader = csv.DictReader(archivo, dialect=dialecto)
        if not reader.fieldnames:
            raise ValueError('El archivo está vacío o no tiene encabezados')
        columnas = {c.strip().casefold(): c for c in reader.fieldnames if c is not None}
        faltan = [x for x in ('nombre', 'telefono', 'invitados') if x not in columnas]
        if faltan:
            raise ValueError(f'Columnas faltantes: {", ".join(faltan)}. Encabezados: {reader.fieldnames}')

        contactos: list[Invitado] = []
        errores: list[str] = []
        vistos: dict[str, int] = {}
        duplicados: set[str] = set()
        for linea, fila in enumerate(reader, start=2):
            if None in fila:
                errores.append(f'Fila {linea}: tiene columnas adicionales; revisa delimitadores y comillas')
                continue
            if not any(str(v or '').strip() for v in fila.values()):
                continue
            nombre = re.sub(r'\s+', ' ', str(fila.get(columnas['nombre']) or '')).strip()
            raw_tel = str(fila.get(columnas['telefono']) or '').strip()
            cupos_raw = str(fila.get(columnas['invitados']) or '').strip()
            if not nombre:
                errores.append(f'Fila {linea}: Nombre vacío')
                continue
            try:
                telefono, pais = normalizar_telefono(raw_tel)
            except ValueError as exc:
                errores.append(f'Fila {linea} ({nombre}): {exc}')
                continue
            if not re.fullmatch(r'[1-9]\d*', cupos_raw):
                errores.append(f'Fila {linea} ({nombre}): Invitados debe ser un entero positivo; recibido {cupos_raw!r}')
                continue
            cupos = int(cupos_raw)
            if telefono in vistos:
                duplicados.add(telefono)
                errores.append(
                    f'Fila {linea} ({nombre}): teléfono duplicado {telefono} '
                    f'(primera aparición fila {vistos[telefono]})'
                )
            else:
                vistos[telefono] = linea
            contactos.append(Invitado(nombre, telefono, pais, cupos))

    # Nunca se envía a un teléfono duplicado: hay ambigüedad en nombre/cupos.
    contactos = [c for c in contactos if c.telefono not in duplicados]
    return contactos, errores


def conectar() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute('''CREATE TABLE IF NOT EXISTS enviados (
        telefono TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        cupos INTEGER NOT NULL,
        enviado_en TEXT NOT NULL
    )''')
    con.commit()
    return con


def mensajes_enviados(con: sqlite3.Connection) -> set[str]:
    return {x[0] for x in con.execute('SELECT telefono FROM enviados')}


def crear_mensaje(c: Invitado, sin_emojis: bool = False) -> str:
    if sin_emojis:
        return (
            '*¡Tenemos una alegría muy especial que queremos compartir contigo!*\n\n'
            'Con el corazón lleno de felicidad y gratitud a Dios, queremos celebrar una hermosa '
            'bendición: *¡los 60 años de vida de nuestro querido Edvin!*\n\n'
            '*Nos llenaría de alegría contar con tu presencia* para compartir juntos este día tan '
            'especial, lleno de sonrisas, cariño y hermosos recuerdos.\n\n'
            '*Hemos preparado esta invitación especialmente para ti:*\n\n'
            f'{FIESTA_URL}\n\n'
            '*¡Te esperamos con mucho cariño para celebrar juntos esta gran bendición!*'
        )
    return (
        '🎉✨ *¡Tenemos una alegría muy especial que queremos compartir contigo!* ✨🎉\n\n'
        'Con el corazón lleno de felicidad y gratitud a Dios, queremos celebrar una hermosa '
        'bendición: *¡los 60 años de vida de nuestro querido Edvin!* 🎂❤️\n\n'
        '*Nos llenaría de alegría contar con tu presencia* para compartir juntos este día tan '
        'especial, lleno de sonrisas, cariño y hermosos recuerdos. 🥳\n\n'
        '💌 *Hemos preparado esta invitación especialmente para ti:*\n\n'
        f'🔗 {FIESTA_URL}\n\n'
        '*¡Te esperamos con mucho cariño para celebrar juntos esta gran bendición!* ❤️🎊'
    )


def enlace(c: Invitado, sin_emojis: bool = False) -> str:
    # web.whatsapp.com/send va directo al chat y evita la página intermedia de wa.me
    # ("Abrir aplicación / Continuar en WhatsApp Web").
    texto = quote(crear_mensaje(c, sin_emojis), safe='')
    return f'https://web.whatsapp.com/send?phone={c.telefono}&text={texto}'


def abrir_en_linux(url: str) -> bool:
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        print('\nNo se detectó una sesión gráfica. Abre manualmente el siguiente enlace en un navegador con WhatsApp:')
        print(url)
        return False
    cmd = shutil.which('xdg-open')
    if not cmd:
        print('\nNo se encontró xdg-open. Instala xdg-utils o abre este enlace manualmente:')
        print(url)
        return False
    try:
        subprocess.Popen([cmd, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError as exc:
        print(f'No se pudo abrir el navegador ({exc}). Enlace: {url}')
        return False
    return True


def resumen(contactos: list[Invitado], errores: list[str], con: sqlite3.Connection) -> tuple[int, int]:
    enviados = mensajes_enviados(con)
    completados = sum(c.telefono in enviados for c in contactos)
    print(f'Contactos válidos y únicos: {len(contactos)}')
    print(f'Cupos totales de los contactos válidos: {sum(c.cupos for c in contactos)}')
    print(f'Envíos confirmados manualmente: {completados}')
    print(f'Pendientes: {len(contactos) - completados}')
    print(f'Guatemala (+502): {sum(c.pais.startswith("Guatemala") for c in contactos)}')
    print(f'Prefijo +1 (NANP): {sum(c.pais.startswith("NANP") for c in contactos)}')
    if errores:
        print(f'\nINCIDENCIAS ({len(errores)}):')
        for err in errores:
            print('  -', err)
    return completados, len(contactos) - completados


def confirmar_envio(con: sqlite3.Connection, c: Invitado) -> None:
    marca = datetime.now().astimezone().isoformat(timespec='seconds')
    con.execute('INSERT OR IGNORE INTO enviados VALUES (?, ?, ?, ?)',
                (c.telefono, c.nombre, c.cupos, marca))
    con.commit()


def _pendientes(contactos: list[Invitado], con: sqlite3.Connection,
                limite: int | None) -> list[Invitado]:
    sent = mensajes_enviados(con)
    lista = [c for c in contactos if c.telefono not in sent]
    if limite is not None:
        lista = lista[:limite]
    return lista


def enviar_interactivo(pendientes: list[Invitado], con: sqlite3.Connection,
                       sin_emojis: bool) -> None:
    """Modo clásico: abre de uno en uno y confirma el envío de cada contacto."""
    for indice, c in enumerate(pendientes, start=1):
        print(f'\n[{indice}/{len(pendientes)}] {c.nombre} | +{c.telefono} | {c.pais} | cupos: {c.cupos}')
        opcion = input('[Enter] Abrir mensaje | [o] omitir | [q] salir: ').strip().lower()
        if opcion == 'q':
            break
        if opcion == 'o':
            continue
        abrir_en_linux(enlace(c, sin_emojis))
        confirmacion = input('¿Pulsaste Enviar y viste el mensaje en WhatsApp? [s] sí | [n] no | [q] salir: ').strip().lower()
        if confirmacion == 's':
            confirmar_envio(con, c)
            print('Registrado como ENVIADO (confirmación manual).')
        elif confirmacion == 'q':
            break
        else:
            print('Permanece PENDIENTE. Verifica en WhatsApp antes de reintentarlo.')


def enviar_rafaga(pendientes: list[Invitado], con: sqlite3.Connection,
                  pausa: float, marcar: bool, sin_emojis: bool) -> None:
    """Abre todos los chats de corrido con una pausa entre cada uno, sin confirmar
    contacto por contacto. Tú solo pulsas Enviar en cada ventana que aparece."""
    print(f'\nModo ráfaga: se abrirán {len(pendientes)} chats con {pausa}s de separación.')
    print('Pulsa Enviar en cada ventana de WhatsApp a medida que se abren. Ctrl+C para detener.\n')
    for indice, c in enumerate(pendientes, start=1):
        print(f'[{indice}/{len(pendientes)}] Abriendo: {c.nombre} | +{c.telefono} | {c.pais}')
        abrir_en_linux(enlace(c, sin_emojis))
        if marcar:
            confirmar_envio(con, c)
        if indice < len(pendientes):
            time.sleep(pausa)
    if marcar:
        print('\nTodos los contactos se marcaron como ENVIADO automáticamente (--marcar).')
    else:
        print('\nLos chats se abrieron pero NINGUNO quedó marcado como enviado.')
        print('Usa --marcar si quieres registrarlos automáticamente, o confirma luego con el modo normal.')


def enviar_solo_enlaces(pendientes: list[Invitado], sin_emojis: bool) -> None:
    """Imprime todos los enlaces wa.me juntos para abrirlos como prefieras."""
    print(f'\n{len(pendientes)} enlaces (uno por línea). Ábrelos en tu navegador:\n')
    for c in pendientes:
        print(f'# {c.nombre} | +{c.telefono} | {c.pais} | cupos: {c.cupos}')
        print(enlace(c, sin_emojis))
        print()
    print('Ningún contacto quedó marcado como enviado. Registra el estado con el modo normal si lo necesitas.')


def enviar(contactos: list[Invitado], errores: list[str], con: sqlite3.Connection,
           limite: int | None, rafaga: bool, pausa: float, marcar: bool,
           solo_enlaces: bool, sin_emojis: bool) -> int:
    if errores:
        print('Corrige las incidencias antes de iniciar. Esto evita enviar a números o personas ambiguas.\n')
        resumen(contactos, errores, con)
        return 2
    pendientes = _pendientes(contactos, con, limite)
    if not pendientes:
        print('No hay invitaciones pendientes.')
        return 0

    if solo_enlaces:
        enviar_solo_enlaces(pendientes, sin_emojis)
        print('\nResumen:')
        resumen(contactos, [], con)
        return 0

    print(f'Hay {len(pendientes)} contactos pendientes. El programa NO pulsa Enviar por ti.')
    print('Primero inicia sesión en https://web.whatsapp.com/ con tu WhatsApp personal.')
    print('\nVista previa del primer mensaje:\n')
    print(crear_mensaje(pendientes[0], sin_emojis))
    if input('\n¿Comenzar? [s/N]: ').strip().lower() != 's':
        print('Cancelado sin cambios.')
        return 0

    if rafaga:
        enviar_rafaga(pendientes, con, pausa, marcar, sin_emojis)
    else:
        enviar_interactivo(pendientes, con, sin_emojis)

    print('\nResumen tras la sesión:')
    resumen(contactos, [], con)
    return 0


def exportar(contactos: list[Invitado], con: sqlite3.Connection) -> None:
    rows = {r[0]: r[1] for r in con.execute('SELECT telefono, enviado_en FROM enviados')}
    with REPORT_PATH.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Nombre', 'Telefono', 'Pais', 'Invitados', 'Estado', 'Fecha_confirmacion_manual'])
        for c in contactos:
            writer.writerow([c.nombre, '+' + c.telefono, c.pais, c.cupos,
                             'ENVIADO' if c.telefono in rows else 'PENDIENTE', rows.get(c.telefono, '')])
    print(f'Reporte exportado: {REPORT_PATH}')


def main() -> int:
    parser = argparse.ArgumentParser(description='Invitaciones desde Linux mediante enlaces wa.me (envío manual).')
    commands = parser.add_subparsers(dest='accion', required=True)
    commands.add_parser('validar', help='Validar CSV y mostrar totales sin abrir WhatsApp')
    commands.add_parser('reporte', help='Mostrar estado actual')
    commands.add_parser('exportar', help='Crear reporte_envios.csv')
    send = commands.add_parser('enviar', help='Abrir mensajes y registrar el envío')
    send.add_argument('--limite', type=int, default=None, help='Máximo de conversaciones a abrir')
    send.add_argument('--rafaga', action='store_true',
                      help='Abre todos los chats de corrido, sin confirmar contacto por contacto')
    send.add_argument('--pausa', type=float, default=3.0,
                      help='Segundos entre cada chat en modo --rafaga (por defecto 3)')
    send.add_argument('--marcar', action='store_true',
                      help='En --rafaga, marca cada contacto como ENVIADO automáticamente al abrirlo')
    send.add_argument('--solo-enlaces', action='store_true',
                      help='Solo imprime todos los enlaces wa.me, sin abrir el navegador')
    send.add_argument('--sin-emojis', action='store_true',
                      help='Envía el mensaje sin emojis (útil si tu navegador los muestra mal)')
    args = parser.parse_args()
    if args.accion == 'enviar':
        if args.limite is not None and args.limite <= 0:
            parser.error('--limite debe ser un entero positivo')
        if args.pausa < 0:
            parser.error('--pausa no puede ser negativa')
        if args.marcar and not args.rafaga:
            parser.error('--marcar solo aplica junto con --rafaga')
        if args.solo_enlaces and args.rafaga:
            parser.error('--solo-enlaces y --rafaga son mutuamente excluyentes')
    try:
        contactos, errores = leer_csv()
    except (FileNotFoundError, ValueError, UnicodeError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
    with conectar() as con:
        if args.accion in ('validar', 'reporte'):
            resumen(contactos, errores, con)
            return 2 if errores else 0
        if args.accion == 'exportar':
            if errores:
                resumen(contactos, errores, con)
                print('Corrige las incidencias antes de exportar.', file=sys.stderr)
                return 2
            exportar(contactos, con)
            return 0
        if args.accion == 'enviar':
            return enviar(contactos, errores, con, args.limite,
                          args.rafaga, args.pausa, args.marcar, args.solo_enlaces,
                          args.sin_emojis)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\nInterrumpido. Los envíos ya registrados se conservan.')
        sys.exit(130)
