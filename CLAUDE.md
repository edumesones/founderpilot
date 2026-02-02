## 1. Que es este proyecto

**People AI (by GUD)** - Asistente interno de Pitaya para proyectos PeopleTop.

**Mision**: Convertir inputs cualitativos (entrevistas, cuestionarios, notas) en claridad accionable sobre roles, organigrama, fricciones, rituales y primeros OKR.

**Principio clave**: No sustituye al consultor -> lo amplifica. Es una "capa IA" que se enchufa al metodo PeopleTop.

## 2. Arquitectura (6 piezas)

1. **Input de datos**: Excel (Typeform), PDF (Working Genius, Org), Word (entrevistas), Objetivos negocio
2. **Contexto del proyecto**: Sector, tamano, pais, equipo directivo, dolor principal, alcance
3. **Core IA**: System prompt maestro con principios PeopleTop (soft power, claridad, foco, estructura)
4. **Modulos funcionales** (sub-agentes):
   - M1. Role Clarity Generator
   - M2. Org Design Architect
   - M3. Friction & Risk Mapper
   - M4. Ritual Designer
   - M5. OKR & Priorities Drafter
   - M6. Executive Summary Builder
5. **Repositorio/memoria**: Carpeta por cliente, outputs etiquetados (Cliente-Ano-Modulo-Version)
6. **Salida**: El consultor convierte outputs en diapositivas, informes, workshops, planes de accion

## 3. Flujo Operativo PeopleTop + People AI

**Fase 1 - Discovery & Diagnostico**
- Discovery call -> Cuestionario PeopleTop + Working Genius
- Cargar en People AI: resumen discovery, dolores, objetivos CEO
- Ejecutar: M3 (Fricciones) + M1 (Claridad de roles)

**Fase 2 - Diseno de organigrama y sistema**
- Lanzar: M2 (Org Design) + M4 (Rituales) + M5 (OKR borrador)

**Fase 3 - Workshop con cliente**
- Llevar: propuestas de roles, organigrama 2026-2028, 10 rituales, 3-5 objetivos con KRs
- Ajustar en vivo (aqui esta el valor del consultor)

**Fase 4 - Cierre & Reporting**
- Ejecutar: M6 (Executive Summary)
- Entregar: PeopleTop Snapshot, Plan 90-180 dias, siguiente paso

## 4. Principios de output

- Claridad > complejidad
- 5-7 responsabilidades clave por rol
- Vincular siempre a negocio (ingresos, eficiencia, riesgo, equipo)
- Lenguaje simple, concreto y sin humo
- Outputs claros, accionables, en bloques

## 5. Como trabajo (desarrollo)

Sigo el ciclo en `docs/feature_cycle.md` (8 fases):
```
Interview → Think Critically → Plan → Branch → Implement → PR → Merge → Wrap-Up
```

Ver `docs/feature_cycle.md` para detalle completo.

## 6. Estado actual

Ver `docs/features/_index.md` para dashboard completo.

## 7. Reglas importantes

- NUNCA codear sin rama creada
- NUNCA implementar sin plan aprobado
- Commits incrementales por tarea
- Tests obligatorios
- **WRAP-UP OBLIGATORIO** después de merge

## 8. Reglas de Terminal

- NO uses `watch` ni comandos que refrescan infinitamente
- Usa `--no-pager` con git: `git diff --no-pager`
- Usa `-n` para limitar output: `git log -n 5`
- Evita `tail -f` o cualquier stream infinito

---

## 9. Context Management

### Dos niveles de contexto

```
.claude/context/                    # Contexto GLOBAL de sesión
├── mcp/                            # Outputs MCP largos (>50 líneas)
├── history/                        # Historial de sesión diario
└── terminal/                       # Logs de comandos

docs/features/FEAT-XXX/context/     # Contexto POR FEATURE
├── session_log.md                  # Log cronológico de la feature
├── decisions.md                    # Decisiones técnicas
├── blockers.md                     # Blockers y resoluciones
└── wrap_up.md                      # Resumen final (post-merge)
```

### Reglas de Context

| Regla | Cuándo |
|-------|--------|
| **Checkpoint obligatorio** | Al completar cada fase del ciclo |
| **Log continuo** | Cada 30 min o 3 tasks durante Implement |
| **MCP largo → archivo** | Si output > 50 líneas |
| **Vincular a feature** | Usar prefijo FEAT-XXX en archivos MCP |
| **Wrap-up obligatorio** | Después de cada merge |

### Formato de Log

```markdown
### [YYYY-MM-DD HH:MM] - [Acción]

**Fase:** [Interview/Think Critically/Plan/Branch/Implement/PR/Merge/Wrap-up]
**Progreso:** X/Y tasks (si aplica)

**Qué se hizo:**
- [Acción 1]

**Decisiones:**
- [Decisión]: [Valor] - [Razón]

**Próximo paso:** [Siguiente acción]
```

### Comandos de Context

| Comando | Propósito |
|---------|-----------|
| `/log "mensaje"` | Añadir entrada manual al session log |
| `/resume FEAT-XXX` | Retomar feature interrumpida |
| `/wrap-up FEAT-XXX` | Cerrar feature (Fase 7) |

### Respuestas MCP Largas

Cualquier respuesta MCP que supere **50 líneas** → guardar en archivo:

```
.claude/context/mcp/FEAT-XXX_YYYYMMDD_HHMMSS_<tool>.md
```

Luego referenciar: "Output guardado en: [ruta]"

### Recuperación de Contexto

Para retomar una feature interrumpida:

```bash
# Ver estado
cat docs/features/FEAT-XXX/status.md

# Ver último progreso
tail -50 docs/features/FEAT-XXX/context/session_log.md

# Ver tasks pendientes
cat docs/features/FEAT-XXX/tasks.md

# O usar el comando
/resume FEAT-XXX
```

---

## 10. Comandos Disponibles - Quick Reference

### Setup (Fase 0)
| Comando | Propósito |
|---------|-----------|
| `/new-project` | Crear estructura de proyecto |
| `/project-interview` | Definir proyecto |
| `/architecture` | Definir arquitectura y ADRs |
| `/mvp` | Planificar MVP features |

### Feature Cycle (Fases 1-8)
| Comando | Fase | Propósito |
|---------|------|-----------|
| `/new-feature FEAT-XXX` | Pre | Crear feature desde template |
| `/interview FEAT-XXX` | 1 | Especificar feature |
| `/think-critically FEAT-XXX` | 2 | Análisis crítico pre-implementación |
| `/plan FEAT-XXX` | 3 | Diseñar implementación |
| `/git sync` | 4+ | Sincronizar con main |
| `/git "mensaje"` | 5 | Commit con mensaje |
| `/git pr` | 6 | Crear pull request |
| `/wrap-up FEAT-XXX` | 8 | Cerrar feature |

### Utilidades
| Comando | Propósito |
|---------|-----------|
| `/fork-feature FEAT-XXX role` | Trabajo paralelo |
| `/resume FEAT-XXX` | Retomar feature |
| `/log "mensaje"` | Añadir al session log |

---

## 11. Ralph Loop - Autonomous Development

### Qué es
Sistema de desarrollo autónomo que ejecuta el ciclo completo de 8 fases con mínima intervención humana.

### Cuándo usar
- Tienes features definidas en `docs/features/_index.md` con status ⚪ Pending
- Quieres automatizar el desarrollo
- Quieres procesar múltiples features en paralelo

### Comandos

| Comando | Propósito |
|---------|-----------|
| `/ralph orchestrator 3` | Procesar todas las features pendientes (max 3 paralelo) |
| `/ralph feature FEAT-XXX` | Procesar una feature específica |
| `/ralph status` | Ver estado de loops activos |
| `/ralph stop` | Detener todos los loops |

### Flujo

```
1. Human añade features a _index.md con ⚪ Pending
2. Human ejecuta ./ralph-orchestrator.sh 3
3. Ralph crea worktrees, ejecuta loops
4. Ralph pausa solo para:
   - Interview incompleto (spec.md con TBD)
   - Think Critically: red flags o confianza baja
   - Merge approval (PR review)
   - 3 fallos consecutivos
5. Human aprueba PRs en GitHub
6. Ralph detecta merge, hace wrap-up, limpia
```

### Archivos Ralph

| Archivo | Propósito |
|---------|-----------|
| `ralph-orchestrator.sh` | Orquestador multi-feature |
| `ralph-feature.sh` | Loop de feature individual |
| `feature-loop-state.json` | Estado de todos los loops |
| `activity.md` | Log de actividad |

### Documentación
Ver `docs/ralph-feature-loop.md` para guía completa.

---

## 12. Nota de Compatibilidad Windows

- Usar `\` en lugar de `/` para rutas en PowerShell
- Usar herramientas nativas de Claude (`create_file`, `view`, `str_replace`) cuando sea posible
- `*>` en PowerShell redirige tanto stdout como stderr
