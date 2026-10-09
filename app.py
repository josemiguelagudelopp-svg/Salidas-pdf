import os
import requests
import customtkinter as ctk
from tkinter import messagebox, ttk
from supabase import create_client, Client

# --- CREDENCIALES DE SUPABASE (Intactas) ---
SUPABASE_URL = 'https://obcwirxjvypxdpxudyqu.supabase.co'
SUPABASE_KEY = 'sb_publishable_nFUde6igy8iYfKScAMFhKQ_K1e7ot-d'
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class GestorSalidasApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Gestor de Salidas de Campo - CustomTkinter")
        self.geometry("950x600")
        
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        # Título principal
        self.label_titulo = ctk.CTkLabel(
            self, 
            text="Organizador Local de Salidas de Campo", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.label_titulo.pack(pady=15)
        
        # Panel de botones superiores
        self.frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_botones.pack(pady=5, fill="x", padx=20)
        
        self.btn_actualizar = ctk.CTkButton(
            self.frame_botones, 
            text="🔄 Actualizar Datos", 
            command=self.cargar_datos
        )
        self.btn_actualizar.pack(side="left", padx=5)
        
        # Único botón requerido para organizar y descargar
        self.btn_organizar = ctk.CTkButton(
            self.frame_botones, 
            text="📥 Organizar", 
            fg_color="#2b8a3e", 
            hover_color="#2b7c35", 
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.organizar_archivos_localmente
        )
        self.btn_organizar.pack(side="left", padx=10)
        
        # Tabla visual de registros (Treeview)
        self.frame_tabla = ctk.CTkFrame(self)
        self.frame_tabla.pack(pady=15, padx=20, fill="both", expand=True)
        
        columns = ("Materia", "Estudiante", "Documento", "Fecha Salida", "URL PDF")
        self.tree = ttk.Treeview(self.frame_tabla, columns=columns, show="headings")
        
        # Configurar columnas
        self.tree.heading("Materia", text="Materia")
        self.tree.heading("Estudiante", text="Estudiante")
        self.tree.heading("Documento", text="Documento")
        self.tree.heading("Fecha Salida", text="Fecha Salida")
        self.tree.heading("URL PDF", text="Enlace PDF")
        
        self.tree.column("Materia", width=180, anchor="w")
        self.tree.column("Estudiante", width=150, anchor="w")
        self.tree.column("Documento", width=100, anchor="center")
        self.tree.column("Fecha Salida", width=100, anchor="center")
        self.tree.column("URL PDF", width=300, anchor="w")
        
        self.scrollbar = ttk.Scrollbar(self.frame_tabla, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Cargar los registros al iniciar la app
        self.cargar_datos()

    def limpiar_nombre(self, texto):
        """Limpia caracteres especiales para que no fallen al crear carpetas y archivos en el PC."""
        if not texto:
            return "Sin_Especificar"
        # Reemplazar caracteres no permitidos en nombres de carpetas de Windows/Linux/Mac
        caracteres_invalidos = '<>:"/\\|?*# '
        for char in caracteres_invalidos:
            texto = texto.replace(char, '_')
        return texto.strip('_')

    def cargar_datos(self):
        """Consulta puramente de lectura a Supabase sin alterar la base de datos."""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        try:
            response = supabase.table('documentos_editados').select('*').execute()
            registros = response.data if response.data else []
            
            for reg in registros:
                self.tree.insert("", "end", values=(
                    reg.get('materia', 'Sin Materia'),
                    reg.get('nombre_estudiante', 'Sin Estudiante'),
                    reg.get('documento_identidad', 'Sin Documento'),
                    reg.get('texto_apartado_2', 'Sin Fecha'),
                    reg.get('url_pdf', '')
                ))
        except Exception as e:
            messagebox.showerror("Error de Conexión", f"No se pudo conectar a Supabase:\n{e}")

    def organizar_archivos_localmente(self):
        """Descarga y agrupa los archivos en carpetas locales según la materia y la fecha."""
        try:
            response = supabase.table('documentos_editados').select('*').execute()
            registros = response.data if response.data else []
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron obtener los registros de Supabase: {e}")
            return
        
        if not registros:
            messagebox.showwarning("Aviso", "No hay registros disponibles en la base de datos.")
            return

        carpeta_base = "Salidas_Organizadas"
        os.makedirs(carpeta_base, exist_ok=True)
        
        contador = 0
        for reg in registros:
            # Obtener materia y fecha exactamente como están en la base de datos
            materia_bruta = reg.get('materia', 'Sin_Materia')
            fecha_bruta = reg.get('texto_apartado_2', 'Sin_Fecha')
            url_pdf = reg.get('url_pdf')
            
            # Limpiar formatos para asegurar compatibilidad con el sistema de archivos
            materia = self.limpiar_nombre(materia_bruta)
            fecha = self.limpiar_nombre(fecha_bruta.replace('/', '-'))
            
            # Nombre por defecto del archivo basado en el estudiante o contador
            estudiante = self.limpiar_nombre(reg.get('nombre_estudiante', 'documento'))
            nombre_archivo = f"{estudiante}.pdf"
            
            # Crear la estructura de carpetas: Salidas_Organizadas / Materia / Fecha
            ruta_carpeta_destino = os.path.join(carpeta_base, materia, fecha)
            os.makedirs(ruta_carpeta_destino, exist_ok=True)
            
            # Descargar el archivo PDF desde Supabase Storage
            if url_pdf:
                try:
                    res_pdf = requests.get(url_pdf, timeout=15)
                    if res_pdf.status_code == 200:
                        ruta_completa_archivo = os.path.join(ruta_carpeta_destino, nombre_archivo)
                        
                        # Evitar sobreescritura si hay varios archivos con el mismo nombre
                        base, ext = os.path.splitext(ruta_completa_archivo)
                        i = 1
                        while os.path.exists(ruta_completa_archivo):
                            ruta_completa_archivo = f"{base}_{i}{ext}"
                            i += 1
                            
                        with open(ruta_completa_archivo, 'wb') as f:
                            f.write(res_pdf.content)
                        contador += 1
                except Exception as ex:
                    print(f"Error descargando el archivo {url_pdf}: {ex}")
                    
        messagebox.showinfo(
            "Organización Exitosa", 
            f"¡Se han descargado y organizado {contador} archivos exitosamente!\n\n"
            f"Búscalos en la carpeta local: '{os.path.abspath(carpeta_base)}'"
        )

if __name__ == '__main__':
    app = GestorSalidasApp()
    app.mainloop()