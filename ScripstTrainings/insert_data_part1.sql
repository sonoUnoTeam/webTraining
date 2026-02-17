-- ========================================
-- TRAININGS Parte 1 (trainingApp_training)
-- ========================================

INSERT INTO `trainingApp_training` (
    `name_training`, `pub_date`, `modificationDate`, `difficulty`, `estimatedDuration`,
    `attempts_allowed`, `state_training`, `passing_score`, `name_training_en`, `name_training_es`
) VALUES
('Entrenamiento de muestra', '2024-04-24 17:16:05.850594', '2024-04-24 18:26:40.580825', 'Easy', 15, 50, 'Active', 70.00, 'Sample Training', 'Entrenamiento de muestra'),
('Funciones Matemáticas', '2024-04-25 13:07:02.257531', '2024-05-28 14:33:47.860726', 'Easy', 20, 5, 'Active', 70.00, 'Mathematical Functions', 'Funciones Matemáticas'),
('Funciones Matemáticas - Ejercitación', '2024-04-25 13:08:58.386107', '2024-06-27 12:15:58.455465', 'Intermediate', 15, 4, 'Active', 70.00, 'Mathematical Functions - Practice', 'Funciones Matemáticas - Ejercitación'),
('Funciones + Ruido', '2024-05-31 22:13:04.468458', '2024-06-05 15:29:50.881649', 'Intermediate', 10, 8, 'Active', 70.00, 'Functions + Noise', 'Funciones + Ruido');

-- ========================================
-- BLOCKS (trainingApp_trainingblock)
-- ========================================
-- Se usa INSERT INTO ... SELECT ... FROM T ... UNION ALL para obtener el training_id.

INSERT INTO `trainingApp_trainingblock` (
    `name_block`, `description`, `estimed_duration_block`, `state_block`, `training_id`,
    `name_block_en`, `name_block_es`, `description_en`, `description_es`
)
-- Para Training "Entrenamiento de muestra"
SELECT
    'Bloque muestra',
    'Bloque para mostrar la din�mica de los entrenamientos',
    15,
    'Active',
    T.id,
    'Sample Block',
    'Bloque muestra',
    'Block to show training dynamics',
    'Bloque para mostrar la din�mica de los entrenamientos'
FROM `trainingApp_training` T
WHERE T.`name_training` = 'Entrenamiento de muestra'

UNION ALL

-- Para Training "Funciones Matem�ticas"
SELECT
    'Funciones Tipo 1',
    'Funciones lineales',
    10,
    'Active',
    T.id,
    'Type 1 Functions',
    'Funciones Tipo 1',
    'Linear functions',
    'Funciones lineales'
FROM `trainingApp_training` T
WHERE T.`name_training` = 'Funciones Matem�ticas'

UNION ALL

SELECT
    'Funciones Tipo 2',
    'Funciones curvas: polin�micas y trigonom�tricas',
    10,
    'Active',
    T.id,
    'Type 2 Functions',
    'Funciones Tipo 2',
    'Curved functions: polynomial and trigonometric',
    'Funciones curvas: polin�micas y trigonom�tricas'
FROM `trainingApp_training` T
WHERE T.`name_training` = 'Funciones Matem�ticas'

UNION ALL

-- Para Training "Funciones Matem�ticas - Ejercitaci�n"
SELECT
    'Funciones Tipo 3',
    'Combinaci�n de funciones',
    10,
    'Active',
    T.id,
    'Type 3 Functions',
    'Funciones Tipo 3',
    'Function combinations',
    'Combinaci�n de funciones'
FROM `trainingApp_training` T
WHERE T.`name_training` = 'Funciones Matem�ticas - Ejercitaci�n'

UNION ALL

SELECT
    'Funciones Tipo 4',
    'Funciones combinadas: lineales + curvas',
    10,
    'Active',
    T.id,
    'Type 4 Functions',
    'Funciones Tipo 4',
    'Combined functions: linear + curved',
    'Funciones combinadas: lineales + curvas'
FROM `trainingApp_training` T
WHERE T.`name_training` = 'Funciones Matem�ticas - Ejercitaci�n'

UNION ALL

-- Para Training "Funciones + Ruido"
SELECT
    'Funciones tipo 1',
    'funciones lineales con ruido',
    5,
    'Active',
    T.id,
    'Type 1 functions',
    'Funciones tipo 1',
    'linear functions with noise',
    'funciones lineales con ruido'
FROM `trainingApp_training` T
WHERE T.`name_training` = 'Funciones + Ruido'

UNION ALL

SELECT
    'Funciones tipo 2',
    'Funciones curvas con ruido',
    5,
    'Active',
    T.id,
    'Type 2 functions',
    'Funciones tipo 2',
    'Curved functions with noise',
    'Funciones curvas con ruido'
FROM `trainingApp_training` T
WHERE T.`name_training` = 'Funciones + Ruido';


-- ========================================
-- DEPLOYS (trainingApp_trainingquestion)
-- ========================================
-- Se usa INSERT INTO ... SELECT ... FROM B ... UNION ALL para obtener el block_id.

INSERT INTO `trainingApp_trainingquestion` (
    `block_id`, `question`, `deploy_image`, `deploy_sound`,
    `question_en`, `question_es`
)
-- Para Block "Bloque muestra"
SELECT
    B.id,
    'Ha detectado sonido?',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/noise.wav',
    'Have you detected sound?',
    'Ha detectado sonido?'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Bloque muestra'

UNION ALL

SELECT
    B.id,
    'Ha detectado sonido?',
    'trainingApp/images/SNR40.300-320.png',
    'trainingApp/sound/sound-noise.300-320.SNR40.wav',
    'Have you detected sound?',
    'Ha detectado sonido?'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Bloque muestra'

UNION ALL

SELECT
    B.id,
    'Ha detectado sonido?',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/sound-noise.260-280.SNR85.wav',
    'Have you detected sound?',
    'Ha detectado sonido?'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Bloque muestra'

UNION ALL

-- Para Block "Funciones Tipo 1"
SELECT
    B.id,
    'Identifica la funci�n mostrada como:',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/fc-constante_sound.mp3',
    'Identify the function shown as:',
    'Identifica la funci�n mostrada como:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 1'

UNION ALL

SELECT
    B.id,
    'Identifica la funci�n mostrada como:',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/decreciente_sound.mp3',
    'Identify the function shown as:',
    'Identifica la funci�n mostrada como:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 1'

UNION ALL

SELECT
    B.id,
    'Identifica la funci�n mostrada como:',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/triangular_sound.mp3',
    'Identify the function shown as:',
    'Identifica la funci�n mostrada como:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 1'

UNION ALL

SELECT
    B.id,
    'Identifica la funci�n mostrada como:',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/creciente_sound.mp3',
    'Identify the function shown as:',
    'Identifica la funci�n mostrada como:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 1'

UNION ALL

SELECT
    B.id,
    'Identifica la funci�n mostrada como:',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/sierra_sound.mp3',
    'Identify the function shown as:',
    'Identifica la funci�n mostrada como:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 1'

UNION ALL

SELECT
    B.id,
    'Identifica la funci�n mostrada como:',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/cuadrada_sound.mp3',
    'Identify the function shown as:',
    'Identifica la funci�n mostrada como:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 1'

UNION ALL

-- Para Block "Funciones Tipo 2"
SELECT
    B.id,
    'Identifica la funci�n mostrada como:',
    'trainingApp/images/cuadratica2plot.png',
    'trainingApp/sound/cuadratica2_sound.mp3',
    'Identify the function shown as:',
    'Identifica la funci�n mostrada como:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 2'

UNION ALL

SELECT
    B.id,
    'Identifica la funci�n mostrada como:',
    'trainingApp/images/cubicaplot.png',
    'trainingApp/sound/cubica_sound.mp3',
    'Identify the function shown as:',
    'Identifica la funci�n mostrada como:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 2'

UNION ALL

SELECT
    B.id,
    'Identifica la funci�n mostrada como:',
    'trainingApp/images/senoplot.png',
    'trainingApp/sound/seno_sound.mp3',
    'Identify the function shown as:',
    'Identifica la funci�n mostrada como:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 2'

UNION ALL

SELECT
    B.id,
    'Identifica la funci�n mostrada como:',
    'trainingApp/images/cuadraticaplot.png',
    'trainingApp/sound/cuadratica_sound.mp3',
    'Identify the function shown as:',
    'Identifica la funci�n mostrada como:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 2'

UNION ALL

SELECT
    B.id,
    'Identifica la funci�n mostrada como:',
    'trainingApp/images/cosenoplot.png',
    'trainingApp/sound/coseno_sound.mp3',
    'Identify the function shown as:',
    'Identifica la funci�n mostrada como:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 2'

UNION ALL

-- Para Block "Funciones Tipo 3"
SELECT
    B.id,
    'Lo que usted escuch� fue una combinaci�n de:',
    'trainingApp/images/Decr-Cte-Decrplot.png',
    'trainingApp/sound/Decr-Cte-Decr_sound.wav',
    'What you heard was a combination of:',
    'Lo que usted escuch� fue una combinaci�n de:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 3'

UNION ALL

SELECT
    B.id,
    'Lo que usted escuch� fue una combinaci�n de:',
    'trainingApp/images/Cte-Cre-Decr-Cteplot.png',
    'trainingApp/sound/Cte-Cre-Decr-Cte_sound.mp3',
    'What you heard was a combination of:',
    'Lo que usted escuch� fue una combinaci�n de:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 3'

UNION ALL

SELECT
    B.id,
    'Lo que usted escuch� fue una combinaci�n de:',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/Cte-Decr-Cre_sound.mp3',
    'What you heard was a combination of:',
    'Lo que usted escuch� fue una combinaci�n de:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 3'

UNION ALL

SELECT
    B.id,
    'Lo que usted escuch� fue una combinaci�n de:',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/Cre-Cte-Decr_sound.mp3',
    'What you heard was a combination of:',
    'Lo que usted escuch� fue una combinaci�n de:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 3'

UNION ALL

-- Para Block "Funciones Tipo 4"
SELECT
    B.id,
    'Lo que escuch� fue una combinaci�n de funciones:',
    'trainingApp/images/Cubica-Cte-Decrplot.png',
    'trainingApp/sound/Cubica-Cte-Decr_sound.mp3',
    'What you heard was a combination of functions:',
    'Lo que escuch� fue una combinaci�n de funciones:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 4'

UNION ALL

SELECT
    B.id,
    'Lo que escuch� fue una combinaci�n de funciones:',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/Decr-Cte-Cre_sound.mp3',
    'What you heard was a combination of functions:',
    'Lo que escuch� fue una combinaci�n de funciones:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 4'

UNION ALL

SELECT
    B.id,
    'Lo que escuch� fue una combinaci�n de funciones:',
    'trainingApp/images/Coseno-Cre-Decrplot.png',
    'trainingApp/sound/Coseno-Cre-Decr_sound.mp3',
    'What you heard was a combination of functions:',
    'Lo que escuch� fue una combinaci�n de funciones:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 4'

UNION ALL

SELECT
    B.id,
    'Lo que escuch� fue una combinaci�n de funciones:',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/Cre-Seno-Cte_sound.mp3',
    'What you heard was a combination of functions:',
    'Lo que escuch� fue una combinaci�n de funciones:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones Tipo 4'

UNION ALL

-- Para Block "Funciones tipo 1" (con ruido)
SELECT
    B.id,
    'Lo que escuch� fue una funci�n:',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/creciente_noise.mp3',
    'What you heard was a function:',
    'Lo que escuch� fue una funci�n:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones tipo 1' AND B.description LIKE '%ruido%'

UNION ALL

SELECT
    B.id,
    'Lo que escuch� fue una funci�n:',
    'trainingApp/images/fc-constanteplot_noise.png',
    'trainingApp/sound/fc-constante_noise.mp3',
    'What you heard was a function:',
    'Lo que escuch� fue una funci�n:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones tipo 1' AND B.description LIKE '%ruido%'

UNION ALL

SELECT
    B.id,
    'Lo que escuch� fue una funci�n:',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/triangular_noise.mp3',
    'What you heard was a function:',
    'Lo que escuch� fue una funci�n:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones tipo 1' AND B.description LIKE '%ruido%'

UNION ALL

SELECT
    B.id,
    'Lo que escuch� fue una funci�n:',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/decreciente_noise.mp3',
    'What you heard was a function:',
    'Lo que escuch� fue una funci�n:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones tipo 1' AND B.description LIKE '%ruido%'

UNION ALL

SELECT
    B.id,
    'Lo que escuch� fue una funci�n:',
    'trainingApp/images/sin_imagen.png',
    'trainingApp/sound/cuadrada_noise.mp3',
    'What you heard was a function:',
    'Lo que escuch� fue una funci�n:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones tipo 1' AND B.description LIKE '%ruido%'

UNION ALL

SELECT
    B.id,
    'Lo que escuch� fue una funci�n:',
    'trainingApp/images/sierraplot_noise.png',
    'trainingApp/sound/sierra_noise.mp3',
    'What you heard was a function:',
    'Lo que escuch� fue una funci�n:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones tipo 1' AND B.description LIKE '%ruido%'

UNION ALL

-- Para Block "Funciones tipo 2" (con ruido)
SELECT
    B.id,
    'Lo que escuch� fue una funci�n:',
    'trainingApp/images/cosenoplot_noise.png',
    'trainingApp/sound/coseno_noise.mp3',
    'What you heard was a function:',
    'Lo que escuch� fue una funci�n:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones tipo 2' AND B.description LIKE '%ruido%'

UNION ALL

SELECT
    B.id,
    'Lo que escuch� fue una funci�n:',
    'trainingApp/images/cubicaplot_noise.png',
    'trainingApp/sound/cubica_noise.mp3',
    'What you heard was a function:',
    'Lo que escuch� fue una funci�n:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones tipo 2' AND B.description LIKE '%ruido%'

UNION ALL

SELECT
    B.id,
    'Lo que escuch� fue una funci�n:',
    'trainingApp/images/cuadraticaplot_noise.png',
    'trainingApp/sound/cuadratica_noise.mp3',
    'What you heard was a function:',
    'Lo que escuch� fue una funci�n:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones tipo 2' AND B.description LIKE '%ruido%'

UNION ALL

SELECT
    B.id,
    'Lo que escuch� fue una funci�n:',
    'trainingApp/images/senoplot_noise.png',
    'trainingApp/sound/seno_noise.mp3',
    'What you heard was a function:',
    'Lo que escuch� fue una funci�n:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones tipo 2' AND B.description LIKE '%ruido%'

UNION ALL

SELECT
    B.id,
    'Lo que escuch� fue una funci�n:',
    'trainingApp/images/cuadratica2plot_noise.png',
    'trainingApp/sound/cuadratica2_noise.mp3',
    'What you heard was a function:',
    'Lo que escuch� fue una funci�n:'
FROM `trainingApp_trainingblock` B
WHERE B.`name_block` = 'Funciones tipo 2' AND B.description LIKE '%ruido%';


-- ========================================
-- CHOICES (trainingApp_choice)
-- ========================================
-- Las inserciones originales con SELECT se mantienen, solo se a�aden backticks.
INSERT INTO `trainingApp_choice` (`choice`, `deploy_id`, `choice_en`, `choice_es`, `correctChoice`)
SELECT 'si', id, 'yes', 'si', FALSE FROM `trainingApp_trainingquestion` WHERE `question` = 'Ha detectado sonido?' AND `deploy_sound` = 'trainingApp/sound/noise.wav';
INSERT INTO `trainingApp_choice` (`choice`, `deploy_id`, `choice_en`, `choice_es`, `correctChoice`)
SELECT 'no', id, 'no', 'no', TRUE FROM `trainingApp_trainingquestion` WHERE `question` = 'Ha detectado sonido?' AND `deploy_sound` = 'trainingApp/sound/noise.wav';
INSERT INTO `trainingApp_choice` (`choice`, `deploy_id`, `choice_en`, `choice_es`, `correctChoice`)
SELECT 'tal vez', id, 'maybe', 'tal vez', FALSE FROM `trainingApp_trainingquestion` WHERE `question` = 'Ha detectado sonido?' AND `deploy_sound` = 'trainingApp/sound/noise.wav';

-- Para deploy con sound-noise.300-320.SNR40.wav (respuesta correcta: "si")
INSERT INTO `trainingApp_choice` (`choice`, `deploy_id`, `choice_en`, `choice_es`, `correctChoice`)
SELECT 'si', id, 'yes', 'si', TRUE FROM `trainingApp_trainingquestion` WHERE `question` = 'Ha detectado sonido?' AND `deploy_sound` = 'trainingApp/sound/sound-noise.300-320.SNR40.wav';
INSERT INTO `trainingApp_choice` (`choice`, `deploy_id`, `choice_en`, `choice_es`, `correctChoice`)
SELECT 'no', id, 'no', 'no', FALSE FROM `trainingApp_trainingquestion` WHERE `question` = 'Ha detectado sonido?' AND `deploy_sound` = 'trainingApp/sound/sound-noise.300-320.SNR40.wav';
INSERT INTO `trainingApp_choice` (`choice`, `deploy_id`, `choice_en`, `choice_es`, `correctChoice`)
SELECT 'tal vez', id, 'maybe', 'tal vez', FALSE FROM `trainingApp_trainingquestion` WHERE `question` = 'Ha detectado sonido?' AND `deploy_sound` = 'trainingApp/sound/sound-noise.300-320.SNR40.wav';

-- Para deploy con sound-noise.260-280.SNR85.wav (respuesta correcta: "si")
INSERT INTO `trainingApp_choice` (`choice`, `deploy_id`, `choice_en`, `choice_es`, `correctChoice`)
SELECT 'si', id, 'yes', 'si', TRUE FROM `trainingApp_trainingquestion` WHERE `question` = 'Ha detectado sonido?' AND `deploy_sound` = 'trainingApp/sound/sound-noise.260-280.SNR85.wav';
INSERT INTO `trainingApp_choice` (`choice`, `deploy_id`, `choice_en`, `choice_es`, `correctChoice`)
SELECT 'no', id, 'no', 'no', FALSE FROM `trainingApp_trainingquestion` WHERE `question` = 'Ha detectado sonido?' AND `deploy_sound` = 'trainingApp/sound/sound-noise.260-280.SNR85.wav';
INSERT INTO `trainingApp_choice` (`choice`, `deploy_id`, `choice_en`, `choice_es`, `correctChoice`)
SELECT 'tal vez', id, 'maybe', 'tal vez', FALSE FROM `trainingApp_trainingquestion` WHERE `question` = 'Ha detectado sonido?' AND `deploy_sound` = 'trainingApp/sound/sound-noise.260-280.SNR85.wav';

-- A partir de aqu�, las inserciones originales usan VALUES con subquery, por lo que se convierten a SELECT ... UNION ALL

INSERT INTO `trainingApp_choice` (`choice`, `deploy_id`, `choice_en`, `choice_es`, `correctChoice`)
-- Choices para deploys de identificaci�n de funciones (fc-constante_sound.mp3)
SELECT 'Creciente', D.id, 'Increasing', 'Creciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/fc-constante_sound.mp3'
UNION ALL
SELECT 'Sierra', D.id, 'Sawtooth', 'Sierra', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/fc-constante_sound.mp3'
UNION ALL
SELECT 'Constante', D.id, 'Constant', 'Constante', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/fc-constante_sound.mp3'
UNION ALL
SELECT 'Triangular', D.id, 'Triangular', 'Triangular', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/fc-constante_sound.mp3'
UNION ALL
SELECT 'Pulso', D.id, 'Pulse', 'Pulso', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/fc-constante_sound.mp3'
UNION ALL
SELECT 'Decreciente', D.id, 'Decreasing', 'Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/fc-constante_sound.mp3'

UNION ALL

-- Choices para funci�n decreciente (decreciente_sound.mp3)
SELECT 'Sierra', D.id, 'Sawtooth', 'Sierra', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/decreciente_sound.mp3'
UNION ALL
SELECT 'Creciente', D.id, 'Increasing', 'Creciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/decreciente_sound.mp3'
UNION ALL
SELECT 'Constante', D.id, 'Constant', 'Constante', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/decreciente_sound.mp3'
UNION ALL
SELECT 'Triangular', D.id, 'Triangular', 'Triangular', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/decreciente_sound.mp3'
UNION ALL
SELECT 'Pulso', D.id, 'Pulse', 'Pulso', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/decreciente_sound.mp3'
UNION ALL
SELECT 'Decreciente', D.id, 'Decreasing', 'Decreciente', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/decreciente_sound.mp3'

UNION ALL

-- Choices para funci�n triangular (triangular_sound.mp3)
SELECT 'Constante', D.id, 'Constant', 'Constante', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/triangular_sound.mp3'
UNION ALL
SELECT 'Creciente', D.id, 'Increasing', 'Creciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/triangular_sound.mp3'
UNION ALL
SELECT 'Sierra', D.id, 'Sawtooth', 'Sierra', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/triangular_sound.mp3'
UNION ALL
SELECT 'Triangular', D.id, 'Triangular', 'Triangular', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/triangular_sound.mp3'
UNION ALL
SELECT 'Pulso', D.id, 'Pulse', 'Pulso', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/triangular_sound.mp3'
UNION ALL
SELECT 'Decreciente', D.id, 'Decreasing', 'Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/triangular_sound.mp3'

UNION ALL

-- Choices para funci�n creciente (creciente_sound.mp3)
SELECT 'Constante', D.id, 'Constant', 'Constante', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/creciente_sound.mp3'
UNION ALL
SELECT 'Creciente', D.id, 'Increasing', 'Creciente', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/creciente_sound.mp3'
UNION ALL
SELECT 'Sierra', D.id, 'Sawtooth', 'Sierra', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/creciente_sound.mp3'
UNION ALL
SELECT 'Triangular', D.id, 'Triangular', 'Triangular', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/creciente_sound.mp3'
UNION ALL
SELECT 'Pulso', D.id, 'Pulse', 'Pulso', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/creciente_sound.mp3'
UNION ALL
SELECT 'Decreciente', D.id, 'Decreasing', 'Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/creciente_sound.mp3'

UNION ALL

-- Choices para funci�n sierra (sierra_sound.mp3)
SELECT 'Creciente', D.id, 'Increasing', 'Creciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/sierra_sound.mp3'
UNION ALL
SELECT 'Constante', D.id, 'Constant', 'Constante', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/sierra_sound.mp3'
UNION ALL
SELECT 'Sierra', D.id, 'Sawtooth', 'Sierra', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/sierra_sound.mp3'
UNION ALL
SELECT 'Triangular', D.id, 'Triangular', 'Triangular', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/sierra_sound.mp3'
UNION ALL
SELECT 'Pulso', D.id, 'Pulse', 'Pulso', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/sierra_sound.mp3'
UNION ALL
SELECT 'Decreciente', D.id, 'Decreasing', 'Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/sierra_sound.mp3'

UNION ALL

-- Choices para funci�n cuadrada/pulso (cuadrada_sound.mp3)
SELECT 'Constante', D.id, 'Constant', 'Constante', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadrada_sound.mp3'
UNION ALL
SELECT 'Creciente', D.id, 'Increasing', 'Creciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadrada_sound.mp3'
UNION ALL
SELECT 'Sierra', D.id, 'Sawtooth', 'Sierra', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadrada_sound.mp3'
UNION ALL
SELECT 'Triangular', D.id, 'Triangular', 'Triangular', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadrada_sound.mp3'
UNION ALL
SELECT 'Pulso', D.id, 'Pulse', 'Pulso', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadrada_sound.mp3'
UNION ALL
SELECT 'Decreciente', D.id, 'Decreasing', 'Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadrada_sound.mp3'

UNION ALL

-- Choices para funciones tipo 2 (curvas)
-- (cuadratica2_sound.mp3)
SELECT 'Cuadr�tica', D.id, 'Quadratic', 'Cuadr�tica', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica2_sound.mp3'
UNION ALL
SELECT 'Coseno', D.id, 'Cosine', 'Coseno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica2_sound.mp3'
UNION ALL
SELECT 'C�bica', D.id, 'Cubic', 'C�bica', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica2_sound.mp3'
UNION ALL
SELECT 'Seno', D.id, 'Sine', 'Seno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica2_sound.mp3'

UNION ALL

-- (cubica_sound.mp3)
SELECT 'Cuadr�tica', D.id, 'Quadratic', 'Cuadr�tica', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cubica_sound.mp3'
UNION ALL
SELECT 'C�bica', D.id, 'Cubic', 'C�bica', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cubica_sound.mp3'
UNION ALL
SELECT 'Coseno', D.id, 'Cosine', 'Coseno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cubica_sound.mp3'
UNION ALL
SELECT 'Seno', D.id, 'Sine', 'Seno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cubica_sound.mp3'

UNION ALL

-- (seno_sound.mp3)
SELECT 'C�bica', D.id, 'Cubic', 'C�bica', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/seno_sound.mp3'
UNION ALL
SELECT 'Cuadr�tica', D.id, 'Quadratic', 'Cuadr�tica', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/seno_sound.mp3'
UNION ALL
SELECT 'Coseno', D.id, 'Cosine', 'Coseno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/seno_sound.mp3'
UNION ALL
SELECT 'Seno', D.id, 'Sine', 'Seno', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/seno_sound.mp3'

UNION ALL

-- (cuadratica_sound.mp3)
SELECT 'Seno', D.id, 'Sine', 'Seno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica_sound.mp3'
UNION ALL
SELECT 'Cuadr�tica', D.id, 'Quadratic', 'Cuadr�tica', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica_sound.mp3'
UNION ALL
SELECT 'C�bica', D.id, 'Cubic', 'C�bica', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica_sound.mp3'
UNION ALL
SELECT 'Coseno', D.id, 'Cosine', 'Coseno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica_sound.mp3'

UNION ALL

-- (coseno_sound.mp3)
SELECT 'C�bica', D.id, 'Cubic', 'C�bica', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/coseno_sound.mp3'
UNION ALL
SELECT 'Coseno', D.id, 'Cosine', 'Coseno', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/coseno_sound.mp3'
UNION ALL
SELECT 'Cuadr�tica', D.id, 'Quadratic', 'Cuadr�tica', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/coseno_sound.mp3'
UNION ALL
SELECT 'Seno', D.id, 'Sine', 'Seno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/coseno_sound.mp3'

UNION ALL

-- Combinaciones de funciones Tipo 3 (Decr-Cte-Decr_sound.wav)
SELECT 'Creciente, Constante, Decreciente', D.id, 'Increasing, Constant, Decreasing', 'Creciente, Constante, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Decr-Cte-Decr_sound.wav'
UNION ALL
SELECT 'Constante, Creciente, Decreciente', D.id, 'Constant, Increasing, Decreasing', 'Constante, Creciente, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Decr-Cte-Decr_sound.wav'
UNION ALL
SELECT 'Decreciente, Constante, Decreciente', D.id, 'Decreasing, Constant, Decreasing', 'Decreciente, Constante, Decreciente', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Decr-Cte-Decr_sound.wav'
UNION ALL
SELECT 'Constante, Decreciente, Creciente', D.id, 'Constant, Decreasing, Increasing', 'Constante, Decreciente, Creciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Decr-Cte-Decr_sound.wav'
UNION ALL
SELECT 'Ninguna de las anteriores', D.id, 'None of the above', 'Ninguna de las anteriores', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Decr-Cte-Decr_sound.wav'

UNION ALL

-- Combinaciones de funciones Tipo 3 (Cte-Cre-Decr-Cte_sound.mp3)
SELECT 'Creciente, Constante, Decreciente', D.id, 'Increasing, Constant, Decreasing', 'Creciente, Constante, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cte-Cre-Decr-Cte_sound.mp3'
UNION ALL
SELECT 'Constante, Creciente, Decreciente', D.id, 'Constant, Increasing, Decreasing', 'Constante, Creciente, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cte-Cre-Decr-Cte_sound.mp3'
UNION ALL
SELECT 'Decreciente, Constante, Decreciente', D.id, 'Decreasing, Constant, Decreasing', 'Decreciente, Constante, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cte-Cre-Decr-Cte_sound.mp3'
UNION ALL
SELECT 'Constante, Decreciente, Creciente', D.id, 'Constant, Decreasing, Increasing', 'Constante, Decreciente, Creciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cte-Cre-Decr-Cte_sound.mp3'
UNION ALL
SELECT 'Ninguna de las anteriores', D.id, 'None of the above', 'Ninguna de las anteriores', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cte-Cre-Decr-Cte_sound.mp3'

UNION ALL

-- Combinaciones de funciones Tipo 3 (Cte-Decr-Cre_sound.mp3)
SELECT 'Creciente, Constante, Decreciente', D.id, 'Increasing, Constant, Decreasing', 'Creciente, Constante, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cte-Decr-Cre_sound.mp3'
UNION ALL
SELECT 'Decreciente, Constante, Decreciente', D.id, 'Decreasing, Constant, Decreasing', 'Decreciente, Constante, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cte-Decr-Cre_sound.mp3'
UNION ALL
SELECT 'Constante, Decreciente, Creciente', D.id, 'Constant, Decreasing, Increasing', 'Constante, Decreciente, Creciente', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cte-Decr-Cre_sound.mp3'
UNION ALL
SELECT 'Constante, Creciente, Decreciente', D.id, 'Constant, Increasing, Decreasing', 'Constante, Creciente, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cte-Decr-Cre_sound.mp3'
UNION ALL
SELECT 'Ninguna de las anteriores', D.id, 'None of the above', 'Ninguna de las anteriores', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cte-Decr-Cre_sound.mp3'

UNION ALL

-- Combinaciones de funciones Tipo 4 (Cubica-Cte-Decr_sound.mp3)
SELECT 'Coseno, Creciente, Decreciente', D.id, 'Cosine, Increasing, Decreasing', 'Coseno, Creciente, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cubica-Cte-Decr_sound.mp3'
UNION ALL
SELECT 'Decreciente, Constante, Creciente', D.id, 'Decreasing, Constant, Increasing', 'Decreciente, Constante, Creciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cubica-Cte-Decr_sound.mp3'
UNION ALL
SELECT 'C�bica, Constante, Decreciente', D.id, 'Cubic, Constant, Decreasing', 'C�bica, Constante, Decreciente', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cubica-Cte-Decr_sound.mp3'
UNION ALL
SELECT 'Creciente, Curva, Constante', D.id, 'Increasing, Curve, Constant', 'Creciente, Curva, Constante', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cubica-Cte-Decr_sound.mp3'
UNION ALL
SELECT 'Ninguna de las anteriores', D.id, 'None of the above', 'Ninguna de las anteriores', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cubica-Cte-Decr_sound.mp3'

UNION ALL

-- Combinaciones de funciones Tipo 4 (Decr-Cte-Cre_sound.mp3)
-- Esta requiere un JOIN para garantizar que es del bloque de Tipo 4 y no de Tipo 3
SELECT 'Coseno, Creciente, Decreciente', D.id, 'Cosine, Increasing, Decreasing', 'Coseno, Creciente, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D
INNER JOIN `trainingApp_trainingblock` B ON D.block_id = B.id
WHERE D.`deploy_sound` = 'trainingApp/sound/Decr-Cte-Cre_sound.mp3' AND D.`question` LIKE '%combinaci�n de funciones%'
UNION ALL
SELECT 'Decreciente, Constante, Creciente', D.id, 'Decreasing, Constant, Increasing', 'Decreciente, Constante, Creciente', TRUE
FROM `trainingApp_trainingquestion` D
INNER JOIN `trainingApp_trainingblock` B ON D.block_id = B.id
WHERE D.`deploy_sound` = 'trainingApp/sound/Decr-Cte-Cre_sound.mp3' AND D.`question` LIKE '%combinaci�n de funciones%'
UNION ALL
SELECT 'C�bica, Constante, Decreciente', D.id, 'Cubic, Constant, Decreasing', 'C�bica, Constante, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D
INNER JOIN `trainingApp_trainingblock` B ON D.block_id = B.id
WHERE D.`deploy_sound` = 'trainingApp/sound/Decr-Cte-Cre_sound.mp3' AND D.`question` LIKE '%combinaci�n de funciones%'
UNION ALL
SELECT 'Creciente, Curva, Constante', D.id, 'Increasing, Curve, Constant', 'Creciente, Curva, Constante', FALSE
FROM `trainingApp_trainingquestion` D
INNER JOIN `trainingApp_trainingblock` B ON D.block_id = B.id
WHERE D.`deploy_sound` = 'trainingApp/sound/Decr-Cte-Cre_sound.mp3' AND D.`question` LIKE '%combinaci�n de funciones%'
UNION ALL
SELECT 'Ninguna de las anteriores', D.id, 'None of the above', 'Ninguna de las anteriores', FALSE
FROM `trainingApp_trainingquestion` D
INNER JOIN `trainingApp_trainingblock` B ON D.block_id = B.id
WHERE D.`deploy_sound` = 'trainingApp/sound/Decr-Cte-Cre_sound.mp3' AND D.`question` LIKE '%combinaci�n de funciones%'

UNION ALL

-- Combinaciones de funciones Tipo 4 (Coseno-Cre-Decr_sound.mp3)
SELECT 'Coseno, Creciente, Decreciente', D.id, 'Cosine, Increasing, Decreasing', 'Coseno, Creciente, Decreciente', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Coseno-Cre-Decr_sound.mp3'
UNION ALL
SELECT 'C�bica, Constante, Decreciente', D.id, 'Cubic, Constant, Decreasing', 'C�bica, Constante, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Coseno-Cre-Decr_sound.mp3'
UNION ALL
SELECT 'Decreciente, Constante, Creciente', D.id, 'Decreasing, Constant, Increasing', 'Decreciente, Constante, Creciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Coseno-Cre-Decr_sound.mp3'
UNION ALL
SELECT 'Creciente, Curva, Constante', D.id, 'Increasing, Curve, Constant', 'Creciente, Curva, Constante', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Coseno-Cre-Decr_sound.mp3'
UNION ALL
SELECT 'Ninguna de las anteriores', D.id, 'None of the above', 'Ninguna de las anteriores', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Coseno-Cre-Decr_sound.mp3'

UNION ALL

-- Combinaciones de funciones Tipo 4 (Cre-Seno-Cte_sound.mp3)
SELECT 'C�bica, Constante, Decreciente', D.id, 'Cubic, Constant, Decreasing', 'C�bica, Constante, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cre-Seno-Cte_sound.mp3'
UNION ALL
SELECT 'Creciente, Curva, Constante', D.id, 'Increasing, Curve, Constant', 'Creciente, Curva, Constante', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cre-Seno-Cte_sound.mp3'
UNION ALL
SELECT 'Decreciente, Constante, Creciente', D.id, 'Decreasing, Constant, Increasing', 'Decreciente, Constante, Creciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cre-Seno-Cte_sound.mp3'
UNION ALL
SELECT 'Coseno, Creciente, Decreciente', D.id, 'Cosine, Increasing, Decreasing', 'Coseno, Creciente, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cre-Seno-Cte_sound.mp3'
UNION ALL
SELECT 'Ninguna de las anteriores', D.id, 'None of the above', 'Ninguna de las anteriores', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/Cre-Seno-Cte_sound.mp3'

UNION ALL

-- Choices para funciones con ruido tipo 1 (creciente_noise.mp3)
SELECT 'Sierra', D.id, 'Sawtooth', 'Sierra', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/creciente_noise.mp3'
UNION ALL
SELECT 'Creciente', D.id, 'Increasing', 'Creciente', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/creciente_noise.mp3'
UNION ALL
SELECT 'Pulso/Cuadrada', D.id, 'Pulse/Square', 'Pulso/Cuadrada', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/creciente_noise.mp3'
UNION ALL
SELECT 'Decreciente', D.id, 'Decreasing', 'Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/creciente_noise.mp3'
UNION ALL
SELECT 'Triangular', D.id, 'Triangular', 'Triangular', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/creciente_noise.mp3'
UNION ALL
SELECT 'Constante', D.id, 'Constant', 'Constante', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/creciente_noise.mp3'

UNION ALL

-- Choices para funciones con ruido tipo 1 (fc-constante_noise.mp3)
SELECT 'Creciente', D.id, 'Increasing', 'Creciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/fc-constante_noise.mp3'
UNION ALL
SELECT 'Constante', D.id, 'Constant', 'Constante', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/fc-constante_noise.mp3'
UNION ALL
SELECT 'Triangular', D.id, 'Triangular', 'Triangular', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/fc-constante_noise.mp3'
UNION ALL
SELECT 'Sierra', D.id, 'Sawtooth', 'Sierra', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/fc-constante_noise.mp3'
UNION ALL
SELECT 'Pulso/Cuadrada', D.id, 'Pulse/Square', 'Pulso/Cuadrada', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/fc-constante_noise.mp3'
UNION ALL
SELECT 'Decreciente', D.id, 'Decreasing', 'Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/fc-constante_noise.mp3'

UNION ALL

-- Choices para funciones con ruido tipo 1 (triangular_noise.mp3)
SELECT 'Decreciente', D.id, 'Decreasing', 'Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/triangular_noise.mp3'
UNION ALL
SELECT 'Triangular', D.id, 'Triangular', 'Triangular', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/triangular_noise.mp3'
UNION ALL
SELECT 'Sierra', D.id, 'Sawtooth', 'Sierra', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/triangular_noise.mp3'
UNION ALL
SELECT 'Pulso/Cuadrada', D.id, 'Pulse/Square', 'Pulso/Cuadrada', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/triangular_noise.mp3'
UNION ALL
SELECT 'Creciente', D.id, 'Increasing', 'Creciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/triangular_noise.mp3'
UNION ALL
SELECT 'Constante', D.id, 'Constant', 'Constante', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/triangular_noise.mp3'

UNION ALL

-- Choices para funciones con ruido tipo 1 (decreciente_noise.mp3)
SELECT 'Sierra', D.id, 'Sawtooth', 'Sierra', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/decreciente_noise.mp3'
UNION ALL
SELECT 'Creciente', D.id, 'Increasing', 'Creciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/decreciente_noise.mp3'
UNION ALL
SELECT 'Constante', D.id, 'Constant', 'Constante', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/decreciente_noise.mp3'
UNION ALL
SELECT 'Triangular', D.id, 'Triangular', 'Triangular', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/decreciente_noise.mp3'
UNION ALL
SELECT 'Pulso/Cuadrada', D.id, 'Pulse/Square', 'Pulso/Cuadrada', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/decreciente_noise.mp3'
UNION ALL
SELECT 'Decreciente', D.id, 'Decreasing', 'Decreciente', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/decreciente_noise.mp3'

UNION ALL

-- Choices para funciones con ruido tipo 1 (cuadrada_noise.mp3)
SELECT 'Constante', D.id, 'Constant', 'Constante', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadrada_noise.mp3'
UNION ALL
SELECT 'Triangular', D.id, 'Triangular', 'Triangular', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadrada_noise.mp3'
UNION ALL
SELECT 'Creciente', D.id, 'Increasing', 'Creciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadrada_noise.mp3'
UNION ALL
SELECT 'Sierra', D.id, 'Sawtooth', 'Sierra', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadrada_noise.mp3'
UNION ALL
SELECT 'Pulso/Cuadrada', D.id, 'Pulse/Square', 'Pulso/Cuadrada', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadrada_noise.mp3'
UNION ALL
SELECT 'Decreciente', D.id, 'Decreasing', 'Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadrada_noise.mp3'

UNION ALL

-- Choices para funciones con ruido tipo 1 (sierra_noise.mp3)
SELECT 'Triangular', D.id, 'Triangular', 'Triangular', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/sierra_noise.mp3'
UNION ALL
SELECT 'Creciente', D.id, 'Increasing', 'Creciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/sierra_noise.mp3'
UNION ALL
SELECT 'Constante', D.id, 'Constant', 'Constante', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/sierra_noise.mp3'
UNION ALL
SELECT 'Sierra', D.id, 'Sawtooth', 'Sierra', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/sierra_noise.mp3'
UNION ALL
SELECT 'Pulso/Cuadrada', D.id, 'Pulse/Square', 'Pulso/Cuadrada', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/sierra_noise.mp3'
UNION ALL
SELECT 'Decreciente', D.id, 'Decreasing', 'Decreciente', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/sierra_noise.mp3'

UNION ALL

-- Choices para funciones con ruido tipo 2 (coseno_noise.mp3)
SELECT 'Seno', D.id, 'Sine', 'Seno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/coseno_noise.mp3'
UNION ALL
SELECT 'Cuadr�tica', D.id, 'Quadratic', 'Cuadr�tica', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/coseno_noise.mp3'
UNION ALL
SELECT 'Coseno', D.id, 'Cosine', 'Coseno', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/coseno_noise.mp3'
UNION ALL
SELECT 'C�bica', D.id, 'Cubic', 'C�bica', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/coseno_noise.mp3'

UNION ALL

-- Choices para funciones con ruido tipo 2 (cubica_noise.mp3)
SELECT 'C�bica', D.id, 'Cubic', 'C�bica', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cubica_noise.mp3'
UNION ALL
SELECT 'Seno', D.id, 'Sine', 'Seno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cubica_noise.mp3'
UNION ALL
SELECT 'Coseno', D.id, 'Cosine', 'Coseno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cubica_noise.mp3'
UNION ALL
SELECT 'Cuadr�tica', D.id, 'Quadratic', 'Cuadr�tica', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cubica_noise.mp3'

UNION ALL

-- Choices para funciones con ruido tipo 2 (cuadratica_noise.mp3)
SELECT 'Coseno', D.id, 'Cosine', 'Coseno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica_noise.mp3'
UNION ALL
SELECT 'Cuadr�tica', D.id, 'Quadratic', 'Cuadr�tica', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica_noise.mp3'
UNION ALL
SELECT 'Seno', D.id, 'Sine', 'Seno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica_noise.mp3'
UNION ALL
SELECT 'C�bica', D.id, 'Cubic', 'C�bica', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica_noise.mp3'

UNION ALL

-- Choices para funciones con ruido tipo 2 (seno_noise.mp3)
SELECT 'Seno', D.id, 'Sine', 'Seno', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/seno_noise.mp3'
UNION ALL
SELECT 'Coseno', D.id, 'Cosine', 'Coseno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/seno_noise.mp3'
UNION ALL
SELECT 'C�bica', D.id, 'Cubic', 'C�bica', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/seno_noise.mp3'
UNION ALL
SELECT 'Cuadr�tica', D.id, 'Quadratic', 'Cuadr�tica', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/seno_noise.mp3'

UNION ALL

-- Choices para funciones con ruido tipo 2 (cuadratica2_noise.mp3)
SELECT 'Cuadr�tica', D.id, 'Quadratic', 'Cuadr�tica', TRUE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica2_noise.mp3'
UNION ALL
SELECT 'Coseno', D.id, 'Cosine', 'Coseno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica2_noise.mp3'
UNION ALL
SELECT 'Seno', D.id, 'Sine', 'Seno', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica2_noise.mp3'
UNION ALL
SELECT 'C�bica', D.id, 'Cubic', 'C�bica', FALSE
FROM `trainingApp_trainingquestion` D WHERE D.`deploy_sound` = 'trainingApp/sound/cuadratica2_noise.mp3'

UNION ALL

-- Combinaciones de funciones Tipo 3 (Cre-Cte-Decr_sound.mp3) - Requiere JOIN para el bloque
SELECT 'Creciente, Constante, Decreciente', D.id, 'Increasing, Constant, Decreasing', 'Creciente, Constante, Decreciente', TRUE
FROM `trainingApp_trainingquestion` D
INNER JOIN `trainingApp_trainingblock` B ON D.block_id = B.id
WHERE D.`deploy_sound` = 'trainingApp/sound/Cre-Cte-Decr_sound.mp3' AND B.`name_block` = 'Funciones Tipo 3'
UNION ALL
SELECT 'Constante, Creciente, Decreciente', D.id, 'Constant, Increasing, Decreasing', 'Constante, Creciente, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D
INNER JOIN `trainingApp_trainingblock` B ON D.block_id = B.id
WHERE D.`deploy_sound` = 'trainingApp/sound/Cre-Cte-Decr_sound.mp3' AND B.`name_block` = 'Funciones Tipo 3'
UNION ALL
SELECT 'Decreciente, Constante, Decreciente', D.id, 'Decreasing, Constant, Decreasing', 'Decreciente, Constante, Decreciente', FALSE
FROM `trainingApp_trainingquestion` D
INNER JOIN `trainingApp_trainingblock` B ON D.block_id = B.id
WHERE D.`deploy_sound` = 'trainingApp/sound/Cre-Cte-Decr_sound.mp3' AND B.`name_block` = 'Funciones Tipo 3'
UNION ALL
SELECT 'Constante, Decreciente, Creciente', D.id, 'Constant, Decreasing, Increasing', 'Constante, Decreciente, Creciente', FALSE
FROM `trainingApp_trainingquestion` D
INNER JOIN `trainingApp_trainingblock` B ON D.block_id = B.id
WHERE D.`deploy_sound` = 'trainingApp/sound/Cre-Cte-Decr_sound.mp3' AND B.`name_block` = 'Funciones Tipo 3'
UNION ALL
SELECT 'Ninguna de las anteriores', D.id, 'None of the above', 'Ninguna de las anteriores', FALSE
FROM `trainingApp_trainingquestion` D
INNER JOIN `trainingApp_trainingblock` B ON D.block_id = B.id
WHERE D.`deploy_sound` = 'trainingApp/sound/Cre-Cte-Decr_sound.mp3' AND B.`name_block` = 'Funciones Tipo 3';

-- ========================================
-- TRAINEE GROUP (trainingApp_traineegroup)
-- ========================================
INSERT INTO `trainingApp_traineegroup` (`name_group`, `description`)
VALUES ('Testing Group', 'Grupo de prueba para desarrollo y testing');

-- ========================================
-- COURSE (trainingApp_course)
-- ========================================
INSERT INTO `trainingApp_course` (
    `name_course`, `description`, `pub_date`, `modification_date`, 
    `state_course`, `required_average_score`, `final_exam_passing_score`,
    `name_course_en`, `name_course_es`, `description_en`, `description_es`
) VALUES (
    'Introducción a Funciones',
    'Curso completo sobre identificación y análisis de funciones matemáticas',
    '2024-04-24 17:16:05.850594',
    '2024-04-24 17:16:05.850594',
    'Active',
    70.00,
    70.00,
    'Introduction to Functions',
    'Introducción a Funciones',
    'Complete course on identification and analysis of mathematical functions',
    'Curso completo sobre identificación y análisis de funciones matemáticas'
);

-- ========================================
-- COURSE-TRAINING RELATIONSHIPS (trainingApp_coursetraining)
-- ========================================
INSERT INTO `trainingApp_coursetraining` (`course_id`, `training_id`, `order`)
SELECT C.id, T.id, 1
FROM `trainingApp_course` C, `trainingApp_training` T
WHERE C.`name_course` = 'Introducción a Funciones' AND T.`name_training` = 'Entrenamiento de muestra'
UNION ALL
SELECT C.id, T.id, 2
FROM `trainingApp_course` C, `trainingApp_training` T
WHERE C.`name_course` = 'Introducción a Funciones' AND T.`name_training` = 'Funciones Matemáticas'
UNION ALL
SELECT C.id, T.id, 3
FROM `trainingApp_course` C, `trainingApp_training` T
WHERE C.`name_course` = 'Introducción a Funciones' AND T.`name_training` = 'Funciones Matemáticas - Ejercitación'
UNION ALL
SELECT C.id, T.id, 4
FROM `trainingApp_course` C, `trainingApp_training` T
WHERE C.`name_course` = 'Introducción a Funciones' AND T.`name_training` = 'Funciones + Ruido';

-- ========================================
-- COURSE-GROUP RELATIONSHIPS (trainingApp_course_groups)
-- ========================================
INSERT INTO `trainingApp_course_groups` (`course_id`, `traineegroup_id`)
SELECT C.id, G.id
FROM `trainingApp_course` C, `trainingApp_traineegroup` G
WHERE C.`name_course` = 'Introducción a Funciones' AND G.`name_group` = 'Testing Group';
