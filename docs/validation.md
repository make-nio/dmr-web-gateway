# Evidencia de validación — 2026-11-09

Entorno: Windows, Node.js v22.22.1, npm 10.9.4.

- `npm ci`/instalación: dependencias exclusivamente de desarrollo; runtime usa Node.
- `npm test`: 7 pruebas pasan. Fixtures de ID big-endian, SHA256 conocido,
  ancho RPTC; handshake real UDP contra mock; datagramas truncados/ID erróneo;
  ping/pong; pérdida de pong y reconexión; MSTCL, MSTNAK, RPTCL;
  timeout separado en login, autorización y configuración; logs por whitelist;
  procesos completos con secreto por archivo y healthcheck sin puerto;
  errores de arranque sin revelar rutas ni contenido.
- La ejecución restringida inicialmente bloqueó UDP local y produjo timeouts;
  la ejecución con acceso loopback pasó.
- Sesión de aceptación de 600 s: en curso; resultado se registra antes del PR.
- Docker no está instalado en esta máquina. Dockerfile/Compose revisados
  estáticamente; build, healthcheck y límites en contenedor pendientes de SRE.
- No se usaron secretos reales, BrandMeister, RF ni infraestructura SRE.

La verificación contra fuentes y simulador no certifica interoperabilidad con
un master real. La issue no debe cerrarse como validada en producción.
