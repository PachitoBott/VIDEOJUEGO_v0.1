from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UserPreferencesData:
    """Representa las preferencias de skin del jugador."""
    
    skin_body: str = "flaco"
    skin_color: str = "blue"


class UserPreferencesManager:
    """Gestiona las preferencias de usuario con escrituras en CSV."""
    
    HEADER: tuple[str, str] = ("skin_body", "skin_color")
    
    def __init__(self, path: Path | None = None) -> None:
        """
        Inicializa el gestor de preferencias.
        
        Args:
            path: Ruta al archivo CSV. Si es None, usa 'user_preferences.csv' 
                  en el directorio del código.
        """
        if path is None:
            # Por defecto, usa el directorio donde está este archivo
            code_dir = Path(__file__).parent.resolve()
            path = code_dir / "user_preferences.csv"
        
        self.path = path
        self._ensure_file()
    
    def load(self) -> UserPreferencesData:
        """
        Carga las preferencias desde el archivo CSV.
        
        Returns:
            UserPreferencesData con las preferencias cargadas, o valores por defecto
            si hay algún error.
        """
        try:
            with self.path.open("r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                
                # Verificar que el encabezado sea correcto
                if tuple(header or ()) != self.HEADER:
                    return UserPreferencesData()
                
                # Leer la primera fila de datos
                row = next(reader, None)
                if not row or len(row) < 2:
                    return UserPreferencesData()
                
                skin_body = row[0].strip() if row[0] else "flaco"
                skin_color = row[1].strip() if row[1] else "blue"
                
                # Validar que los valores sean válidos
                valid_bodies = {"flaco", "gordo"}
                valid_colors = {"blue", "red", "green", "grey"}
                
                if skin_body not in valid_bodies:
                    skin_body = "flaco"
                if skin_color not in valid_colors:
                    skin_color = "blue"
                
                return UserPreferencesData(
                    skin_body=skin_body,
                    skin_color=skin_color
                )
                
        except (FileNotFoundError, ValueError, IndexError):
            return UserPreferencesData()
    
    def save(self, preferences: UserPreferencesData) -> None:
        """
        Guarda las preferencias al archivo CSV.
        
        Args:
            preferences: Datos de preferencias a guardar.
        """
        # Usar un archivo temporal para escritura atómica
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        
        try:
            with tmp_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.HEADER)
                writer.writerow([
                    preferences.skin_body,
                    preferences.skin_color
                ])
            
            # Reemplazar el archivo original con el temporal
            tmp_path.replace(self.path)
        except Exception as e:
            print(f"Error guardando preferencias: {e}")
            # Limpiar el archivo temporal si existe
            if tmp_path.exists():
                tmp_path.unlink()
    
    def _ensure_file(self) -> None:
        """
        Asegura que el archivo de preferencias exista.
        Si no existe, lo crea con valores por defecto.
        """
        if not self.path.exists():
            # Crear el directorio padre si no existe
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Crear el archivo con valores por defecto
            self.save(UserPreferencesData())
