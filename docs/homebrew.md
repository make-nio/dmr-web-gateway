# Protocolo revisado

Referencias primarias consultadas el 2026-11-09:

- [DroidStar dmr.cpp](https://github.com/nostar/DroidStar/blob/8c4ced58ebd1b68f2c6633fd1a64b531acfd0796/dmr.cpp), recepción RPTACK y configuración de 302 bytes.
- [MMDVMHost histórico DMRNetwork.cpp](https://github.com/g4klx/MMDVM-Host/blob/a0ec58539a23badc0a7c4e2e3de524d671a9c8b0/DMRNetwork.cpp), login, autorización, configuración, ping y cierre.
- [MMDVMHost actual](https://github.com/g4klx/MMDVM-Host/blob/master/DMRNetwork.cpp): cambió el enlace; no usarlo como especificación de este handshake histórico.

Implementación original del subset de control, sin copiar código de las fuentes.
Los identificadores son uint32 big-endian. RPTL = 8 bytes; RPTACK = 10
(salt de 4 bytes en login, ID en respuestas posteriores); RPTK = 40
(cabecera + ID + SHA256(salt binario || password)); RPTC = 302.
RPTPING/MSTPONG = 11; RPTCL/MSTCL = 9; MSTNAK = 10.

RPTC incluye callsign 8, RX/TX 9 cada una, potencia 2, color 2, latitud 8,
longitud 9, altura 3, localidad 20, descripción 19, slots 1, URL 124,
software 40 y paquete 40. Se usan metadatos ficticios constantes, ASCII,
sin terminador NUL ni frecuencias operativas. La configuración no es pública.

Estados: stopped -> login -> auth -> config -> ready. Un timeout de fase,
pong perdido, NAK o cierre remoto provoca retry, socket nuevo y handshake
completo. Espera exponencial de 1 a 30 s, reiniciada al establecer sesión.
Ping cada 5 s, timeout de 5 s; opciones más cortas solo para tests.
Solo se aceptan datagramas de la dirección/puerto conectado, tamaño exacto,
estado esperado e ID propio (salvo el salt). Bytes extra/truncados se ignoran.
Homebrew no autentica ACKs ni distingue todos los duplicados retrasados de
ACKs de fases distintas; este spike no promete resolver esa limitación del wire.

Logs JSON por lista permitida: únicamente event y estado. Nunca se serializan
errores arbitrarios, paquetes, configuración, rutas de secretos, salt o digest.
Se revisaron longitudes antes de leer buffers, callbacks de sockets anteriores,
cancelación de timers y limpieza al cerrar. El prototipo no implementa DMRD,
RPTO, retransmisión de cada fase, jitter ni autorización de red real.
