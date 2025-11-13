from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class StatisticsSnapshot:
    """Representa el estado acumulado de estadísticas del juego."""

    total_runs: int = 0
    total_duration_seconds: float = 0.0
    total_rooms_explored: int = 0
    total_gold_obtained: int = 0
    total_gold_spent: int = 0
    total_kills: int = 0
    total_deaths: int = 0


class StatisticsManager:
    """Gestiona estadísticas acumuladas con escrituras atómicas en CSV."""

    HEADER: tuple[str, ...] = (
        "total_runs",
        "total_duration_seconds",
        "total_rooms_explored",
        "total_gold_obtained",
        "total_gold_spent",
        "total_kills",
        "total_deaths",
    )

    PREVIOUS_AGG_HEADER: tuple[str, ...] = (
        "total_runs",
        "total_duration_seconds",
        "total_rooms_explored",
        "total_gold_collected",
        "total_kills",
        "total_deaths",
    )

    LEGACY_HEADER: tuple[str, ...] = (
        "timestamp",
        "seed",
        "duration_seconds",
        "rooms_explored",
        "gold",
        "reason",
    )

    def __init__(self, path: Path | None = None) -> None:
        base_dir = Path(__file__).resolve().parent
        self.path = path or base_dir / "assets" / "estadisticas.csv"
        self._ensure_file()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def record_run(
        self,
        *,
        duration_seconds: float,
        rooms_explored: int,
        gold_obtained: int,
        gold_spent: int,
    ) -> None:
        """Incrementa los totales asociados a una partida completada."""

        snapshot = self.load_snapshot()
        updated = replace(
            snapshot,
            total_runs=snapshot.total_runs + 1,
            total_duration_seconds=snapshot.total_duration_seconds
            + max(0.0, float(duration_seconds)),
            total_rooms_explored=snapshot.total_rooms_explored + max(0, int(rooms_explored)),
            total_gold_obtained=snapshot.total_gold_obtained + max(0, int(gold_obtained)),
            total_gold_spent=snapshot.total_gold_spent + max(0, int(gold_spent)),
        )
        self._write_snapshot(updated)

    def record_kill(self, count: int = 1) -> None:
        """Registra derrotas de enemigos."""

        if count <= 0:
            return
        snapshot = self.load_snapshot()
        updated = replace(snapshot, total_kills=snapshot.total_kills + int(count))
        self._write_snapshot(updated)

    def record_death(self, count: int = 1) -> None:
        """Registra muertes del jugador."""

        if count <= 0:
            return
        snapshot = self.load_snapshot()
        updated = replace(snapshot, total_deaths=snapshot.total_deaths + int(count))
        self._write_snapshot(updated)

    def load_snapshot(self) -> StatisticsSnapshot:
        """Devuelve el estado agregado actual desde disco."""

        try:
            with self.path.open("r", newline="", encoding="utf-8") as stats_file:
                reader = csv.reader(stats_file)
                header = next(reader, None)
                if tuple(header or ()) != self.HEADER:
                    return StatisticsSnapshot()
                row = next(reader, None)
        except FileNotFoundError:
            return StatisticsSnapshot()

        return self._snapshot_from_row(row)

    def summary_lines(self) -> tuple[str, ...]:
        """Genera líneas amigables para mostrar en el menú."""

        snapshot = self.load_snapshot()
        if (
            snapshot.total_runs == 0
            and snapshot.total_duration_seconds == 0.0
            and snapshot.total_rooms_explored == 0
            and snapshot.total_gold_obtained == 0
            and snapshot.total_gold_spent == 0
            and snapshot.total_kills == 0
            and snapshot.total_deaths == 0
        ):
            return (
                "Estadísticas",
                "",
                "No hay estadísticas registradas todavía.",
                "Juega partidas para generar progreso.",
            )

        lines: list[str] = [
            "Estadísticas",
            "",
            f"Enemigos derrotados: {snapshot.total_kills}",
            f"Muertes del jugador: {snapshot.total_deaths}",
            "",
            f"Oro obtenido: {snapshot.total_gold_obtained}",
            f"Oro gastado: {snapshot.total_gold_spent}",
            "",
            f"Tiempo jugado: {self._format_duration(snapshot.total_duration_seconds)}",
            f"Partidas completadas: {snapshot.total_runs}",
            f"Salas exploradas: {snapshot.total_rooms_explored}",
        ]

        return tuple(lines)

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def _ensure_file(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._write_snapshot(StatisticsSnapshot())
            return

        try:
            with self.path.open("r", newline="", encoding="utf-8") as stats_file:
                reader = csv.reader(stats_file)
                header = next(reader, None)
                if header is None:
                    raise ValueError("Archivo de estadísticas vacío")
                header_tuple = tuple(header)
                if header_tuple == self.HEADER:
                    return
                if header_tuple[: len(self.HEADER)] == self.HEADER:
                    row = next(reader, None)
                    legacy_snapshot = self._snapshot_from_row(row)
                elif header_tuple == self.LEGACY_HEADER:
                    legacy_snapshot = self._convert_legacy_rows(reader)
                elif header_tuple == self.PREVIOUS_AGG_HEADER:
                    legacy_snapshot = self._convert_previous_aggregate(reader)
                else:
                    raise ValueError("Encabezado desconocido")
        except Exception:
            legacy_snapshot = StatisticsSnapshot()

        self._write_snapshot(legacy_snapshot)

    def _write_snapshot(self, snapshot: StatisticsSnapshot) -> None:
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp_path.open("w", newline="", encoding="utf-8") as tmp_file:
            writer = csv.writer(tmp_file)
            writer.writerow(self.HEADER)
            writer.writerow(
                [
                    str(max(0, snapshot.total_runs)),
                    f"{max(0.0, snapshot.total_duration_seconds):.2f}",
                    str(max(0, snapshot.total_rooms_explored)),
                    str(max(0, snapshot.total_gold_obtained)),
                    str(max(0, snapshot.total_gold_spent)),
                    str(max(0, snapshot.total_kills)),
                    str(max(0, snapshot.total_deaths)),
                ]
            )
        tmp_path.replace(self.path)

    def _snapshot_from_row(
        self, row: Sequence[str | None] | None
    ) -> StatisticsSnapshot:
        if not row:
            return StatisticsSnapshot()

        def _parse_int(value: str | None) -> int:
            try:
                return max(0, int(value or 0))
            except (TypeError, ValueError):
                return 0

        def _parse_float(value: str | None) -> float:
            try:
                return max(0.0, float(value or 0.0))
            except (TypeError, ValueError):
                return 0.0

        def _value(idx: int) -> str | None:
            return row[idx] if idx < len(row) else None

        return StatisticsSnapshot(
            total_runs=_parse_int(_value(0)),
            total_duration_seconds=_parse_float(_value(1)),
            total_rooms_explored=_parse_int(_value(2)),
            total_gold_obtained=_parse_int(_value(3)),
            total_gold_spent=_parse_int(_value(4)),
            total_kills=_parse_int(_value(5)),
            total_deaths=_parse_int(_value(6)),
        )

    def _convert_legacy_rows(self, reader: csv.reader) -> StatisticsSnapshot:
        total_runs = 0
        total_duration = 0.0
        total_rooms = 0
        total_gold = 0
        total_deaths = 0

        for row in reader:
            if len(row) != len(self.LEGACY_HEADER):
                continue
            total_runs += 1
            try:
                total_duration += max(0.0, float(row[2]))
            except ValueError:
                pass
            try:
                total_rooms += max(0, int(row[3]))
            except ValueError:
                pass
            try:
                total_gold += max(0, int(row[4]))
            except ValueError:
                pass
            reason = row[5] if len(row) > 5 else ""
            if reason == "player_death":
                total_deaths += 1

        return StatisticsSnapshot(
            total_runs=total_runs,
            total_duration_seconds=total_duration,
            total_rooms_explored=total_rooms,
            total_gold_obtained=total_gold,
            total_gold_spent=0,
            total_kills=0,
            total_deaths=total_deaths,
        )

    def _convert_previous_aggregate(self, reader: csv.reader) -> StatisticsSnapshot:
        row = next(reader, None)
        if not row:
            return StatisticsSnapshot()

        def _parse_int(value: str | None) -> int:
            try:
                return max(0, int(value or 0))
            except (TypeError, ValueError):
                return 0

        def _parse_float(value: str | None) -> float:
            try:
                return max(0.0, float(value or 0.0))
            except (TypeError, ValueError):
                return 0.0

        return StatisticsSnapshot(
            total_runs=_parse_int(row[0] if len(row) > 0 else 0),
            total_duration_seconds=_parse_float(row[1] if len(row) > 1 else 0.0),
            total_rooms_explored=_parse_int(row[2] if len(row) > 2 else 0),
            total_gold_obtained=_parse_int(row[3] if len(row) > 3 else 0),
            total_gold_spent=0,
            total_kills=_parse_int(row[4] if len(row) > 4 else 0),
            total_deaths=_parse_int(row[5] if len(row) > 5 else 0),
        )

    @staticmethod
    def _format_duration(duration_seconds: float) -> str:
        seconds = int(max(0.0, duration_seconds))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:d}h {minutes:02d}m {seconds:02d}s"
        if minutes:
            return f"{minutes:d}m {seconds:02d}s"
        return f"{seconds:d}s"


__all__ = ["StatisticsManager", "StatisticsSnapshot"]
