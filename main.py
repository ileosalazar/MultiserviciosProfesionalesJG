import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QInputDialog
from PySide6.QtGui import QIcon, QRegularExpressionValidator, QIntValidator, QDoubleValidator 
from PySide6.QtCore import QFile, QDate, QRegularExpression
from PySide6.QtUiTools import QUiLoader
from database import conectar_bd
import random
import string

def ruta_recurso(ruta_relativa):
    try:
        ruta_base = sys._MEIPASS
    except Exception:
        ruta_base = os.path.abspath(".")

    return os.path.join(ruta_base, ruta_relativa)


#Pantalla agendar cita desde el administrador
class NuevaCitaWindow:
    def __init__(self, parent=None): 
        self.parent = parent
        loader = QUiLoader()
        archivo = QFile(ruta_recurso("nueva_cita.ui"))
        archivo.open(QFile.ReadOnly)
        self.ui = loader.load(archivo)
        archivo.close()
        self.ui.setWindowTitle("Agendar Nueva Cita")
        self.ui.input_fecha.setMinimumDate(QDate.currentDate())

        self.ui.btn_nuevo_aparato.clicked.connect(self.alternar_modo_aparato)
        self.ui.btn_guardar_cita.clicked.connect(self.guardar_cita)
        
        self.ui.combo_cliente.currentIndexChanged.connect(self.cargar_aparatos)
        
        self.cargar_clientes()

    def cargar_clientes(self):
        conexion = conectar_bd()
        if not conexion: return
        try:
            cursor = conexion.cursor()
            cursor.execute("SELECT id, nombre, apellido_paterno FROM clientes")
            clientes = cursor.fetchall()
            
            self.ui.combo_cliente.clear()
            self.ui.combo_cliente.addItem("Seleccione un cliente...", None)
            
            for cliente in clientes:
                id_cliente = cliente[0]
                nombre_completo = f"{cliente[1]} {cliente[2]}"
                
                self.ui.combo_cliente.addItem(nombre_completo, id_cliente)

            self.ui.tabla_clientes.setColumnHidden(0, True)

        except Exception as e:
            print(f"Error al cargar clientes: {e}")
        finally:
            cursor.close()
            conexion.close()


    def cargar_aparatos(self):
        id_cliente = self.ui.combo_cliente.currentData()
        
        self.ui.combo_aparato.clear()
        
        if not id_cliente:
            return 
            
        conexion = conectar_bd()
        if not conexion: return
        try:
            cursor = conexion.cursor()
            cursor.execute("SELECT id, tipo, marca FROM aparatos WHERE id_cliente = %s", (id_cliente,))
            aparatos = cursor.fetchall()
            
            if not aparatos:
                self.ui.combo_aparato.addItem("Sin aparatos registrados", None)
                return
                
            for ap in aparatos:
                id_aparato = ap[0]
                descripcion = f"{ap[1]} {ap[2]}" 
                self.ui.combo_aparato.addItem(descripcion, id_aparato)

            self.ui.tabla_aparatos.setColumnHidden(0, True)

        except Exception as e:
            print(f"Error al cargar aparatos: {e}")
        finally:
            cursor.close()
            conexion.close()

    def alternar_modo_aparato(self):
        if self.ui.combo_aparato.isEnabled():
            self.ui.combo_aparato.setEnabled(False)
        
            self.ui.txt_nuevo_tipo.setEnabled(True)
            self.ui.txt_nueva_marca.setEnabled(True)
        
            self.ui.btn_nuevo_aparato.setText("Cancelar Nuevo")
        
        else:
            self.ui.combo_aparato.setEnabled(True)
        
            self.ui.txt_nuevo_tipo.setEnabled(False)
            self.ui.txt_nueva_marca.setEnabled(False)
        
            self.ui.txt_nuevo_tipo.clear()
            self.ui.txt_nueva_marca.clear()
            

    def guardar_cita(self):
        id_cliente = self.ui.combo_cliente.currentData()
        fecha = self.ui.input_fecha.text()

        id_aparato_final = None

        if self.ui.combo_aparato.isEnabled():
            id_aparato_final = self.ui.combo_aparato.currentData()

            if not id_aparato_final:
                QMessageBox.warning(self.ui, "Error", "Selecciona un aparato.")
                return

        else:
            nuevo_tipo = self.ui.txt_nuevo_tipo.text().strip()
            nueva_marca = self.ui.txt_nueva_marca.text().strip()

            if not nuevo_tipo or not nueva_marca:
                QMessageBox.warning(self, "Error", "Debes ingresar el tipo y marca del nuevo aparato.")
                return

            conexion = conectar_bd()
            if not conexion: return
            cursor = conexion.cursor()
            
            sql_aparato = "INSERT INTO aparatos (id_cliente, tipo, marca) VALUES (%s, %s, %s) RETURNING id"
            cursor.execute(sql_aparato, (id_cliente, nuevo_tipo, nueva_marca))
            id_aparato_final = cursor.fetchone()[0]

            conexion.commit()

        if not id_cliente or not fecha:
            QMessageBox.warning(self.ui, "Error", "Llena todos los campos.")
            return


        letras_numeros = string.ascii_uppercase + string.digits
        codigo_aleatorio = ''.join(random.choices(letras_numeros, k=5))
        folio = f"MS-{codigo_aleatorio}"

        conexion = conectar_bd()
        if not conexion: return
        try:
            cursor = conexion.cursor()
            
            sql_servicio = """
            INSERT INTO servicios (id_aparato, fecha_visita, estado, costo_revision, costo_mano_obra, folio_seguimiento) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
            valores_servicio = (id_aparato_final, fecha, "Pendiente", 0.00, 0.00, folio)
            cursor.execute(sql_servicio, valores_servicio)
            conexion.commit() 
            
            QMessageBox.information(self.ui, "Éxito", f"Cita agendada.\nFolio del cliente: {folio}. Cambie el estado de la cita a 'En revisión' para agregar el costo de revisión.")

            if self.parent:
                self.parent.cargar_citas()

            self.ui.close() 
            
        except Exception as e:
            conexion.rollback()
            QMessageBox.critical(self.ui, "Error BD", f"Fallo al guardar:\n{e}")
        finally:
            cursor.close()
            conexion.close()


#Pantalla agregar refaccion a una cita
class AgregarPiezaWindow:
    def __init__(self, parent=None, folio=""):
        self.parent = parent
        self.folio = folio
        
        loader = QUiLoader()
        archivo = QFile(ruta_recurso("agregar_pieza.ui"))
        archivo.open(QFile.ReadOnly)
        self.ui = loader.load(archivo)
        archivo.close()
        
        self.ui.setWindowTitle(f"Agregar Pieza - Folio: {self.folio}")
        
        self.cargar_inventario_combo()

        self.ui.input_cantidad.setValidator(validador_numeros)
        
        self.ui.combo_refaccion.currentIndexChanged.connect(self.actualizar_etiquetas)
        self.ui.btn_guardar_pieza.clicked.connect(self.guardar_pieza)

        self.actualizar_etiquetas()

    def cargar_inventario_combo(self):
        conexion = conectar_bd()
        if not conexion: return
        try:
            cursor = conexion.cursor()
            cursor.execute("SELECT id, nombre, stock, precio_publico FROM refacciones ORDER BY nombre ASC")
            piezas = cursor.fetchall()
            
            for p in piezas:
                id_pieza, nombre, stock, precio = p
                datos_ocultos = {"id": id_pieza, "stock": stock, "precio": precio}
                self.ui.combo_refaccion.addItem(nombre, datos_ocultos)
        except Exception as e:
            print(f"Error al cargar combo: {e}")
        finally:
            cursor.close()
            conexion.close()

    def actualizar_etiquetas(self):
        datos = self.ui.combo_refaccion.currentData()
        
        if datos:
            self.ui.lbl_stock_actual.setText(f"Stock disponible: {datos['stock']}")
            self.ui.lbl_precio_sugerido.setText(f"Precio unitario: ${datos['precio']:.2f}")
            
            if datos['stock'] <= 0:
                self.ui.lbl_stock_actual.setStyleSheet("color: red; font-weight: bold;")
            else:
                self.ui.lbl_stock_actual.setStyleSheet("color: green;")

    def guardar_pieza(self):
        datos = self.ui.combo_refaccion.currentData()
        cantidad_texto = self.ui.input_cantidad.text().strip()

        if not datos or not cantidad_texto:
            QMessageBox.warning(self.ui, "Error", "Asegúrate de llenar la cantidad.")
            return

        try:
            cantidad = int(cantidad_texto)
            if cantidad <= 0:
                raise ValueError

            if cantidad > datos['stock']:
                QMessageBox.warning(self.ui, "Stock Insuficiente", 
                    f"Estás intentando agregar {cantidad} piezas, pero solo tienes {datos['stock']} en el inventario.")
                return

            conexion = conectar_bd()
            if not conexion: return
            cursor = conexion.cursor()
            
            cursor.execute("SELECT id FROM servicios WHERE folio_seguimiento = %s", (self.folio,))
            resultado = cursor.fetchone()
            if not resultado: return
            id_servicio = resultado[0]
            
            sql_detalle = """
                INSERT INTO detalle_servicio (id_servicio, id_refaccion, cantidad, precio_unitario)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id_servicio, id_refaccion) 
                DO UPDATE SET cantidad = detalle_servicio.cantidad + EXCLUDED.cantidad;
            """
            cursor.execute(sql_detalle, (id_servicio, datos['id'], cantidad, datos['precio']))
            
            sql_restar_stock = "UPDATE refacciones SET stock = stock - %s WHERE id = %s"
            cursor.execute(sql_restar_stock, (cantidad, datos['id']))
            
            conexion.commit()
            
            QMessageBox.information(self.ui, "Éxito", "Refacción agregada y stock descontado.")
            
            if self.parent:
                self.parent.cargar_citas()
                self.parent.cargar_inventario()
                
            self.ui.close()
            
        except ValueError:
            QMessageBox.warning(self.ui, "Error", "La cantidad debe ser un número entero mayor a cero.")
        except Exception as e:
            conexion.rollback()
            QMessageBox.critical(self.ui, "Error BD", f"Fallo al guardar:\n{e}")
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'conexion' in locals(): conexion.close()


#Pantalla guardar nueva refacción
class NuevaRefaccionWindow:
    def __init__(self, parent=None):
        self.parent = parent
        loader = QUiLoader()
        archivo = QFile(ruta_recurso("nueva_refaccion.ui"))
        archivo.open(QFile.ReadOnly)
        self.ui = loader.load(archivo)
        archivo.close()
        
        self.ui.setWindowTitle("Registrar Nueva Refacción")
        
        self.cargar_proveedores_combo()

        self.ui.input_stock.setValidator(validador_stock)
        self.ui.input_costo.setValidator(validador_dinero)
        self.ui.input_precio.setValidator(validador_dinero)
        
        self.ui.btn_guardar_refaccion.clicked.connect(self.guardar_refaccion)

    def cargar_proveedores_combo(self):
        conexion = conectar_bd()
        if not conexion: return
        try:
            cursor = conexion.cursor()
            cursor.execute("SELECT id, empresa FROM proveedores ORDER BY empresa ASC")
            proveedores = cursor.fetchall()
            
            self.ui.combo_proveedor.addItem("Sin proveedor asignado", None)
            
            for prov in proveedores:
                id_prov, empresa = prov
                self.ui.combo_proveedor.addItem(empresa, id_prov)
                
        except Exception as e:
            print(f"Error al cargar proveedores en el combo: {e}")
        finally:
            cursor.close()
            conexion.close()

    def guardar_refaccion(self):
        nombre = self.ui.input_nombre.text().strip()
        stock = self.ui.input_stock.text().strip()
        costo = self.ui.input_costo.text().strip()
        precio = self.ui.input_precio.text().strip()
        
        id_proveedor = self.ui.combo_proveedor.currentData()

        if not all([nombre, stock, costo, precio]):
            QMessageBox.warning(self.ui, "Error", "Llena todos los campos de texto.")
            return

        conexion = conectar_bd()
        if not conexion: return
        try:
            cursor = conexion.cursor()
            
            sql = """
                INSERT INTO refacciones (nombre, stock, precio_compra, precio_publico, id_proveedor) 
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (nombre, int(stock), float(costo), float(precio), id_proveedor))
            conexion.commit()
            
            QMessageBox.information(self.ui, "Éxito", "Refacción registrada en inventario.")
            
            if self.parent:
                self.parent.cargar_inventario()
            self.ui.close()
            
        except ValueError:
            QMessageBox.warning(self.ui, "Error", "Stock, costo y precio deben ser números.")
        except Exception as e:
            conexion.rollback()
            QMessageBox.critical(self.ui, "Error BD", f"Fallo al guardar:\n{e}")
        finally:
            cursor.close()
            conexion.close()


#Pantalla dashboard administrador
class DashboardAdmin:
    def __init__(self):
        loader = QUiLoader()
        archivo = QFile(ruta_recurso("dashboard_admin.ui"))
        archivo.open(QFile.ReadOnly)
        self.ui = loader.load(archivo)
        archivo.close()
        self.ui.setWindowTitle("Panel de Control - Multiservicios")

        self.ui.input_nueva_pass.setMaxLength(8)
        self.ui.input_confirmar_pass.setMaxLength(8)
        self.ui.input_nuevo_usuario.setMaxLength(6)
        self.ui.input_nuevo_nombre.setMaxLength(25)

        regex_numeros = QRegularExpression(r"^[0-9]+$")
        validador_numeros = QRegularExpressionValidator(regex_numeros)
        self.ui.input_nuevo_usuario.setValidator(validador_numeros)

        self.ui.btn_nueva_cita.clicked.connect(self.abrir_nueva_cita)
        self.ui.btn_editar_estado.clicked.connect(self.editar_estado)
        self.ui.btn_agregar_pieza.clicked.connect(self.abrir_agregar_pieza)
        self.ui.btn_eliminar_cita.clicked.connect(self.eliminar_cita)
        self.ui.btn_actualizar_fecha.clicked.connect(self.actualizar_fecha_admin)
        self.ui.tabla_citas.itemSelectionChanged.connect(self.mostrar_diagnostico_seleccionado)

        self.ui.dt_fecha_admin.setMinimumDate(QDate.currentDate())

        self.ui.btn_salir.clicked.connect(self.cerrar_sesion)

        self.cargar_citas()
        self.cargar_inventario()
        self.cargar_clientes()
        self.cargar_proveedores()

        self.ui.btn_nueva_refaccion.clicked.connect(self.abrir_nueva_refaccion)
        self.ui.btn_editar_stock.clicked.connect(self.abrir_editar_stock)

        self.ui.btn_nuevo_cliente.clicked.connect(self.abrir_nuevo_cliente)
        self.ui.btn_historial_cliente.clicked.connect(self.abrir_historial)

        self.ui.btn_nuevo_proveedor.clicked.connect(self.abrir_nuevo_proveedor)
        self.ui.btn_eliminar_proveedor.clicked.connect(self.eliminar_proveedor)

        self.ui.btn_nuevo_admin.clicked.connect(self.crear_nuevo_admin)

        self.ui.showMaximized()

    def cargar_citas(self):
        conexion = conectar_bd()
        if not conexion: return
        
        try:
            cursor = conexion.cursor()
            
            sql = """
            SELECT 
                s.folio_seguimiento,
                c.nombre || ' ' || c.apellido_paterno || ' ' || COALESCE(c.apellido_materno, '') AS cliente,
                a.tipo || ' ' || a.marca AS aparato,
                s.fecha_visita,
                s.estado,
                CASE 
                    WHEN s.estado = 'Cancelado' THEN COALESCE(s.costo_revision, 0)
                    ELSE (COALESCE(s.costo_revision, 0) + COALESCE(s.costo_mano_obra, 0) + COALESCE(SUM(d.cantidad * d.precio_unitario), 0))
                END AS total,
                TO_CHAR(s.fecha_estimada, 'DD-MM-YYYY') AS fecha_entrega            
            FROM servicios s
            JOIN aparatos a ON s.id_aparato = a.id 
            JOIN clientes c ON a.id_cliente = c.id
            LEFT JOIN detalle_servicio d ON d.id_servicio = s.id
            GROUP BY s.id, c.nombre, c.apellido_paterno, c.apellido_materno, a.tipo, a.marca, s.fecha_visita, s.estado, s.folio_seguimiento
            ORDER BY s.fecha_visita DESC
        """
            cursor.execute(sql)
            citas = cursor.fetchall()
            
            self.ui.tabla_citas.setRowCount(0)
            
            for fila_num, cita in enumerate(citas):
                self.ui.tabla_citas.insertRow(fila_num)
                
                for col_num, dato in enumerate(cita):

                    if dato is None or str(dato).strip() == "":
                        texto_celda = "N/E"

                    elif col_num == 5:
                            texto_celda = f"${dato:.2f}"

                    else:
                        texto_celda = str(dato)
        
                    celda = QTableWidgetItem(texto_celda)
                    self.ui.tabla_citas.setItem(fila_num, col_num, celda)

                    
        except Exception as e:
            print(f"Error al cargar la tabla: {e}")
        finally:
            cursor.close()
            conexion.close()

    def cargar_clientes(self):
        conexion = conectar_bd()
        if not conexion: return
        
        try:
            cursor = conexion.cursor()
            
            sql = """
            SELECT 
                c.id,
                TRIM(c.nombre || ' ' || c.apellido_paterno || ' ' || COALESCE(c.apellido_materno, '')) AS nombre_completo,
                c.telefono,                
                CONCAT_WS(', ', 
                    NULLIF(TRIM(c.calle || ' ' || COALESCE(c.numero, '')), ''), 
                    NULLIF(c.colonia, ''), 
                    NULLIF(c.codigo_postal, ''), 
                    NULLIF(c.municipio, '')
                ) AS direccion_completa,                
                COUNT(DISTINCT a.id) AS total_aparatos,
                MAX(s.fecha_visita) AS ultima_visita
            FROM clientes c
            LEFT JOIN aparatos a ON c.id = a.id_cliente
            LEFT JOIN servicios s ON a.id = s.id_aparato
            GROUP BY c.id, c.nombre, c.apellido_paterno, c.apellido_materno, c.calle, c.numero, c.colonia, c.codigo_postal, c.municipio
            ORDER BY c.id DESC
            """
            cursor.execute(sql)
            clientes = cursor.fetchall()
            
            self.ui.tabla_clientes.setRowCount(0)
            
            for fila_num, cliente in enumerate(clientes):
                self.ui.tabla_clientes.insertRow(fila_num)
                
                for col_num, dato in enumerate(cliente):

                    if dato is None or str(dato).strip() == "":
                        texto_celda = "N/E"
                            
                    else:
                        texto_celda = str(dato)
                        
                    celda = QTableWidgetItem(texto_celda)
                    self.ui.tabla_clientes.setItem(fila_num, col_num, celda)
            
            self.ui.tabla_clientes.setColumnHidden(0, True)
                    
        except Exception as e:
            print(f"Error al cargar clientes: {e}")
        finally:
            cursor.close()
            conexion.close()

    def abrir_nueva_cita(self):
        self.ventana_cita = NuevaCitaWindow(self)
        self.ventana_cita.ui.show()

    def editar_estado(self):
        fila = self.ui.tabla_citas.currentRow()

        conexion = conectar_bd()
        if not conexion: return

        cursor = conexion.cursor()
        
        if fila == -1:
            QMessageBox.warning(self.ui, "Atención", "Selecciona una cita de la tabla primero.")
            return

        folio = self.ui.tabla_citas.item(fila, 0).text()
        estado_actual = self.ui.tabla_citas.item(fila, 4).text()

        estados = ["Pendiente", "En revisión", "Esperando aprobación del cliente", "En servicio", "Terminado", "Cancelado"]
        
        try:
            indice_actual = estados.index(estado_actual)
        except ValueError:
            indice_actual = 0

        nuevo_estado, ok_estado = QInputDialog.getItem(
            self.ui, 
            "Cambiar Estado", 
            f"Modificando el estado del folio: {folio}", 
            estados, 
            indice_actual, 
            False
        )

        if not ok_estado or nuevo_estado == estado_actual:
            return

        sql = ""
        valores = ()

        if nuevo_estado == "En revisión": 
            costo, ok_costo = QInputDialog.getDouble(
                self.ui,
                "Costo de Revisión",
                "Ingresa el costo por la revisión del aparato:",
                300.00,    
                0.00,      
                10000.00,  
                2          
            )
            
            if ok_costo:
                sql = "UPDATE servicios SET estado = %s, costo_revision = %s WHERE folio_seguimiento = %s"
                valores = (nuevo_estado, costo, folio)
            else:
                return

        elif nuevo_estado == "Esperando aprobación del cliente":

            diagnostico, ok_diag = QInputDialog.getMultiLineText(
                self.ui, "Diagnóstico del Equipo", "Ingresa el diagnóstico y los detalles de la reparación propuesta:")

            if ok_diag:

                costo_mano_obra, ok_mano_obra = QInputDialog.getDouble(
                    self.ui,
                    "Costo de Mano de Obra",
                    "Ingresa el costo por la mano de obra, es decir, el costo del servicio como tal:",
                    500.00,    
                    0.00,      
                    30000.00,  
                    2          
                )
            
                if ok_mano_obra:
                    sql = "UPDATE servicios SET estado = %s, costo_mano_obra = %s, diagnostico = %s WHERE folio_seguimiento = %s"
                    valores = (nuevo_estado, costo_mano_obra, diagnostico, folio)
                
                else:
                    return
            else:
                return

        elif nuevo_estado == "Cancelado":
            confirmacion = QMessageBox.question(
                self.ui, 
                "Confirmar Cancelación", 
                "¿Estás seguro de cancelar este servicio? Las piezas cotizadas regresarán al inventario de inmediato.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if confirmacion == QMessageBox.StandardButton.Yes:
                cursor.execute("SELECT id FROM servicios WHERE folio_seguimiento = %s", (folio,))
                resultado_id = cursor.fetchone()
                
                if resultado_id:
                    id_servicio = resultado_id[0]
                    
                    cursor.execute("SELECT cantidad, id_refaccion FROM detalle_servicio WHERE id_servicio = %s", (id_servicio,))
                    piezas_usadas = cursor.fetchall()

                    QMessageBox.information(self.ui, "Diagnóstico", f"Python encontró {len(piezas_usadas)} piezas para devolver de este folio.")
                    
                    if piezas_usadas:
                        for pieza in piezas_usadas:
                                cantidad_devolver = pieza[0]
                                id_pieza = pieza[1]
                                
                                cursor.execute("UPDATE refacciones SET stock = stock + %s WHERE id = %s", (cantidad_devolver, id_pieza))
                                
                                if cursor.rowcount == 0:
                                    QMessageBox.warning(self.ui, "Falla en Inventario", f"La base de datos ignoró la pieza con ID {id_pieza}. Verifica si aún existe en tu catálogo.")


                sql = "UPDATE servicios SET estado = %s, costo_mano_obra = 0 WHERE folio_seguimiento = %s"
                valores = (nuevo_estado, folio)
            
            else:
                return    

        else:
            sql = "UPDATE servicios SET estado = %s WHERE folio_seguimiento = %s"
            valores = (nuevo_estado, folio)

        
        try:
            cursor.execute(sql, valores)
            conexion.commit()
            
            QMessageBox.information(self.ui, "Éxito", f"El servicio {folio} ahora está '{nuevo_estado}'.")
            self.cargar_citas()
            self.cargar_inventario()
            
        except Exception as e:
            conexion.rollback()
            QMessageBox.critical(self.ui, "Error en la base de datos", f"Fallo al actualizar:\n{e}")
        finally:
            cursor.close()
            conexion.close()


    def abrir_agregar_pieza(self):
        fila = self.ui.tabla_citas.currentRow()
        if fila == -1:
            QMessageBox.warning(self.ui, "Atención", "Selecciona una cita de la tabla primero.")
            return
            
        folio = self.ui.tabla_citas.item(fila, 0).text()
        
        self.ventana_piezas = AgregarPiezaWindow(self, folio)
        self.ventana_piezas.ui.show()

    def abrir_editar_stock(self):
        fila = self.ui.tabla_inventario.currentRow()
        if fila == -1:
            QMessageBox.warning(self.ui, "Atención", "Selecciona una pieza de la tabla primero.")
            return
            
        id_pieza = int(self.ui.tabla_inventario.item(fila, 0).text())
        nombre = self.ui.tabla_inventario.item(fila, 1).text()
        
        conexion = conectar_bd()
        if not conexion: return
        try:
            cursor = conexion.cursor()
            cursor.execute("SELECT precio_compra, precio_publico FROM refacciones WHERE id = %s", (id_pieza,))
            resultado = cursor.fetchone()
            
            if resultado:
                costo = resultado[0]
                precio = resultado[1]
                
                self.ventana_editar = EditarStockWindow(self, id_pieza, nombre, costo, precio)
                self.ventana_editar.ui.show()
        except Exception as e:
            QMessageBox.critical(self.ui, "Error", f"No se pudo cargar la pieza:\n{e}")
        finally:
            cursor.close()
            conexion.close()


    def eliminar_cita(self):
        fila = self.ui.tabla_citas.currentRow()

        conexion = conectar_bd()
        if not conexion: return
        
        if fila == -1:
            QMessageBox.warning(self.ui, "Atención", "Selecciona la cita que deseas eliminar.")
            return

        folio = self.ui.tabla_citas.item(fila, 0).text()
        cliente = self.ui.tabla_citas.item(fila, 1).text()

        try:
            cursor = conexion.cursor()
        
            cursor.execute("SELECT id, estado FROM servicios WHERE folio_seguimiento = %s", (folio,))
            resultado = cursor.fetchone()
        
            if not resultado:
                return 
            
            id_servicio = resultado[0]
            estado_actual = resultado[1]
        
            if estado_actual != 'Cancelado':
                QMessageBox.warning(
                self.ui, 
                "Operación Denegada", 
                "Solo puedes eliminar de la base de datos las citas que ya estén en estado 'Cancelado'.\n\nSi necesitas borrarla, cancélala primero para asegurar que las piezas regresen al inventario."
                )
                return
            
            confirmacion = QMessageBox.question(
                self.ui, 
                "Eliminar Cita", 
                f"¿Estás seguro de eliminar permanentemente el folio {folio}? Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
        
            if confirmacion == QMessageBox.StandardButton.Yes:
                cursor.execute("DELETE FROM detalle_servicio WHERE id_servicio = %s", (id_servicio,))
                cursor.execute("DELETE FROM servicios WHERE id = %s", (id_servicio,))
            
                conexion.commit()
                QMessageBox.information(self.ui, "Éxito", "La cita y su historial de piezas han sido eliminados por completo.")
            
                self.cargar_citas() 
            
        except Exception as e:
            conexion.rollback()
            QMessageBox.critical(self.ui, "Error al eliminar", f"Fallo en la base de datos: {str(e)}")

    def actualizar_fecha_admin(self):
        fila = self.ui.tabla_citas.currentRow()

        conexion = conectar_bd()

        if fila == -1:
            QMessageBox.warning(self.ui, "Selección requerida", "Por favor, selecciona una cita de la tabla para cambiar su fecha.")
            return
        
        folio = self.ui.tabla_citas.item(fila, 0).text()
    
        nueva_fecha_bd = self.ui.dt_fecha_admin.date().toString("yyyy-MM-dd")
    
        try:
            cursor = conexion.cursor()
            sql = "UPDATE servicios SET fecha_estimada = %s WHERE folio_seguimiento = %s"
            cursor.execute(sql, (nueva_fecha_bd, folio))
        
            conexion.commit()
            QMessageBox.information(self.ui, "Éxito", "La fecha de entrega estimada ha sido actualizada.")
        
            self.cargar_citas() 
        
        except Exception as e:
            conexion.rollback()
            QMessageBox.critical(self.ui, "Error", f"No se pudo actualizar la fecha: {str(e)}")

    def mostrar_diagnostico_seleccionado(self):
        fila = self.ui.tabla_citas.currentRow()

        conexion = conectar_bd()

        if fila == -1:
            self.ui.txt_diagnostico_admin.clear()
            return
        
        folio = self.ui.tabla_citas.item(fila, 0).text()
    
        try:
            cursor = conexion.cursor()
            cursor.execute("SELECT diagnostico FROM servicios WHERE folio_seguimiento = %s", (folio,))
            resultado = cursor.fetchone()
        
            if resultado and resultado[0]:
                self.ui.txt_diagnostico_admin.setText(resultado[0])
            else:
                self.ui.txt_diagnostico_admin.setText("Sin diagnóstico registrado aún. Registre un diagnóstico después de agregar refacciones a una cita" \
                " y cambiar el estado a 'Esperando aprobación del cliente', donde ingresará también el costo de la mano de obra.")
            
        except Exception as e:
            self.ui.txt_diagnostico_admin.setText(f"Error al cargar: {str(e)}")

    def cerrar_sesion(self):
        respuesta = QMessageBox.question(
            self.ui, "Confirmar Salida", 
            "¿Deseas cerrar la sesión?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if respuesta == QMessageBox.Yes:
            self.ventana_inicio = BienvenidaWindow()
            self.ventana_inicio.show()
            self.ui.close()

    def cargar_inventario(self):
        conexion = conectar_bd()
        if not conexion: return
        try:
            cursor = conexion.cursor()
            sql = """
            SELECT 
                r.id,
                r.nombre,
                r.stock,
                r.precio_publico,
                (r.precio_publico - r.precio_compra) AS margen,
                p.empresa AS proveedor
            FROM refacciones r
            LEFT JOIN proveedores p ON r.id_proveedor = p.id
            ORDER BY r.id DESC
        """
            cursor.execute(sql)
            refacciones = cursor.fetchall()
            
            self.ui.tabla_inventario.setRowCount(0)

            for fila_num, ref in enumerate(refacciones):
                self.ui.tabla_inventario.insertRow(fila_num)

                for col_num, dato in enumerate(ref):
                    
                    if dato is None or str(dato).strip() == "":
                        texto_celda = "N/E"

                    elif col_num in [3, 4]:
                        texto_celda = f"${dato:.2f}"

                    else:
                        texto_celda = str(dato)
                        
                    celda = QTableWidgetItem(texto_celda)
                    self.ui.tabla_inventario.setItem(fila_num, col_num, celda)

                self.ui.tabla_inventario.setColumnHidden(0, True)

        except Exception as e:
            print(f"Error al cargar inventario: {e}")
        finally:
            cursor.close()
            conexion.close()

    def abrir_nueva_refaccion(self):
        self.ventana_refaccion = NuevaRefaccionWindow(self)
        self.ventana_refaccion.ui.show()


    def abrir_nuevo_cliente(self):
        self.ventana_cliente = NuevoClienteWindow(self)
        self.ventana_cliente.ui.show()

    def abrir_historial(self):
        fila = self.ui.tabla_clientes.currentRow()
        
        if fila == -1:
            QMessageBox.warning(self.ui, "Atención", "Selecciona un cliente de la tabla primero.")
            return
            
        id_cliente = int(self.ui.tabla_clientes.item(fila, 0).text())
        nombre = self.ui.tabla_clientes.item(fila, 1).text()
        telefono = self.ui.tabla_clientes.item(fila, 2).text()
        
        self.ventana_historial = HistorialClienteWindow(self, id_cliente, nombre, telefono)
        self.ventana_historial.ui.show()

    def cargar_proveedores(self):
        conexion = conectar_bd()
        if not conexion: return
        
        try:
            cursor = conexion.cursor()
            cursor.execute("SELECT id, empresa, contacto, telefono, email FROM proveedores ORDER BY empresa ASC")
            proveedores = cursor.fetchall()
            
            self.ui.tabla_proveedores.setRowCount(0)
            
            for fila_num, proveedor in enumerate(proveedores):
                self.ui.tabla_proveedores.insertRow(fila_num)
                
                for col_num, dato in enumerate(proveedor):
                    
                    if dato is None or str(dato).strip() == "":
                        texto_celda = "N/E"

                    else:
                        texto_celda = str(dato)

                    celda = QTableWidgetItem(texto_celda)
                    self.ui.tabla_proveedores.setItem(fila_num, col_num, celda)
            self.ui.tabla_proveedores.setColumnHidden(0, True)
                    
        except Exception as e:
            print(f"Error al cargar proveedores: {e}")
        finally:
            cursor.close()
            conexion.close()

    def abrir_nuevo_proveedor(self):
        self.ventana_proveedor = NuevoProveedorWindow(self)
        self.ventana_proveedor.ui.show()

    def eliminar_proveedor(self):
        fila = self.ui.tabla_proveedores.currentRow()
        
        if fila == -1:
            QMessageBox.warning(self.ui, "Atención", "Selecciona un proveedor de la tabla primero.")
            return
            
        id_proveedor = int(self.ui.tabla_proveedores.item(fila, 0).text())
        empresa = self.ui.tabla_proveedores.item(fila, 1).text()
        
        respuesta = QMessageBox.question(
            self.ui,
            "Confirmar Eliminación",
            f"¿Estás seguro de que deseas eliminar a '{empresa}' de tu directorio?\n\nLas piezas de tu inventario vinculadas a él no se borrarán, solo quedarán sin proveedor asignado.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if respuesta == QMessageBox.Yes:
            conexion = conectar_bd()
            if not conexion: return
            
            try:
                cursor = conexion.cursor()
                cursor.execute("DELETE FROM proveedores WHERE id = %s", (id_proveedor,))
                conexion.commit()
                
                QMessageBox.information(self.ui, "Éxito", "Proveedor eliminado correctamente.")
                
                self.cargar_proveedores()
                
            except Exception as e:
                conexion.rollback()
                QMessageBox.critical(self.ui, "Error BD", f"Fallo al eliminar:\n{e}")
            finally:
                cursor.close()
                conexion.close()

    def crear_nuevo_admin(self):

        conexion = conectar_bd()

        nuevo_usuario = self.ui.input_nuevo_usuario.text().strip()
        nuevo_nombre = self.ui.input_nuevo_nombre.text().strip()
        nueva_pass = self.ui.input_nueva_pass.text()
        confirmar_pass = self.ui.input_confirmar_pass.text()
        pass_actual_ingresada = self.ui.input_pass_actual.text()
    
        if not all([nuevo_usuario, nuevo_nombre, nueva_pass, confirmar_pass, pass_actual_ingresada]):
            QMessageBox.warning(self.ui, "Campos Incompletos", "Por favor llena todos los campos.")
            return
        
        if nueva_pass != confirmar_pass:
            QMessageBox.warning(self.ui, "Error de Contraseña", "Las contraseñas del nuevo usuario no coinciden.")
            return
        
        try:
            cursor = conexion.cursor()
        
            cursor.execute("SELECT password FROM usuarios WHERE usuario = %s", (self.usuario_actual,))
            resultado = cursor.fetchone()
        
            if not resultado or resultado[0] != pass_actual_ingresada:
                QMessageBox.critical(self.ui, "Acceso Denegado", "Tu contraseña de administrador actual es incorrecta. Operación cancelada.")
                return
            
            sql_insert = "INSERT INTO usuarios (nombre_corto, usuario, password) VALUES (%s, %s, %s)"
            cursor.execute(sql_insert, (nuevo_nombre, nuevo_usuario, nueva_pass))
            conexion.commit()
        
            QMessageBox.information(self.ui, "Éxito", f"El administrador '{nuevo_usuario}' ha sido creado correctamente.")
        
            self.ui.input_nuevo_usuario.clear()
            self.ui.input_nuevo_nombre.clear()
            self.ui.input_nueva_pass.clear()
            self.ui.input_confirmar_pass.clear()
            self.ui.input_pass_actual.clear()
        
        except Exception as e:
            conexion.rollback()
            if "Unique violation" in str(e) or "llave duplicada" in str(e).lower():
                QMessageBox.warning(self.ui, "Usuario Duplicado", "Ese nombre de usuario ya está registrado. Elige otro.")
            else:
                QMessageBox.critical(self.ui, "Error", f"Ocurrió un error en la base de datos: {str(e)}")


#Pantalla editar stock o precio desde el admin
class EditarStockWindow:
    def __init__(self, parent=None, id_pieza=0, nombre="", costo=0.0, precio=0.0):
        self.parent = parent
        self.id_pieza = id_pieza
        
        loader = QUiLoader()
        archivo = QFile(ruta_recurso("editar_stock.ui"))
        archivo.open(QFile.ReadOnly)
        self.ui = loader.load(archivo)
        archivo.close()
        
        self.ui.setWindowTitle("Actualizar Inventario")
        self.ui.lbl_nombre_pieza.setText(f"Editando: {nombre}")

        self.ui.input_sumar_stock.setValidator(validador_stock)
        self.ui.input_nuevo_costo.setValidator(validador_dinero)
        self.ui.input_nuevo_precio.setValidator(validador_dinero)
        
        self.ui.input_nuevo_costo.setText(str(costo))
        self.ui.input_nuevo_precio.setText(str(precio))
        self.ui.input_sumar_stock.setText("0") 
        
        self.ui.btn_actualizar_stock.clicked.connect(self.actualizar_bd)

    def actualizar_bd(self):
        sumar_str = self.ui.input_sumar_stock.text().strip()
        costo_str = self.ui.input_nuevo_costo.text().strip()
        precio_str = self.ui.input_nuevo_precio.text().strip()
        
        if not all([sumar_str, costo_str, precio_str]):
            QMessageBox.warning(self.ui, "Error", "No dejes campos vacíos.")
            return
            
        conexion = conectar_bd()
        if not conexion: return
        
        try:
            sumar_stock = int(sumar_str)
            nuevo_costo = float(costo_str)
            nuevo_precio = float(precio_str)
            
            cursor = conexion.cursor()
            
            sql = """
                UPDATE refacciones 
                SET stock = stock + %s, 
                    precio_compra = %s, 
                    precio_publico = %s 
                WHERE id = %s
            """
            cursor.execute(sql, (sumar_stock, nuevo_costo, nuevo_precio, self.id_pieza))
            conexion.commit()
            
            QMessageBox.information(self.ui, "Éxito", "Inventario actualizado.")
            
            if self.parent:
                self.parent.cargar_inventario()
                
            self.ui.close()
            
        except ValueError:
            QMessageBox.warning(self.ui, "Error", "Ingresa solo números. No uses el símbolo de $.")
        except Exception as e:
            conexion.rollback()
            QMessageBox.critical(self.ui, "Error BD", f"Fallo al actualizar:\n{e}")
        finally:
            cursor.close()
            conexion.close()


#Pantalla agendar cita desde el cliente
class AgendarClienteWindow:
    def __init__(self):
        loader = QUiLoader()
        archivo = QFile(ruta_recurso("agendar_cliente.ui"))
        archivo.open(QFile.ReadOnly)
        self.ui = loader.load(archivo)
        archivo.close()
        self.ui.input_fecha.setMinimumDate(QDate.currentDate())

        self.ui.input_nombre.setValidator(validador_letras)
        self.ui.input_apellidop.setValidator(validador_letras)
        self.ui.input_apellidom.setValidator(validador_letras)
        self.ui.input_telefono.setValidator(validador_numeros)
        self.ui.txt_cp.setValidator(validador_numeros)
        self.ui.txt_municipio.setValidator(validador_letras)

        self.ui.input_telefono.setMaxLength(10)

        self.ui.setWindowTitle("Agendar Reparación")
        self.ui.btn_confirmar_cita.clicked.connect(self.procesar_agendamiento)


    def procesar_agendamiento(self):
        nombre = self.ui.input_nombre.text().strip()
        apellidop = self.ui.input_apellidop.text().strip()
        apellidom = self.ui.input_apellidom.text().strip()
        telefono = self.ui.input_telefono.text().strip()
        tipo = self.ui.input_tipo_aparato.text().strip()
        marca = self.ui.input_marca.text().strip()
        fecha = self.ui.input_fecha.text().strip()

        calle = self.ui.txt_calle.text().strip()
        numero = self.ui.txt_numero.text().strip()
        colonia = self.ui.txt_colonia.text().strip()
        cp = self.ui.txt_cp.text().strip()
        municipio = self.ui.txt_municipio.text().strip()

        if not all([nombre, apellidop, apellidom, telefono, tipo, marca, fecha, calle, numero, colonia, cp, municipio]):
            QMessageBox.warning(self.ui, "Faltan datos", "Por favor llena todos los campos.")
            return

        conexion = conectar_bd()
        if not conexion: return
        
        try:
            cursor = conexion.cursor()
            
            sql_buscar = "SELECT id FROM clientes WHERE nombre = %s AND apellido_paterno = %s AND apellido_materno = %s"
            cursor.execute(sql_buscar, (nombre, apellidop, apellidom))
            cliente_existente = cursor.fetchone()

            if cliente_existente:
                id_cliente = cliente_existente[0]
                    
                sql_actualizar_tel = "UPDATE clientes SET telefono = %s WHERE id = %s"
                cursor.execute(sql_actualizar_tel, (telefono, id_cliente))
            else:
                sql_cliente = "INSERT INTO clientes (nombre, apellido_paterno, apellido_materno, telefono, calle, numero, colonia, codigo_postal, municipio) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"
                cursor.execute(sql_cliente, (nombre, apellidop, apellidom, telefono, calle, numero, colonia, cp, municipio))
                id_cliente = cursor.fetchone()[0]

            sql_aparato = "INSERT INTO aparatos (id_cliente, tipo, marca) VALUES (%s, %s, %s) RETURNING id"
            cursor.execute(sql_aparato, (id_cliente, tipo, marca))
            id_aparato = cursor.fetchone()[0]

            codigo_aleatorio = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            folio = f"MS-{codigo_aleatorio}"
            
            sql_servicio = """
                INSERT INTO servicios (id_aparato, fecha_visita, estado, costo_revision, folio_seguimiento) VALUES (%s, %s, %s, %s, %s)
            """
            valores = (
                id_aparato,      
                fecha,        
                "Pendiente",         
                0.00,                 
                folio       
            )   

            
            cursor.execute(sql_servicio, valores)
            
            conexion.commit() 
            
            QMessageBox.information(self.ui, "Cita Confirmada", 
                f"¡Gracias {nombre}!\n\nTu técnico irá el {fecha}.\nGuarda tu folio de seguimiento: {folio}")
            self.ui.close()
            
        except Exception as e:
            conexion.rollback()
            QMessageBox.critical(self.ui, "Error", f"No se pudo agendar:\n{e}")
        finally:
            cursor.close()
            conexion.close()


#Pantalla nuevo cliente desde admin
class NuevoClienteWindow:
    def __init__(self, parent=None):
        self.parent = parent
        loader = QUiLoader()
        archivo = QFile(ruta_recurso("nuevo_cliente.ui"))
        archivo.open(QFile.ReadOnly)
        self.ui = loader.load(archivo)
        archivo.close()

        self.ui.input_nombre.setValidator(validador_letras)
        self.ui.input_paterno.setValidator(validador_letras)
        self.ui.input_materno.setValidator(validador_letras)
        self.ui.input_telefono.setValidator(validador_numeros)
        self.ui.txt_cp.setValidator(validador_numeros)
        self.ui.txt_municipio.setValidator(validador_letras)

        self.ui.input_telefono.setMaxLength(10)
        
        self.ui.setWindowTitle("Registrar Cliente Manual")
        self.ui.btn_guardar.clicked.connect(self.guardar_cliente)

    def guardar_cliente(self):
        nombre = self.ui.input_nombre.text().strip()
        paterno = self.ui.input_paterno.text().strip()
        materno = self.ui.input_materno.text().strip()
        telefono = self.ui.input_telefono.text().strip()

        calle = self.ui.txt_calle.text().strip()
        numero = self.ui.txt_numero.text().strip()
        colonia = self.ui.txt_colonia.text().strip()
        cp = self.ui.txt_cp.text().strip()
        municipio = self.ui.txt_municipio.text().strip()   

        if not all([nombre, paterno, materno, telefono, calle, numero, colonia, cp, municipio]):
            QMessageBox.warning(self.ui, "Faltan datos", "Por favor llena todos los campos.")
            return

        conexion = conectar_bd()
        if not conexion: return
        
        try:
            cursor = conexion.cursor()
            
            cursor.execute("SELECT id FROM clientes WHERE nombre = %s AND apellido_paterno = %s", (nombre, paterno))
            if cursor.fetchone():
                QMessageBox.warning(self.ui, "Atención", "Este cliente ya está registrado en el sistema.")
                return
            
            sql = """
                INSERT INTO clientes (nombre, apellido_paterno, apellido_materno, telefono, calle, numero, colonia, codigo_postal, municipio) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            materno_db = materno if materno else None
            
            cursor.execute(sql, (nombre, paterno, materno_db, telefono, calle, numero, colonia, cp, municipio))
            conexion.commit()
            
            QMessageBox.information(self.ui, "Éxito", "Cliente registrado correctamente.")
            
            if self.parent:
                self.parent.cargar_clientes()
                
            self.ui.close()
            
        except Exception as e:
            conexion.rollback()
            QMessageBox.critical(self.ui, "Error BD", f"Fallo al guardar:\n{e}")
        finally:
            cursor.close()
            conexion.close()


#Pantalla historial cliente
class HistorialClienteWindow:
    def __init__(self, parent=None, id_cliente=0, nombre="", telefono=""):
        self.parent = parent
        self.id_cliente = id_cliente
        
        loader = QUiLoader()
        archivo = QFile(ruta_recurso("historial_cliente.ui"))
        archivo.open(QFile.ReadOnly)
        self.ui = loader.load(archivo)
        archivo.close()
        
        self.ui.setWindowTitle(f"Historial - {nombre}")
        
        self.ui.lbl_nombre_historial.setText(f"Cliente: {nombre}")
        self.ui.lbl_telefono_historial.setText(f"Teléfono: {telefono}")
        
        self.ui.btn_cerrar_historial.clicked.connect(self.ui.close)
        
        self.cargar_historial()

    def cargar_historial(self):
        conexion = conectar_bd()
        if not conexion: return
        
        try:
            cursor = conexion.cursor()
            
            #Consulta de historial del cliente
            sql = """
            SELECT 
                s.folio_seguimiento,
                a.tipo || ' ' || a.marca AS aparato,
                s.fecha_visita,
                s.estado,
                (COALESCE(s.costo_revision, 0) + COALESCE(s.costo_mano_obra, 0) + COALESCE(SUM(d.cantidad * d.precio_unitario), 0)) AS total_pagado
            FROM servicios s
            JOIN aparatos a ON s.id_aparato = a.id
            -- Corregimos el alias a "d" para que coincida con la suma matemática
            LEFT JOIN detalle_servicio d ON s.id = d.id_servicio
            WHERE a.id_cliente = %s
            GROUP BY 
                s.id, s.folio_seguimiento, a.tipo, a.marca,
                s.fecha_visita, s.estado, s.costo_revision, s.costo_mano_obra -- Agregamos el costo de mano de obra aquí
            ORDER BY s.fecha_visita DESC
        """
            cursor.execute(sql, (self.id_cliente,))
            historial = cursor.fetchall()
            
            self.ui.tabla_historial.setRowCount(0)
            
            for fila_num, registro in enumerate(historial):
                self.ui.tabla_historial.insertRow(fila_num)
                
                for col_num, dato in enumerate(registro):
                    
                    if col_num == 4:
                        texto_celda = f"${dato:.2f}"
                    else:
                        texto_celda = str(dato)
                        
                    celda = QTableWidgetItem(texto_celda)
                    self.ui.tabla_historial.setItem(fila_num, col_num, celda)
                    
        except Exception as e:
            print(f"Error al cargar historial: {e}")
        finally:
            cursor.close()
            conexion.close()


#Pantalla nuevo proveedor
class NuevoProveedorWindow:
    def __init__(self, parent=None):
        self.parent = parent
        loader = QUiLoader()
        archivo = QFile(ruta_recurso("nuevo_proveedor.ui"))
        archivo.open(QFile.ReadOnly)
        self.ui = loader.load(archivo)
        archivo.close()
        
        self.ui.setWindowTitle("Registrar Nuevo Proveedor")

        self.ui.input_telefono.setValidator(validador_numeros)
        self.ui.input_telefono.setMaxLength(10)
        
        self.ui.btn_guardar_proveedor.clicked.connect(self.guardar_proveedor)

    def guardar_proveedor(self):
        empresa = self.ui.input_empresa.text().strip()
        contacto = self.ui.input_contacto.text().strip()
        telefono = self.ui.input_telefono.text().strip()
        email = self.ui.input_email.text().strip()

        if not empresa:
            QMessageBox.warning(self.ui, "Error", "El nombre de la empresa es obligatorio.")
            return

        conexion = conectar_bd()
        if not conexion: return
        
        try:
            cursor = conexion.cursor()
            
            sql = """
                INSERT INTO proveedores (empresa, contacto, telefono, email) 
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (empresa, contacto, telefono, email))
            conexion.commit()
            
            QMessageBox.information(self.ui, "Éxito", "Proveedor registrado correctamente.")
            
            if self.parent:
                self.parent.cargar_proveedores()
                
            self.ui.close()
            
        except Exception as e:
            conexion.rollback()
            QMessageBox.critical(self.ui, "Error BD", f"Fallo al guardar:\n{e}")
        finally:
            cursor.close()
            conexion.close()


#Pantalla dashboard cliente
class DashboardCliente:
    def __init__(self):
        loader = QUiLoader()
        archivo = QFile(ruta_recurso("dashboard_cliente.ui"))
        archivo.open(QFile.ReadOnly)
        self.ui = loader.load(archivo)
        archivo.close()
        
        self.ui.setWindowTitle("Portal de Clientes - Consulta tu Folio")
        
        self.ui.btn_buscar.clicked.connect(self.buscar_folio)
        self.ui.btn_volver.clicked.connect(self.volver_inicio)

        self.ui.btn_agendar_nueva.clicked.connect(self.abrir_agendar)
        self.ui.btn_aprobar.clicked.connect(self.aprobar_presupuesto)
        self.ui.btn_rechazar.clicked.connect(self.rechazar_presupuesto)

    def buscar_folio(self):
        folio_texto = self.ui.input_folio.text().strip().upper()
        
        if not folio_texto:
            QMessageBox.warning(self.ui, "Atención", "Por favor ingresa tu número de folio.")
            return
            
        conexion = conectar_bd()
        if not conexion: return
        
        try:
            cursor = conexion.cursor()
            #Consulta SQL usando folio del cliente
            sql = """
                SELECT 
                    c.nombre,
                    a.tipo || ' ' || a.marca AS aparato,
                    s.estado,
                    CASE 
                        WHEN s.estado = 'Cancelado' THEN COALESCE(s.costo_revision, 0)
                        ELSE (COALESCE(s.costo_revision, 0) + COALESCE(s.costo_mano_obra, 0) + COALESCE(SUM(d.cantidad * d.precio_unitario), 0))
                    END AS total,
                    s.diagnostico,
                    TO_CHAR(s.fecha_estimada, 'DD-MM-YYYY') AS fecha_entrega
                FROM servicios s
                JOIN aparatos a ON s.id_aparato = a.id
                JOIN clientes c ON a.id_cliente = c.id
                LEFT JOIN detalle_servicio d ON d.id_servicio = s.id
                WHERE s.folio_seguimiento = %s
                GROUP BY s.id, c.nombre, a.tipo, a.marca, s.diagnostico, s.fecha_estimada
            """
            cursor.execute(sql, (folio_texto,))
            resultado = cursor.fetchone()
            
            if resultado:

                self.folio_confirmado = folio_texto
                self.ui.lbl_cliente.setText(f"Cliente: {resultado[0]}")
                self.ui.lbl_aparato.setText(f"Aparato: {resultado[1]}")
                self.ui.lbl_estado.setText(f"Estado Actual: {resultado[2]}")
                self.ui.lbl_total.setText(f"Total a pagar: ${resultado[3]:.2f}")
                

                diagnostico_bd = resultado[4]
                if diagnostico_bd:
                    self.ui.lbl_diagnostico.setText(f"Diagnóstico: {diagnostico_bd}")
                else:
                    self.ui.lbl_diagnostico.setText("Diagnóstico: Tu aparato aún no ha sido revisado.")

                if resultado[2] == 'Esperando aprobación del cliente':
                    self.ui.btn_aprobar.setEnabled(True)
                    self.ui.btn_rechazar.setEnabled(True)
                    self.ui.lbl_fecha_entrega.setText("Fecha de entrega estimada: Esperando a que se apruebe el servicio.")
                else:
                    self.ui.btn_aprobar.setEnabled(False)
                    self.ui.btn_rechazar.setEnabled(False)

                    if resultado[2] == 'En Servicio' and resultado[5]:
                        self.ui.lbl_fecha_entrega.setText(f"Fecha de entrega estimada: {resultado[5]}")

                if resultado[2] == 'Pendiente':
                    self.ui.lbl_estado.setStyleSheet("color: orange; font-weight: bold; font-size: 14px;")
                elif resultado[2] == 'Terminado':
                    self.ui.lbl_estado.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
                
                    
            else:
                QMessageBox.warning(self.ui, "No encontrado", "No existe ninguna cita con ese folio. Verifica que tu folio sea correcto, y vuelve a intentar.")
                self.ui.lbl_cliente.setText("Cliente: ")
                self.ui.lbl_aparato.setText("Aparato: ")
                self.ui.lbl_estado.setText("Estado: ")
                self.ui.lbl_total.setText("Total a pagar: ")
                self.ui.lbl_diagnostico.setText("Diagnóstico: ")
                self.ui.lbl_fecha_entrega.setText("Fecha de entrega estimada: ")

        except Exception as e:
            QMessageBox.critical(self.ui, "Error", f"Fallo al consultar:\n{e}, contacte con soporte técnico.")
        finally:
            cursor.close()
            conexion.close()


    def aprobar_presupuesto(self):
        
        if not hasattr(self, 'folio_confirmado') or not self.folio_confirmado:
            QMessageBox.warning(self.ui, "Alerta", "Primero debes buscar un folio válido.")
            return

        folio = self.folio_confirmado

        fecha_base = QDate.currentDate().addDays(10)
        fecha_bd = fecha_base.toString("yyyy-MM-dd")
        fecha_visual = fecha_base.toString("dd-MM-yyyy")

        conexion = conectar_bd()
        if not conexion: return
        try:
            cursor = conexion.cursor()
            sql = "UPDATE servicios SET estado = 'En Servicio', fecha_estimada = %s WHERE folio_seguimiento = %s"
            cursor.execute(sql, (fecha_bd, folio))
            conexion.commit()
        
            QMessageBox.information(self.ui, "Aprobado", f"Presupuesto aprobado exitosamente.\nTu fecha estimada de entrega es: {fecha_visual}")
        
            self.buscar_folio() 

            self.ui.btn_aprobar.setEnabled(False)
            self.ui.btn_rechazar.setEnabled(False)
        
        except Exception as e:
            QMessageBox.critical(self.ui, "Error", f"Ocurrió un error al aprobar: {str(e)}")
        finally:
            cursor.close()
            conexion.close()


    def rechazar_presupuesto(self):
        
        if not hasattr(self, 'folio_confirmado') or not self.folio_confirmado:
                    QMessageBox.warning(self.ui, "Alerta", "Primero debes buscar un folio válido.")
                    return
        
        folio = self.folio_confirmado
    
        confirmacion = QMessageBox.question(
            self.ui, 
            "Confirmar Rechazo", 
            "¿Estás seguro de que deseas rechazar el presupuesto? El servicio será cancelado.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

        conexion = conectar_bd()
        if confirmacion == QMessageBox.StandardButton.Yes:
            try:
                cursor = conexion.cursor()
                cursor.execute("SELECT id FROM servicios WHERE folio_seguimiento = %s", (folio,))
                resultado = cursor.fetchone()

                if not resultado:
                    return

                id_servicio = resultado[0]

                cursor.execute("SELECT cantidad, id_refaccion FROM detalle_servicio WHERE id_servicio = %s", (id_servicio,))
                piezas_usadas = cursor.fetchall()

                if piezas_usadas:
                    sql_devolucion = "UPDATE refacciones SET stock = stock + %s WHERE id = %s"
                    cursor.executemany(sql_devolucion, piezas_usadas)

                sql = "UPDATE servicios SET estado = 'Cancelado', costo_mano_obra = 0 WHERE id = %s"
                cursor.execute(sql, (id_servicio,))
                conexion.commit()
            
                QMessageBox.information(self.ui, "Cancelado", "El presupuesto ha sido rechazado exitosamente.")
        
                self.buscar_folio() 
            
            except Exception as e:
                conexion.rollback()
                QMessageBox.critical(self.ui, "Error", f"Ocurrió un error al cancelar: {str(e)}")
            finally:
                cursor.close()
                conexion.close()

    def volver_inicio(self):
        self.ventana_inicio = BienvenidaWindow()
        self.ventana_inicio.show()
        self.ui.close()

    def abrir_agendar(self):
        self.ventana_agendar = AgendarClienteWindow()
        self.ventana_agendar.ui.show()

#Pantalla login
class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loader = QUiLoader()
        archivo = QFile(ruta_recurso("login.ui"))
        archivo.open(QFile.ReadOnly)
        self.ui = loader.load(archivo, self)
        archivo.close()
        self.setCentralWidget(self.ui)
        self.resize(self.ui.size())
        self.setWindowTitle("Acceso Administrador")

        self.ui.btn_entrar.clicked.connect(self.verificar_login)
        self.ui.btn_volver.clicked.connect(self.volver_bienvenida)

    def verificar_login(self):
        usuario_texto = self.ui.input_usuario.text()
        password_texto = self.ui.input_password.text()

        if not usuario_texto or not password_texto:
            QMessageBox.warning(self, "Cuidado", "Llena todos los campos.")
            return

        conexion = conectar_bd()
        if not conexion:
            QMessageBox.critical(self, "Error", "No hay conexión a la base de datos.")
            return
            
        try:
            cursor = conexion.cursor()
            sql = "SELECT nombre_corto FROM usuarios WHERE usuario = %s AND password = %s"
            cursor.execute(sql, (usuario_texto, password_texto))
            resultado = cursor.fetchone() 

            if resultado:
                nombre_admin = resultado[0]
                QMessageBox.information(self, "Bienvenido", f"¡Hola {nombre_admin}! Has iniciado sesión correctamente.")
                self.dashboard = DashboardAdmin() 
                self.dashboard.usuario_actual = usuario_texto
                self.close()                       
                
            else:
                QMessageBox.warning(self, "Error", "Usuario o contraseña incorrectos.")
                self.ui.input_password.clear()
                
        except Exception as e:
            QMessageBox.critical(self, "Error BD", f"Fallo al consultar:\n{e}")
        finally:
            cursor.close()
            conexion.close()

    def volver_bienvenida(self):
        self.ventana_inicio = BienvenidaWindow()
        self.ventana_inicio.show()
        self.close()
            
#Pantalla inicial
class BienvenidaWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        loader = QUiLoader()
        archivo = QFile(ruta_recurso("bienvenida.ui"))
        archivo.open(QFile.ReadOnly)
        self.ui = loader.load(archivo, self)
        archivo.close()
        self.setCentralWidget(self.ui)
        self.resize(self.ui.size())
        self.setWindowTitle("Selecciona tu perfil")

        self.ui.btn_admin.clicked.connect(self.abrir_login)
        self.ui.btn_cliente.clicked.connect(self.abrir_portal_cliente)

    def abrir_login(self):
        self.ventana_login = LoginWindow()
        self.ventana_login.show()
        self.close()

    def abrir_portal_cliente(self):
        self.ventana_cliente = DashboardCliente()
        self.ventana_cliente.ui.show() 
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    os.chdir(ruta_recurso("."))

    regla_texto = QRegularExpression(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$")
    validador_letras = QRegularExpressionValidator(regla_texto)

    regla_numeros = QRegularExpression(r"^[0-9]+$")
    validador_numeros = QRegularExpressionValidator(regla_numeros)

    validador_stock = QIntValidator(0, 9999)
    validador_dinero = QDoubleValidator(0.00, 99999.99, 2)
    validador_dinero.setNotation(QDoubleValidator.StandardNotation)
    
    app.setWindowIcon(QIcon(ruta_recurso("icono.png")))
    ventana = BienvenidaWindow()
    ventana.show()
    sys.exit(app.exec())