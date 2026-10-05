from flask import Flask, render_template, request
import time
import sys

# Límite de llamadas recursivas en memoria
sys.setrecursionlimit(60000)

caballo_chess = Flask(__name__)

# Genera los saltos legales del caballo dentro del tablero 8x8
def obtener_movimientos(x, y, n=8):
    posibles_saltos = [
        (x + 2, y + 1), (x + 2, y - 1),
        (x - 2, y + 1), (x - 2, y - 1),
        (x + 1, y + 2), (x + 1, y - 2),
        (x - 1, y + 2), (x - 1, y - 2)
    ]
    movimientos_validos = []
    for nx, ny in posibles_saltos:
        if nx >= 0 and nx < n and ny >= 0 and ny < n:
            movimientos_validos.append((nx, ny))
    return movimientos_validos

# Cuenta cuántas casillas libres tiene alrededor una posición
def contar_salidas(x, y, visitados, n=8):
    salidas_libres = 0
    for nx, ny in obtener_movimientos(x, y, n):
        if (nx, ny) not in visitados:
            salidas_libres += 1
    return salidas_libres

# 1. Algoritmo A* (Búsqueda Informada)
def resolver_a_estrella(x, y, paso, ruta, visitados, eventos, stats, n=8):
    stats["nodos_evaluados"] += 1
    if paso > stats["profundidad_max"]:
        stats["profundidad_max"] = paso

    eventos.append({"tipo": "avanzar", "x": x, "y": y, "paso": paso})

    # Si completó las 64 casillas, terminamos con éxito
    if paso == n * n:
        return True

    vecinos = obtener_movimientos(x, y, n)
    candidatos = []

    for nx, ny in vecinos:
        if (nx, ny) not in visitados:
            g = paso                                   # Costo del camino recorrido
            h = contar_salidas(nx, ny, visitados, n)   # Estimación heurística de salidas
            f = g + h                                  # Función de evaluación f(n) = g(n) + h(n)
            candidatos.append((f, h, nx, ny))

    # Se ordena para probar primero el camino con menor costo total
    candidatos.sort()

    for f, h, nx, ny in candidatos:
        visitados.add((nx, ny))
        ruta.append((nx, ny))

        if resolver_a_estrella(nx, ny, paso + 1, ruta, visitados, eventos, stats, n):
            return True

        # Si este camino no tuvo salida, retrocedemos
        stats["retrocesos"] += 1
        eventos.append({
            "tipo": "retroceder",
            "x": nx,
            "y": ny,
            "x_ant": x,
            "y_ant": y,
            "paso": paso
        })
        visitados.remove((nx, ny))
        ruta.pop()

    return False

# 2. Algoritmo DFS (Búsqueda Ciega por Profundidad)
def resolver_dfs_intensivo(x, y, ruta, visitados, eventos, stats, n=8, max_eventos=180):
    stats["nodos_evaluados"] += 1
    paso_actual = len(ruta)

    if paso_actual > stats["profundidad_max"]:
        stats["profundidad_max"] = paso_actual

    if paso_actual == n * n:
        return True

    # Parada de seguridad para no bloquear la computadora
    if stats["nodos_evaluados"] >= stats["limite_nodos"]:
        return False

    vecinos = obtener_movimientos(x, y, n)

    for nx, ny in vecinos:
        if (nx, ny) not in visitados:
            visitados.add((nx, ny))
            ruta.append((nx, ny))
            nuevo_paso = len(ruta)

            # Guarda los primeros pasos para la animación en el navegador
            if len(eventos) < max_eventos:
                eventos.append({"tipo": "avanzar", "x": nx, "y": ny, "paso": nuevo_paso})

            if resolver_dfs_intensivo(nx, ny, ruta, visitados, eventos, stats, n, max_eventos):
                return True

            if stats["nodos_evaluados"] >= stats["limite_nodos"]:
                return False

            # Vuelta atrás (Backtracking)
            stats["retrocesos"] += 1
            if len(eventos) < max_eventos:
                eventos.append({
                    "tipo": "retroceder",
                    "x": nx,
                    "y": ny,
                    "x_ant": x,
                    "y_ant": y,
                    "paso": nuevo_paso - 1
                })

            visitados.remove((nx, ny))
            ruta.pop()

    return False

# Ruta principal de la aplicación Flask
@caballo_chess.route('/')
def inicio():
    x_param = request.args.get('x')
    y_param = request.args.get('y')

    # Si falta algún parámetro, mostramos la pantalla para elegir casilla
    if not x_param or not y_param:
        return render_template('index.html', modo="seleccion", start_x=None, start_y=None)

    # Conversión directa y segura a número entero sin usar try / except
    if x_param.isdigit() and y_param.isdigit():
        start_x = int(x_param)
        start_y = int(y_param)
    else:
        start_x = 0
        start_y = 0

    # Ejecución y medición de A*
    stats_a = {"nodos_evaluados": 0, "retrocesos": 0, "profundidad_max": 1}
    eventos_a = []
    ruta_a = [(start_x, start_y)]
    visitados_a = {(start_x, start_y)}

    tiempo_inicio_a = time.perf_counter()
    exito_a = resolver_a_estrella(start_x, start_y, 1, ruta_a, visitados_a, eventos_a, stats_a, 8)
    tiempo_a = round((time.perf_counter() - tiempo_inicio_a) * 1000, 3)

    # Ejecución y medición de DFS (Explora hasta 150,000 nodos)
    stats_dfs = {
        "nodos_evaluados": 0,
        "retrocesos": 0,
        "profundidad_max": 1,
        "limite_nodos": 150000
    }
    eventos_dfs = [{"tipo": "avanzar", "x": start_x, "y": start_y, "paso": 1}]
    ruta_dfs = [(start_x, start_y)]
    visitados_dfs = {(start_x, start_y)}

    tiempo_inicio_dfs = time.perf_counter()
    exito_dfs = resolver_dfs_intensivo(start_x, start_y, ruta_dfs, visitados_dfs, eventos_dfs, stats_dfs, 8, max_eventos=180)
    tiempo_dfs = round((time.perf_counter() - tiempo_inicio_dfs) * 1000, 3)

    # Porcentajes de eficiencia de búsqueda
    eficiencia_a = round((64 / stats_a["nodos_evaluados"]) * 100, 1)
    eficiencia_dfs = round((stats_dfs["profundidad_max"] / stats_dfs["nodos_evaluados"]) * 100, 3)

    return render_template(
        'index.html',
        modo="simulacion",
        start_x=start_x,
        start_y=start_y,
        eventos_a=eventos_a,
        exito_a=exito_a,
        tiempo_a=tiempo_a,
        stats_a=stats_a,
        eficiencia_a=eficiencia_a,
        eventos_dfs=eventos_dfs,
        exito_dfs=exito_dfs,
        tiempo_dfs=tiempo_dfs,
        stats_dfs=stats_dfs,
        eficiencia_dfs=eficiencia_dfs
    )

if __name__ == '__main__':
    caballo_chess.run(debug=True)