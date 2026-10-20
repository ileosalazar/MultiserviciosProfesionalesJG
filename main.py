import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QInputDialog
from PySide6.QtGui import QIcon 
from PySide6.QtCore import QFile
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


class NuevaCitaWindow:
    def __init__(self, parent=None): 
        self.parent = parent
        loader = QUiLoader()
        archivo = QFile(ruta_recurso("nueva_cita.ui"))
        archivo.open(QFile.ReadOnly)
        self.ui = loader.load(archivo)
        archivo.close()
        self.ui.setWindowTitle("Agendar Nueva Cita")
        
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

    def guardar_cita(self):
        id_cliente = self.ui.combo_cliente.currentData()
        id_aparato = self.ui.combo_aparato.currentData()
        fecha = self.ui.input_fecha.text()
        costo = self.ui.input_costo_revision.text()

        if not id_cliente or not id_aparato or not fecha or not costo:
            QMessageBox.warning(self.ui, "Error", "Llena todos los campos.")
            return

        letras_numeros = string.ascii_uppercase + string.digits
        codigo_aleatorio = ''.join(random.choices(letras_numeros, k=5))
        folio = f"MS-{codigo_aleatorio}"

        conexion = conectar_bd()
        if not conexion: return
        try:
            cursor = conexion.cursor()
            
            sql = """
                INSERT INTO servicios (id_aparato, fecha_visita, estado, costo_revision, folio_seguimiento) 
                VALUES (%s, %s, %s, %s, %s)
            """

            valores = (
                id_aparato, 
                fecha,          
                "Pendiente",             
                costo,                    
                folio                     
            )

            cursor.execute(sql, valores)
            conexion.commit() 
            
            QMessageBox.information(self.ui, "Éxito", f"Cita agendada.\nFolio del cliente: {folio}")

            if self.parent:
                self.parent.cargar_citas()

            self.ui.close() 
            
        except Exception as e:
            conexion.rollback()
            QMessageBox.critical(self.ui, "Error BD", f"Fallo al guardar:\n{e}")
        finally:
            cursor.close()
            conexion.close()


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
            
            nombre_pieza = self.ui.combo_refaccion.currentText()
            sql_detalle = """
                INSERT INTO detalle_servicio (id_servicio, id_refaccion, descripcion, cantidad, precio_unitario)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id_servicio, id_refaccion) 
                DO UPDATE SET cantidad = detalle_servicio.cantidad + EXCLUDED.cantidad;
            """
            cursor.execute(sql_detalle, (id_servicio, datos['id'], nombre_pieza, cantidad, datos['precio']))
            
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


class DashboardAdmin:
    def __init__(self):
        loader = QUiLoader()
        archivo = QFile(ruta_recurso("dashboard_admin.ui"))
        archivo.open(QFile.ReadOnly)
        self.ui = loader.load(archivo)
        archivo.close()
        self.ui.setWindowTitle("Panel de Control - Multiservicios")

        self.ui.btn_nueva_cita.clicked.connect(self.abrir_nueva_cita)
        self.ui.btn_editar_estado.clicked.connect(self.editar_estado)
        self.ui.btn_agregar_pieza.clicked.connect(self.abrir_agregar_pieza)
        self.ui.btn_eliminar_cita.clicked.connect(self.eliminar_cita)
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
                (COALESCE(s.costo_revision, 0) + COALESCE(SUM(d.cantidad * d.precio_unitario), 0)) AS total
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
                    
                    if col_num == 5:
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
                
                -- NUEVA COLUMNA: Unimos la dirección separada por comas
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
                    
                    if col_num == 4:
                        texto_celda = str(dato) if dato else "Sin visitas"
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
        
        if fila == -1:
            QMessageBox.warning(self.ui, "Atención", "Selecciona una cita de la tabla primero.")
            return

        folio = self.ui.tabla_citas.item(fila, 0).text()
        estado_actual = self.ui.tabla_citas.item(fila, 4).text()

        estados = ["Pendiente", "En Revisión", "Esperando Aprobación", "Terminado", "Cancelado"]
        
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

        if nuevo_estado == "En Revisión": 
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

        else:
            sql = "UPDATE servicios SET estado = %s WHERE folio_seguimiento = %s"
            valores = (nuevo_estado, folio)

        conexion = conectar_bd()
        if not conexion: return
        
        try:
            cursor = conexion.cursor()
            cursor.execute(sql, valores)
            conexion.commit()
            
            QMessageBox.information(self.ui, "Éxito", f"El servicio {folio} ahora está '{nuevo_estado}'.")
            self.cargar_citas()
            
        except Exception as e:
            conexion.rollback()
            QMessageBox.critical(self.ui, "Error BD", f"Fallo al actualizar:\n{e}")
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
        
        if fila == -1:
            QMessageBox.warning(self.ui, "Atención", "Selecciona la cita que deseas eliminar.")
            return

        folio = self.ui.tabla_citas.item(fila, 0).text()
        cliente = self.ui.tabla_citas.item(fila, 1).text()

        respuesta = QMessageBox.warning(
            self.ui, 
            "Peligro: Borrar Registro", 
            f"¿Estás absolutamente seguro de querer eliminar la cita {folio} de {cliente}?\n\nEsta acción borrará el servicio de la base de datos para siempre y no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.Cancel, 
            QMessageBox.Cancel
        )

        if respuesta == QMessageBox.Yes:
            conexion = conectar_bd()
            if not conexion: return
            
            try:
                cursor = conexion.cursor()
                
                sql = "DELETE FROM servicios WHERE folio_seguimiento = %s"
                cursor.execute(sql, (folio,))
                
                conexion.commit()
                
                QMessageBox.information(self.ui, "Eliminado", f"El folio {folio} ha sido eliminado con éxito.")
                
                self.cargar_citas()
                
            except Exception as e:
                conexion.rollback()
                QMessageBox.critical(self.ui, "Error BD", f"Fallo al eliminar:\n{e}")
            finally:
                cursor.close()
                conexion.close()

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
                SELECT id, nombre, stock, precio_publico, (precio_publico - precio_compra) AS margen 
                FROM refacciones 
                ORDER BY nombre ASC
            """
            cursor.execute(sql)
            refacciones = cursor.fetchall()
            
            self.ui.tabla_inventario.setRowCount(0)
            for fila_num, ref in enumerate(refacciones):
                self.ui.tabla_inventario.insertRow(fila_num)
                for col_num, dato in enumerate(ref):
                    if col_num in [3, 4]:
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
                    texto_celda = str(dato) if dato else ""
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
                    (s.costo_revision + COALESCE(SUM(ds.cantidad * ds.precio_unitario), 0)) AS total_pagado
                FROM servicios s
                JOIN aparatos a ON s.id_aparato = a.id
                LEFT JOIN detalle_servicio ds ON s.id = ds.id_servicio
                WHERE a.id_cliente = %s
                GROUP BY 
                    s.id, s.folio_seguimiento, a.tipo, a.marca, 
                    s.fecha_visita, s.estado, s.costo_revision
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
                    (s.costo_revision + COALESCE(SUM(d.cantidad * d.precio_unitario), 0)) AS total
                FROM servicios s
                JOIN aparatos a ON s.id_aparato = a.id
                JOIN clientes c ON a.id_cliente = c.id
                LEFT JOIN detalle_servicio d ON d.id_servicio = s.id
                WHERE s.folio_seguimiento = %s
                GROUP BY s.id, c.nombre, a.tipo, a.marca
            """
            cursor.execute(sql, (folio_texto,))
            resultado = cursor.fetchone()
            
            if resultado:
                self.ui.lbl_cliente.setText(f"Cliente: {resultado[0]}")
                self.ui.lbl_aparato.setText(f"Equipo: {resultado[1]}")
                self.ui.lbl_estado.setText(f"Estado Actual: {resultado[2]}")
                self.ui.lbl_total.setText(f"Total a pagar: ${resultado[3]:.2f}")
                
                if resultado[2] == 'Pendiente':
                    self.ui.lbl_estado.setStyleSheet("color: orange; font-weight: bold; font-size: 14px;")
                elif resultado[2] == 'Terminado':
                    self.ui.lbl_estado.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
                    
            else:
                QMessageBox.warning(self.ui, "No encontrado", "No existe ninguna cita con ese folio. Verifica y vuelve a intentar.")
                self.ui.lbl_cliente.setText("")
                self.ui.lbl_aparato.setText("")
                self.ui.lbl_estado.setText("")
                self.ui.lbl_total.setText("")
                
        except Exception as e:
            QMessageBox.critical(self.ui, "Error", f"Fallo al consultar:\n{e}")
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
            sql = "SELECT nombre FROM usuarios WHERE usuario = %s AND password = %s"
            cursor.execute(sql, (usuario_texto, password_texto))
            resultado = cursor.fetchone() 

            if resultado:
                nombre_admin = resultado[0]
                QMessageBox.information(self, "Bienvenido", f"¡Hola {nombre_admin}! Has iniciado sesión correctamente.")
                self.dashboard = DashboardAdmin() 
                self.close()                       
                
            else:
                QMessageBox.warning(self, "Error", "Usuario o contraseña incorrectos.")
                self.ui.input_password.clear()
                
        except Exception as e:
            QMessageBox.critical(self, "Error BD", f"Fallo al consultar:\n{e}")
        finally:
            cursor.close()
            conexion.close()
            
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
    
    app.setWindowIcon(QIcon(ruta_recurso("icono.png")))
    ventana = BienvenidaWindow()
    ventana.show()
    sys.exit(app.exec())