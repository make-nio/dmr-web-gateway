# Sprint 1 · D1 · Referencias para contrastar las tramas de voz

**Dictamen propuesto a arquitectura, 11 de noviembre de 2026.** Usar dmrgo
como comparador externo de formato y FEC, anclado en un par de silencio con
salida conocida. Para voz, la fuente candidata más directa es DVSI. Sigue
pendiente obtener un par PCM/AMBE con perfil DMR y condiciones de uso
verificados. D1 fue una revisión documental. Todos los criterios de D2 que
siguen están **pendientes de ejecución**.

## Contrato observado en C7

Una trama corresponde a 160 muestras PCM mono s16le a 8 kHz (20 ms). La
salida comprimida se concatena en orden temporal, nueve octetos por trama,
sin cabecera, separador ni relleno. C7 archiva el hash de cada secuencia,
además de los WAV. Para el caso de referencia hay pares de información y
trama protegida archivados por índice en C5. Ejemplo ya registrado, índice
0: `adaptedInput49=1011000000110010101110010100111110000010111000101`,
`adapted72=b0357c6213d29f05c5`.
[Empaquetador de C5 reutilizado por C7](../../experiments/vocoder/c5/pack.cpp) ·
[Datos por trama de C5](../../experiments/vocoder/evidence/c5/frames.jsonl) ·
[Validación y hashes de C7](../../experiments/vocoder/evidence/c7/manifest.json).

Los índices siguientes empiezan en cero. Cada fila enumera dónde se coloca
cada bit del parámetro, del más al menos significativo, en los 49 de
información. El bit de información 0 sale primero.

| Parámetro | Posiciones de información |
|---|---|
| b0 | 0,1,2,3,37,38,39 |
| b1 | 4,5,6,7,35 |
| b2 | 8,9,10,11,36 |
| b3 | 12,13,14,15,16,17,18,19,40 |
| b4 | 20,21,22,23,41,42,43 |
| b5 | 24,25,26,27,44 |
| b6 | 28,29,30,45 |
| b7 | 31,32,33,46 |
| b8 | 34,47,48 |

| Información | Transformación C7 | Posiciones en los 72 bits locales |
|---|---|---|
| 0–11, a | Golay extendido (24,12) de a | 0–23 (A) |
| 12–23, b | Golay (23,12) alineado mediante `encode23127(b) >> 1`, XOR con la máscara de a | 24–46 (B) |
| 24–48, c | Los 25 bits sin protección | 47–71 (C) |

La máscara empieza con estado 16a. Para cada uno de sus 23 bits se avanza
el estado como (173 × estado + 13849) módulo 65536 y se emite su bit 15,
primero el bit superior de la máscara. A, B y C ya protegido/enmascarado
según corresponda se concatenan MSB primero. En cada octeto el primer bit
ocupa el peso 128. La ganancia ×1 de C6 interviene al sintetizar PCM.
[Fuente fijada de la máscara](https://github.com/MW0MWZ/OpenDMR/blob/d28164b39ba4d91ad5948ff22707937f8944f70f/opendmr.cpp#L79) ·
[Correspondencia auditada en C2–C5](sprint-1-vocoder-phase-c.md).

## Comparación documental con el silencio externo

dmrgo, revisión `f78e033e90559995213498973fe9d75e9bd45b93`, publica
**F801A99F8CE080** como siete octetos de información. Son 49 bits MSB primero
y siete ceros de relleno en la parte baja del último octeto. Publica
**B9E881526173002A6B** como los 72 bits intercalados de un tramo de voz de
20 ms. La constante de MMDVMHost para rellenar ráfagas aporta un ancla para
el segundo valor. dmrgo atribuye explícitamente su silencio a MMDVMHost.
Es un solo linaje de vector. El silencio digital de entrada de Par-07
puede llevar al encoder a otra representación de silencio válida. El
estímulo inequívoco para D2 es la información literal de 49 bits.
[Par publicado](https://github.com/USA-RedDragon/dmrgo/blob/f78e033e90559995213498973fe9d75e9bd45b93/v2/vocoder/frame.go) ·
[Test con resultado literal](https://github.com/USA-RedDragon/dmrgo/blob/f78e033e90559995213498973fe9d75e9bd45b93/v2/vocoder/ambe72_test.go) ·
[Constante de MMDVMHost](https://github.com/g4klx/MMDVM-Host/blob/master/DMRDefines.h).

**Transformación exacta propuesta para comparar.** Tomar la concatenación
local de 72 bits y dividirla, en orden, en cuatro filas de 18 bits. Leer una
columna a la vez, de arriba hacia abajo, desde la columna 0 hasta la 17.
Equivalentemente, el bit local de índice k ocupa en canal la posición
**4 × (k módulo 18) + parte entera de k/18**. Para volver al formato local,
el bit de canal j va al índice **18 × (j módulo 4) + parte entera de j/4**.
Los primeros tres bits de A van a 0,4,8; el primero de B a 25; el primero de
C a 46. Se conservan los 72 bits y su condición de protegidos o de datos.
Aplicar este paso a una trama ya protegida una sola vez. Para comparar
los 49 bits con la API Go basta empaquetarlos en siete octetos con el
relleno indicado. Estas relaciones se dedujeron por inspección de
`columns`, `Encode` y las tablas de la versión de referencia.
[Implementación Go](https://github.com/USA-RedDragon/dmrgo/blob/f78e033e90559995213498973fe9d75e9bd45b93/v2/internal/fec/ambe/ambe.go) ·
[Tablas de posiciones](https://github.com/USA-RedDragon/dmrgo/blob/f78e033e90559995213498973fe9d75e9bd45b93/v2/internal/fecref/ambe/tables_gen.go).

Un tramo de 72 bits tampoco es una ráfaga DMR completa. Para la voz de una
ráfaga de 60 ms, el test de dmrgo reúne tres tramos de nueve octetos en
orden. En los 264 bits de la ráfaga están los primeros 108 bits de voz,
48 centrales de señalización/sincronismo y otros 108 de voz. La división
corta por la mitad el segundo tramo. D2 puede trabajar con tramos aislados.
[Extracción en voiceSlots](https://github.com/USA-RedDragon/dmrgo/blob/f78e033e90559995213498973fe9d75e9bd45b93/v2/vocoder/ambe72_test.go) ·
[ETSI TS 102 361-1 V2.6.1, §6.1](https://www.etsi.org/deliver/etsi_ts/102300_102399/10236101/02.06.01_60/ts_10236101v020601p.pdf).

## Referencias y grado de independencia

| Fuente | Qué puede contrastar | Independencia, procedencia y condiciones |
|---|---|---|
| dmrgo, API EncodeAMBE72/DecodeAMBE72 | FEC, máscara, intercalado, bits recuperados y errores en bloques A/B | Implementación Go externa al banco, con cálculo Golay y pruebas propias. Independencia parcial: comparte convenciones y silencio con MMDVMHost. Su referencia interna es una versión anterior del mismo paquete. MIT en la raíz. La API citada opera en bits; omite análisis/síntesis de voz. [Código](https://github.com/USA-RedDragon/dmrgo/blob/f78e033e90559995213498973fe9d75e9bd45b93/v2/vocoder/frame.go) · [Prueba diferencial interna](https://github.com/USA-RedDragon/dmrgo/blob/f78e033e90559995213498973fe9d75e9bd45b93/v2/internal/fec/ambe/ambe_test.go) · [Licencia](https://github.com/USA-RedDragon/dmrgo/blob/f78e033e90559995213498973fe9d75e9bd45b93/LICENSE) |
| MMDVMHost, DMR_SILENCE_DATA | Ancla interoperativa de relleno en orden de canal | Fuente primaria del silencio que usa dmrgo. Proyecto GPL v2 según su README. El Golay de OpenDMR también lleva crédito de Jonathan Naylor; la concordancia de proyectos con ese linaje tiene valor limitado como corroboración independiente. [Constante](https://github.com/g4klx/MMDVM-Host/blob/master/DMRDefines.h) · [Licencia](https://github.com/g4klx/MMDVM-Host/blob/master/COPYING) · [Golay de OpenDMR](https://github.com/MW0MWZ/OpenDMR/blob/d28164b39ba4d91ad5948ff22707937f8944f70f/encoder/cgolay24128.cpp) |
| ETSI TS 102 361-1 | Ubicación y duración del payload de voz en la interfaz aérea | Fuente normativa independiente para la estructura de ráfaga. Documento de ETSI con sus avisos de copyright. El socket de 216 bits no aporta por sí solo un resultado PCM esperado ni un vector semántico para b0…b8. [Norma, versión consultada](https://www.etsi.org/deliver/etsi_ts/102300_102399/10236101/02.06.01_60/ts_10236101v020601p.pdf) |
| DVSI, vectores oficiales AMBE-3000-HDK y USB-3000 | Posibles pares PCM/voz comprimida del fabricante para comparar voz | Independencia alta respecto de OpenDMR si se identifica un archivo del perfil correcto. El catálogo ofrece vectores en varios modos, incluso P25. En D1 solo se verificó el catálogo. Faltan identificación 2450+1150 bit/s, interfaz/cabecera, sentido del par, versión, hash y condiciones de uso offline y distribución. Material del proveedor, sin licencia abierta verificada para el paquete. [Catálogo oficial](https://www.dvsinc.com/dlapps/appsoft.shtml) |
| Captura voice.bin en dmrgo | Tramas tomadas como entrada por tests de ráfaga y FEC | La prueba extrae tramos y reencoda los considerados limpios. El archivo carece en esa prueba de PCM conocido, transcripción y procedencia/permiso individual comprobados. La licencia del código no establece derechos sobre voces de terceros. Excluir del mínimo. [Fixture](https://github.com/USA-RedDragon/dmrgo/blob/f78e033e90559995213498973fe9d75e9bd45b93/v2/layer2/testdata/voice.bin) · [Uso concreto](https://github.com/USA-RedDragon/dmrgo/blob/f78e033e90559995213498973fe9d75e9bd45b93/v2/vocoder/ambe72_test.go) |
| BLIP25 y sus goldens | Comparador secundario de voz en ambas direcciones | Otro motor ya estudiado. Sus goldens internos detectan regresiones; los externos DVSI no se distribuyen en el repositorio. Si se consiguieran, contarían como evidencia de su fuente DVSI. Código declarado MIT, procedencia de ingeniería inversa y advertencias de patentes. [README fijado](https://github.com/OpenBLIP25/blip25-vocoder/blob/d1762813b7142c021f4105c832bf7f060d1249fa/README.md) · [Evaluación previa](sprint-1-vocoder-plan.md) |

## D2 propuesto para aprobación

1. **Formato, un vector literal.** En un banco offline separado, fijar las
   dos revisiones, toolchain y hashes de entradas. Usar el par de silencio
   anterior desde los 49 bits, antes de FEC. Comparar los nueve bytes del
   empaquetador experimental tras intercalado con el literal publicado.
   En sentido inverso, desintercalar el literal y recuperar exactamente los
   49 bits con OpenDMR. Verificar también los dos sentidos con la API Go,
   siete ceros de padding y las 72 posiciones únicas. Aceptación: cero
   diferencias y recuperación limpia. Registrar primera posición divergente
   y parar ese nivel si falla. Evitar usar encode/decode del mismo motor
   para fabricar su propio valor esperado.
2. **Formato fuera del silencio y FEC.** Preseleccionar las tramas 0–3
   archivadas en C5 del caso que C7 reprodujo con hash idéntico. Para cada
   una, comparar el slot Go generado desde `adaptedInput49` con el slot
   intercalado desde `adapted72`, y los 49 bits recuperados en el sentido
   inverso. Luego invertir por separado cada una de las 72 posiciones en
   una trama limpia: 47 perturbaciones simples en A/B deben recuperar
   exactamente los 49 bits en ambos decodificadores de trama; 25 en C deben
   cambiar solo el bit crudo correspondiente. Registrar por motor el
   resultado y, donde exista, el contador de errores. Este alcance cubre
   errores simples; queda abierta la cobertura de múltiples errores.
3. **Voz, decisión separada.** Si se obtiene un vector DVSI autorizado del
   modo DMR, documentar formato, nivel de interfaz, reloj de 20 ms, estado
   inicial, origen del PCM (estímulo o síntesis esperada) y derechos. Para
   recepción: decodificar una secuencia externa y verificar duración exacta
   e inteligibilidad contra texto conocido (propuesta: dos oyentes, cada
   uno identifica al menos 9 de 10 palabras predefinidas). Para transmisión:
   evaluar una secuencia **producida por OpenDMR** con un decoder externo
   autorizado offline y el mismo criterio. Un archivo precalculado solo
   habilita los sentidos que permita contrastar. Una diferencia entre
   encoders no implica por sí sola voz inválida. Registrar métricas y
   escucha por sentido, preacordar referencia antes de ejecutar. Si faltan
   vectores o decoder elegible, dejar el sentido correspondiente **pendiente**.

D2 mínimo puede cerrar resultados de formato/FEC con dependencias de ensayo
preparadas previamente para uso sin red. El estado actual es
**interoperabilidad de voz no demostrada**. El contrato de proveedor sigue
abierto. Se solicita revisión arquitectónica del comparador, del vector y
de los criterios antes de pasar de esta especificación a una prueba.
